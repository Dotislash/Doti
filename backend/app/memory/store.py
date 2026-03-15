"""Two-layer memory: MEMORY.md (long-term facts) + HISTORY.md (searchable log).

Adapted from nanobot's memory system with LLM-driven consolidation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from app.agent.provider_client import ProviderClient

_SAVE_MEMORY_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save the memory consolidation result to persistent storage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "history_entry": {
                        "type": "string",
                        "description": (
                            "A paragraph (2-5 sentences) summarizing key events/decisions/topics. "
                            "Start with [YYYY-MM-DD HH:MM]. Include detail useful for grep search."
                        ),
                    },
                    "memory_update": {
                        "type": "string",
                        "description": (
                            "Full updated long-term memory as markdown. Include all existing "
                            "facts plus new ones. Return unchanged if nothing new."
                        ),
                    },
                },
                "required": ["history_entry", "memory_update"],
            },
        },
    }
]

_CONSOLIDATION_SYSTEM = (
    "You are a memory consolidation agent. "
    "Call the save_memory tool with your consolidation of the conversation."
)


class MemoryStore:
    """Two-layer memory: MEMORY.md (long-term facts) + HISTORY.md (grep-searchable log)."""

    def __init__(self, workspace: str | Path):
        workspace = Path(workspace)
        self.memory_dir = workspace / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.memory_dir / "MEMORY.md"
        self.history_file = self.memory_dir / "HISTORY.md"

    def read_long_term(self) -> str:
        if self.memory_file.exists():
            return self.memory_file.read_text(encoding="utf-8")
        return ""

    def write_long_term(self, content: str) -> None:
        self.memory_file.write_text(content, encoding="utf-8")

    def append_history(self, entry: str) -> None:
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(entry.rstrip() + "\n\n")

    def get_memory_context(self) -> str:
        """Return formatted memory content for system prompt injection."""
        long_term = self.read_long_term()
        if long_term:
            return f"## Long-term Memory\n\n{long_term}"
        return ""

    async def consolidate(
        self,
        messages: list[dict[str, Any]],
        provider: ProviderClient,
        *,
        archive_all: bool = False,
    ) -> bool:
        """Consolidate conversation messages into MEMORY.md + HISTORY.md via LLM.

        Returns True on success, False on failure.
        """
        if not messages:
            return True

        lines: list[str] = []
        for m in messages:
            content = m.get("content")
            if not content or not isinstance(content, str):
                continue
            role = m.get("role", "unknown").upper()
            lines.append(f"{role}: {content[:300]}")

        if not lines:
            return True

        current_memory = self.read_long_term()
        prompt = (
            "Process this conversation and call the save_memory tool "
            "with your consolidation.\n\n"
            f"## Current Long-term Memory\n{current_memory or '(empty)'}\n\n"
            f"## Conversation to Process\n" + "\n".join(lines)
        )

        try:
            result = await provider.chat_with_tools(
                messages=[
                    {"role": "system", "content": _CONSOLIDATION_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                tools=_SAVE_MEMORY_TOOL,
            )

            if not result.tool_calls:
                logger.warning("Memory consolidation: LLM did not call save_memory")
                return False

            raw_args = result.tool_calls[0].arguments
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            if not isinstance(args, dict):
                logger.warning("Memory consolidation: unexpected arguments type {}", type(args).__name__)
                return False

            if entry := args.get("history_entry"):
                if not isinstance(entry, str):
                    entry = json.dumps(entry, ensure_ascii=False)
                self.append_history(entry)

            if update := args.get("memory_update"):
                if not isinstance(update, str):
                    update = json.dumps(update, ensure_ascii=False)
                if update != current_memory:
                    self.write_long_term(update)

            logger.info("Memory consolidation done: {} messages processed", len(lines))
            return True

        except Exception:
            logger.exception("Memory consolidation failed")
            return False
