"""Tests for ThreadStore JSONL persistence."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.storage.thread_store import ThreadStore


@pytest.fixture
def store(tmp_path):
    return ThreadStore(base_dir=tmp_path)


def _thread_payload(thread_id: str = "thr_1") -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "thread_id": thread_id,
        "title": "Test thread",
        "thread_type": "task",
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }


async def test_create_and_list(store):
    thread = _thread_payload("thr_create_list")

    await store.create(thread)
    threads = await store.list_threads()

    assert len(threads) == 1
    assert threads[0]["thread_id"] == "thr_create_list"


async def test_get(store):
    thread = _thread_payload("thr_get")
    await store.create(thread)

    found = await store.get("thr_get")

    assert found is not None
    assert found["thread_id"] == "thr_get"


async def test_get_not_found(store):
    found = await store.get("missing")
    assert found is None


async def test_delete(store):
    await store.create(_thread_payload("thr_delete"))

    deleted = await store.delete("thr_delete")
    threads = await store.list_threads()

    assert deleted is True
    assert threads == []


async def test_delete_not_found(store):
    deleted = await store.delete("missing")
    assert deleted is False


async def test_append_and_load_messages(store):
    await store.create(_thread_payload("thr_msgs"))
    await store.append_message("thr_msgs", "msg_1", "user", "hello")
    await store.append_message("thr_msgs", "msg_2", "assistant", "hi")

    messages = await store.load_thread_messages("thr_msgs")

    assert len(messages) == 2
    assert messages[0]["id"] == "msg_1"
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "hello"
    assert messages[1]["id"] == "msg_2"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "hi"


async def test_update_status(store):
    await store.create(_thread_payload("thr_status"))

    await store.update_status("thr_status", "paused")
    updated = await store.get("thr_status")

    assert updated is not None
    assert updated["status"] == "paused"
