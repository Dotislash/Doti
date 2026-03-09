"""Tests for the WebSocket endpoint with mocked LLM provider."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ws_hello(client):
    with client.websocket_connect("/ws") as ws:
        data = ws.receive_json()
        assert data["type"] == "server.hello"
        assert data["payload"]["protocol_version"] == "1.0"


def _consume_history_sync(ws):
    """Read and discard the history.sync message sent after server.hello."""
    msg = ws.receive_json()
    assert msg["type"] == "history.sync"
    return msg


async def _fake_stream(_messages):
    """Mock stream that yields tokens."""
    for token in ["Hello", " world", "!"]:
        yield token


def test_ws_chat_send_streaming(client):
    with patch("app.api.ws.router._get_provider") as mock_get, \
         patch("app.api.ws.router._get_registry") as mock_reg:
        mock_provider = AsyncMock()
        mock_provider.stream_chat = _fake_stream
        mock_get.return_value = mock_provider

        # Empty registry so runtime falls back to simple streaming
        from app.tools.registry import ToolRegistry
        mock_reg.return_value = ToolRegistry()

        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # server.hello
            _consume_history_sync(ws)  # history.sync

            ws.send_json({
                "type": "chat.send",
                "event_id": "evt_1",
                "ts": 1709000000,
                "payload": {
                    "content": "hello",
                    "client_msg_id": "cmsg_1",
                },
            })

            # run.state(queued)
            msg = ws.receive_json()
            assert msg["type"] == "run.state"
            assert msg["payload"]["state"] == "queued"

            # run.state(running)
            msg = ws.receive_json()
            assert msg["type"] == "run.state"
            assert msg["payload"]["state"] == "running"

            # chat.delta tokens
            deltas = []
            while True:
                msg = ws.receive_json()
                if msg["type"] == "chat.delta":
                    deltas.append(msg["payload"]["delta"])
                elif msg["type"] == "chat.final":
                    assert msg["payload"]["content"] == "Hello world!"
                    break

            assert deltas == ["Hello", " world", "!"]

            # run.state(completed)
            msg = ws.receive_json()
            assert msg["type"] == "run.state"
            assert msg["payload"]["state"] == "completed"


def test_ws_invalid_message(client):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # server.hello
        _consume_history_sync(ws)  # history.sync
        ws.send_text('{"bad": "message"}')
        resp = ws.receive_json()
        assert resp["type"] == "error"
        assert resp["payload"]["code"] == "invalid_message"


def test_ws_history_sync(client):
    """Verify history.sync is sent after server.hello."""
    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "server.hello"
        history = ws.receive_json()
        assert history["type"] == "history.sync"
        assert "messages" in history["payload"]
        assert isinstance(history["payload"]["messages"], list)


def test_rest_main_messages(client):
    """Test REST endpoint for main messages."""
    r = client.get("/api/v1/main/messages")
    assert r.status_code == 200
    data = r.json()
    assert "messages" in data
    assert "has_more" in data
