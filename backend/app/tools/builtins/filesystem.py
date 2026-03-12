"""Built-in filesystem tools — read, write, list directory."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.tools.base import BaseTool, RiskLevel, ToolResult


def _resolve_safe(path_str: str, workspace: str) -> Path:
    """Resolve a path and ensure it stays within the workspace root."""
    ws = Path(workspace).resolve()
    target = (ws / path_str).resolve()
    if not (target == ws or str(target).startswith(str(ws) + os.sep)):
        raise PermissionError(f"Path escapes workspace: {path_str}")
    return target


class ReadFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file at the given path (relative to workspace)."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to workspace"},
            },
            "required": ["path"],
        }

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.low

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        try:
            resolved = _resolve_safe(path, self._workspace)
            content = resolved.read_text(encoding="utf-8")
            if len(content) > 50_000:
                content = content[:50_000] + "\n... [truncated]"
            return ToolResult(output=content)
        except PermissionError as e:
            return ToolResult(output=str(e), is_error=True)
        except Exception as e:
            return ToolResult(output=str(e), is_error=True)


class WriteFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file (relative to workspace). Creates the file if it doesn't exist."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to workspace"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        }

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.medium

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        try:
            resolved = _resolve_safe(path, self._workspace)
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
            return ToolResult(output=f"Written {len(content)} bytes to {path}")
        except PermissionError as e:
            return ToolResult(output=str(e), is_error=True)
        except Exception as e:
            return ToolResult(output=str(e), is_error=True)


class ListDirectoryTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return "List files and directories at the given path (relative to workspace)."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path relative to workspace", "default": "."},
            },
            "required": [],
        }

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.low

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", ".")
        try:
            resolved = _resolve_safe(path, self._workspace)
            entries = []
            for entry in sorted(os.listdir(resolved)):
                full = resolved / entry
                kind = "dir" if full.is_dir() else "file"
                entries.append(f"[{kind}] {entry}")
            if not entries:
                return ToolResult(output="(empty directory)")
            return ToolResult(output="\n".join(entries))
        except PermissionError as e:
            return ToolResult(output=str(e), is_error=True)
        except Exception as e:
            return ToolResult(output=str(e), is_error=True)
