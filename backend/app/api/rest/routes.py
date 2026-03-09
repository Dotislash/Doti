"""REST API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.api.ws import router as ws_router_module
from app.core.config.runtime_config import RuntimeConfig
from app.core.models import Thread, ThreadType

router = APIRouter(prefix="/api/v1")

# Stores injected at app startup
_message_store = None
_thread_store = None
_runtime_config: RuntimeConfig | None = None

KNOWN_MODELS = [
    "anthropic/claude-sonnet-4-5",
    "anthropic/claude-opus-4-5",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "openai/o1",
    "openai/o3-mini",
]


def set_stores(message_store, thread_store) -> None:
    global _message_store, _thread_store
    _message_store = message_store
    _thread_store = thread_store


def set_config(config: RuntimeConfig) -> None:
    global _runtime_config
    _runtime_config = config
    ws_router_module._config = config
    ws_router_module._provider = None


def _get_runtime_config() -> RuntimeConfig:
    global _runtime_config
    if _runtime_config is None:
        _runtime_config = ws_router_module._get_config()
    return _runtime_config


def _mask_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    suffix = api_key[-4:]
    return f"sk-...****{suffix}"


def _public_config(config: RuntimeConfig) -> dict:
    data = config.model_dump()
    data.pop("workspace", None)
    data.pop("host", None)
    data.pop("port", None)
    data["api_key"] = _mask_api_key(config.api_key)
    return data


class ConfigUpdateRequest(BaseModel):
    model: str | None = None
    api_key: str | None = None
    api_base: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/config")
async def get_config() -> dict:
    config = _get_runtime_config()
    return _public_config(config)


@router.patch("/config")
async def update_config(body: ConfigUpdateRequest) -> dict:
    config = _get_runtime_config()
    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(config, field, value)
    set_config(config)
    return _public_config(config)


@router.get("/config/models")
async def list_known_models() -> dict[str, list[str]]:
    return {"models": KNOWN_MODELS}


@router.get("/main/messages")
async def get_main_messages(
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    if _message_store is None:
        return {"messages": [], "has_more": False}

    all_msgs = await _message_store.load_all()
    total = len(all_msgs)
    messages = all_msgs[-limit:] if total > limit else all_msgs
    return {
        "messages": messages,
        "has_more": total > limit,
    }


# --- Threads ---


class ThreadCreateRequest(BaseModel):
    title: str | None = None
    thread_type: str = "task"


@router.get("/threads")
async def list_threads() -> dict:
    if _thread_store is None:
        return {"threads": []}
    threads = await _thread_store.list_threads()
    return {"threads": threads}


@router.post("/threads", status_code=201)
async def create_thread(body: ThreadCreateRequest) -> dict:
    if _thread_store is None:
        raise HTTPException(500, "Thread store not initialized")

    thread = Thread(
        title=body.title,
        thread_type=ThreadType(body.thread_type),
    )
    data = {
        "thread_id": thread.thread_id,
        "title": thread.title,
        "thread_type": thread.thread_type.value,
        "status": thread.status.value,
        "created_at": thread.created_at.isoformat(),
        "updated_at": thread.updated_at.isoformat(),
    }
    await _thread_store.create(data)
    return data


@router.get("/threads/{thread_id}")
async def get_thread(thread_id: str) -> dict:
    if _thread_store is None:
        raise HTTPException(500, "Thread store not initialized")

    thread = await _thread_store.get(thread_id)
    if thread is None:
        raise HTTPException(404, "Thread not found")
    return thread


@router.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str) -> dict:
    if _thread_store is None:
        raise HTTPException(500, "Thread store not initialized")

    deleted = await _thread_store.delete(thread_id)
    if not deleted:
        raise HTTPException(404, "Thread not found")
    return {"deleted": True}


@router.get("/threads/{thread_id}/messages")
async def get_thread_messages(
    thread_id: str,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    if _thread_store is None:
        raise HTTPException(500, "Thread store not initialized")

    thread = await _thread_store.get(thread_id)
    if thread is None:
        raise HTTPException(404, "Thread not found")

    messages = await _thread_store.load_thread_messages(thread_id, limit)
    return {"messages": messages}
