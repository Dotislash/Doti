"""Routine management for automation triggers and event-driven actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable

from loguru import logger
from ulid import ULID

from app.automation.event_queue import Event, EventQueue, EventType, Subscription
from app.automation.triggers import Trigger


@dataclass(slots=True, kw_only=True)
class Routine:
    """A named automation rule that runs an async action on matching events."""

    name: str
    event_types: set[EventType]
    action: Callable[[Event], Awaitable[None]]
    routine_id: str = field(default_factory=lambda: str(ULID()))
    description: str = ""
    source_pattern: str | None = None
    enabled: bool = True


class RoutineManager:
    """Coordinates routine subscriptions, trigger lifecycle, and queue startup/shutdown."""

    def __init__(self, queue: EventQueue) -> None:
        self._queue = queue
        self._routines: dict[str, Routine] = {}
        self._triggers: dict[str, Trigger] = {}
        self._subscription_ids: dict[str, str] = {}

    def add_routine(self, routine: Routine) -> str:
        """Register a routine and subscribe it when enabled."""

        if routine.routine_id in self._routines:
            raise ValueError(f"routine already exists: {routine.routine_id}")

        self._routines[routine.routine_id] = routine
        if routine.enabled:
            subscription_id = self._subscribe_routine(routine)
            self._subscription_ids[routine.routine_id] = subscription_id

        logger.info("Added routine routine_id={} name={} enabled={}", routine.routine_id, routine.name, routine.enabled)
        return routine.routine_id

    def remove_routine(self, routine_id: str) -> bool:
        """Unsubscribe and remove a routine from the manager."""

        routine = self._routines.pop(routine_id, None)
        if routine is None:
            return False

        subscription_id = self._subscription_ids.pop(routine_id, None)
        if subscription_id is not None:
            self._queue.unsubscribe(subscription_id)

        logger.info("Removed routine routine_id={} name={}", routine_id, routine.name)
        return True

    def enable_routine(self, routine_id: str) -> bool:
        """Enable a routine and ensure it is subscribed."""

        routine = self._routines.get(routine_id)
        if routine is None:
            return False

        routine.enabled = True
        if routine_id not in self._subscription_ids:
            self._subscription_ids[routine_id] = self._subscribe_routine(routine)

        logger.info("Enabled routine routine_id={} name={}", routine_id, routine.name)
        return True

    def disable_routine(self, routine_id: str) -> bool:
        """Disable a routine and remove its active subscription."""

        routine = self._routines.get(routine_id)
        if routine is None:
            return False

        routine.enabled = False
        subscription_id = self._subscription_ids.pop(routine_id, None)
        if subscription_id is not None:
            self._queue.unsubscribe(subscription_id)

        logger.info("Disabled routine routine_id={} name={}", routine_id, routine.name)
        return True

    async def add_trigger(self, trigger: Trigger) -> str:
        """Register and start a trigger immediately."""

        if trigger.trigger_id in self._triggers:
            raise ValueError(f"trigger already exists: {trigger.trigger_id}")

        self._triggers[trigger.trigger_id] = trigger
        await trigger.start(self._queue)
        logger.info("Added trigger trigger_id={} type={}", trigger.trigger_id, type(trigger).__name__)
        return trigger.trigger_id

    async def remove_trigger(self, trigger_id: str) -> bool:
        """Stop and remove a trigger."""

        trigger = self._triggers.pop(trigger_id, None)
        if trigger is None:
            return False

        await trigger.stop()
        logger.info("Removed trigger trigger_id={} type={}", trigger_id, type(trigger).__name__)
        return True

    def list_routines(self) -> list[Routine]:
        """Return all registered routines."""

        return list(self._routines.values())

    def list_triggers(self) -> list[Trigger]:
        """Return all registered triggers."""

        return list(self._triggers.values())

    async def start(self) -> None:
        """Start the queue and then ensure all triggers are running."""

        await self._queue.start()
        for trigger in self._triggers.values():
            await trigger.start(self._queue)
        logger.info("Started routine manager routines={} triggers={}", len(self._routines), len(self._triggers))

    async def stop(self) -> None:
        """Stop all triggers and then stop the queue."""

        for trigger in self._triggers.values():
            try:
                await trigger.stop()
            except Exception:
                logger.exception("Failed to stop trigger trigger_id={}", trigger.trigger_id)
        await self._queue.stop()
        logger.info("Stopped routine manager")

    def _subscribe_routine(self, routine: Routine) -> str:
        async def _callback(event: Event) -> None:
            if not routine.enabled:
                return
            try:
                await routine.action(event)
            except Exception:
                logger.exception("Routine action failed routine_id={} event_id={}", routine.routine_id, event.event_id)

        subscription = Subscription(
            callback=_callback,
            event_types=set(routine.event_types),
            source_pattern=routine.source_pattern,
        )
        subscription_id = self._queue.subscribe(subscription)
        logger.debug(
            "Subscribed routine routine_id={} subscription_id={} event_types={} source_pattern={}",
            routine.routine_id,
            subscription_id,
            sorted(event_type.value for event_type in routine.event_types),
            routine.source_pattern,
        )
        return subscription_id
