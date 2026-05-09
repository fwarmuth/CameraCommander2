from __future__ import annotations

import asyncio
import contextlib

from ..api.websocket import EventBus
from ..hardware.tripod.base import TripodAdapter
from .jobs import JobManager


class TripodPositionPublisher:
    """Periodically publish tripod position without owning motion control."""

    def __init__(
        self,
        *,
        tripod: TripodAdapter | None,
        jobs: JobManager,
        event_bus: EventBus,
    ) -> None:
        self.tripod = tripod
        self.jobs = jobs
        self.event_bus = event_bus
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self.tripod is None or self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop.set()
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        while not self._stop.is_set():
            if self.tripod is not None:
                status = await self.tripod.status()
                await self.event_bus.publish(
                    "tripod.position",
                    {
                        "pan_deg": status.position_pan_deg,
                        "tilt_deg": status.position_tilt_deg,
                        "drivers_enabled": status.drivers_enabled,
                    },
                )
            interval_s = 0.25 if self.jobs.active() is not None else 1.0
            await asyncio.sleep(interval_s)


__all__ = ["TripodPositionPublisher"]
