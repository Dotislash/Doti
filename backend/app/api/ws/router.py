"""WebSocket endpoint — connects clients to the agent runtime."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.agent.provider_client import ProviderClient
from app.agent.runtime import execute_run
from app.api.ws.connection_manager import ConnectionManager
from app.api.ws.protocol import (
    ErrorEnvelope,
    ErrorPayload,
    RunStateEnvelope,
    RunStatePayload,
    ServerHelloEnvelope,
    ServerHelloPayload,
    parse_client_message,
)
from app.core.config.runtime_config import RuntimeConfig
from app.core.models import RunContext, RunState

router = APIRouter()
manager = ConnectionManager()

# Lazy-initialized on first use
_provider: ProviderClient | None = None
_config: RuntimeConfig | None = None


def _get_config() -> RuntimeConfig:
    global _config
    if _config is None:
        _config = RuntimeConfig()
    return _config


def _get_provider() -> ProviderClient:
    global _provider
    if _provider is None:
        cfg = _get_config()
        _provider = ProviderClient(
            model=cfg.model,
            api_key=cfg.api_key,
            api_base=cfg.api_base,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
    return _provider


# Track active runs per conversation to enforce single-run constraint
_active_runs: dict[str, str] = {}  # conversation_id -> run_id


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        await manager.send(
            websocket,
            ServerHelloEnvelope(
                payload=ServerHelloPayload(
                    protocol_version="1.0",
                    server_id="doti-backend",
                ),
            ),
        )

        while True:
            raw = await websocket.receive_text()
            try:
                msg = parse_client_message(raw)
            except ValueError:
                logger.warning("Invalid client message")
                await manager.send(websocket, ErrorEnvelope(
                    payload=ErrorPayload(code="invalid_message", message="Invalid message"),
                ))
                continue

            if msg.type == "client.hello":
                logger.info("Client hello: v={}", msg.payload.protocol_version)
                continue

            if msg.type == "chat.send":
                cid = msg.payload.conversation_id
                content = msg.payload.content

                # Enforce single active run per conversation
                if cid in _active_runs:
                    await manager.send(websocket, ErrorEnvelope(
                        payload=ErrorPayload(
                            code="conversation_busy",
                            message="A run is already active",
                            run_id=_active_runs[cid],
                        ),
                    ))
                    continue

                run = RunContext(conversation_id=cid)
                _active_runs[cid] = run.run_id

                # Signal queued
                await manager.send(websocket, RunStateEnvelope(
                    payload=RunStatePayload(
                        run_id=run.run_id, conversation_id=cid, state=RunState.queued,
                    ),
                ))

                try:
                    async for envelope in execute_run(run, content, _get_provider()):
                        await manager.send(websocket, envelope)
                finally:
                    _active_runs.pop(cid, None)

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    finally:
        manager.disconnect(websocket)
