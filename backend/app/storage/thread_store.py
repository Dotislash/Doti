from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import aiofiles


class ThreadStore:
    """JSONL storage for thread metadata and per-thread messages."""

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.metadata_path = self.base_dir / "data" / "threads.jsonl"
        self.threads_dir = self.base_dir / "data" / "threads"

        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        self.threads_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path.touch(exist_ok=True)

    def _thread_messages_path(self, thread_id: str) -> Path:
        return self.threads_dir / f"{thread_id}.jsonl"

    async def _load_threads(self) -> list[dict]:
        if not self.metadata_path.exists():
            return []

        async with aiofiles.open(self.metadata_path, mode="r", encoding="utf-8") as f:
            lines = await f.readlines()

        threads: list[dict] = []
        for line in lines:
            text = line.strip()
            if not text:
                continue
            threads.append(json.loads(text))
        return threads

    async def _write_threads(self, threads: list[dict]) -> None:
        async with aiofiles.open(self.metadata_path, mode="w", encoding="utf-8") as f:
            for thread in threads:
                await f.write(json.dumps(thread, ensure_ascii=False) + "\n")

    async def create(self, thread: dict) -> None:
        async with aiofiles.open(self.metadata_path, mode="a", encoding="utf-8") as f:
            await f.write(json.dumps(thread, ensure_ascii=False) + "\n")

    async def list_threads(self) -> list[dict]:
        return await self._load_threads()

    async def get(self, thread_id: str) -> dict | None:
        threads = await self._load_threads()
        for thread in threads:
            if thread.get("thread_id") == thread_id:
                return thread
        return None

    async def update_status(self, thread_id: str, status: str) -> None:
        threads = await self._load_threads()
        now = datetime.now(timezone.utc).isoformat()

        for thread in threads:
            if thread.get("thread_id") == thread_id:
                thread["status"] = status
                thread["updated_at"] = now

        await self._write_threads(threads)

    async def delete(self, thread_id: str) -> bool:
        threads = await self._load_threads()
        kept_threads = [t for t in threads if t.get("thread_id") != thread_id]
        deleted = len(kept_threads) != len(threads)

        if not deleted:
            return False

        await self._write_threads(kept_threads)

        thread_messages_path = self._thread_messages_path(thread_id)
        thread_messages_path.unlink(missing_ok=True)
        return True

    async def append_message(self, thread_id: str, message_id: str, role: str, content: str) -> None:
        message_path = self._thread_messages_path(thread_id)
        message_path.parent.mkdir(parents=True, exist_ok=True)
        message_path.touch(exist_ok=True)

        payload = {
            "id": message_id,
            "role": role,
            "content": content,
            "ts": int(datetime.now(timezone.utc).timestamp()),
        }
        async with aiofiles.open(message_path, mode="a", encoding="utf-8") as f:
            await f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    async def load_thread_messages(self, thread_id: str, n: int = 50) -> list[dict]:
        message_path = self._thread_messages_path(thread_id)
        if not message_path.exists() or n <= 0:
            return []

        async with aiofiles.open(message_path, mode="r", encoding="utf-8") as f:
            lines = await f.readlines()

        messages: list[dict] = []
        for line in lines[-n:]:
            text = line.strip()
            if not text:
                continue
            messages.append(json.loads(text))
        return messages
