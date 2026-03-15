"""In-memory conversation history manager."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING

from loguru import logger

from app.core.models import _new_message_id
from app.memory.context_builder import ContextBuilder
from app.memory.store import MemoryStore

if TYPE_CHECKING:
    from app.agent.provider_client import ProviderClient
    from app.storage.message_store import MessageStore
    from app.storage.thread_store import ThreadStore

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
        workspace: str = ".",
    ) -> None:
        self._histories: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
        self._store = store
        self._thread_store = thread_store
        self._context = ContextBuilder(workspace)
        self._memory = MemoryStore(workspace)
        self._consolidating: set[str] = set()

    def has_conversation(self, conversation_id: str) -> bool:
        return conversation_id in self._histories

    def get_messages(self, conversation_id: str) -> list[dict[str, str]]:
        """Return system prompt (with memory) + conversation history."""
        history = self._histories.get(conversation_id, [])
        if conversation_id in self._histories:
            self._histories.move_to_end(conversation_id)
        system_prompt = self._context.build_system_prompt()
        return [{"role": "system", "content": system_prompt}] + history

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

    async def consolidate_if_needed(
        self, conversation_id: str, provider: ProviderClient
    ) -> None:
        """Trigger LLM-driven memory consolidation if conversation is long enough."""
        if conversation_id in self._consolidating:
            return
        history = self._histories.get(conversation_id)
        if not history or len(history) < COMPRESS_THRESHOLD:
            return

        self._consolidating.add(conversation_id)
        try:
            keep_count = MAX_HISTORY // 2
            old_messages = history[:-keep_count] if len(history) > keep_count else []
            if not old_messages:
                return

            success = await self._memory.consolidate(old_messages, provider)
            if success:
                self._histories[conversation_id] = history[-keep_count:]
                logger.info(
                    "Consolidated {} messages for {}, kept {}",
                    len(old_messages), conversation_id, keep_count,
                )
            else:
                logger.warning("Consolidation failed for {}, falling back to trim", conversation_id)
                self._trim_fallback(conversation_id)
        except Exception:
            logger.exception("Consolidation error for {}", conversation_id)
            self._trim_fallback(conversation_id)
        finally:
            self._consolidating.discard(conversation_id)

    def _trim(self, conversation_id: str) -> None:
        """Hard cap: if history exceeds MAX_HISTORY, truncate oldest."""
        history = self._histories.get(conversation_id)
        if history and len(history) > MAX_HISTORY:
            self._histories[conversation_id] = history[-MAX_HISTORY:]

    def _trim_fallback(self, conversation_id: str) -> None:
        """Fallback compression when LLM consolidation fails."""
        history = self._histories.get(conversation_id)
        if not history or len(history) <= COMPRESS_THRESHOLD:
            return
        keep_count = MAX_HISTORY // 2
        old = history[:-keep_count]
        summary_lines: list[str] = []
        for m in old:
            role = m.get("role", "unknown")
            content = m.get("content", "")
            if isinstance(content, str):
                snippet = content[:100] + ("..." if len(content) > 100 else "")
                summary_lines.append(f"- {role}: {snippet}")
        summary = "\n".join(summary_lines)
        summary_msg = {"role": "system", "content": f"{SUMMARY_HEADER}\n{summary}"}
        self._histories[conversation_id] = [summary_msg] + history[-keep_count:]
