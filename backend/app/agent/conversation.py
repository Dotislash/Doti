"""In-memory conversation history manager."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING

from app.core.models import _new_message_id

if TYPE_CHECKING:
    from app.storage.message_store import MessageStore
    from app.storage.thread_store import ThreadStore

SYSTEM_PROMPT = (
    "You are DOTI, a helpful AI assistant running locally on the user's machine. "
    "You are direct, concise, and technically capable. "
    "Respond in the same language the user writes in."
)

MAX_HISTORY = 50  # Keep last N messages to avoid token overflow
MAX_CONVERSATIONS = 100  # Max in-memory conversations before LRU eviction
COMPRESS_THRESHOLD = 40
COMPRESS_BATCH = 20
SUMMARY_HEADER = "[Conversation summary]"


class ConversationManager:
    """Holds message history per conversation_id with LRU eviction."""

    def __init__(
        self,
        store: MessageStore | None = None,
        thread_store: ThreadStore | None = None,
    ) -> None:
        self._histories: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
        self._store = store
        self._thread_store = thread_store

    def has_conversation(self, conversation_id: str) -> bool:
        return conversation_id in self._histories

    def get_messages(self, conversation_id: str) -> list[dict[str, str]]:
        """Return system prompt + conversation history."""
        history = self._histories.get(conversation_id, [])
        if conversation_id in self._histories:
            self._histories.move_to_end(conversation_id)
        return [{"role": "system", "content": SYSTEM_PROMPT}] + history

    async def add_user_message(self, conversation_id: str, content: str) -> None:
        await self._add_message(conversation_id, "user", content)

    async def add_assistant_message(self, conversation_id: str, content: str) -> None:
        await self._add_message(conversation_id, "assistant", content)

    async def load_history(self, conversation_id: str) -> None:
        if conversation_id == "main":
            if self._store is None:
                return
            loaded = await self._store.load_recent(MAX_HISTORY)
        else:
            if self._thread_store is None:
                return
            loaded = await self._thread_store.load_thread_messages(
                conversation_id, MAX_HISTORY
            )

        history: list[dict[str, str]] = []
        for message in loaded:
            role = message.get("role")
            content = message.get("content")
            if isinstance(role, str) and isinstance(content, str):
                history.append({"role": role, "content": content})

        self._histories[conversation_id] = history[-MAX_HISTORY:]
        self._histories.move_to_end(conversation_id)
        self._evict()

    def _evict(self) -> None:
        """Evict oldest conversations if over limit, but never evict 'main'."""
        while len(self._histories) > MAX_CONVERSATIONS:
            # Pop oldest (first) entry, skip "main"
            oldest_key = next(iter(self._histories))
            if oldest_key == "main":
                # Move main to end and try next
                self._histories.move_to_end("main")
                oldest_key = next(iter(self._histories))
                if oldest_key == "main":
                    break  # Only main left
            self._histories.pop(oldest_key)

    async def _add_message(self, conversation_id: str, role: str, content: str) -> None:
        history = self._histories.setdefault(conversation_id, [])
        history.append({"role": role, "content": content})
        self._trim(conversation_id)
        self._histories.move_to_end(conversation_id)
        self._evict()

        message_id = _new_message_id()
        if conversation_id == "main":
            if self._store is not None:
                await self._store.append(message_id, role, content)
        elif self._thread_store is not None:
            await self._thread_store.append_message(
                conversation_id, message_id, role, content
            )

    def _trim(self, conversation_id: str) -> None:
        history = self._histories.get(conversation_id)
        if not history:
            return

        while len(history) > COMPRESS_THRESHOLD and len(history) >= COMPRESS_BATCH:
            old = history[:COMPRESS_BATCH]
            summary_lines: list[str] = []
            start_index = 0

            first = old[0]
            first_role = first.get("role")
            first_content = first.get("content")
            if (
                isinstance(first_role, str)
                and isinstance(first_content, str)
                and first_role == "system"
                and first_content.startswith(SUMMARY_HEADER)
            ):
                merged = first_content[len(SUMMARY_HEADER) :].lstrip("\n")
                if merged:
                    summary_lines.append(merged)
                start_index = 1

            for message in old[start_index:]:
                role = message.get("role")
                content = message.get("content")
                role_text = role if isinstance(role, str) else "unknown"
                content_text = content if isinstance(content, str) else ""
                snippet = content_text[:100]
                suffix = "..." if len(content_text) > 100 else ""
                summary_lines.append(f"- {role_text}: {snippet}{suffix}")

            summary = "\n".join(line for line in summary_lines if line)
            summary_msg = {
                "role": "system",
                "content": (
                    f"{SUMMARY_HEADER}\n{summary}" if summary else SUMMARY_HEADER
                ),
            }
            history = [summary_msg] + history[COMPRESS_BATCH:]

        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]

        self._histories[conversation_id] = history
