"""WebSocket endpoint — connects clients to the agent runtime."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.agent.conversation import ConversationManager
from app.agent.provider_client import ProviderClient
from app.agent.runtime import ApprovalGate, execute_run
from app.api.ws.connection_manager import ConnectionManager
from app.api.ws.protocol import (
    ErrorEnvelope,
    ErrorPayload,
    HistoryMessagePayload,
    HistorySyncEnvelope,
    HistorySyncPayload,
    RunStateEnvelope,
    RunStatePayload,
    ServerHelloEnvelope,
    ServerHelloPayload,
    ThreadCreatedEnvelope,
    ThreadInfoPayload,
    ThreadListResultEnvelope,
    ThreadListResultPayload,
    ThreadUpdatedEnvelope,
    ThreadUpdatedPayload,
    parse_client_message,
)
from app.core.config.runtime_config import RuntimeConfig
from app.core.models import RunContext, RunState, Thread, ThreadType
from app.storage.message_store import MessageStore
from app.storage.thread_store import ThreadStore
from app.tools.registry import ToolRegistry, create_default_registry

router = APIRouter()
manager = ConnectionManager()

# Lazy-initialized on first use
_provider: ProviderClient | None = None
_config: RuntimeConfig | None = None
_store: MessageStore | None = None
_thread_store: ThreadStore | None = None
_conversations: ConversationManager | None = None
_registry: ToolRegistry | None = None
_active_runs: dict[str, str] = {}  # conversation_id -> run_id
_approval_gates: dict[str, ApprovalGate] = {}  # conversation_id -> approval gate
_run_tasks: set[asyncio.Task[None]] = set()


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


def _get_store() -> MessageStore:
    global _store
    if _store is None:
        cfg = _get_config()
        _store = MessageStore(base_dir=cfg.workspace)
    return _store


def _get_thread_store() -> ThreadStore:
    global _thread_store
    if _thread_store is None:
        cfg = _get_config()
        _thread_store = ThreadStore(base_dir=cfg.workspace)
    return _thread_store


def _get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = create_default_registry()
    return _registry


async def _get_conversations() -> ConversationManager:
    global _conversations
    if _conversations is None:
        store = _get_store()
        _conversations = ConversationManager(store=store, thread_store=_get_thread_store())
        await _conversations.load_history("main")
    return _conversations


async def _build_history_sync(conversation_id: str = "main") -> HistorySyncEnvelope:
    """Build a history.sync envelope with recent messages."""
    if conversation_id == "main":
        store = _get_store()
        recent = await store.load_recent(50)
    else:
        ts = _get_thread_store()
        recent = await ts.load_thread_messages(conversation_id, 50)

    messages = [
        HistoryMessagePayload(
            id=m["id"], role=m["role"], content=m["content"], ts=m["ts"],
        )
        for m in recent
        if m.get("role") in ("user", "assistant")
    ]
    return HistorySyncEnvelope(
        payload=HistorySyncPayload(
            conversation_id=conversation_id,
            messages=messages,
            has_more=len(messages) >= 50,
        ),
    )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        # Send server hello
        await manager.send(
            websocket,
            ServerHelloEnvelope(
                payload=ServerHelloPayload(
                    protocol_version="1.0",
                    server_id="doti-backend",
                ),
            ),
        )

        # Send Main message history
        history_envelope = await _build_history_sync()
        await manager.send(websocket, history_envelope)

        conversations = await _get_conversations()

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

                if cid not in conversations._histories:
                    await conversations.load_history(cid)

                run = RunContext(conversation_id=cid)
                _active_runs[cid] = run.run_id

                # Signal queued
                await manager.send(websocket, RunStateEnvelope(
                    payload=RunStatePayload(
                        run_id=run.run_id, conversation_id=cid, state=RunState.queued,
                    ),
                ))

                gate = ApprovalGate()
                _approval_gates[cid] = gate

                async def _run_agent(
                    _run: RunContext = run,
                    _content: str = content,
                    _cid: str = cid,
                    _gate: ApprovalGate = gate,
                ) -> None:
                    try:
                        async for envelope in execute_run(
                            _run,
                            _content,
                            _get_provider(),
                            conversations,
                            _get_registry(),
                            _gate,
                        ):
                            await manager.send(websocket, envelope)
                    except Exception:
                        logger.exception("Run failed run_id={} conversation_id={}", _run.run_id, _cid)
                        await manager.send(websocket, ErrorEnvelope(
                            payload=ErrorPayload(
                                code="internal_error",
                                message="Run failed",
                                run_id=_run.run_id,
                            ),
                        ))
                    finally:
                        _active_runs.pop(_cid, None)
                        _approval_gates.pop(_cid, None)

                task = asyncio.create_task(_run_agent())
                _run_tasks.add(task)
                task.add_done_callback(_run_tasks.discard)

            elif msg.type == "tool.approve":
                resolved = False
                for gate in _approval_gates.values():
                    if gate.resolve(msg.payload.approval_id, msg.payload.approved):
                        resolved = True
                        break

                if not resolved:
                    await manager.send(websocket, ErrorEnvelope(
                        payload=ErrorPayload(
                            code="internal_error",
                            message=f"No pending approval found for {msg.payload.approval_id}",
                        ),
                    ))

            elif msg.type == "thread.create":
                thread = Thread(
                    title=msg.payload.title,
                    thread_type=ThreadType(msg.payload.thread_type),
                )
                ts = _get_thread_store()
                await ts.create({
                    "thread_id": thread.thread_id,
                    "title": thread.title,
                    "thread_type": thread.thread_type.value,
                    "status": thread.status.value,
                    "created_at": thread.created_at.isoformat(),
                    "updated_at": thread.updated_at.isoformat(),
                })
                logger.info("Thread created: {}", thread.thread_id)
                await manager.send(websocket, ThreadCreatedEnvelope(
                    payload=ThreadInfoPayload(
                        thread_id=thread.thread_id,
                        title=thread.title,
                        thread_type=thread.thread_type.value,
                        status=thread.status.value,
                        created_at=thread.created_at.isoformat(),
                    ),
                ))

            elif msg.type == "thread.list":
                ts = _get_thread_store()
                threads = await ts.list_threads()
                items = [
                    ThreadInfoPayload(
                        thread_id=t["thread_id"],
                        title=t.get("title"),
                        thread_type=t.get("thread_type", "task"),
                        status=t.get("status", "active"),
                        created_at=t.get("created_at", ""),
                    )
                    for t in threads
                ]
                await manager.send(websocket, ThreadListResultEnvelope(
                    payload=ThreadListResultPayload(threads=items),
                ))

            elif msg.type == "thread.delete":
                ts = _get_thread_store()
                deleted = await ts.delete(msg.payload.thread_id)
                if deleted:
                    await manager.send(websocket, ThreadUpdatedEnvelope(
                        payload=ThreadUpdatedPayload(
                            thread_id=msg.payload.thread_id,
                            status="deleted",
                        ),
                    ))
                else:
                    await manager.send(websocket, ErrorEnvelope(
                        payload=ErrorPayload(
                            code="thread_not_found",
                            message=f"Thread {msg.payload.thread_id} not found",
                        ),
                    ))

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    finally:
        manager.disconnect(websocket)
