"""Automation trigger implementations for timer and file events."""

from __future__ import annotations

import abc
import asyncio
import contextlib
import datetime as dt
import fnmatch
from pathlib import Path

from loguru import logger

from app.automation.event_queue import Event, EventQueue, EventType


class Trigger(abc.ABC):
    """Base interface for all automation triggers."""

    @property
    @abc.abstractmethod
    def trigger_id(self) -> str:
        """Stable trigger identifier."""

    @abc.abstractmethod
    async def start(self, queue: EventQueue) -> None:
        """Start emitting events into the provided queue."""

    @abc.abstractmethod
    async def stop(self) -> None:
        """Stop background tasks and release resources."""


class IntervalTrigger(Trigger):
    """Emit timer events on a fixed interval."""

    def __init__(self, trigger_id: str, interval_seconds: float, source_name: str | None = None) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0")
        self._trigger_id = trigger_id
        self._interval_seconds = interval_seconds
        self._source_name = source_name
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    @property
    def trigger_id(self) -> str:
        return self._trigger_id

    async def start(self, queue: EventQueue) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(queue), name=f"interval-trigger:{self._trigger_id}")
        logger.info("Started IntervalTrigger trigger_id={} interval={}s", self._trigger_id, self._interval_seconds)

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        logger.info("Stopped IntervalTrigger trigger_id={}", self._trigger_id)

    async def _run(self, queue: EventQueue) -> None:
        source = f"interval:{self._source_name or self._trigger_id}"
        payload = {"trigger_id": self._trigger_id, "interval": self._interval_seconds}

        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._interval_seconds)
                break
            except asyncio.TimeoutError:
                await queue.publish(Event(event_type=EventType.TIMER_FIRED, source=source, payload=payload.copy()))


class CronTrigger(Trigger):
    """Emit a timer event once per day at a specific local time."""

    def __init__(self, trigger_id: str, hour: int, minute: int = 0, source_name: str | None = None) -> None:
        if hour < 0 or hour > 23:
            raise ValueError("hour must be between 0 and 23")
        if minute < 0 or minute > 59:
            raise ValueError("minute must be between 0 and 59")

        self._trigger_id = trigger_id
        self._hour = hour
        self._minute = minute
        self._source_name = source_name
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    @property
    def trigger_id(self) -> str:
        return self._trigger_id

    async def start(self, queue: EventQueue) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(queue), name=f"cron-trigger:{self._trigger_id}")
        logger.info("Started CronTrigger trigger_id={} at {:02d}:{:02d}", self._trigger_id, self._hour, self._minute)

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        logger.info("Stopped CronTrigger trigger_id={}", self._trigger_id)

    async def _run(self, queue: EventQueue) -> None:
        source = f"cron:{self._source_name or self._trigger_id}"
        payload = {"trigger_id": self._trigger_id, "hour": self._hour, "minute": self._minute}

        while not self._stop_event.is_set():
            sleep_seconds = self._seconds_until_next_fire()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=sleep_seconds)
                break
            except asyncio.TimeoutError:
                await queue.publish(Event(event_type=EventType.TIMER_FIRED, source=source, payload=payload.copy()))

    def _seconds_until_next_fire(self) -> float:
        now = dt.datetime.now()
        target = now.replace(hour=self._hour, minute=self._minute, second=0, microsecond=0)
        if target <= now:
            target = target + dt.timedelta(days=1)
        return (target - now).total_seconds()


class FileWatchTrigger(Trigger):
    """Emit file-changed events by polling a directory snapshot."""

    def __init__(
        self,
        trigger_id: str,
        watch_path: str,
        poll_interval: float = 5.0,
        patterns: list[str] | None = None,
    ) -> None:
        if poll_interval <= 0:
            raise ValueError("poll_interval must be > 0")

        self._trigger_id = trigger_id
        self._watch_path = Path(watch_path)
        self._poll_interval = poll_interval
        self._patterns = patterns
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._known_files: dict[str, float] = {}

    @property
    def trigger_id(self) -> str:
        return self._trigger_id

    async def start(self, queue: EventQueue) -> None:
        if self._task is not None and not self._task.done():
            return
        self._known_files = self._scan_files()
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(queue), name=f"file-watch-trigger:{self._trigger_id}")
        logger.info(
            "Started FileWatchTrigger trigger_id={} path={} poll_interval={}s",
            self._trigger_id,
            str(self._watch_path),
            self._poll_interval,
        )

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        logger.info("Stopped FileWatchTrigger trigger_id={}", self._trigger_id)

    async def _run(self, queue: EventQueue) -> None:
        source = f"file_watch:{self._watch_path}"

        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._poll_interval)
                break
            except asyncio.TimeoutError:
                pass

            current = self._scan_files()
            added = current.keys() - self._known_files.keys()
            removed = self._known_files.keys() - current.keys()
            maybe_modified = current.keys() & self._known_files.keys()

            for file_path in sorted(added):
                await queue.publish(
                    Event(
                        event_type=EventType.FILE_CHANGED,
                        source=source,
                        payload={
                            "trigger_id": self._trigger_id,
                            "path": file_path,
                            "change_type": "added",
                        },
                    )
                )

            for file_path in sorted(maybe_modified):
                if current[file_path] == self._known_files[file_path]:
                    continue
                await queue.publish(
                    Event(
                        event_type=EventType.FILE_CHANGED,
                        source=source,
                        payload={
                            "trigger_id": self._trigger_id,
                            "path": file_path,
                            "change_type": "modified",
                        },
                    )
                )

            for file_path in sorted(removed):
                await queue.publish(
                    Event(
                        event_type=EventType.FILE_CHANGED,
                        source=source,
                        payload={
                            "trigger_id": self._trigger_id,
                            "path": file_path,
                            "change_type": "deleted",
                        },
                    )
                )

            self._known_files = current

    def _scan_files(self) -> dict[str, float]:
        if not self._watch_path.exists() or not self._watch_path.is_dir():
            logger.warning("FileWatchTrigger path unavailable trigger_id={} path={}", self._trigger_id, str(self._watch_path))
            return {}

        files: dict[str, float] = {}
        for path in self._watch_path.rglob("*"):
            if not path.is_file():
                continue
            if not self._matches_patterns(path):
                continue
            try:
                files[str(path)] = path.stat().st_mtime
            except OSError:
                continue
        return files

    def _matches_patterns(self, path: Path) -> bool:
        if not self._patterns:
            return True

        rel_path = str(path.relative_to(self._watch_path))
        name = path.name
        for pattern in self._patterns:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(name, pattern):
                return True
        return False
