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

    def __init__(
        self,
        bus: EventBus,
        camera: Any = None,
        tripod: Any = None,
        calibration: Any = None,
        safety: Any = None,
        disk: Any = None,
    ) -> None:
        self._bus = bus
        self.camera = camera
        self.tripod = tripod
        self.calibration = calibration
        self.safety = safety
        self.disk = disk
        self._lock = asyncio.Lock()
        self._active_job_id: str | None = None
        self._jobs: dict[str, Job] = {}
        self._stop_events: dict[str, asyncio.Event] = {}

    @property
    def active_job_id(self) -> str | None:
        return self._active_job_id

    def get(self, job_id: str) -> Job:
        if job_id not in self._jobs:
            raise ValueError(f"Job {job_id} not found")
        return self._jobs[job_id]

    async def wait(self, job_id: str) -> None:
        while self.get(job_id).status == JobStatus.running:
            await asyncio.sleep(0.1)

    async def open(self) -> None:
        if self.camera:
            await self.camera.open()
        if self.tripod:
            await self.tripod.open()

    async def close(self) -> None:
        if self.camera:
            await self.camera.close()
        if self.tripod:
            await self.tripod.close()

    async def start(self, kind: JobKind, config: Configuration) -> Job:
        if self._lock.locked():
            raise JobAlreadyRunningError("Another job is currently active")

        job_id = str(uuid.uuid4())
        job = Job(
            job_id=job_id,
            kind=kind,
            status=JobStatus.pending,
            created_at=datetime.now(tz=UTC),
        )

        self._jobs[job_id] = job
        self._stop_events[job_id] = asyncio.Event()
        self._active_job_id = job_id

        # Launch background task
        asyncio.create_task(self._run_job(job_id, kind, config))

        return job

    async def _run_job(self, job_id: str, kind: JobKind, config: Configuration) -> None:
        job = self._jobs[job_id]
        async with self._lock:
            try:
                if kind == JobKind.timelapse:
                    from .timelapse import TimelapseRunner

                    runner = TimelapseRunner(
                        self.camera, self.tripod, self.safety, self.disk
                    )
                    await runner.run(job, config, self._stop_events[job_id])
                # Add other kinds later
            except Exception as exc:
                from ..core.models import FaultEvent

                job.status = JobStatus.failed
                job.fault = FaultEvent(code="error", message=str(exc))
            finally:
                job.finished_at = datetime.now(tz=UTC)
                await self._publish_job(job)
                self._active_job_id = None
                self._stop_events.pop(job_id, None)

    async def _publish_job(self, job: Job) -> None:
        await self._bus.publish(f"job.{job.job_id}.state", job.model_dump())

    async def stop(self, job_id: str) -> None:
        if ev := self._stop_events.get(job_id):
            ev.set()
