"""WebSocket endpoint — connects clients to the agent runtime."""

from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.agent.conversation import ConversationManager
from app.core.audit import log_tool_approval
from app.agent.provider_client import ProviderClient
from app.agent.runtime import ApprovalGate, execute_run
from app.api.ws.connection_manager import ConnectionManager
from app.api.ws.protocol import (
    AgentThinkingEnvelope,
    ErrorEnvelope,
    ErrorPayload,
    ExecutorListResultEnvelope,
    ExecutorListResultPayload,
    ExecutorStatusResultEnvelope,
    ExecutorStatusResultPayload,
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
    ToolRequestEnvelope,
    ToolResultEnvelope,
    parse_client_message,
)
from app.core.config.models import SecurityConfig
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
_conversation_locks: dict[str, asyncio.Lock] = {}  # per-conversation locks
# conversation_id -> (gate, owning websocket)
_approval_gates: dict[str, tuple[ApprovalGate, WebSocket]] = {}
_run_tasks: set[asyncio.Task[None]] = set()


def _get_conversation_lock(cid: str) -> asyncio.Lock:
    if cid not in _conversation_locks:
        _conversation_locks[cid] = asyncio.Lock()
    return _conversation_locks[cid]


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
        cfg = _get_config()
        _registry = create_default_registry(workspace=cfg.workspace)
    return _registry


async def _get_conversations() -> ConversationManager:
    global _conversations
    if _conversations is None:
        store = _get_store()
        _conversations = ConversationManager(store=store, thread_store=_get_thread_store())
        await _conversations.load_history("main")
    return _conversations


async def _build_history_sync(conversation_id: str = "main") -> HistorySyncEnvelope:
    """Build a history.sync envelope with messages and raw history items."""
    if conversation_id == "main":
        store = _get_store()
        loaded = await store.load_recent(50)
    else:
        ts = _get_thread_store()
        loaded = await ts.load_thread_messages(conversation_id, 50)

    items: list[dict] = []
    for item in loaded:
        if not isinstance(item, dict):
            continue

        if isinstance(item.get("kind"), str):
            normalized = dict(item)
            normalized.setdefault("ts", 0)
            items.append(normalized)
            continue

        role = item.get("role")
        content = item.get("content")
        message_id = item.get("id")
        if (
            isinstance(role, str)
            and isinstance(content, str)
            and isinstance(message_id, str)
            and role in ("user", "assistant")
        ):
            items.append({
                "kind": "message",
                "id": message_id,
                "role": role,
                "content": content,
                "ts": item.get("ts", 0),
            })

    messages = [
        HistoryMessagePayload(
            id=m["id"], role=m["role"], content=m["content"], ts=m["ts"],
        )
        for m in items
        if m.get("kind") == "message" and m.get("role") in ("user", "assistant")
    ]
    # Both main and threads are capped at 50; has_more if we hit that limit.
    has_more = len(loaded) >= 50
    return HistorySyncEnvelope(
        payload=HistorySyncPayload(
            conversation_id=conversation_id,
            messages=messages,
            items=items,
            has_more=has_more,
        ),
    )


def _ws_auth_ok(websocket: WebSocket) -> bool:
    """Verify WS auth via query param ?token=... if DOTI_API_TOKEN is set."""
    expected = os.environ.get("DOTI_API_TOKEN")
    if not expected:
        return True  # No token configured = local-only mode
    token = websocket.query_params.get("token", "")
    return token == expected


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    if not _ws_auth_ok(websocket):
        await websocket.close(code=4001, reason="Unauthorized")
        return

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

                # Atomic check-and-set with per-conversation lock
                lock = _get_conversation_lock(cid)
                async with lock:
                    if cid in _active_runs:
                        await manager.send(websocket, ErrorEnvelope(
                            payload=ErrorPayload(
                                code="conversation_busy",
                                message="A run is already active",
                                run_id=_active_runs[cid],
                            ),
                        ))
                        continue

                    # Validate conversation_id: must be "main" or an existing thread
                    if cid != "main":
                        ts = _get_thread_store()
                        thread_meta = await ts.get(cid)
                        if thread_meta is None:
                            await manager.send(websocket, ErrorEnvelope(
                                payload=ErrorPayload(
                                    code="thread_not_found",
                                    message=f"Thread {cid} does not exist",
                                ),
                            ))
                            continue

                    if not conversations.has_conversation(cid):
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
                _approval_gates[cid] = (gate, websocket)

                # Resolve security config for this run
                from app.api.rest.routes import _get_doti_config
                _security = _get_doti_config().security

                async def _run_agent(
                    _run: RunContext = run,
                    _content: str = content,
                    _cid: str = cid,
                    _gate: ApprovalGate = gate,
                    _sec: SecurityConfig = _security,
                ) -> None:
                    try:
                        async for envelope in execute_run(
                            _run,
                            _content,
                            _get_provider(),
                            conversations,
                            _get_registry(),
                            _gate,
                            security=_sec,
                        ):
                            try:
                                await manager.send(websocket, envelope)
                            except Exception:
                                logger.warning("WebSocket disconnected mid-run, stopping send for run_id={}", _run.run_id)
                                return

                            if _cid != "main":
                                continue

                            store = _get_store()
                            if isinstance(envelope, AgentThinkingEnvelope):
                                await store.append_item({
                                    "kind": "thinking",
                                    "id": envelope.event_id,
                                    "content": envelope.payload.content,
                                    "iteration": envelope.payload.iteration,
                                })
                            elif isinstance(envelope, ToolRequestEnvelope):
                                await store.append_item({
                                    "kind": "tool_request",
                                    "id": envelope.event_id,
                                    "tool_name": envelope.payload.tool_name,
                                    "arguments": envelope.payload.arguments,
                                    "risk_level": envelope.payload.risk_level,
                                    "approval_id": envelope.payload.approval_id,
                                })
                            elif isinstance(envelope, ToolResultEnvelope):
                                await store.append_item({
                                    "kind": "tool_result",
                                    "id": envelope.event_id,
                                    "tool_name": envelope.payload.tool_name,
                                    "result": envelope.payload.result,
                                    "is_error": envelope.payload.is_error,
                                })
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
                        _conversation_locks.pop(_cid, None)

                task = asyncio.create_task(_run_agent())
                _run_tasks.add(task)
                task.add_done_callback(_run_tasks.discard)

            elif msg.type == "tool.approve":
                # Only resolve gates owned by this websocket connection
                resolved = False
                for g_cid, (g_gate, g_ws) in list(_approval_gates.items()):
                    if g_ws is not websocket:
                        continue
                    if g_gate.resolve(msg.payload.approval_id, msg.payload.approved):
                        log_tool_approval(msg.payload.approval_id, msg.payload.approved)
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
                try:
                    thread_type = ThreadType(msg.payload.thread_type)
                except ValueError:
                    await manager.send(websocket, ErrorEnvelope(
                        payload=ErrorPayload(
                            code="invalid_message",
                            message=f"Invalid thread_type: {msg.payload.thread_type}",
                        ),
                    ))
                    continue
                # Validate executor exists if specified
                executor_id = getattr(msg.payload, "executor", None)
                if executor_id is not None:
                    from app.api.rest.routes import _get_doti_config
                    if executor_id not in _get_doti_config().executors:
                        await manager.send(websocket, ErrorEnvelope(
                            payload=ErrorPayload(
                                code="executor_not_found",
                                message=f"Executor '{executor_id}' not found",
                            ),
                        ))
                        continue

                thread = Thread(
                    title=msg.payload.title,
                    thread_type=thread_type,
                    executor=executor_id,
                )
                ts = _get_thread_store()
                await ts.create({
                    "thread_id": thread.thread_id,
                    "title": thread.title,
                    "executor": thread.executor,
                    "thread_type": thread.thread_type.value,
                    "status": thread.status.value,
                    "created_at": thread.created_at.isoformat(),
                    "updated_at": thread.updated_at.isoformat(),
                })
                logger.info("Thread created: {} executor={}", thread.thread_id, thread.executor)
                await manager.send(websocket, ThreadCreatedEnvelope(
                    payload=ThreadInfoPayload(
                        thread_id=thread.thread_id,
                        title=thread.title,
                        executor=thread.executor,
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
                        executor=t.get("executor"),
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

            elif msg.type == "executor.list":
                from app.api.rest.routes import _get_executor_manager
                try:
                    em = _get_executor_manager()
                    executors = await em.list_executors()
                except Exception as exc:
                    await manager.send(websocket, ErrorEnvelope(
                        payload=ErrorPayload(
                            code="executor_error", message=str(exc),
                        ),
                    ))
                    continue
                await manager.send(websocket, ExecutorListResultEnvelope(
                    payload=ExecutorListResultPayload(executors=executors),
                ))

            elif msg.type == "executor.status":
                from app.api.rest.routes import _get_executor_manager
                eid = msg.payload.executor_id
                try:
                    em = _get_executor_manager()
                    status = await em.get_status(eid)
                    endpoint = None
                    if status == "running":
                        try:
                            endpoint = await em.get_endpoint(eid)
                        except Exception:
                            pass
                except Exception as exc:
                    await manager.send(websocket, ErrorEnvelope(
                        payload=ErrorPayload(
                            code="executor_error", message=str(exc),
                        ),
                    ))
                    continue
                await manager.send(websocket, ExecutorStatusResultEnvelope(
                    payload=ExecutorStatusResultPayload(
                        executor_id=eid, status=status, endpoint=endpoint,
                    ),
                ))

            elif msg.type == "executor.attach":
                # Attach executor to main conversation (store in-memory)
                eid = msg.payload.executor_id
                from app.api.rest.routes import _get_doti_config
                if eid not in _get_doti_config().executors:
                    await manager.send(websocket, ErrorEnvelope(
                        payload=ErrorPayload(
                            code="executor_not_found",
                            message=f"Executor '{eid}' not found",
                        ),
                    ))
                    continue
                logger.info("Executor attached to main: {}", eid)
                await manager.send(websocket, ExecutorStatusResultEnvelope(
                    payload=ExecutorStatusResultPayload(
                        executor_id=eid, status="attached",
                    ),
                ))

            elif msg.type == "executor.detach":
                logger.info("Executor detached from main")
                await manager.send(websocket, ExecutorStatusResultEnvelope(
                    payload=ExecutorStatusResultPayload(
                        executor_id="", status="detached",
                    ),
                ))

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    finally:
        manager.disconnect(websocket)
