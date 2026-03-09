"""Run lifecycle orchestrator — manages a single agent run."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

from loguru import logger
from ulid import ULID

from app.agent.conversation import ConversationManager
from app.agent.provider_client import ProviderClient
from app.api.ws.protocol import (
    AgentThinkingEnvelope,
    AgentThinkingPayload,
    ChatDeltaEnvelope,
    ChatDeltaPayload,
    ChatFinalEnvelope,
    ChatFinalPayload,
    RunStateEnvelope,
    RunStatePayload,
    ToolRequestEnvelope,
    ToolRequestPayload,
    ToolResultEnvelope,
    ToolResultPayload,
)
from app.core.models import Message, RunContext, RunState
from app.tools.base import RiskLevel, ToolResult
from app.tools.registry import ToolRegistry

MAX_TOOL_ITERATIONS = 10


class ApprovalGate:
    """Manages pending tool approvals via asyncio Futures."""

    def __init__(self):
        self._pending: dict[str, asyncio.Future[bool]] = {}

    def create(self, approval_id: str) -> asyncio.Future[bool]:
        """Create a pending approval, returns a future to await."""
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending[approval_id] = fut
        return fut

    def resolve(self, approval_id: str, approved: bool) -> bool:
        """Resolve a pending approval. Returns True if found."""
        fut = self._pending.pop(approval_id, None)
        if fut is not None and not fut.done():
            fut.set_result(approved)
            return True
        return False


def _new_approval_id() -> str:
    return f"apr_{ULID()}"


async def execute_run(
    run: RunContext,
    user_message: str,
    provider: ProviderClient,
    conversations: ConversationManager,
    registry: ToolRegistry | None = None,
    gate: ApprovalGate | None = None,
) -> AsyncGenerator[
    AgentThinkingEnvelope | ChatDeltaEnvelope | ChatFinalEnvelope | RunStateEnvelope | ToolRequestEnvelope | ToolResultEnvelope,
    None,
]:
    """Execute a run: stream LLM response as protocol envelopes."""
    cid = run.conversation_id
    rid = run.run_id

    # Add user message to history
    await conversations.add_user_message(cid, user_message)

    # Signal: running
    run.state = RunState.running
    yield RunStateEnvelope(payload=RunStatePayload(
        run_id=rid, conversation_id=cid, state=RunState.running,
    ))

    messages = conversations.get_messages(cid)
    seq = 0

    try:
        openai_tools = registry.to_openai_tools() if registry is not None else []

        # Fallback mode: no tools registered, stream text directly.
        if not openai_tools:
            full_content = ""
            async for token in provider.stream_chat(messages):
                if token.startswith("[provider_error]"):
                    run.state = RunState.failed
                    yield RunStateEnvelope(payload=RunStatePayload(
                        run_id=rid, conversation_id=cid, state=RunState.failed,
                    ))
                    return

                seq += 1
                full_content += token
                yield ChatDeltaEnvelope(payload=ChatDeltaPayload(
                    conversation_id=cid, run_id=rid, seq=seq, delta=token,
                ))

            await conversations.add_assistant_message(cid, full_content)
            msg = Message(conversation_id=cid, role="assistant", content=full_content)
            yield ChatFinalEnvelope(payload=ChatFinalPayload(
                conversation_id=cid, run_id=rid,
                message_id=msg.message_id, content=full_content,
            ))

            run.state = RunState.completed
            yield RunStateEnvelope(payload=RunStatePayload(
                run_id=rid, conversation_id=cid, state=RunState.completed,
            ))
            return

        # Tool loop mode (ReAct-style).
        loop_messages: list[dict] = list(messages)
        for iteration in range(MAX_TOOL_ITERATIONS):
            result = await provider.chat_with_tools(loop_messages, openai_tools)

            if result.error:
                logger.error("Provider tool chat failed for run {}: {}", rid, result.error)
                run.state = RunState.failed
                yield RunStateEnvelope(payload=RunStatePayload(
                    run_id=rid, conversation_id=cid, state=RunState.failed,
                ))
                return

            if result.tool_calls:
                # Emit thinking content if the LLM produced reasoning alongside tool calls
                if result.content:
                    yield AgentThinkingEnvelope(payload=AgentThinkingPayload(
                        conversation_id=cid, run_id=rid,
                        content=result.content, iteration=iteration + 1,
                    ))

                assistant_tool_calls = []
                for tc in result.tool_calls:
                    assistant_tool_calls.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments,
                        },
                    })

                loop_messages.append({
                    "role": "assistant",
                    "content": result.content or None,
                    "tool_calls": assistant_tool_calls,
                })

                for tc in result.tool_calls:
                    tool_result = ToolResult(output="Tool execution failed", is_error=True)
                    should_execute = True
                    try:
                        arguments = json.loads(tc.arguments) if tc.arguments else {}
                        if not isinstance(arguments, dict):
                            raise ValueError("Tool arguments must be a JSON object")
                    except Exception:
                        arguments = {}
                        tool_result = ToolResult(
                            output="Invalid tool arguments JSON; expected object",
                            is_error=True,
                        )
                        risk_level = RiskLevel.high
                        should_execute = False
                    else:
                        tool = registry.get(tc.name) if registry is not None else None
                        risk_level = tool.risk_level if tool is not None else RiskLevel.critical

                    approval_id = _new_approval_id()
                    yield ToolRequestEnvelope(payload=ToolRequestPayload(
                        approval_id=approval_id,
                        conversation_id=cid,
                        tool_name=tc.name,
                        arguments=arguments,
                        risk_level=risk_level.value,
                    ))

                    if should_execute and risk_level in {RiskLevel.high, RiskLevel.critical}:
                        if gate is None:
                            logger.info(
                                "No approval gate; proceeding tool call run={} tool={} approval_id={}",
                                rid,
                                tc.name,
                                approval_id,
                            )
                        else:
                            logger.info(
                                "Waiting for tool approval run={} tool={} approval_id={}",
                                rid,
                                tc.name,
                                approval_id,
                            )
                            approved = await gate.create(approval_id)
                            if not approved:
                                logger.info(
                                    "Tool approval denied run={} tool={} approval_id={}",
                                    rid,
                                    tc.name,
                                    approval_id,
                                )
                                tool_result = ToolResult(
                                    output="Tool call denied by user",
                                    is_error=True,
                                )
                                should_execute = False
                            else:
                                logger.info(
                                    "Tool approval granted run={} tool={} approval_id={}",
                                    rid,
                                    tc.name,
                                    approval_id,
                                )

                    if should_execute:
                        try:
                            if registry is None:
                                raise KeyError(f"Tool not found: {tc.name}")
                            tool_result = await registry.execute(tc.name, arguments)
                        except Exception as exc:
                            tool_result = ToolResult(output=str(exc), is_error=True)

                    yield ToolResultEnvelope(payload=ToolResultPayload(
                        conversation_id=cid,
                        tool_name=tc.name,
                        result=tool_result.output,
                        is_error=tool_result.is_error,
                    ))

                    loop_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.name,
                        "content": tool_result.output,
                    })

                continue

            final_content = result.content
            if final_content:
                seq += 1
                yield ChatDeltaEnvelope(payload=ChatDeltaPayload(
                    conversation_id=cid, run_id=rid, seq=seq, delta=final_content,
                ))

            await conversations.add_assistant_message(cid, final_content)
            msg = Message(conversation_id=cid, role="assistant", content=final_content)
            yield ChatFinalEnvelope(payload=ChatFinalPayload(
                conversation_id=cid,
                run_id=rid,
                message_id=msg.message_id,
                content=final_content,
            ))

            run.state = RunState.completed
            yield RunStateEnvelope(payload=RunStatePayload(
                run_id=rid, conversation_id=cid, state=RunState.completed,
            ))
            return

        logger.error("Run {} exceeded max tool iterations ({})", rid, MAX_TOOL_ITERATIONS)
        run.state = RunState.failed
        yield RunStateEnvelope(payload=RunStatePayload(
            run_id=rid, conversation_id=cid, state=RunState.failed,
        ))
        return

    except Exception:
        logger.exception("Run {} failed", rid)
        run.state = RunState.failed
        yield RunStateEnvelope(payload=RunStatePayload(
            run_id=rid, conversation_id=cid, state=RunState.failed,
        ))
