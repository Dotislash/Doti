"""Tests for automation event queue, routine manager, and triggers."""

from __future__ import annotations

import asyncio

import pytest

from app.automation.event_queue import Event, EventQueue, EventType, Subscription
from app.automation.routines import Routine, RoutineManager
from app.automation.triggers import IntervalTrigger


@pytest.mark.asyncio
async def test_event_queue_publish_subscribe():
    queue = EventQueue()
    received: list[Event] = []

    async def callback(event: Event) -> None:
        received.append(event)

    queue.subscribe(Subscription(callback=callback))
    await queue.start()
    try:
        await queue.publish(Event(event_type=EventType.MANUAL, source="test:manual", payload={"k": "v"}))
        await asyncio.sleep(0.05)
        assert len(received) == 1
        assert received[0].event_type == EventType.MANUAL
    finally:
        await queue.stop()


@pytest.mark.asyncio
async def test_event_queue_filter_by_type():
    queue = EventQueue()
    received: list[Event] = []

    async def callback(event: Event) -> None:
        received.append(event)

    queue.subscribe(
        Subscription(
            callback=callback,
            event_types={EventType.TIMER_FIRED},
        )
    )
    await queue.start()
    try:
        await queue.publish(
            Event(event_type=EventType.FILE_CHANGED, source="file:watch", payload={"path": "x.txt"})
        )
        await asyncio.sleep(0.05)
        assert received == []
    finally:
        await queue.stop()


@pytest.mark.asyncio
async def test_event_queue_source_pattern():
    queue = EventQueue()
    received: list[Event] = []

    async def callback(event: Event) -> None:
        received.append(event)

    queue.subscribe(Subscription(callback=callback, source_pattern="cron:*"))
    await queue.start()
    try:
        await queue.publish(Event(event_type=EventType.TIMER_FIRED, source="interval:heartbeat", payload={}))
        await queue.publish(Event(event_type=EventType.TIMER_FIRED, source="cron:daily", payload={}))
        await asyncio.sleep(0.05)
        assert len(received) == 1
        assert received[0].source == "cron:daily"
    finally:
        await queue.stop()


@pytest.mark.asyncio
async def test_routine_manager_add_remove():
    queue = EventQueue()
    manager = RoutineManager(queue)

    async def action(_event: Event) -> None:
        return

    routine = Routine(name="r1", event_types={EventType.MANUAL}, action=action)
    routine_id = manager.add_routine(routine)

    routine_ids = {item.routine_id for item in manager.list_routines()}
    assert routine_id in routine_ids

    removed = manager.remove_routine(routine_id)
    assert removed is True
    assert all(item.routine_id != routine_id for item in manager.list_routines())


@pytest.mark.asyncio
async def test_routine_manager_enable_disable():
    queue = EventQueue()
    manager = RoutineManager(queue)
    calls: list[Event] = []

    async def action(event: Event) -> None:
        calls.append(event)

    routine = Routine(name="toggle", event_types={EventType.MANUAL}, action=action, enabled=True)
    routine_id = manager.add_routine(routine)

    await manager.start()
    try:
        assert manager.disable_routine(routine_id) is True
        await queue.publish(Event(event_type=EventType.MANUAL, source="manual:test", payload={}))
        await asyncio.sleep(0.05)
        assert calls == []

        assert manager.enable_routine(routine_id) is True
        await queue.publish(Event(event_type=EventType.MANUAL, source="manual:test", payload={}))
        await asyncio.sleep(0.05)
        assert len(calls) == 1
    finally:
        await manager.stop()


@pytest.mark.asyncio
async def test_interval_trigger_fires():
    queue = EventQueue()
    received: list[Event] = []

    async def callback(event: Event) -> None:
        received.append(event)

    queue.subscribe(
        Subscription(
            callback=callback,
            event_types={EventType.TIMER_FIRED},
            source_pattern="interval:*",
        )
    )

    trigger = IntervalTrigger(trigger_id="interval_test", interval_seconds=0.1)

    await queue.start()
    await trigger.start(queue)
    try:
        await asyncio.sleep(0.3)
        assert len(received) >= 2
        assert all(event.event_type == EventType.TIMER_FIRED for event in received)
    finally:
        await trigger.stop()
        await queue.stop()


@pytest.mark.asyncio
async def test_routine_manager_lifecycle():
    queue = EventQueue()
    manager = RoutineManager(queue)
    calls: list[Event] = []

    async def action(event: Event) -> None:
        calls.append(event)

    manager.add_routine(Routine(name="life", event_types={EventType.MANUAL}, action=action))

    await manager.start()
    await queue.publish(Event(event_type=EventType.MANUAL, source="manual:lifecycle", payload={}))
    await asyncio.sleep(0.05)
    assert len(calls) == 1

    await manager.stop()
