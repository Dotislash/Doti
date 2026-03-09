"""Built-in shell execution tool."""

from __future__ import annotations

import asyncio
from typing import Any

from app.tools.base import BaseTool, RiskLevel, ToolResult

MAX_OUTPUT = 20_000  # chars
DEFAULT_TIMEOUT = 30  # seconds


class ShellExecTool(BaseTool):
    @property
    def name(self) -> str:
        return "shell_exec"

    @property
    def description(self) -> str:
        return "Execute a shell command and return stdout and stderr. Use for running scripts, installing packages, checking system state, etc."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 30, max 120)",
                    "default": DEFAULT_TIMEOUT,
                },
            },
            "required": ["command"],
        }

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.high

    async def execute(self, **kwargs: Any) -> ToolResult:
        command = kwargs.get("command", "")
        timeout = min(int(kwargs.get("timeout", DEFAULT_TIMEOUT)), 120)

        if not command.strip():
            return ToolResult(output="Empty command", is_error=True)

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            out = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")

            result_parts = []
            if out:
                result_parts.append(out)
            if err:
                result_parts.append(f"[stderr]\n{err}")

            output = "\n".join(result_parts) or "(no output)"

            if len(output) > MAX_OUTPUT:
                output = output[:MAX_OUTPUT] + "\n... [truncated]"

            if proc.returncode != 0:
                output = f"[exit code {proc.returncode}]\n{output}"

            return ToolResult(output=output, is_error=proc.returncode != 0)

        except asyncio.TimeoutError:
            proc.kill()  # type: ignore[possibly-undefined]
            return ToolResult(output=f"Command timed out after {timeout}s", is_error=True)
        except Exception as e:
            return ToolResult(output=str(e), is_error=True)
