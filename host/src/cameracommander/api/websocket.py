"""WebSocket fan-out hub.

A single in-memory event bus per running host process. Subscribers register
topic patterns (literal name or trailing ``*`` wildcard for prefix match per
``contracts/host-events.asyncapi.yaml``); publishers call :meth:`EventBus.publish`
with a topic + JSON-serialisable payload, and the bus dispatches to matching
subscriber queues.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from ..core.logging import logger


def _matches(topic: str, pattern: str) -> bool:
    """Match a topic against a pattern. Trailing ``*`` is a prefix wildcard."""

    if pattern == topic:
        return True
    if pattern.endswith("*"):
        return topic.startswith(pattern[:-1])
    return False


@dataclass(slots=True)
class Subscriber:
    queue: asyncio.Queue[str] = field(default_factory=lambda: asyncio.Queue(maxsize=256))
    topics: set[str] = field(default_factory=set)

    def matches(self, topic: str) -> bool:
        return any(_matches(topic, p) for p in self.topics)

    def subscribe(self, topics: list[str]) -> None:
        self.topics.update(topics)

    def unsubscribe(self, topics: list[str]) -> None:
        for t in topics:
            self.topics.discard(t)


class EventBus:
    """In-process pub-sub for ``/ws/events``."""

    def __init__(self) -> None:
        self._subs: set[Subscriber] = set()
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Broadcast ``{topic, payload}`` to every subscriber whose pattern matches."""

        frame = json.dumps({"topic": topic, "payload": payload}, default=str)
        async with self._lock:
            targets = [s for s in self._subs if s.matches(topic)]
        for sub in targets:
            try:
                sub.queue.put_nowait(frame)
            except asyncio.QueueFull:
                logger.warning("websocket subscriber queue full; dropping frame for {}", topic)

    async def register(self, sub: Subscriber) -> None:
        async with self._lock:
            self._subs.add(sub)

    async def unregister(self, sub: Subscriber) -> None:
        async with self._lock:
            self._subs.discard(sub)

    async def stream(self, sub: Subscriber) -> AsyncIterator[str]:
        """Yield outbound frames for one subscriber as long as the connection lives."""

        try:
            while True:
                frame = await sub.queue.get()
                yield frame
        finally:
            with contextlib.suppress(Exception):
                await self.unregister(sub)


__all__ = ["EventBus", "Subscriber"]
