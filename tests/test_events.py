import asyncio
from datetime import datetime

import pytest

from webpilot.events import Event, EventBus


def _make_event(kind: str = "test", payload: dict | None = None) -> Event:
    return Event(kind=kind, payload=payload or {}, ts=datetime.utcnow())


async def test_publish_no_subscribers_does_not_block_or_raise():
    bus = EventBus()
    # Should be a no-op; no subscribers registered.
    bus.publish("brief-1", _make_event())
    # Internal state should not have created an entry for brief-1.
    assert bus._queues.get("brief-1", []) == []


async def test_subscribe_yields_events_published_after_subscribe():
    bus = EventBus()
    received: list[Event] = []
    ready = asyncio.Event()

    async def consumer():
        ready.set()
        async for evt in bus.subscribe("brief-1"):
            received.append(evt)
            if len(received) >= 2:
                break

    task = asyncio.create_task(consumer())
    await ready.wait()
    # Give the subscriber a chance to register its queue.
    await asyncio.sleep(0.01)

    e1 = _make_event("a", {"i": 1})
    e2 = _make_event("b", {"i": 2})
    bus.publish("brief-1", e1)
    bus.publish("brief-1", e2)

    await asyncio.wait_for(task, timeout=1.0)
    assert received == [e1, e2]


async def test_multiple_subscribers_each_get_their_own_copy():
    bus = EventBus()
    received_a: list[Event] = []
    received_b: list[Event] = []
    ready = asyncio.Event()
    started = 0
    lock = asyncio.Lock()

    async def consumer(out: list[Event]):
        nonlocal started
        async for evt in bus.subscribe("brief-1"):
            async with lock:
                pass
            out.append(evt)
            break

    async def starter(out):
        nonlocal started
        async for evt in bus.subscribe("brief-1"):
            out.append(evt)
            break

    # Use a helper that signals when its queue is registered.
    async def consumer_signaled(out: list[Event], signal: asyncio.Event):
        agen = bus.subscribe("brief-1")
        # advance once to register the queue; we use anext on first iter
        signal.set()
        async for evt in agen:
            out.append(evt)
            break

    s1 = asyncio.Event()
    s2 = asyncio.Event()
    t1 = asyncio.create_task(consumer_signaled(received_a, s1))
    t2 = asyncio.create_task(consumer_signaled(received_b, s2))
    await s1.wait()
    await s2.wait()
    await asyncio.sleep(0.01)  # let both reach the queue.get

    evt = _make_event("fanout", {"x": 1})
    bus.publish("brief-1", evt)

    await asyncio.wait_for(asyncio.gather(t1, t2), timeout=1.0)
    assert received_a == [evt]
    assert received_b == [evt]


async def test_queue_removed_after_subscriber_exits():
    bus = EventBus()

    agen = bus.subscribe("brief-1")
    # Prime the generator so it registers its queue.
    fetch_task = asyncio.create_task(agen.__anext__())
    await asyncio.sleep(0.01)
    assert len(bus._queues.get("brief-1", [])) == 1

    bus.publish("brief-1", _make_event())
    await fetch_task  # consume the single event

    # Closing the async generator runs its finally block (queue cleanup).
    await agen.aclose()

    assert bus._queues.get("brief-1", []) == []


async def test_close_causes_all_subscribers_to_exit():
    bus = EventBus()
    received_a: list[Event] = []
    received_b: list[Event] = []

    async def consumer(out: list[Event]):
        async for evt in bus.subscribe("brief-1"):
            out.append(evt)

    t1 = asyncio.create_task(consumer(received_a))
    t2 = asyncio.create_task(consumer(received_b))
    await asyncio.sleep(0.01)

    e1 = _make_event("hello")
    bus.publish("brief-1", e1)
    await asyncio.sleep(0.01)

    bus.close("brief-1")

    await asyncio.wait_for(asyncio.gather(t1, t2), timeout=1.0)
    assert received_a == [e1]
    assert received_b == [e1]
    # And queues are cleaned up after subscribers exit.
    assert bus._queues.get("brief-1", []) == []


async def test_brief_id_isolation():
    bus = EventBus()
    received_a: list[Event] = []
    received_b: list[Event] = []

    async def consumer(brief_id: str, out: list[Event]):
        async for evt in bus.subscribe(brief_id):
            out.append(evt)

    ta = asyncio.create_task(consumer("A", received_a))
    tb = asyncio.create_task(consumer("B", received_b))
    await asyncio.sleep(0.01)

    evt_a = _make_event("for-a")
    bus.publish("A", evt_a)
    await asyncio.sleep(0.01)

    bus.close("A")
    bus.close("B")

    await asyncio.wait_for(asyncio.gather(ta, tb), timeout=1.0)
    assert received_a == [evt_a]
    assert received_b == []
