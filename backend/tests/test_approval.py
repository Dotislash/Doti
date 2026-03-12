import asyncio
from unittest.mock import AsyncMock

import pytest

from app.agent.conversation import ConversationManager
from app.agent.provider_client import StreamResult, ToolCallChunk
from app.agent.runtime import ApprovalGate, execute_run
from app.api.ws.protocol import ChatFinalEnvelope, RunStateEnvelope, ToolRequestEnvelope, ToolResultEnvelope
from app.core.models import RunContext, RunState
from app.tools.base import BaseTool, RiskLevel, ToolResult
from app.tools.registry import ToolRegistry


class MockHighRiskTool(BaseTool):
    def __init__(self) -> None:
        self.execute_mock = AsyncMock(return_value=ToolResult(output="executed"))

    @property
    def name(self):
        return "dangerous_tool"

    @property
    def description(self):
        return "A test tool"

    @property
    def parameters(self):
        return {"type": "object", "properties": {"x": {"type": "string"}}}

    @property
    def risk_level(self):
        return RiskLevel.high

    async def execute(self, **kwargs):
        return await self.execute_mock(**kwargs)


async def _resolve_when_pending(gate: ApprovalGate, approval_id: str, approved: bool) -> None:
    while not gate.resolve(approval_id, approved):
        await asyncio.sleep(0)


def _build_provider_mock() -> AsyncMock:
    provider = AsyncMock()
    provider.chat_with_tools = AsyncMock(
        side_effect=[
            StreamResult(
                content="",
                tool_calls=[
                    ToolCallChunk(
                        id="call_1",
                        name="dangerous_tool",
                        arguments='{"x":"value"}',
                    )
                ],
            ),
            StreamResult(content="done", tool_calls=[]),
        ]
    )
    return provider


@pytest.mark.asyncio
async def test_approval_gate_resolve_approved():
    gate = ApprovalGate()
    fut = gate.create("apr_1")

    resolved = gate.resolve("apr_1", True)

    assert resolved is True
    assert fut.done()
    assert fut.result() is True


@pytest.mark.asyncio
async def test_approval_gate_resolve_denied():
    gate = ApprovalGate()
    fut = gate.create("apr_1")

    resolved = gate.resolve("apr_1", False)

    assert resolved is True
    assert fut.done()
    assert fut.result() is False


@pytest.mark.asyncio
async def test_approval_gate_resolve_unknown():
    gate = ApprovalGate()

    resolved = gate.resolve("apr_missing", True)

    assert resolved is False


@pytest.mark.asyncio
async def test_approval_gate_resolve_twice():
    gate = ApprovalGate()
    gate.create("apr_1")

    first = gate.resolve("apr_1", True)
    second = gate.resolve("apr_1", True)

    assert first is True
    assert second is False


@pytest.mark.asyncio
async def test_execute_run_with_gate_approved():
    provider = _build_provider_mock()
    conversations = ConversationManager()
    registry = ToolRegistry()
    tool = MockHighRiskTool()
    registry.register(tool)
    gate = ApprovalGate()
    run = RunContext(conversation_id="conv_approved")

    events = []
    pending_resolvers = []
    async for envelope in execute_run(
        run=run,
        user_message="run tool",
        provider=provider,
        conversations=conversations,
        registry=registry,
        gate=gate,
    ):
        events.append(envelope)
        if isinstance(envelope, ToolRequestEnvelope):
            pending_resolvers.append(
                asyncio.create_task(
                    _resolve_when_pending(gate, envelope.payload.approval_id, True)
                )
            )

    if pending_resolvers:
        await asyncio.gather(*pending_resolvers)

    assert any(isinstance(e, ToolRequestEnvelope) for e in events)
    assert any(isinstance(e, ToolResultEnvelope) for e in events)
    assert any(isinstance(e, ChatFinalEnvelope) for e in events)
    assert tool.execute_mock.await_count == 1
    tool.execute_mock.assert_awaited_once_with(x="value")
    assert provider.chat_with_tools.await_count == 2

    tool_result = next(e for e in events if isinstance(e, ToolResultEnvelope))
    assert tool_result.payload.result == "executed"
    assert tool_result.payload.is_error is False

    assert run.state == RunState.completed
    assert isinstance(events[-1], RunStateEnvelope)
    assert events[-1].payload.state == RunState.completed


@pytest.mark.asyncio
async def test_execute_run_with_gate_denied():
    provider = _build_provider_mock()
    conversations = ConversationManager()
    registry = ToolRegistry()
    tool = MockHighRiskTool()
    registry.register(tool)
    gate = ApprovalGate()
    run = RunContext(conversation_id="conv_denied")

    events = []
    pending_resolvers = []
    async for envelope in execute_run(
        run=run,
        user_message="run tool",
        provider=provider,
        conversations=conversations,
        registry=registry,
        gate=gate,
    ):
        events.append(envelope)
        if isinstance(envelope, ToolRequestEnvelope):
            pending_resolvers.append(
                asyncio.create_task(
                    _resolve_when_pending(gate, envelope.payload.approval_id, False)
                )
            )

    if pending_resolvers:
        await asyncio.gather(*pending_resolvers)

    assert any(isinstance(e, ToolRequestEnvelope) for e in events)
    assert any(isinstance(e, ToolResultEnvelope) for e in events)
    assert tool.execute_mock.await_count == 0
    assert provider.chat_with_tools.await_count == 2

    tool_result = next(e for e in events if isinstance(e, ToolResultEnvelope))
    assert "denied" in tool_result.payload.result.lower()
    assert tool_result.payload.is_error is True


@pytest.mark.asyncio
async def test_execute_run_without_gate_auto_approves():
    provider = _build_provider_mock()
    conversations = ConversationManager()
    registry = ToolRegistry()
    tool = MockHighRiskTool()
    registry.register(tool)
    run = RunContext(conversation_id="conv_no_gate")

    events = [
        envelope
        async for envelope in execute_run(
            run=run,
            user_message="run tool",
            provider=provider,
            conversations=conversations,
            registry=registry,
            gate=None,
        )
    ]

    assert any(isinstance(e, ToolRequestEnvelope) for e in events)
    assert any(isinstance(e, ToolResultEnvelope) for e in events)
    assert any(isinstance(e, ChatFinalEnvelope) for e in events)
    assert tool.execute_mock.await_count == 1
    tool.execute_mock.assert_awaited_once_with(x="value")
    assert provider.chat_with_tools.await_count == 2
