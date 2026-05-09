"""Timelapse capture runner."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterable
from pathlib import Path

from ..core.config import Angles, Configuration, TimelapseSequenceConfig
from ..core.models import Job, JobProgress, JobStatus
from ..hardware.camera.base import CameraAdapter
from ..hardware.tripod.base import TripodAdapter
from ..persistence.sessions_fs import SessionRepository
from .disk import DiskGuard
from .metadata import MetadataWriter
from .post_process import VideoAssembler
from .safety import SafetyService


def _linear_interpolate(
    *,
    start: Angles,
    target: Angles,
    total_frames: int,
) -> Iterable[Angles]:
    for index in range(total_frames):
        ratio = index / (total_frames - 1)
        yield Angles(
            pan_deg=start.pan_deg + (target.pan_deg - start.pan_deg) * ratio,
            tilt_deg=start.tilt_deg + (target.tilt_deg - start.tilt_deg) * ratio,
        )


class TimelapseRunner:
    def __init__(
        self,
        *,
        camera: CameraAdapter,
        tripod: TripodAdapter | None,
        sessions: SessionRepository,
        assembler: VideoAssembler,
    ) -> None:
        self.camera = camera
        self.tripod = tripod
        self.sessions = sessions
        self.assembler = assembler

    async def run(
        self,
        *,
        job: Job,
        config: Configuration,
        stop_requested: asyncio.Event,
        publish_progress,
    ) -> Job:
        sequence = config.sequence
        if not isinstance(sequence, TimelapseSequenceConfig):
            raise ValueError("TimelapseRunner requires a timelapse sequence")

        frames_dir = Path(config.output.output_dir)
        frames_dir.mkdir(parents=True, exist_ok=True)
        session = self.sessions.create(job.job_id, config)
        job.session_id = session.session_id
        job.status = JobStatus.running
        job.started_at = job.started_at or config.metadata.created_at
        job.progress = JobProgress(frames_total=sequence.total_frames)
        await publish_progress(job)

        safety = SafetyService.from_config(config)
        safety.validate_sequence(config)
        disk = DiskGuard(
            frames_dir,
            disk_min_free_bytes=config.safety.disk_min_free_bytes,
            initial_avg_frame_bytes=config.safety.disk_avg_frame_bytes,
        )
        metadata = MetadataWriter(frames_dir, strategy=config.output.metadata_strategy)
        running_avg = config.safety.disk_avg_frame_bytes
        total_bytes = 0
        cadence_overruns = 0
        points = list(
            _linear_interpolate(
                start=sequence.start,
                target=sequence.target,
                total_frames=sequence.total_frames,
            )
        )

        for index, point in enumerate(points):
            if stop_requested.is_set():
                job.status = JobStatus.stopped
                break

            cycle_started = time.monotonic()
            disk.assert_room_for_next_frame(
                frames_remaining=sequence.total_frames - index,
                running_avg_bytes=running_avg,
            )
            result = await self.camera.capture_still(autofocus=False)
            filename = config.output.frame_filename_template.format(
                index=index,
                ext=result.extension,
            )
            frame_path = frames_dir / filename
            frame_path.write_bytes(result.bytes_)
            total_bytes += len(result.bytes_)
            running_avg = max(1, total_bytes // (index + 1))

            metadata_path = metadata.write_frame(
                index=index,
                image_path=frame_path,
                pan_deg=point.pan_deg,
                tilt_deg=point.tilt_deg,
                config=config,
            )
            self.sessions.add_asset(
                session,
                path=frame_path,
                kind="frame",
                content_type=result.content_type,
            )
            if metadata_path.exists():
                self.sessions.add_asset(session, path=metadata_path, kind="metadata")

            job.progress.frames_completed = index + 1
            job.last_position = point
            await publish_progress(job)

            if index < len(points) - 1:
                next_point = points[index + 1]
                safety.guard_move(next_point.pan_deg, next_point.tilt_deg)
                if self.tripod is not None:
                    await self.tripod.move_to(
                        next_point.pan_deg,
                        next_point.tilt_deg,
                        expected_duration_s=config.safety.move_timeout_margin_s,
                    )
                elapsed = time.monotonic() - cycle_started
                remaining = sequence.interval_s - elapsed
                if remaining > 0:
                    await asyncio.sleep(max(sequence.settle_time_s, remaining))
                else:
                    cadence_overruns += 1

        job.cadence_warnings = cadence_overruns
        if job.status == JobStatus.running:
            job.status = JobStatus.completed

        session = self.sessions.get(session.session_id)
        session.status = job.status
        session.metrics.frames_captured = job.progress.frames_completed
        session.metrics.cadence_warnings = cadence_overruns
        session.frames_captured = job.progress.frames_completed
        session.flags["cadence_warning"] = (
            cadence_overruns > 0
            and cadence_overruns / max(sequence.total_frames, 1) > 0.2
        )
        if config.output.video.assemble and job.status == JobStatus.completed:
            video = await self.assembler.assemble(
                frames_dir=frames_dir,
                output=config.output,
                session_id=session.session_id,
            )
            self.sessions.add_asset(
                session,
                path=video,
                kind="video",
                content_type="video/mp4",
            )
        self.sessions.save(session)
        return job


__all__ = ["TimelapseRunner", "_linear_interpolate"]
