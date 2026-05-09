"""Timelapse orchestration loop."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..core.config import Configuration
from ..core.models import Job, JobStatus, Angles
from ..hardware.camera.base import CameraAdapter
from ..hardware.tripod.base import TripodAdapter
from .safety import SafetyService
from .disk import DiskGuard
from .metadata import MetadataWriter

def _linear_interpolate(start: float, target: float, current: int, total: int) -> float:
    """Linearly interpolate between start and target."""
    if total <= 1:
        return start
    return start + (target - start) * (current / (total - 1))


class TimelapseRunner:
    def __init__(
        self,
        camera: CameraAdapter,
        tripod: TripodAdapter,
        safety: SafetyService,
        disk: DiskGuard,
    ) -> None:
        self.camera = camera
        self.tripod = tripod
        self.safety = safety
        self.disk = disk

    async def run(self, job: Job, config: Configuration, stop_event: asyncio.Event) -> None:
        job.status = JobStatus.running
        job.started_at = datetime.now(tz=UTC)

        output_dir = Path(config.output.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        meta_writer = MetadataWriter(output_dir / "metadata.csv")

        total = config.sequence.total_frames
        interval = timedelta(seconds=config.sequence.interval_s)

        for i in range(total):
            if stop_event.is_set():
                job.status = JobStatus.stopped
                break

            loop_start = datetime.now(tz=UTC)

            # 1. Capture
            await self.camera.capture_still()

            # 2. Metadata
            current_pan = _linear_interpolate(
                config.sequence.start.pan_deg,
                config.sequence.target.pan_deg,
                i,
                total,
            )
            current_tilt = _linear_interpolate(
                config.sequence.start.tilt_deg,
                config.sequence.target.tilt_deg,
                i,
                total,
            )
            meta_writer.add_frame(i, current_pan, current_tilt)

            # 3. Move for next frame
            if i < total - 1:
                next_pan = _linear_interpolate(
                    config.sequence.start.pan_deg,
                    config.sequence.target.pan_deg,
                    i + 1,
                    total,
                )
                next_tilt = _linear_interpolate(
                    config.sequence.start.tilt_deg,
                    config.sequence.target.tilt_deg,
                    i + 1,
                    total,
                )
                self.safety.guard_move(next_pan, next_tilt)
                await self.tripod.move_to(next_pan, next_tilt)
            
            # 4. Progress
            job.progress.frames_completed = i + 1
            job.progress.frames_total = total
            
            # 5. Cadence wait
            elapsed = datetime.now(tz=UTC) - loop_start
            wait_time = (interval - elapsed).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        if job.status == JobStatus.running:
            job.status = JobStatus.completed
