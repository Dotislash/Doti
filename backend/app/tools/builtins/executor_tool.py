"""Built-in executor command tool."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from app.executor.manager import ExecutorManager, ExecutorManagerError
from app.executor.tools.shell import _BLOCKED_PATTERNS
from app.tools.base import BaseTool, RiskLevel, ToolResult

MAX_OUTPUT = 20_000  # chars
DEFAULT_TIMEOUT = 30  # seconds
MAX_TIMEOUT = 120  # seconds

_BLOCKED_RE = re.compile("|".join(_BLOCKED_PATTERNS), re.IGNORECASE)


class ExecutorRunTool(BaseTool):
    def __init__(self, executor_manager: ExecutorManager, workspace: str = ".") -> None:
        super().__init__(workspace=workspace)
        self._executor_manager = executor_manager

    @property
    def name(self) -> str:
        return "executor_run"

    @property
    def description(self) -> str:
        return "Execute a command inside a sandboxed executor container."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "executor_id": {"type": "string", "description": "Executor id to target"},
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 30, max 120)",
                    "default": DEFAULT_TIMEOUT,
                },
            },
            "required": ["executor_id", "command"],
        }

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.high

    async def execute(self, **kwargs: Any) -> ToolResult:
        executor_id = str(kwargs.get("executor_id", "")).strip()
        command = str(kwargs.get("command", ""))

        try:
            timeout = int(kwargs.get("timeout", DEFAULT_TIMEOUT))
        except (TypeError, ValueError):
            return ToolResult(output="Invalid timeout value", is_error=True)

        timeout = min(max(timeout, 1), MAX_TIMEOUT)

        if not executor_id:
            return ToolResult(output="Missing executor_id", is_error=True)
        if not command.strip():
            return ToolResult(output="Empty command", is_error=True)

        if _BLOCKED_RE.search(command):
            return ToolResult(
                output=f"Command blocked by safety filter: {command[:80]}",
                is_error=True,
            )

        try:
            exit_code, output = await asyncio.wait_for(
                self._executor_manager.execute_command(
                    executor_id=executor_id,
                    command=command,
                    timeout=timeout,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return ToolResult(output=f"Command timed out after {timeout}s", is_error=True)
        except ExecutorManagerError as exc:
            return ToolResult(output=str(exc), is_error=True)
        except Exception as exc:
            return ToolResult(output=str(exc), is_error=True)

        if len(output) > MAX_OUTPUT:
            output = output[:MAX_OUTPUT] + "\n... [truncated]"
        if not output:
            output = "(no output)"
        if exit_code != 0:
            output = f"[exit code {exit_code}]\n{output}"

        return ToolResult(output=output, is_error=exit_code != 0)
