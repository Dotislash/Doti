"""REST API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.models import Thread, ThreadType

router = APIRouter(prefix="/api/v1")

# Stores injected at app startup
_message_store = None
_thread_store = None


def set_stores(message_store, thread_store) -> None:
    global _message_store, _thread_store
    _message_store = message_store
    _thread_store = thread_store


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


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
