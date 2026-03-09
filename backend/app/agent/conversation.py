"""In-memory conversation history manager."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.models import _new_message_id

if TYPE_CHECKING:
    from app.storage.message_store import MessageStore

SYSTEM_PROMPT = (
    "You are DOTI, a helpful AI assistant running locally on the user's machine. "
    "You are direct, concise, and technically capable. "
    "Respond in the same language the user writes in."
)

MAX_HISTORY = 50  # Keep last N messages to avoid token overflow


class ConversationManager:
    """Holds message history per conversation_id."""

    def __init__(self, store: MessageStore | None = None) -> None:
        self._histories: dict[str, list[dict[str, str]]] = {}
        self._store = store

    def get_messages(self, conversation_id: str) -> list[dict[str, str]]:
        """Return system prompt + conversation history."""
        history = self._histories.get(conversation_id, [])
        return [{"role": "system", "content": SYSTEM_PROMPT}] + history

    async def add_user_message(self, conversation_id: str, content: str) -> None:
        await self._add_message(conversation_id, "user", content)

    async def add_assistant_message(self, conversation_id: str, content: str) -> None:
        await self._add_message(conversation_id, "assistant", content)

    async def load_history(self, conversation_id: str) -> None:
        if self._store is None:
            return

        loaded = await self._store.load_recent(MAX_HISTORY)
        history: list[dict[str, str]] = []
        for message in loaded:
            role = message.get("role")
            content = message.get("content")
            if isinstance(role, str) and isinstance(content, str):
                history.append({"role": role, "content": content})

        self._histories[conversation_id] = history[-MAX_HISTORY:]

    async def _add_message(self, conversation_id: str, role: str, content: str) -> None:
        history = self._histories.setdefault(conversation_id, [])
        history.append({"role": role, "content": content})
        self._trim(conversation_id)

        if self._store is not None:
            await self._store.append(_new_message_id(), role, content)

    def _trim(self, conversation_id: str) -> None:
        history = self._histories.get(conversation_id)
        if history and len(history) > MAX_HISTORY:
            self._histories[conversation_id] = history[-MAX_HISTORY:]
