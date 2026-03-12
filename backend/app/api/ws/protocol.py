from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from ulid import ULID
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from app.core.models import RunState


def _new_event_id() -> str:
    return f"evt_{ULID()}"


def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


class ClientHelloPayload(BaseModel):
    protocol_version: str
    client_id: str | None = None


class ChatSendPayload(BaseModel):
    conversation_id: str = "main"
    content: str
    client_msg_id: str


class ServerHelloPayload(BaseModel):
    protocol_version: str
    server_id: str


class ChatDeltaPayload(BaseModel):
    conversation_id: str
    run_id: str
    seq: int
    delta: str


class ChatFinalPayload(BaseModel):
    conversation_id: str
    run_id: str
    message_id: str
    content: str


class RunStatePayload(BaseModel):
    run_id: str
    conversation_id: str
    state: RunState


class HistoryMessagePayload(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    ts: int


class HistorySyncPayload(BaseModel):
    conversation_id: str = "main"
    messages: list[HistoryMessagePayload]
    items: list[dict[str, Any]] = Field(default_factory=list)
    has_more: bool = False


class AgentThinkingPayload(BaseModel):
    conversation_id: str
    run_id: str
    content: str
    iteration: int


class ToolRequestPayload(BaseModel):
    approval_id: str
    conversation_id: str
    tool_name: str
    arguments: dict
    risk_level: str


class ToolResultPayload(BaseModel):
    conversation_id: str
    tool_name: str
    result: str
    is_error: bool = False


class ToolApprovePayload(BaseModel):
    approval_id: str
    approved: bool


class ThreadCreatePayload(BaseModel):
    title: str | None = None
    executor: str | None = None
    thread_type: Literal["task", "focus"] = "task"


class ThreadListPayload(BaseModel):
    pass


class ThreadDeletePayload(BaseModel):
    thread_id: str


class ThreadInfoPayload(BaseModel):
    thread_id: str
    title: str | None
    executor: str | None = None
    thread_type: str
    status: str
    created_at: str


class ThreadListResultPayload(BaseModel):
    threads: list[ThreadInfoPayload]


class ThreadUpdatedPayload(BaseModel):
    thread_id: str
    title: str | None = None
    executor: str | None = None
    status: str | None = None


class ExecutorListPayload(BaseModel):
    pass


class ExecutorStatusPayload(BaseModel):
    executor_id: str


class ExecutorAttachPayload(BaseModel):
    executor_id: str


class ExecutorDetachPayload(BaseModel):
    pass


class ExecutorListResultPayload(BaseModel):
    executors: list[dict]


class ExecutorStatusResultPayload(BaseModel):
    executor_id: str
    status: str
    endpoint: str | None = None


class ErrorPayload(BaseModel):
    code: Literal[
        "invalid_message",
        "conversation_busy",
        "internal_error",
        "provider_error",
        "thread_not_found",
        "executor_not_found",
        "executor_error",
    ]
    message: str
    run_id: str | None = None


class ClientHelloEnvelope(BaseModel):
    type: Literal["client.hello"] = "client.hello"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ClientHelloPayload


class ChatSendEnvelope(BaseModel):
    type: Literal["chat.send"] = "chat.send"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ChatSendPayload


class ThreadCreateEnvelope(BaseModel):
    type: Literal["thread.create"] = "thread.create"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ThreadCreatePayload


class ThreadListEnvelope(BaseModel):
    type: Literal["thread.list"] = "thread.list"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ThreadListPayload


class ThreadDeleteEnvelope(BaseModel):
    type: Literal["thread.delete"] = "thread.delete"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ThreadDeletePayload


class ExecutorListEnvelope(BaseModel):
    type: Literal["executor.list"] = "executor.list"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ExecutorListPayload


class ExecutorStatusEnvelope(BaseModel):
    type: Literal["executor.status"] = "executor.status"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ExecutorStatusPayload


class ExecutorAttachEnvelope(BaseModel):
    type: Literal["executor.attach"] = "executor.attach"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ExecutorAttachPayload


class ExecutorDetachEnvelope(BaseModel):
    type: Literal["executor.detach"] = "executor.detach"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ExecutorDetachPayload


class ToolApproveEnvelope(BaseModel):
    type: Literal["tool.approve"] = "tool.approve"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ToolApprovePayload


ClientEnvelope = Annotated[
    ClientHelloEnvelope
    | ChatSendEnvelope
    | ThreadCreateEnvelope
    | ThreadListEnvelope
    | ThreadDeleteEnvelope
    | ExecutorListEnvelope
    | ExecutorStatusEnvelope
    | ExecutorAttachEnvelope
    | ExecutorDetachEnvelope
    | ToolApproveEnvelope,
    Field(discriminator="type"),
]


class ServerHelloEnvelope(BaseModel):
    type: Literal["server.hello"] = "server.hello"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ServerHelloPayload


class ChatDeltaEnvelope(BaseModel):
    type: Literal["chat.delta"] = "chat.delta"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ChatDeltaPayload


class ChatFinalEnvelope(BaseModel):
    type: Literal["chat.final"] = "chat.final"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ChatFinalPayload


class RunStateEnvelope(BaseModel):
    type: Literal["run.state"] = "run.state"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: RunStatePayload


class HistorySyncEnvelope(BaseModel):
    type: Literal["history.sync"] = "history.sync"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: HistorySyncPayload


class ThreadCreatedEnvelope(BaseModel):
    type: Literal["thread.created"] = "thread.created"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ThreadInfoPayload


class ThreadListResultEnvelope(BaseModel):
    type: Literal["thread.list_result"] = "thread.list_result"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ThreadListResultPayload


class ThreadUpdatedEnvelope(BaseModel):
    type: Literal["thread.updated"] = "thread.updated"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ThreadUpdatedPayload


class ExecutorListResultEnvelope(BaseModel):
    type: Literal["executor.list_result"] = "executor.list_result"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ExecutorListResultPayload


class ExecutorStatusResultEnvelope(BaseModel):
    type: Literal["executor.status_result"] = "executor.status_result"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ExecutorStatusResultPayload


class AgentThinkingEnvelope(BaseModel):
    type: Literal["agent.thinking"] = "agent.thinking"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: AgentThinkingPayload


class ToolRequestEnvelope(BaseModel):
    type: Literal["tool.request"] = "tool.request"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ToolRequestPayload


class ToolResultEnvelope(BaseModel):
    type: Literal["tool.result"] = "tool.result"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ToolResultPayload


class ErrorEnvelope(BaseModel):
    type: Literal["error"] = "error"
    event_id: str = Field(default_factory=_new_event_id)
    ts: int = Field(default_factory=_now_ts)
    payload: ErrorPayload


ServerEnvelope = Annotated[
    ServerHelloEnvelope
    | ChatDeltaEnvelope
    | ChatFinalEnvelope
    | RunStateEnvelope
    | HistorySyncEnvelope
    | ThreadCreatedEnvelope
    | ThreadListResultEnvelope
    | ThreadUpdatedEnvelope
    | ExecutorListResultEnvelope
    | ExecutorStatusResultEnvelope
    | AgentThinkingEnvelope
    | ToolRequestEnvelope
    | ToolResultEnvelope
    | ErrorEnvelope,
    Field(discriminator="type"),
]


_client_adapter = TypeAdapter(ClientEnvelope)


def parse_client_message(raw: str) -> ClientEnvelope:
    try:
        return _client_adapter.validate_json(raw)
    except ValidationError as exc:
        raise ValueError("Invalid client message") from exc
