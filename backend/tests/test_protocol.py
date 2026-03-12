"""Tests for WS protocol types and parsing."""

import json

from app.api.ws.protocol import (
    ChatSendEnvelope,
    ClientHelloEnvelope,
    ServerHelloEnvelope,
    ServerHelloPayload,
    parse_client_message,
)
from app.core.models import RunState


def test_parse_client_hello():
    raw = json.dumps({
        "type": "client.hello",
        "event_id": "evt_1",
        "ts": 1709000000,
        "payload": {"protocol_version": "1.0"},
    })
    msg = parse_client_message(raw)
    assert isinstance(msg, ClientHelloEnvelope)
    assert msg.payload.protocol_version == "1.0"
    assert msg.payload.client_id is None


def test_parse_chat_send():
    raw = json.dumps({
        "type": "chat.send",
        "event_id": "evt_2",
        "ts": 1709000000,
        "payload": {
            "content": "hello",
            "client_msg_id": "cmsg_1",
        },
    })
    msg = parse_client_message(raw)
    assert isinstance(msg, ChatSendEnvelope)
    assert msg.payload.content == "hello"
    assert msg.payload.conversation_id == "main"


def test_parse_invalid_message():
    import pytest
    with pytest.raises(ValueError):
        parse_client_message('{"type": "unknown", "payload": {}}')


def test_server_envelope_serialization():
    env = ServerHelloEnvelope(
        payload=ServerHelloPayload(protocol_version="1.0", server_id="test"),
    )
    data = env.model_dump(mode="json")
    assert data["type"] == "server.hello"
    assert data["payload"]["protocol_version"] == "1.0"
    assert "event_id" in data
    assert "ts" in data


def test_run_state_enum():
    assert RunState.queued == "queued"
    assert RunState.completed.value == "completed"


def test_chat_send_defaults():
    raw = json.dumps({
        "type": "chat.send",
        "event_id": "evt_3",
        "ts": 1709000000,
        "payload": {"content": "hi", "client_msg_id": "c1"},
    })
    msg = parse_client_message(raw)
    assert msg.payload.conversation_id == "main"
