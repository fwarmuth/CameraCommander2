"""WebSocket fan-out hub.

A single in-memory event bus per running host process. Subscribers register
topic patterns (literal name or trailing ``*`` wildcard for prefix match per
``contracts/host-events.asyncapi.yaml``); publisher broadcasts to all matches.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


def _matches(pattern: str, topic: str) -> bool:
    if pattern == topic:
        return True
    if pattern.endswith("*"):
        return topic.startswith(pattern[:-1])
    return False

@dataclass(slots=True, eq=False)
class Subscriber:
    queue: asyncio.Queue[str] = field(default_factory=lambda: asyncio.Queue(maxsize=256))
    topics: set[str] = field(default_factory=set)

    def matches(self, topic: str) -> bool:
        return any(_matches(p, topic) for p in self.topics)

    def subscribe(self, patterns: list[str]) -> None:
        self.topics.update(patterns)

    def unsubscribe(self, patterns: list[str]) -> None:
        for p in patterns:
            self.topics.discard(p)


class EventBus:
    """In-memory topic-based event bus."""

    def __init__(self) -> None:
        self._subs: set[Subscriber] = set()
        self._lock = asyncio.Lock()

    async def register(self, sub: Subscriber) -> None:
        async with self._lock:
            self._subs.add(sub)

    async def unregister(self, sub: Subscriber) -> None:
        async with self._lock:
            self._subs.discard(sub)

    async def stream(self, sub: Subscriber) -> AsyncIterator[str]:
        """Yield JSON frames from the subscriber's queue indefinitely."""
        while True:
            yield await sub.queue.get()

    async def publish(self, topic: str, payload: Any) -> None:
...
        """Broadcast a message to all matching subscribers."""
        frame = json.dumps({"topic": topic, "payload": payload})
        async with self._lock:
            for sub in self._subs:
                if sub.matches(topic):
                    with contextlib.suppress(asyncio.QueueFull):
                        sub.queue.put_nowait(frame)

    @contextlib.asynccontextmanager
    async def subscribe(self, patterns: list[str]) -> AsyncIterator[asyncio.Queue[str]]:
        """Context manager for registering a temporary subscriber."""
        sub = Subscriber(topics=set(patterns))
        await self.register(sub)
        try:
            yield sub.queue
        finally:
            await self.unregister(sub)


__all__ = ["EventBus", "Subscriber"]
