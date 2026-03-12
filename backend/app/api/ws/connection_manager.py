from __future__ import annotations

from fastapi import WebSocket
from loguru import logger

from pydantic import BaseModel


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._seq: dict[WebSocket, int] = {}

    @property
    def active_count(self) -> int:
        return len(self._connections)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        self._seq[ws] = 0
        logger.info("WS connected (active={})", self.active_count)

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        self._seq.pop(ws, None)
        logger.info("WS disconnected (active={})", self.active_count)

    async def send(self, ws: WebSocket, envelope: BaseModel) -> None:
        data = envelope.model_dump(mode="json")
        data["event_id"] = self._next_event_id(ws)
        await ws.send_json(data)

    async def broadcast(self, envelope: BaseModel) -> None:
        for ws in list(self._connections):
            await self.send(ws, envelope)

    def _next_event_id(self, ws: WebSocket) -> str:
        seq = self._seq.get(ws, 0) + 1
        self._seq[ws] = seq
        return f"evt_{seq}"
