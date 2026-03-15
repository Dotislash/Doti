from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.api.ws import handlers as h
from app.api.ws import protocol as p
from app.api.ws.connection_manager import ConnectionManager
from app.core.config.models import DotiConfig

router = APIRouter()


class ServerState:
    def __init__(self, config: DotiConfig):
        self.config = config
        self.conn_manager = ConnectionManager()
        self._provider = None
        self._store = None
        self._thread_store = None
        self._conversations = None
        self._registry = None
        self.active_runs = {}
        self.conversation_locks = {}
        self.approval_gates = {}
        self.run_tasks = set()

    def get_conversation_lock(self, cid: str):
        return self.conversation_locks.setdefault(cid, asyncio.Lock())

    def get_provider(self):
        if self._provider is None:
            from app.agent.provider_client import ProviderClient

            model, api_key, api_base = self.config.get_primary_model()
            max_tokens = (
                self.config.profile.primary.context.max_tokens
                if self.config.profile.primary
                else 4096
            )
            self._provider = ProviderClient(
                model=model,
                api_key=api_key,
                api_base=api_base,
                temperature=0.7,
                max_tokens=max_tokens,
            )
        return self._provider

    def get_store(self):
        if self._store is None:
            from app.storage.message_store import MessageStore

            self._store = MessageStore(base_dir=self.config.workspace)
        return self._store

    def get_thread_store(self):
        if self._thread_store is None:
            from app.storage.thread_store import ThreadStore

            self._thread_store = ThreadStore(base_dir=self.config.workspace)
        return self._thread_store

    def get_registry(self):
        if self._registry is None:
            from app.tools.registry import create_default_registry

            self._registry = create_default_registry(workspace=self.config.workspace)
        return self._registry

    async def get_conversations(self):
        if self._conversations is None:
            from app.agent.conversation import ConversationManager

            self._conversations = ConversationManager(
                store=self.get_store(),
                thread_store=self.get_thread_store(),
                workspace=self.config.workspace,
            )
            await self._conversations.load_history("main")
        return self._conversations

    def reset_provider(self):
        self._provider = None


_state: ServerState | None = None


def init_server_state(config: DotiConfig):
    global _state
    _state = ServerState(config)
    return _state


def get_server_state():
    if _state is None:
        raise RuntimeError("ServerState not initialized")
    return _state


HANDLERS = h.HANDLERS


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    state = get_server_state()
    if state.config.api_token and websocket.query_params.get("token", "") != state.config.api_token:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    await state.conn_manager.connect(websocket)
    try:
        await state.conn_manager.send(
            websocket,
            p.ServerHelloEnvelope(
                payload=p.ServerHelloPayload(protocol_version="1.0", server_id="doti-backend")
            ),
        )
        await state.conn_manager.send(websocket, await h.build_history_sync(state))
        while True:
            raw = await websocket.receive_text()
            try:
                msg = p.parse_client_message(raw)
            except ValueError:
                logger.warning("Invalid client message")
                await state.conn_manager.send(
                    websocket,
                    p.ErrorEnvelope(
                        payload=p.ErrorPayload(code="invalid_message", message="Invalid message")
                    ),
                )
                continue
            if msg.type == "client.hello":
                logger.info("Client hello: v={}", msg.payload.protocol_version)
                continue
            handler = HANDLERS.get(msg.type)
            if handler is not None:
                await handler(state, websocket, msg)
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    finally:
        state.conn_manager.disconnect(websocket)
