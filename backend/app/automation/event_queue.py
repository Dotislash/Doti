"""Async event queue for automation triggers and routines."""

from __future__ import annotations

import asyncio
import fnmatch
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable

from ulid import ULID


logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Supported event categories for the automation system."""

    TIMER_FIRED = "timer_fired"
    FILE_CHANGED = "file_changed"
    CHAT_COMPLETED = "chat_completed"
    MANUAL = "manual"
    SYSTEM = "system"


@dataclass(slots=True)
class Event:
    """Event data emitted by triggers and consumed by subscriptions."""

    event_type: EventType
    source: str
    payload: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(ULID()))


@dataclass(slots=True)
class Subscription:
    """Subscription rule and async callback for matching events."""

    callback: Callable[[Event], Awaitable[None]]
    subscription_id: str = field(default_factory=lambda: str(ULID()))
    event_types: set[EventType] = field(default_factory=set)
    source_pattern: str | None = None


class EventQueue:
    """In-memory async queue with basic publish/subscribe routing."""

    def __init__(self, maxsize: int = 1000) -> None:
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=maxsize)
        self._subscriptions: dict[str, Subscription] = {}
        self._consumer_task: asyncio.Task[None] | None = None

    async def publish(self, event: Event) -> None:
        """Publish an event to the internal queue."""

        await self._queue.put(event)

    def subscribe(self, subscription: Subscription) -> str:
        """Register a subscription and return its identifier."""

        self._subscriptions[subscription.subscription_id] = subscription
        return subscription.subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription by id."""

        return self._subscriptions.pop(subscription_id, None) is not None

    async def start(self) -> None:
        """Start the queue consumer as a background task."""

        if self._consumer_task is not None and not self._consumer_task.done():
            return
        self._consumer_task = asyncio.create_task(self._consume_loop(), name="event-queue-consumer")

    async def stop(self) -> None:
        """Stop the queue consumer task."""

        if self._consumer_task is None:
            return
        self._consumer_task.cancel()
        try:
            await self._consumer_task
        except asyncio.CancelledError:
            pass
        finally:
            self._consumer_task = None

    async def _consume_loop(self) -> None:
        """Continuously dispatch events to matching subscriptions."""

        while True:
            event = await self._queue.get()
            try:
                for subscription in tuple(self._subscriptions.values()):
                    if not self._matches(subscription, event):
                        continue
                    try:
                        await subscription.callback(event)
                    except Exception:
                        logger.exception(
                            "Event handler failed for subscription_id=%s event_id=%s",
                            subscription.subscription_id,
                            event.event_id,
                        )
            finally:
                self._queue.task_done()

    @staticmethod
    def _matches(subscription: Subscription, event: Event) -> bool:
        if subscription.event_types and event.event_type not in subscription.event_types:
            return False
        if subscription.source_pattern and not fnmatch.fnmatch(event.source, subscription.source_pattern):
            return False
        return True
