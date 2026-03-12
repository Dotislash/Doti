"""Shell execution tool for the doti-executor MCP server."""

from __future__ import annotations

import asyncio
import shlex
import shutil

from mcp.server.fastmcp import Context, FastMCP


DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 120
MAX_OUTPUT_CHARS = 50000
COMPOUND_TOKENS = ("|", "&&", "||", ";", ">", "<", "$(", "`", "\n")
RTK_BINARY = shutil.which("rtk")


def _is_compound_command(command: str) -> bool:
    return any(token in command for token in COMPOUND_TOKENS)


def _truncate_output(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text

    omitted = len(text) - limit
    return f"{text[:limit]}\n... [truncated {omitted} chars]"


def register(mcp: FastMCP, workspace: str = "/workspace") -> None:
    @mcp.tool()
    async def shell_exec(command: str, timeout: int = DEFAULT_TIMEOUT_SECONDS, ctx: Context | None = None) -> dict:
        """Execute a shell command in the container workspace."""
        if not command.strip():
            return {"exit_code": 1, "stdout": "", "stderr": "Command cannot be empty."}

        safe_timeout = max(1, min(int(timeout), MAX_TIMEOUT_SECONDS))
        is_compound = _is_compound_command(command)

        if ctx is not None:
            await ctx.info(
                f"shell_exec command={command!r} timeout={safe_timeout}s workspace={workspace} "
                f"rtk={'yes' if RTK_BINARY else 'no'} compound={'yes' if is_compound else 'no'}"
            )

        try:
            if is_compound:
                argv = ["sh", "-c", command]
            else:
                command_args = shlex.split(command)
                if RTK_BINARY:
                    argv = [RTK_BINARY, *command_args]
                else:
                    argv = command_args

            process = await asyncio.create_subprocess_exec(
                *argv,
                cwd=workspace,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except ValueError as exc:
            return {"exit_code": 1, "stdout": "", "stderr": f"Invalid command: {exc}"}
        except FileNotFoundError as exc:
            return {"exit_code": 1, "stdout": "", "stderr": f"Command not found: {exc}"}
        except Exception as exc:  # pragma: no cover - defensive path
            return {"exit_code": 1, "stdout": "", "stderr": f"Failed to start command: {exc}"}

        try:
            stdout_b, stderr_b = await asyncio.wait_for(process.communicate(), timeout=safe_timeout)
            exit_code = process.returncode
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            return {
                "exit_code": 124,
                "stdout": "",
                "stderr": f"Command timed out after {safe_timeout}s.",
            }

        stdout = _truncate_output(stdout_b.decode("utf-8", errors="replace"))
        stderr = _truncate_output(stderr_b.decode("utf-8", errors="replace"))

        if exit_code != 0:
            prefix = f"Command exited with code {exit_code}."
            stderr = f"{prefix}\n{stderr}" if stderr else prefix

        if ctx is not None:
            await ctx.info(f"shell_exec completed exit_code={exit_code}")

        return {"exit_code": exit_code, "stdout": stdout, "stderr": stderr}
