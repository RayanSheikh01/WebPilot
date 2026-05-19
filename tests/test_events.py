import pytest

@pytest.mark.asyncio
async def test_event_creation():
    from webpilot.events import event_bus
    events_received = []

    async def test_listener(data):
        events_received.append(data)

    await event_bus.subscribe("test_event", test_listener)
    await event_bus.publish("test_event", {"key": "value"})

    assert len(events_received) == 1
    assert events_received[0] == {"key": "value"}

@pytest.mark.asyncio
async def test_multiple_listeners():
    from webpilot.events import event_bus
    events_received_1 = []
    events_received_2 = []

    async def listener_one(data):
        events_received_1.append(data)

    async def listener_two(data):
        events_received_2.append(data)

    await event_bus.subscribe("multi_event", listener_one)
    await event_bus.subscribe("multi_event", listener_two)
    await event_bus.publish("multi_event", {"multi": "data"})

    assert len(events_received_1) == 1
    assert len(events_received_2) == 1
    assert events_received_1[0] == {"multi": "data"}
    assert events_received_2[0] == {"multi": "data"}

@pytest.mark.asyncio
async def test_no_listeners():
    from webpilot.events import event_bus
    # This should not raise an error even if there are no listeners
    await event_bus.publish("no_listener_event", {"data": "test"})

@pytest.mark.asyncio
async def test_listener_order():
    from webpilot.events import event_bus
    events_received = []

    async def first_listener(data):
        events_received.append("first")

    async def second_listener(data):
        events_received.append("second")

    await event_bus.subscribe("order_event", first_listener)
    await event_bus.subscribe("order_event", second_listener)
    await event_bus.publish("order_event", {"order": "test"})

    assert events_received == ["first", "second"]
