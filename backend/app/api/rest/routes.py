"""REST API endpoints."""

from __future__ import annotations

import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.api.ws import router as ws_router_module
from app.core.audit import log_config_change
from app.core.config.loader import load_config, to_runtime_config
from app.core.config.models import (
    DotiConfig,
    ExecutorConfig,
    ModelConfig,
    ProfileConfig,
    ProfileRoleConfig,
    ProviderConfig,
    SecurityConfig,
    ThinkingConfig,
    ToolApprovalPolicy,
)
from app.core.models import Thread, ThreadType
from app.executor.manager import ExecutorManager, ExecutorManagerError

router = APIRouter(prefix="/api/v1")

# Stores injected at app startup
_message_store = None
_thread_store = None
_doti_config: DotiConfig | None = None
_executor_manager: ExecutorManager | None = None


def _require_auth(request: Request) -> None:
    """Verify Bearer token if DOTI_API_TOKEN is configured."""
    token = os.environ.get("DOTI_API_TOKEN")
    if not token:
        return  # No token configured = no auth required (local-only mode)
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {token}":
        raise HTTPException(401, "Unauthorized")


def set_stores(message_store, thread_store) -> None:
    global _message_store, _thread_store
    _message_store = message_store
    _thread_store = thread_store


def set_doti_config(config: DotiConfig) -> None:
    global _doti_config, _executor_manager
    _doti_config = config
    _executor_manager = None
    ws_router_module._config = to_runtime_config(config)
    ws_router_module._provider = None



def _get_doti_config() -> DotiConfig:
    global _doti_config
    if _doti_config is None:
        set_doti_config(load_config())
    return _doti_config


def _get_executor_manager() -> ExecutorManager:
    global _executor_manager
    if _executor_manager is None:
        config = _get_doti_config()
        _executor_manager = ExecutorManager(config.executors.values())
    return _executor_manager


def _raise_executor_http_error(exc: ExecutorManagerError) -> None:
    message = str(exc)
    lowered = message.lower()
    if "docker is unavailable" in lowered or "docker sdk is unavailable" in lowered:
        raise HTTPException(503, message) from exc
    if "unknown executor_id" in lowered or "removed" in lowered or "not found" in lowered:
        raise HTTPException(404, message) from exc
    raise HTTPException(503, message) from exc


def _mask_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    suffix = api_key[-4:]
    return f"****{suffix}"


def _public_config(config: DotiConfig) -> dict:
    data = config.model_dump()
    providers = data.get("providers", {})
    for provider in providers.values():
        if isinstance(provider, dict):
            provider["api_key"] = _mask_api_key(provider.get("api_key"))
    return data


class ProviderModelRequest(BaseModel):
    id: str
    thinking: ThinkingConfig | None = None


class ProviderUpsertRequest(BaseModel):
    api_base: str | None = None
    api_key: str | None = None
    models: dict[str, ProviderModelRequest] | None = None


class ModelUpsertRequest(BaseModel):
    id: str
    context_window: int | None = None
    pricing: dict | None = None
    thinking: ThinkingConfig | None = None


class ProfilePatchRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    primary: ProfileRoleConfig | None = None
    long_context: ProfileRoleConfig | None = None
    automation: ProfileRoleConfig | None = None


class SecurityPatchRequest(BaseModel):
    tool_approval: ToolApprovalPolicy | None = None
    tool_allowlist: list[str] | None = None


class ExecutorUpsertRequest(BaseModel):
    workspace: str
    image: str = "doti-sandbox:latest"
    idle_timeout: int = 600
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    network: bool = False
    rtk_enabled: bool = True


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/config")
async def get_config() -> dict:
    config = _get_doti_config()
    return _public_config(config)


@router.get("/config/providers")
async def list_providers() -> dict:
    config = _get_doti_config()
    providers: list[dict] = []

    for name, provider in config.providers.items():
        providers.append(
            {
                "name": name,
                "api_base": provider.api_base,
                "api_key": _mask_api_key(provider.api_key),
                "model_count": len(provider.models),
                "models": [
                    {
                        "alias": alias,
                        "id": model.id,
                        "thinking": model.thinking.model_dump(),
                    }
                    for alias, model in provider.models.items()
                ],
            }
        )

    return {"providers": providers}


@router.post("/config/providers/{name}")
async def upsert_provider(name: str, body: ProviderUpsertRequest, _=Depends(_require_auth)) -> dict:
    config = _get_doti_config()
    provider = config.providers.get(name, ProviderConfig())

    if "api_base" in body.model_fields_set:
        provider.api_base = body.api_base
    if "api_key" in body.model_fields_set:
        provider.api_key = body.api_key
    if body.models is not None:
        for alias, model_req in body.models.items():
            provider.models[alias] = ModelConfig(
                id=model_req.id,
                thinking=model_req.thinking or ThinkingConfig(),
            )

    config.providers[name] = provider
    set_doti_config(config)
    log_config_change(f"/config/providers/{name}", "POST", f"upsert provider {name}")
    return {
        "name": name,
        "api_base": provider.api_base,
        "api_key": _mask_api_key(provider.api_key),
        "models": {
            alias: {
                "id": model.id,
                "thinking": model.thinking.model_dump(),
            }
            for alias, model in provider.models.items()
        },
    }


@router.delete("/config/providers/{name}")
async def delete_provider(name: str, _=Depends(_require_auth)) -> dict:
    config = _get_doti_config()
    if name not in config.providers:
        raise HTTPException(404, "Provider not found")

    del config.providers[name]
    set_doti_config(config)
    log_config_change(f"/config/providers/{name}", "DELETE", f"deleted provider {name}")
    return {"deleted": True, "provider": name}


@router.get("/config/models")
async def list_models() -> dict:
    config = _get_doti_config()
    return {"models": config.list_all_models()}


@router.post("/config/providers/{provider}/models/{alias}")
async def upsert_model(provider: str, alias: str, body: ModelUpsertRequest, _=Depends(_require_auth)) -> dict:
    config = _get_doti_config()
    provider_config = config.providers.get(provider)
    if provider_config is None:
        raise HTTPException(404, "Provider not found")

    provider_config.models[alias] = ModelConfig(
        id=body.id,
        context_window=body.context_window,
        pricing=body.pricing,
        thinking=body.thinking or ThinkingConfig(),
    )
    set_doti_config(config)

    model = provider_config.models[alias]
    return {
        "provider": provider,
        "alias": alias,
        "model": model.model_dump(),
    }


@router.delete("/config/providers/{provider}/models/{alias}")
async def delete_model(provider: str, alias: str, _=Depends(_require_auth)) -> dict:
    config = _get_doti_config()
    provider_config = config.providers.get(provider)
    if provider_config is None:
        raise HTTPException(404, "Provider not found")
    if alias not in provider_config.models:
        raise HTTPException(404, "Model not found")

    del provider_config.models[alias]
    set_doti_config(config)
    return {"deleted": True, "provider": provider, "alias": alias}


@router.get("/config/profile")
async def get_profile() -> dict:
    config = _get_doti_config()
    return config.profile.model_dump()


@router.patch("/config/profile")
async def patch_profile(body: ProfilePatchRequest, _=Depends(_require_auth)) -> dict:
    config = _get_doti_config()

    if "name" in body.model_fields_set and body.name is not None:
        config.profile.name = body.name
    if "description" in body.model_fields_set and body.description is not None:
        config.profile.description = body.description
    if "primary" in body.model_fields_set:
        config.profile.primary = body.primary
    if "long_context" in body.model_fields_set:
        config.profile.long_context = body.long_context
    if "automation" in body.model_fields_set:
        config.profile.automation = body.automation

    set_doti_config(config)
    return config.profile.model_dump()


@router.get("/config/security")
async def get_security() -> dict:
    config = _get_doti_config()
    return config.security.model_dump()


@router.patch("/config/security")
async def patch_security(body: SecurityPatchRequest, _=Depends(_require_auth)) -> dict:
    config = _get_doti_config()

    if "tool_approval" in body.model_fields_set and body.tool_approval is not None:
        config.security.tool_approval = body.tool_approval
    if "tool_allowlist" in body.model_fields_set and body.tool_allowlist is not None:
        config.security.tool_allowlist = body.tool_allowlist

    set_doti_config(config)
    log_config_change("/config/security", "PATCH", f"policy={config.security.tool_approval.value}")
    return config.security.model_dump()


@router.get("/executors")
async def list_executors() -> dict:
    manager = _get_executor_manager()
    try:
        executors = await manager.list_executors()
    except ExecutorManagerError as exc:
        _raise_executor_http_error(exc)
    return {"executors": executors}


@router.post("/executors/{executor_id}/start")
async def start_executor(executor_id: str, _=Depends(_require_auth)) -> dict:
    manager = _get_executor_manager()
    try:
        endpoint = await manager.ensure_running(executor_id)
    except ExecutorManagerError as exc:
        _raise_executor_http_error(exc)
    log_config_change(f"/executors/{executor_id}/start", "POST", f"started executor {executor_id}")
    return {"executor_id": executor_id, "endpoint": endpoint, "status": "running"}


@router.post("/executors/{executor_id}/stop")
async def stop_executor(executor_id: str, _=Depends(_require_auth)) -> dict:
    manager = _get_executor_manager()
    try:
        await manager.stop(executor_id)
    except ExecutorManagerError as exc:
        _raise_executor_http_error(exc)
    log_config_change(f"/executors/{executor_id}/stop", "POST", f"stopped executor {executor_id}")
    return {"executor_id": executor_id, "stopped": True}


@router.delete("/executors/{executor_id}")
async def remove_executor(executor_id: str, _=Depends(_require_auth)) -> dict:
    manager = _get_executor_manager()
    try:
        await manager.remove(executor_id)
    except ExecutorManagerError as exc:
        _raise_executor_http_error(exc)
    log_config_change(f"/executors/{executor_id}", "DELETE", f"removed executor container {executor_id}")
    return {"executor_id": executor_id, "removed": True}


@router.get("/executors/{executor_id}/status")
async def get_executor_status(executor_id: str) -> dict:
    manager = _get_executor_manager()
    try:
        status = await manager.get_status(executor_id)
    except ExecutorManagerError as exc:
        _raise_executor_http_error(exc)
    if status == "unknown":
        raise HTTPException(404, f"Unknown executor_id '{executor_id}'")
    return {"executor_id": executor_id, "status": status}


@router.post("/config/executors/{executor_id}")
async def upsert_executor_config(executor_id: str, body: ExecutorUpsertRequest, _=Depends(_require_auth)) -> dict:
    config = _get_doti_config()
    config.executors[executor_id] = ExecutorConfig(
        id=executor_id,
        workspace=body.workspace,
        image=body.image,
        idle_timeout=body.idle_timeout,
        memory_limit=body.memory_limit,
        cpu_limit=body.cpu_limit,
        network=body.network,
        rtk_enabled=body.rtk_enabled,
    )
    set_doti_config(config)
    log_config_change(f"/config/executors/{executor_id}", "POST", f"upsert executor config {executor_id}")
    return config.executors[executor_id].model_dump()


@router.delete("/config/executors/{executor_id}")
async def delete_executor_config(executor_id: str, _=Depends(_require_auth)) -> dict:
    config = _get_doti_config()
    if executor_id not in config.executors:
        raise HTTPException(404, "Executor config not found")
    del config.executors[executor_id]
    set_doti_config(config)
    log_config_change(f"/config/executors/{executor_id}", "DELETE", f"deleted executor config {executor_id}")
    return {"deleted": True, "executor_id": executor_id}


@router.get("/main/messages")
async def get_main_messages(
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    if _message_store is None:
        return {"messages": [], "has_more": False}

    messages = await _message_store.load_recent(limit + 1)
    has_more = len(messages) > limit
    if has_more:
        messages = messages[1:]  # Drop oldest, keep last `limit`
    return {
        "messages": messages,
        "has_more": has_more,
    }


# --- Threads ---


class ThreadCreateRequest(BaseModel):
    title: str | None = None
    thread_type: Literal["task", "focus"] = "task"


@router.get("/threads")
async def list_threads() -> dict:
    if _thread_store is None:
        return {"threads": []}
    threads = await _thread_store.list_threads()
    return {"threads": threads}


@router.post("/threads", status_code=201)
async def create_thread(body: ThreadCreateRequest) -> dict:
    if _thread_store is None:
        raise HTTPException(500, "Thread store not initialized")

    thread = Thread(
        title=body.title,
        thread_type=ThreadType(body.thread_type),
    )
    data = {
        "thread_id": thread.thread_id,
        "title": thread.title,
        "thread_type": thread.thread_type.value,
        "status": thread.status.value,
        "created_at": thread.created_at.isoformat(),
        "updated_at": thread.updated_at.isoformat(),
    }
    await _thread_store.create(data)
    return data


@router.get("/threads/{thread_id}")
async def get_thread(thread_id: str) -> dict:
    if _thread_store is None:
        raise HTTPException(500, "Thread store not initialized")

    thread = await _thread_store.get(thread_id)
    if thread is None:
        raise HTTPException(404, "Thread not found")
    return thread


@router.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str) -> dict:
    if _thread_store is None:
        raise HTTPException(500, "Thread store not initialized")

    deleted = await _thread_store.delete(thread_id)
    if not deleted:
        raise HTTPException(404, "Thread not found")
    return {"deleted": True}


@router.get("/threads/{thread_id}/messages")
async def get_thread_messages(
    thread_id: str,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    if _thread_store is None:
        raise HTTPException(500, "Thread store not initialized")

    thread = await _thread_store.get(thread_id)
    if thread is None:
        raise HTTPException(404, "Thread not found")

    messages = await _thread_store.load_thread_messages(thread_id, limit)
    return {"messages": messages}
