from __future__ import annotations

import asyncio
from pathlib import Path

from ..core.config import Configuration, VideoPanSequenceConfig
from ..core.models import Job, JobProgress, JobStatus
from ..hardware.camera.base import CameraAdapter
from ..hardware.tripod.base import TripodAdapter
from ..persistence.sessions_fs import SessionRepository
from .safety import SafetyService


class VideoPanRunner:
    def __init__(
        self,
        *,
        camera: CameraAdapter,
        tripod: TripodAdapter | None,
        sessions: SessionRepository,
    ) -> None:
        self.camera = camera
        self.tripod = tripod
        self.sessions = sessions

    async def run(
        self,
        *,
        job: Job,
        config: Configuration,
        stop_requested: asyncio.Event,
        publish_progress,
    ) -> Job:
        sequence = config.sequence
        if not isinstance(sequence, VideoPanSequenceConfig):
            raise ValueError("VideoPanRunner requires a video_pan sequence")

        output_dir = Path(config.output.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        session = self.sessions.create(job.job_id, config)
        job.session_id = session.session_id
        job.status = JobStatus.running
        job.started_at = job.started_at or config.metadata.created_at
        job.progress = JobProgress(frames_total=0, motion_pct=0.0)

        safety = SafetyService.from_config(config)
        safety.validate_sequence(config)
        if self.tripod is not None:
            await self.tripod.move_to(
                sequence.start.pan_deg,
                sequence.start.tilt_deg,
                expected_duration_s=config.safety.move_timeout_margin_s,
            )
            job.last_position = sequence.start
        await publish_progress(job)

        if stop_requested.is_set():
            job.status = JobStatus.stopped
            return self._finish_session(job, session.session_id, duration_s=0.0)

        await self.camera.start_recording()
        try:
            if self.tripod is not None:
                await self.tripod.move_to(
                    sequence.target.pan_deg,
                    sequence.target.tilt_deg,
                    expected_duration_s=sequence.duration_s + config.safety.move_timeout_margin_s,
                )
            else:
                await asyncio.sleep(sequence.duration_s)
        finally:
            await self.camera.stop_recording()

        job.last_position = sequence.target
        job.progress.motion_pct = 1.0
        if job.status == JobStatus.running:
            job.status = JobStatus.completed

        video_path = output_dir / "video_pan.mock"
        video_path.write_text(
            f"mock video pan recording for session {session.session_id}\n",
            encoding="utf-8",
        )
        session = self.sessions.get(session.session_id)
        self.sessions.add_asset(
            session,
            path=video_path,
            kind="video",
            content_type="application/octet-stream",
        )
        return self._finish_session(job, session.session_id, duration_s=sequence.duration_s)

    def _finish_session(self, job: Job, session_id: str, *, duration_s: float) -> Job:
        session = self.sessions.get(session_id)
        session.status = job.status
        session.metrics.duration_s = duration_s
        self.sessions.save(session)
        return job


__all__ = ["VideoPanRunner"]
