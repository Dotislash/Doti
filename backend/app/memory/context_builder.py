"""System prompt assembly with memory, skills, and runtime context."""

from __future__ import annotations

import platform
import time
from datetime import datetime
from pathlib import Path

from app.memory.store import MemoryStore


class ContextBuilder:
    """Assembles the system prompt from identity, memory, and runtime context."""

    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace)
        self.memory = MemoryStore(self.workspace)

    def build_system_prompt(self) -> str:
        parts = [self._identity()]

        memory_ctx = self.memory.get_memory_context()
        if memory_ctx:
            parts.append(memory_ctx)

        return "\n\n---\n\n".join(parts)

    def build_runtime_context(self) -> str:
        """Runtime metadata prepended to user message (not system prompt)."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        tz = time.strftime("%Z") or "UTC"
        return f"[Runtime Context]\nTime: {now} ({tz})\nWorkspace: {self.workspace}"

    def _identity(self) -> str:
        ws_path = str(self.workspace.resolve())
        system = platform.system()
        runtime = (
            f"{'macOS' if system == 'Darwin' else system} "
            f"{platform.machine()}, Python {platform.python_version()}"
        )

        return (
            "# DOTI\n\n"
            "You are DOTI, a helpful AI assistant running locally on the user's machine.\n"
            "You are direct, concise, and technically capable.\n"
            "Respond in the same language the user writes in.\n\n"
            f"## Runtime\n{runtime}\n\n"
            f"## Workspace\n"
            f"Your workspace is at: {ws_path}\n"
            f"- Long-term memory: {ws_path}/memory/MEMORY.md\n"
            f"- History log: {ws_path}/memory/HISTORY.md (grep-searchable)\n\n"
            "## Guidelines\n"
            "- State intent before tool calls, but NEVER predict results before receiving them.\n"
            "- Before modifying a file, read it first.\n"
            "- If a tool call fails, analyze the error before retrying.\n"
            "- Ask for clarification when the request is ambiguous."
        )
