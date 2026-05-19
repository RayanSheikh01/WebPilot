class EventBus:
    def __init__(self):
        self.listeners = {}
    async def subscribe(self, event_name, callback):
        if event_name not in self.listeners:
            self.listeners[event_name] = []
        self.listeners[event_name].append(callback)

    async def publish(self, event_name, data):
        if event_name in self.listeners:
            for callback in self.listeners[event_name]:
                await callback(data)

event_bus = EventBus()
