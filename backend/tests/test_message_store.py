"""Tests for JSONL MessageStore."""

import json

import pytest

from app.storage.message_store import MessageStore


@pytest.fixture
def store(tmp_path):
    return MessageStore(base_dir=str(tmp_path))


async def test_append_and_load(store):
    await store.append("msg_1", "user", "hello")
    await store.append("msg_2", "assistant", "hi there")

    messages = await store.load_all()
    assert len(messages) == 2
    assert messages[0]["id"] == "msg_1"
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "hello"
    assert messages[1]["id"] == "msg_2"
    assert messages[1]["role"] == "assistant"


async def test_load_recent(store):
    for i in range(10):
        await store.append(f"msg_{i}", "user", f"message {i}")

    recent = await store.load_recent(3)
    assert len(recent) == 3
    assert recent[0]["id"] == "msg_7"
    assert recent[2]["id"] == "msg_9"


async def test_load_empty(store):
    messages = await store.load_all()
    assert messages == []

    recent = await store.load_recent(10)
    assert recent == []


async def test_jsonl_format(store):
    await store.append("msg_1", "user", "test")

    with open(store.store_path) as f:
        lines = f.readlines()

    assert len(lines) == 1
    data = json.loads(lines[0])
    assert set(data.keys()) == {"id", "role", "content", "ts"}
    assert isinstance(data["ts"], int)


async def test_unicode_content(store):
    await store.append("msg_1", "user", "你好世界 🌍")
    messages = await store.load_all()
    assert messages[0]["content"] == "你好世界 🌍"
