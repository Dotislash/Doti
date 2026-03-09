from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

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


class ErrorPayload(BaseModel):
    code: Literal[
        "invalid_message",
        "conversation_busy",
        "internal_error",
        "provider_error",
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


ClientEnvelope = Annotated[
    ClientHelloEnvelope | ChatSendEnvelope,
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
    | ErrorEnvelope,
    Field(discriminator="type"),
]


_client_adapter = TypeAdapter(ClientEnvelope)


def parse_client_message(raw: str) -> ClientEnvelope:
    try:
        return _client_adapter.validate_json(raw)
    except ValidationError as exc:
        raise ValueError("Invalid client message") from exc
