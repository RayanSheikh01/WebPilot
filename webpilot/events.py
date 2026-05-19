"""In-memory async pub/sub for brief lifecycle events.

The bus is intentionally tiny: per-`brief_id` fan-out via `asyncio.Queue`s. The
agent loop publishes synchronously (`publish` is not async), and HTTP/SSE
subscribers consume via `async for evt in bus.subscribe(brief_id)`.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncGenerator


@dataclass
class Event:
    """A single lifecycle event for a brief.

    JSON-serializable (callers stringify `ts` via `.isoformat()` as needed).
    """

    kind: str
    payload: dict
    ts: datetime
    id: int | None = None


# Sentinel pushed by `close()` to make subscribers exit cleanly.
_SENTINEL = object()


class EventBus:
    """Per-`brief_id` async fan-out bus."""

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = {}

    def publish(self, brief_id: str, event: Event) -> None:
        """Deliver `event` to every current subscriber of `brief_id`.

        Synchronous (no awaits) so it can be called from inside the
        agent tool-use loop without forcing every call site to be async.
        No-op if there are no subscribers. Never raises.
        """
        queues = self._queues.get(brief_id)
        if not queues:
            return
        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # Queues are unbounded by default; defensive only.
                pass

    async def subscribe(self, brief_id: str) -> AsyncGenerator[Event, None]:
        """Yield events for `brief_id` until the sentinel arrives or the
        consumer breaks/cancels. Always cleans up its queue on exit.
        """
        queue: asyncio.Queue = asyncio.Queue()
        self._queues.setdefault(brief_id, []).append(queue)
        try:
            while True:
                item = await queue.get()
                if item is _SENTINEL:
                    break
                yield item
        finally:
            queues = self._queues.get(brief_id)
            if queues is not None:
                try:
                    queues.remove(queue)
                except ValueError:
                    pass
                if not queues:
                    self._queues.pop(brief_id, None)

    def close(self, brief_id: str) -> None:
        """Signal every subscriber of `brief_id` to exit its loop."""
        queues = self._queues.get(brief_id)
        if not queues:
            return
        for q in queues:
            try:
                q.put_nowait(_SENTINEL)
            except asyncio.QueueFull:
                pass
