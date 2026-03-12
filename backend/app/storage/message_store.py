from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
from loguru import logger


class MessageStore:
    """Append-only JSONL message storage."""

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.store_path = self.base_dir / "data" / "main.jsonl"
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.touch(exist_ok=True)

    async def append(self, message_id: str, role: str, content: str) -> None:
        payload = {
            "id": message_id,
            "role": role,
            "content": content,
            "ts": int(datetime.now(timezone.utc).timestamp()),
        }
        await self.append_item(payload)

    async def append_item(self, item: dict) -> None:
        payload = dict(item)
        if "ts" not in payload:
            payload["ts"] = int(datetime.now(timezone.utc).timestamp())
        async with aiofiles.open(self.store_path, mode="a", encoding="utf-8") as f:
            await f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    async def load_recent(self, n: int = 50) -> list[dict]:
        if not self.store_path.exists():
            return []

        async with aiofiles.open(self.store_path, mode="r", encoding="utf-8") as f:
            lines = await f.readlines()

        if n <= 0:
            return []

        messages: list[dict] = []
        for line in lines[-n:]:
            text = line.strip()
            if not text:
                continue
            try:
                messages.append(json.loads(text))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed JSONL line in {}", self.store_path)
        return messages

    async def load_all(self) -> list[dict]:
        if not self.store_path.exists():
            return []

        async with aiofiles.open(self.store_path, mode="r", encoding="utf-8") as f:
            lines = await f.readlines()

        messages: list[dict] = []
        for line in lines:
            text = line.strip()
            if not text:
                continue
            try:
                messages.append(json.loads(text))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed JSONL line in {}", self.store_path)
        return messages
