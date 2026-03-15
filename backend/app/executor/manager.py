from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Iterable, Literal

try:
    import docker
    import docker.errors as docker_errors
except Exception:  # pragma: no cover - allows graceful behavior when SDK is absent
    docker = None
    docker_errors = None

from app.core.config.models import ExecutorConfig

logger = logging.getLogger(__name__)

Status = Literal["running", "stopped", "removed", "unknown"]


class ExecutorManagerError(RuntimeError):
    """Raised when executor lifecycle operations cannot be completed."""


class ExecutorManager:
    """Manage Docker-backed executor containers for MCP communication."""

    def __init__(self, configs: Iterable[ExecutorConfig]) -> None:
        self._configs: dict[str, ExecutorConfig] = {cfg.id: cfg for cfg in configs}
        self._last_activity: dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._client = None

    async def ensure_running(self, executor_id: str) -> str:
        """Create/start container if needed and return its HTTP endpoint."""

        async with self._lock:
            config = self._get_config(executor_id)
            container = await self._get_or_create_container(config)

            status = await self._container_status(container)
            if status != "running":
                await self._docker_call(container.start)

            host_port = await self._resolve_host_port(container)
            self._last_activity[executor_id] = time.time()
            return f"http://127.0.0.1:{host_port}"

    async def get_endpoint(self, executor_id: str) -> str:
        """Return HTTP endpoint for a running executor container."""

        async with self._lock:
            config = self._get_config(executor_id)
            container = await self._get_container_by_name(self._container_name(config.id))
            if container is None:
                raise ExecutorManagerError(f"Executor '{executor_id}' is removed")

            status = await self._container_status(container)
            if status != "running":
                raise ExecutorManagerError(f"Executor '{executor_id}' is not running")

            host_port = await self._resolve_host_port(container)
            self._last_activity[executor_id] = time.time()
            return f"http://127.0.0.1:{host_port}"

    async def execute_command(
        self, executor_id: str, command: str, timeout: int = 30
    ) -> tuple[int, str]:
        """Execute command inside container. Returns (exit_code, output)."""

        async with self._lock:
            config = self._get_config(executor_id)
            container = await self._get_container_by_name(self._container_name(config.id))
            if container is None:
                raise ExecutorManagerError(f"Executor '{executor_id}' is not created")

            status = await self._container_status(container)
            if status != "running":
                raise ExecutorManagerError(f"Executor '{executor_id}' is not running")

            exec_result = await asyncio.wait_for(
                self._docker_call(
                    container.exec_run,
                    command,
                    workdir="/workspace",
                    demux=False,
                    tty=False,
                    stdout=True,
                    stderr=True,
                    stream=False,
                    socket=False,
                ),
                timeout=timeout,
            )
            output = exec_result.output
            if isinstance(output, bytes):
                decoded_output = output.decode("utf-8", errors="replace")
            else:
                decoded_output = str(output)

            self._last_activity[executor_id] = time.time()
            return (int(exec_result.exit_code), decoded_output)

    async def stop(self, executor_id: str) -> None:
        """Stop container while preserving it for future restart."""

        async with self._lock:
            self._get_config(executor_id)
            container = await self._get_container_by_name(self._container_name(executor_id))
            if container is None:
                return
            status = await self._container_status(container)
            if status == "running":
                await self._docker_call(container.stop)

    async def remove(self, executor_id: str) -> None:
        """Remove container completely and clear tracked activity."""

        async with self._lock:
            self._get_config(executor_id)
            container = await self._get_container_by_name(self._container_name(executor_id))
            if container is None:
                self._last_activity.pop(executor_id, None)
                return

            try:
                await self._docker_call(container.remove, force=True)
            finally:
                self._last_activity.pop(executor_id, None)

    async def get_status(self, executor_id: str) -> Status:
        """Return one of: running, stopped, removed, unknown."""

        if executor_id not in self._configs:
            return "unknown"

        try:
            container = await self._get_container_by_name(self._container_name(executor_id))
            if container is None:
                return "removed"
            return await self._container_status(container)
        except ExecutorManagerError:
            return "unknown"

    async def list_executors(self) -> list[dict]:
        """List known executors and their current state."""

        results: list[dict] = []
        for executor_id, cfg in self._configs.items():
            status = await self.get_status(executor_id)
            results.append(
                {
                    "id": executor_id,
                    "workspace": cfg.workspace,
                    "image": cfg.image,
                    "status": status,
                    "last_activity": self._last_activity.get(executor_id),
                }
            )
        return results

    async def idle_check(self) -> None:
        """Stop executors that have exceeded their idle timeout."""

        now = time.time()
        to_stop: list[str] = []

        async with self._lock:
            for executor_id, cfg in self._configs.items():
                if cfg.idle_timeout <= 0:
                    continue
                last_activity = self._last_activity.get(executor_id)
                if last_activity is None:
                    continue
                if now - last_activity >= cfg.idle_timeout:
                    to_stop.append(executor_id)

        for executor_id in to_stop:
            try:
                await self.stop(executor_id)
            except ExecutorManagerError:
                logger.exception("Idle stop failed for executor_id=%s", executor_id)

    async def cleanup_all(self) -> None:
        """Stop all managed executors, used during graceful shutdown."""

        for executor_id in self._configs:
            try:
                await self.stop(executor_id)
            except ExecutorManagerError:
                logger.exception("Cleanup stop failed for executor_id=%s", executor_id)

    def _get_config(self, executor_id: str) -> ExecutorConfig:
        config = self._configs.get(executor_id)
        if config is None:
            raise ExecutorManagerError(f"Unknown executor_id '{executor_id}'")
        return config

    async def _get_or_create_container(self, config: ExecutorConfig):
        container = await self._get_container_by_name(self._container_name(config.id))
        if container is not None:
            return container

        workspace = str(Path(config.workspace).resolve())
        labels = {
            "doti.executor": config.id,
            "doti.workspace": workspace,
        }
        return await self._docker_call(
            self._client_or_raise().containers.create,
            image=config.image,
            name=self._container_name(config.id),
            labels=labels,
            working_dir="/workspace",
            volumes={workspace: {"bind": "/workspace", "mode": "rw"}},
            ports={"8811/tcp": None},
            network="bridge" if config.network else "none",
            mem_limit=config.memory_limit or "512m",
            read_only=True,
            tmpfs={"/tmp": "rw,noexec,nosuid,size=64m"},
            detach=True,
        )

    async def _get_container_by_name(self, name: str):
        client = self._client_or_raise()
        try:
            return await self._docker_call(client.containers.get, name)
        except ExecutorManagerError as exc:
            if docker_errors is not None and isinstance(exc.__cause__, docker_errors.NotFound):
                return None
            raise

    async def _container_status(self, container) -> Status:
        await self._docker_call(container.reload)
        status = getattr(container, "status", None)
        if status == "running":
            return "running"
        if status in {"created", "exited", "paused", "restarting"}:
            return "stopped"
        return "unknown"

    async def _resolve_host_port(self, container) -> str:
        await self._docker_call(container.reload)
        ports = ((container.attrs or {}).get("NetworkSettings") or {}).get("Ports") or {}
        bindings = ports.get("8811/tcp")
        if not bindings:
            raise ExecutorManagerError("Executor endpoint is not published")
        host_port = bindings[0].get("HostPort")
        if not host_port:
            raise ExecutorManagerError("Executor endpoint host port is missing")
        return str(host_port)

    async def _docker_call(self, fn, *args, **kwargs):
        try:
            return await asyncio.to_thread(fn, *args, **kwargs)
        except Exception as exc:
            if docker_errors is not None and isinstance(exc, docker_errors.DockerException):
                raise ExecutorManagerError(
                    "Docker is unavailable. Ensure Docker is installed and running."
                ) from exc
            raise

    def _client_or_raise(self):
        if docker is None:
            raise ExecutorManagerError(
                "Docker SDK is unavailable. Install the 'docker' Python package."
            )
        if self._client is None:
            try:
                self._client = docker.from_env()
            except Exception as exc:
                if docker_errors is not None and isinstance(exc, docker_errors.DockerException):
                    raise ExecutorManagerError(
                        "Docker is unavailable. Ensure Docker is installed and running."
                    ) from exc
                raise
        return self._client

    @staticmethod
    def _container_name(executor_id: str) -> str:
        return f"doti-exec-{executor_id}"
