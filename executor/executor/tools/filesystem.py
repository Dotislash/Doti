"""Filesystem tools for the doti-executor MCP server."""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP

MAX_READ_CHARS = 100_000
RTK_BINARY = shutil.which("rtk")


def _resolve(path: str, workspace: str) -> Path:
    """Resolve path relative to workspace. All paths are workspace-relative."""
    ws = Path(workspace).resolve()
    target = (ws / path).resolve()
    # Defense-in-depth: even inside Docker, prevent escaping mount
    if not (target == ws or str(target).startswith(str(ws) + os.sep)):
        raise PermissionError(f"Path escapes workspace: {path}")
    return target


async def _rtk_read(path: str, workspace: str) -> str:
    """Read file via RTK for token-compressed output."""
    proc = await asyncio.create_subprocess_exec(
        RTK_BINARY, "read", path,
        cwd=workspace,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"rtk read failed: {err}")
    return stdout.decode("utf-8", errors="replace")


def register(mcp: FastMCP, workspace: str = "/workspace") -> None:

    @mcp.tool()
    async def read_file(path: str, ctx: Context | None = None) -> str:
        """Read a file from the workspace. Path is relative to workspace root."""
        target = _resolve(path, workspace)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        if ctx:
            await ctx.info(f"read_file path={path}")

        # Use RTK for compressed output if available
        if RTK_BINARY:
            try:
                return await _rtk_read(path, workspace)
            except Exception:
                pass  # Fallback to direct read

        content = target.read_text(encoding="utf-8", errors="replace")
        if len(content) > MAX_READ_CHARS:
            content = content[:MAX_READ_CHARS] + f"\n... [truncated, {len(content)} total chars]"
        return content

    @mcp.tool()
    async def write_file(path: str, content: str, ctx: Context | None = None) -> str:
        """Write content to a file in the workspace. Creates parent directories if needed."""
        target = _resolve(path, workspace)

        if ctx:
            await ctx.info(f"write_file path={path} ({len(content)} chars)")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Written {len(content)} chars to {path}"

    @mcp.tool()
    async def list_dir(path: str = ".", ctx: Context | None = None) -> str:
        """List directory contents. Path is relative to workspace root."""
        target = _resolve(path, workspace)
        if not target.is_dir():
            raise FileNotFoundError(f"Directory not found: {path}")

        if ctx:
            await ctx.info(f"list_dir path={path}")

        # Use RTK for compressed listing if available
        if RTK_BINARY:
            try:
                proc = await asyncio.create_subprocess_exec(
                    RTK_BINARY, "ls", "-la", str(target),
                    cwd=workspace,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
                if proc.returncode == 0:
                    return stdout.decode("utf-8", errors="replace")
            except Exception:
                pass  # Fallback

        entries = []
        for entry in sorted(target.iterdir()):
            kind = "d" if entry.is_dir() else "f"
            size = entry.stat().st_size if entry.is_file() else 0
            entries.append(f"[{kind}] {entry.name}  ({size})")
        return "\n".join(entries) if entries else "(empty directory)"

    @mcp.tool()
    async def find_files(pattern: str, path: str = ".", ctx: Context | None = None) -> str:
        """Find files matching a glob pattern in the workspace."""
        target = _resolve(path, workspace)
        if not target.is_dir():
            raise FileNotFoundError(f"Directory not found: {path}")

        if ctx:
            await ctx.info(f"find_files pattern={pattern} path={path}")

        # Use RTK find if available
        if RTK_BINARY:
            try:
                proc = await asyncio.create_subprocess_exec(
                    RTK_BINARY, "find", pattern,
                    cwd=str(target),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
                if proc.returncode == 0:
                    return stdout.decode("utf-8", errors="replace")
            except Exception:
                pass  # Fallback

        matches = list(target.rglob(pattern))
        if not matches:
            return f"No files matching '{pattern}'"

        # Limit results
        MAX_RESULTS = 200
        lines = [str(m.relative_to(target)) for m in matches[:MAX_RESULTS]]
        if len(matches) > MAX_RESULTS:
            lines.append(f"... and {len(matches) - MAX_RESULTS} more")
        return "\n".join(lines)
