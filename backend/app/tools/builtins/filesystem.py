"""Built-in filesystem tools — read, write, list directory."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.tools.base import BaseTool, RiskLevel, ToolResult


class ReadFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file at the given path."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative file path"},
            },
            "required": ["path"],
        }

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.low

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        try:
            content = Path(path).read_text(encoding="utf-8")
            if len(content) > 50_000:
                content = content[:50_000] + "\n... [truncated]"
            return ToolResult(output=content)
        except Exception as e:
            return ToolResult(output=str(e), is_error=True)


class WriteFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file. Creates the file if it doesn't exist, overwrites if it does."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative file path"},
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
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return ToolResult(output=f"Written {len(content)} bytes to {path}")
        except Exception as e:
            return ToolResult(output=str(e), is_error=True)


class ListDirectoryTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return "List files and directories at the given path."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to list", "default": "."},
            },
            "required": [],
        }

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.low

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", ".")
        try:
            entries = []
            for entry in sorted(os.listdir(path)):
                full = os.path.join(path, entry)
                kind = "dir" if os.path.isdir(full) else "file"
                entries.append(f"[{kind}] {entry}")
            if not entries:
                return ToolResult(output="(empty directory)")
            return ToolResult(output="\n".join(entries))
        except Exception as e:
            return ToolResult(output=str(e), is_error=True)
