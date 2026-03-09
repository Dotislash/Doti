from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field
from ulid import ULID


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_run_id() -> str:
    return f"run_{ULID()}"


def _new_message_id() -> str:
    return f"msg_{ULID()}"


class RunState(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class RunContext(BaseModel):
    run_id: str = Field(default_factory=_new_run_id)
    conversation_id: str = "main"
    state: RunState = RunState.queued
    created_at: datetime = Field(default_factory=_utcnow)


class Message(BaseModel):
    message_id: str = Field(default_factory=_new_message_id)
    conversation_id: str = "main"
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime = Field(default_factory=_utcnow)
