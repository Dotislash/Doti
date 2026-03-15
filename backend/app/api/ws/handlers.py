"""WebSocket message handlers."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fastapi import WebSocket
from loguru import logger

from app.agent.runtime import ApprovalGate, execute_run
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
    ThreadCreatedEnvelope,
    ThreadInfoPayload,
    ThreadListResultEnvelope,
    ThreadListResultPayload,
    ThreadUpdatedEnvelope,
    ThreadUpdatedPayload,
    ToolRequestEnvelope,
    ToolResultEnvelope,
)
from app.core.audit import log_tool_approval
from app.core.models import RunContext, RunState, Thread, ThreadType

if TYPE_CHECKING:
    from app.api.ws.protocol import (
        ChatSendEnvelope,
        ExecutorAttachEnvelope,
        ExecutorDetachEnvelope,
        ExecutorListEnvelope,
        ExecutorStatusEnvelope,
        ThreadCreateEnvelope,
        ThreadDeleteEnvelope,
        ThreadListEnvelope,
        ToolApproveEnvelope,
    )
    from app.api.ws.router import ServerState


async def build_history_sync(
    state: ServerState,
    conversation_id: str = "main",
) -> HistorySyncEnvelope:
    """Build a history.sync envelope with messages and raw history items."""
    if conversation_id == "main":
        store = state.get_store()
        loaded = await store.load_recent(50)
    else:
        ts = state.get_thread_store()
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
            items.append(
                {
                    "kind": "message",
                    "id": message_id,
                    "role": role,
                    "content": content,
                    "ts": item.get("ts", 0),
                }
            )

    messages = [
        HistoryMessagePayload(
            id=m["id"],
            role=m["role"],
            content=m["content"],
            ts=m["ts"],
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


async def _run_agent(
    state: ServerState,
    websocket: WebSocket,
    run: RunContext,
    content: str,
    conversation_id: str,
    gate: ApprovalGate,
) -> None:
    from app.api.rest.routes import _get_doti_config

    security = _get_doti_config().security
    conversations = await state.get_conversations()
    try:
        async for envelope in execute_run(
            run,
            content,
            state.get_provider(),
            conversations,
            state.get_registry(),
            gate,
            security=security,
        ):
            try:
                await state.conn_manager.send(websocket, envelope)
            except Exception:
                logger.warning(
                    "WebSocket disconnected mid-run, stopping send for run_id={}",
                    run.run_id,
                )
                return

            if conversation_id != "main":
                continue

            store = state.get_store()
            if isinstance(envelope, AgentThinkingEnvelope):
                await store.append_item(
                    {
                        "kind": "thinking",
                        "id": envelope.event_id,
                        "content": envelope.payload.content,
                        "iteration": envelope.payload.iteration,
                    }
                )
            elif isinstance(envelope, ToolRequestEnvelope):
                await store.append_item(
                    {
                        "kind": "tool_request",
                        "id": envelope.event_id,
                        "tool_name": envelope.payload.tool_name,
                        "arguments": envelope.payload.arguments,
                        "risk_level": envelope.payload.risk_level,
                        "approval_id": envelope.payload.approval_id,
                    }
                )
            elif isinstance(envelope, ToolResultEnvelope):
                await store.append_item(
                    {
                        "kind": "tool_result",
                        "id": envelope.event_id,
                        "tool_name": envelope.payload.tool_name,
                        "result": envelope.payload.result,
                        "is_error": envelope.payload.is_error,
                    }
                )
        # After successful run, trigger memory consolidation if needed
        try:
            await conversations.consolidate_if_needed(
                conversation_id, state.get_provider()
            )
        except Exception:
            logger.warning("Post-run consolidation failed for {}", conversation_id)
    except Exception:
        logger.exception("Run failed run_id={} conversation_id={}", run.run_id, conversation_id)
        await state.conn_manager.send(
            websocket,
            ErrorEnvelope(
                payload=ErrorPayload(
                    code="internal_error",
                    message="Run failed",
                    run_id=run.run_id,
                ),
            ),
        )
    finally:
        state.active_runs.pop(conversation_id, None)
        state.approval_gates.pop(conversation_id, None)
        state.conversation_locks.pop(conversation_id, None)


async def handle_chat_send(state: ServerState, ws: WebSocket, msg: ChatSendEnvelope) -> None:
    cid = msg.payload.conversation_id
    content = msg.payload.content

    conversations = await state.get_conversations()
    lock = state.get_conversation_lock(cid)
    async with lock:
        if cid in state.active_runs:
            await state.conn_manager.send(
                ws,
                ErrorEnvelope(
                    payload=ErrorPayload(
                        code="conversation_busy",
                        message="A run is already active",
                        run_id=state.active_runs[cid],
                    ),
                ),
            )
            return

        if cid != "main":
            ts = state.get_thread_store()
            thread_meta = await ts.get(cid)
            if thread_meta is None:
                await state.conn_manager.send(
                    ws,
                    ErrorEnvelope(
                        payload=ErrorPayload(
                            code="thread_not_found",
                            message=f"Thread {cid} does not exist",
                        ),
                    ),
                )
                return

        if not conversations.has_conversation(cid):
            await conversations.load_history(cid)

        run = RunContext(conversation_id=cid)
        state.active_runs[cid] = run.run_id

    await state.conn_manager.send(
        ws,
        RunStateEnvelope(
            payload=RunStatePayload(
                run_id=run.run_id,
                conversation_id=cid,
                state=RunState.queued,
            ),
        ),
    )

    gate = ApprovalGate()
    state.approval_gates[cid] = (gate, ws)

    task = asyncio.create_task(_run_agent(state, ws, run, content, cid, gate))
    state.run_tasks.add(task)
    task.add_done_callback(state.run_tasks.discard)


async def handle_tool_approve(state: ServerState, ws: WebSocket, msg: ToolApproveEnvelope) -> None:
    resolved = False
    for _cid, (gate, gate_ws) in list(state.approval_gates.items()):
        if gate_ws is not ws:
            continue
        if gate.resolve(msg.payload.approval_id, msg.payload.approved):
            log_tool_approval(msg.payload.approval_id, msg.payload.approved)
            resolved = True
            break

    if not resolved:
        await state.conn_manager.send(
            ws,
            ErrorEnvelope(
                payload=ErrorPayload(
                    code="internal_error",
                    message=f"No pending approval found for {msg.payload.approval_id}",
                ),
            ),
        )


async def handle_thread_create(
    state: ServerState, ws: WebSocket, msg: ThreadCreateEnvelope
) -> None:
    try:
        thread_type = ThreadType(msg.payload.thread_type)
    except ValueError:
        await state.conn_manager.send(
            ws,
            ErrorEnvelope(
                payload=ErrorPayload(
                    code="invalid_message",
                    message=f"Invalid thread_type: {msg.payload.thread_type}",
                ),
            ),
        )
        return

    executor_id = getattr(msg.payload, "executor", None)
    if executor_id is not None:
        from app.api.rest.routes import _get_doti_config

        if executor_id not in _get_doti_config().executors:
            await state.conn_manager.send(
                ws,
                ErrorEnvelope(
                    payload=ErrorPayload(
                        code="executor_not_found",
                        message=f"Executor '{executor_id}' not found",
                    ),
                ),
            )
            return

    thread = Thread(
        title=msg.payload.title,
        thread_type=thread_type,
        executor=executor_id,
    )
    ts = state.get_thread_store()
    await ts.create(
        {
            "thread_id": thread.thread_id,
            "title": thread.title,
            "executor": thread.executor,
            "thread_type": thread.thread_type.value,
            "status": thread.status.value,
            "created_at": thread.created_at.isoformat(),
            "updated_at": thread.updated_at.isoformat(),
        }
    )
    logger.info("Thread created: {} executor={}", thread.thread_id, thread.executor)
    await state.conn_manager.send(
        ws,
        ThreadCreatedEnvelope(
            payload=ThreadInfoPayload(
                thread_id=thread.thread_id,
                title=thread.title,
                executor=thread.executor,
                thread_type=thread.thread_type.value,
                status=thread.status.value,
                created_at=thread.created_at.isoformat(),
            ),
        ),
    )


async def handle_thread_list(state: ServerState, ws: WebSocket, msg: ThreadListEnvelope) -> None:
    del msg
    ts = state.get_thread_store()
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
    await state.conn_manager.send(
        ws,
        ThreadListResultEnvelope(
            payload=ThreadListResultPayload(threads=items),
        ),
    )


async def handle_thread_delete(
    state: ServerState, ws: WebSocket, msg: ThreadDeleteEnvelope
) -> None:
    ts = state.get_thread_store()
    deleted = await ts.delete(msg.payload.thread_id)
    if deleted:
        await state.conn_manager.send(
            ws,
            ThreadUpdatedEnvelope(
                payload=ThreadUpdatedPayload(
                    thread_id=msg.payload.thread_id,
                    status="deleted",
                ),
            ),
        )
        return
    await state.conn_manager.send(
        ws,
        ErrorEnvelope(
            payload=ErrorPayload(
                code="thread_not_found",
                message=f"Thread {msg.payload.thread_id} not found",
            ),
        ),
    )


async def handle_executor_list(
    state: ServerState, ws: WebSocket, msg: ExecutorListEnvelope
) -> None:
    del msg
    from app.api.rest.routes import _get_executor_manager

    try:
        em = _get_executor_manager()
        executors = await em.list_executors()
    except Exception as exc:
        await state.conn_manager.send(
            ws,
            ErrorEnvelope(payload=ErrorPayload(code="executor_error", message=str(exc))),
        )
        return
    await state.conn_manager.send(
        ws,
        ExecutorListResultEnvelope(
            payload=ExecutorListResultPayload(executors=executors),
        ),
    )


async def handle_executor_status(
    state: ServerState, ws: WebSocket, msg: ExecutorStatusEnvelope
) -> None:
    from app.api.rest.routes import _get_executor_manager

    executor_id = msg.payload.executor_id
    try:
        em = _get_executor_manager()
        status = await em.get_status(executor_id)
        endpoint = None
        if status == "running":
            try:
                endpoint = await em.get_endpoint(executor_id)
            except Exception:
                pass
    except Exception as exc:
        await state.conn_manager.send(
            ws,
            ErrorEnvelope(payload=ErrorPayload(code="executor_error", message=str(exc))),
        )
        return
    await state.conn_manager.send(
        ws,
        ExecutorStatusResultEnvelope(
            payload=ExecutorStatusResultPayload(
                executor_id=executor_id,
                status=status,
                endpoint=endpoint,
            ),
        ),
    )


async def handle_executor_attach(
    state: ServerState, ws: WebSocket, msg: ExecutorAttachEnvelope
) -> None:
    executor_id = msg.payload.executor_id
    from app.api.rest.routes import _get_doti_config

    if executor_id not in _get_doti_config().executors:
        await state.conn_manager.send(
            ws,
            ErrorEnvelope(
                payload=ErrorPayload(
                    code="executor_not_found",
                    message=f"Executor '{executor_id}' not found",
                )
            ),
        )
        return
    logger.info("Executor attached to main: {}", executor_id)
    await state.conn_manager.send(
        ws,
        ExecutorStatusResultEnvelope(
            payload=ExecutorStatusResultPayload(
                executor_id=executor_id,
                status="attached",
            ),
        ),
    )


async def handle_executor_detach(
    state: ServerState, ws: WebSocket, msg: ExecutorDetachEnvelope
) -> None:
    del msg
    logger.info("Executor detached from main")
    await state.conn_manager.send(
        ws,
        ExecutorStatusResultEnvelope(
            payload=ExecutorStatusResultPayload(
                executor_id="",
                status="detached",
            ),
        ),
    )


HANDLERS = {
    "chat.send": handle_chat_send,
    "tool.approve": handle_tool_approve,
    "thread.create": handle_thread_create,
    "thread.list": handle_thread_list,
    "thread.delete": handle_thread_delete,
    "executor.list": handle_executor_list,
    "executor.status": handle_executor_status,
    "executor.attach": handle_executor_attach,
    "executor.detach": handle_executor_detach,
}
