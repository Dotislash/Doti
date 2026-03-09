"""Run lifecycle orchestrator — manages a single agent run."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from loguru import logger

from app.agent.conversation import ConversationManager
from app.agent.provider_client import ProviderClient
from app.api.ws.protocol import (
    ChatDeltaEnvelope,
    ChatDeltaPayload,
    ChatFinalEnvelope,
    ChatFinalPayload,
    RunStateEnvelope,
    RunStatePayload,
)
from app.core.models import Message, RunContext, RunState


async def execute_run(
    run: RunContext,
    user_message: str,
    provider: ProviderClient,
    conversations: ConversationManager,
) -> AsyncGenerator[ChatDeltaEnvelope | ChatFinalEnvelope | RunStateEnvelope, None]:
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
    full_content = ""

    try:
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

        # Save assistant response to history
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

    except Exception:
        logger.exception("Run {} failed", rid)
        run.state = RunState.failed
        yield RunStateEnvelope(payload=RunStatePayload(
            run_id=rid, conversation_id=cid, state=RunState.failed,
        ))
