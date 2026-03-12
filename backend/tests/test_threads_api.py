"""Tests for thread REST and WebSocket endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.api.rest import routes as rest_routes
from app.api.ws import router as ws_router


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DOTI_WORKSPACE", str(tmp_path))

    ws_router._config = None
    ws_router._store = None
    ws_router._thread_store = None
    ws_router._conversations = None
    rest_routes.set_stores(None, None)

    with TestClient(app) as test_client:
        yield test_client


def _consume_server_bootstrap(ws):
    hello = ws.receive_json()
    assert hello["type"] == "server.hello"

    history = ws.receive_json()
    assert history["type"] == "history.sync"


def test_list_threads_empty(client):
    response = client.get("/api/v1/threads")

    assert response.status_code == 200
    assert response.json() == {"threads": []}


def test_create_thread(client):
    response = client.post("/api/v1/threads", json={"title": "My thread", "thread_type": "task"})

    assert response.status_code == 201
    data = response.json()
    assert data["thread_id"].startswith("thr_")
    assert data["title"] == "My thread"
    assert data["thread_type"] == "task"
    assert data["status"] == "active"


def test_create_and_list(client):
    created = client.post("/api/v1/threads", json={"title": "Listed thread"})
    created_id = created.json()["thread_id"]

    response = client.get("/api/v1/threads")

    assert response.status_code == 200
    threads = response.json()["threads"]
    assert any(thread["thread_id"] == created_id for thread in threads)


def test_get_thread_not_found(client):
    response = client.get("/api/v1/threads/fake_id")

    assert response.status_code == 404
    assert response.json()["detail"] == "Thread not found"


def test_delete_thread_not_found(client):
    response = client.delete("/api/v1/threads/fake_id")

    assert response.status_code == 404
    assert response.json()["detail"] == "Thread not found"


def test_ws_thread_create(client):
    with client.websocket_connect("/ws") as ws:
        _consume_server_bootstrap(ws)

        ws.send_json({
            "type": "thread.create",
            "event_id": "evt_thread_create",
            "ts": 1709000000,
            "payload": {
                "title": "WS thread",
                "thread_type": "task",
            },
        })

        msg = ws.receive_json()

    assert msg["type"] == "thread.created"
    payload = msg["payload"]
    assert payload["thread_id"].startswith("thr_")
    assert payload["title"] == "WS thread"
    assert payload["thread_type"] == "task"
    assert payload["status"] == "active"


def test_ws_thread_list(client):
    created = client.post("/api/v1/threads", json={"title": "REST created thread", "thread_type": "task"})
    created_id = created.json()["thread_id"]

    with client.websocket_connect("/ws") as ws:
        _consume_server_bootstrap(ws)

        ws.send_json({
            "type": "thread.list",
            "event_id": "evt_thread_list",
            "ts": 1709000001,
            "payload": {},
        })

        msg = ws.receive_json()

    assert msg["type"] == "thread.list_result"
    threads = msg["payload"]["threads"]
    assert any(thread["thread_id"] == created_id for thread in threads)
