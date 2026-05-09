"""Single-job orchestration service."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Literal

from ..api.websocket import EventBus
from ..core.config import Configuration
from ..core.errors import CalibrationRequiredError, JobAlreadyRunningError
from ..core.models import FaultEvent, Job, JobKind, JobStatus
from ..hardware.camera.base import CameraAdapter
from ..hardware.tripod.base import TripodAdapter
from ..persistence.sessions_fs import SessionRepository
from .calibration import CalibrationService
from .post_process import VideoAssembler
from .timelapse import TimelapseRunner
from .video_pan import VideoPanRunner


class JobManager:
    def __init__(
        self,
        *,
        camera: CameraAdapter,
        tripod: TripodAdapter | None,
        calibration: CalibrationService,
        sessions: SessionRepository,
        event_bus: EventBus | None = None,
    ) -> None:
        self.camera = camera
        self.tripod = tripod
        self.calibration = calibration
        self.sessions = sessions
        self.event_bus = event_bus
        self._jobs: dict[str, Job] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._stop_events: dict[str, asyncio.Event] = {}
        self._active_job_id: str | None = None
        self._lock = asyncio.Lock()

    async def open(self) -> None:
        await self.camera.open()
        if self.tripod is not None:
            await self.tripod.open()

    async def close(self) -> None:
        if self.tripod is not None:
            await self.tripod.close()
        await self.camera.close()

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def active(self) -> Job | None:
        return self._jobs.get(self._active_job_id) if self._active_job_id else None

    async def wait(self, job_id: str) -> None:
        task = self._tasks.get(job_id)
        if task is not None:
            await task

    async def stop(self, job_id: str) -> Job:
        job = self._jobs[job_id]
        event = self._stop_events.get(job_id)
        if event is not None:
            event.set()
        await self.wait(job_id)
        return job

    async def start(self, kind: Literal["timelapse", "video_pan"], config: Configuration) -> Job:
        if not self.calibration.is_homed:
            raise CalibrationRequiredError("calibration is unknown")
        async with self._lock:
            if self._active_job_id is not None:
                raise JobAlreadyRunningError(
                    "another job is already running",
                    active_job_id=self._active_job_id,
                )
            job = Job(
                job_id=str(uuid.uuid4()),
                kind=JobKind(kind),
                status=JobStatus.running,
                progress={"frames_total": getattr(config.sequence, "total_frames", 0)},
            )
            self._jobs[job.job_id] = job
            self._active_job_id = job.job_id
            stop_event = asyncio.Event()
            self._stop_events[job.job_id] = stop_event
            task = asyncio.create_task(self._run(job, config, stop_event))
            self._tasks[job.job_id] = task
            return job

    async def _publish_job(self, job: Job) -> None:
        if self.event_bus is not None:
            await self.event_bus.publish(
                f"job.{job.job_id}.state",
                job.model_dump(mode="json"),
            )
            await self.event_bus.publish(
                f"job.{job.job_id}.progress",
                job.progress.model_dump(mode="json"),
            )

    async def _run(self, job: Job, config: Configuration, stop_event: asyncio.Event) -> None:
        try:
            if job.kind == JobKind.timelapse:
                runner = TimelapseRunner(
                    camera=self.camera,
                    tripod=self.tripod,
                    sessions=self.sessions,
                    assembler=VideoAssembler(self.event_bus),
                )
                await runner.run(
                    job=job,
                    config=config,
                    stop_requested=stop_event,
                    publish_progress=self._publish_job,
                )
            else:
                runner = VideoPanRunner(
                    camera=self.camera,
                    tripod=self.tripod,
                    sessions=self.sessions,
                )
                await runner.run(
                    job=job,
                    config=config,
                    stop_requested=stop_event,
                    publish_progress=self._publish_job,
                )
        except Exception as exc:
            job.status = JobStatus.failed
            job.fault = FaultEvent(
                code=getattr(exc, "code", "camera_capture_failed"),
                message=str(exc),
                recoverable=False,
            )
            if self.event_bus is not None:
                await self.event_bus.publish(
                    f"job.{job.job_id}.fault",
                    job.fault.model_dump(mode="json"),
                )
        finally:
            job.finished_at = datetime.now(tz=UTC)
            await self._publish_job(job)
            self._active_job_id = None
            self._stop_events.pop(job.job_id, None)


__all__ = ["JobManager"]
