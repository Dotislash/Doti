"""In-memory conversation history manager."""

from __future__ import annotations

SYSTEM_PROMPT = (
    "You are DOTI, a helpful AI assistant running locally on the user's machine. "
    "You are direct, concise, and technically capable. "
    "Respond in the same language the user writes in."
)

MAX_HISTORY = 50  # Keep last N messages to avoid token overflow


class ConversationManager:
    """Holds message history per conversation_id."""

    def __init__(self) -> None:
        self._histories: dict[str, list[dict[str, str]]] = {}

    def get_messages(self, conversation_id: str) -> list[dict[str, str]]:
        """Return system prompt + conversation history."""
        history = self._histories.get(conversation_id, [])
        return [{"role": "system", "content": SYSTEM_PROMPT}] + history

    def add_user_message(self, conversation_id: str, content: str) -> None:
        history = self._histories.setdefault(conversation_id, [])
        history.append({"role": "user", "content": content})
        self._trim(conversation_id)

    def add_assistant_message(self, conversation_id: str, content: str) -> None:
        history = self._histories.setdefault(conversation_id, [])
        history.append({"role": "assistant", "content": content})
        self._trim(conversation_id)

    def _trim(self, conversation_id: str) -> None:
        history = self._histories.get(conversation_id)
        if history and len(history) > MAX_HISTORY:
            self._histories[conversation_id] = history[-MAX_HISTORY:]
