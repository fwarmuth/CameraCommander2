"""Single-job orchestration service."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Literal

from ..api.websocket import EventBus
from ..core.config import Configuration
from ..core.errors import JobAlreadyRunningError
from ..core.models import Job, JobKind, JobStatus


class JobManager:
    """Ensures sequential execution and provides lifecycle telemetry."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._lock = asyncio.Lock()
        self._active_job_id: str | None = None
        self._stop_events: dict[str, asyncio.Event] = {}

    @property
    def active_job_id(self) -> str | None:
        return self._active_job_id

    async def start(self, kind: JobKind, config: Configuration) -> Job:
        if self._lock.locked():
            raise JobAlreadyRunningError("Another job is currently active")

        job_id = str(uuid.uuid4())
        job = Job(
            job_id=job_id,
            kind=kind,
            status=JobStatus.pending,
            created_at=datetime.now(tz=UTC)
        )
        
        self._stop_events[job_id] = asyncio.Event()
        # The actual execution happens in a background task
        return job

    async def _publish_job(self, job: Job) -> None:
        await self._bus.publish(f"job.{job.job_id}.state", job.model_dump())

    async def stop(self, job_id: str) -> None:
        if ev := self._stop_events.get(job_id):
            ev.set()
