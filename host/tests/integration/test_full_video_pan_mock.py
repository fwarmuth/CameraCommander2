from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest

from cameracommander.core.config import Configuration
from cameracommander.core.models import TripodState, TripodStatus
from cameracommander.hardware.camera.mock import MockCameraAdapter
from cameracommander.hardware.tripod.base import MoveResult, StatusReport
from cameracommander.persistence.sessions_fs import SessionRepository
from cameracommander.services.calibration import CalibrationService
from cameracommander.services.jobs import JobManager


class RecordingMockCamera(MockCameraAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.recording_started_at: float | None = None
        self.recording_stopped_at: float | None = None

    async def start_recording(self) -> None:
        self.recording_started_at = time.monotonic()
        await super().start_recording()

    async def stop_recording(self) -> None:
        self.recording_stopped_at = time.monotonic()
        await super().stop_recording()


class TimedMockTripod:
    def __init__(self) -> None:
        self.pan = 0.0
        self.tilt = 0.0
        self.move_started_at: float | None = None
        self.move_finished_at: float | None = None
        self.duration_s = 0.05

    async def open(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def status(self) -> TripodStatus:
        return TripodStatus(
            state=TripodState.connected,
            firmware_version="1.0.1",
            drivers_enabled=True,
            position_pan_deg=self.pan,
            position_tilt_deg=self.tilt,
        )

    async def version(self) -> str:
        return "1.0.1"

    async def report(self) -> StatusReport:
        return StatusReport(self.pan, self.tilt, True)

    async def move_to(
        self,
        pan_deg: float,
        tilt_deg: float,
        *,
        expected_duration_s: float | None = None,
    ) -> MoveResult:
        self.move_started_at = time.monotonic()
        await asyncio.sleep(self.duration_s)
        self.pan = pan_deg
        self.tilt = tilt_deg
        self.move_finished_at = time.monotonic()
        return MoveResult(
            pan_deg=pan_deg,
            tilt_deg=tilt_deg,
            duration_s=(self.move_finished_at - self.move_started_at),
        )

    async def nudge(
        self,
        *,
        delta_pan_deg: float = 0.0,
        delta_tilt_deg: float = 0.0,
    ) -> MoveResult:
        return await self.move_to(self.pan + delta_pan_deg, self.tilt + delta_tilt_deg)

    async def home(self) -> None:
        self.pan = 0.0
        self.tilt = 0.0

    async def set_drivers(self, enabled: bool) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def set_microstep(self, microstep: int) -> None:
        return None


def _config(tmp_path: Path) -> Configuration:
    return Configuration.model_validate(
        {
            "metadata": {"name": "Mock video pan"},
            "camera": {},
            "tripod": {"serial": {"port": "socket://127.0.0.1:9999"}},
            "safety": {
                "tilt_min_deg": -45.0,
                "tilt_max_deg": 45.0,
                "move_timeout_margin_s": 0.2,
                "disk_min_free_bytes": 0,
                "disk_avg_frame_bytes": 1,
            },
            "output": {"output_dir": str(tmp_path / "output")},
            "sequence": {
                "kind": "video_pan",
                "duration_s": 0.05,
                "start": {"pan_deg": 0.0, "tilt_deg": 0.0},
                "target": {"pan_deg": 5.0, "tilt_deg": 2.0},
            },
        }
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_mock_video_pan_syncs_recording_and_motion(tmp_path: Path) -> None:
    camera = RecordingMockCamera()
    tripod = TimedMockTripod()
    calibration = CalibrationService()
    calibration.mark_homed()
    sessions = SessionRepository(tmp_path / "sessions")
    jobs = JobManager(
        camera=camera,
        tripod=tripod,
        calibration=calibration,
        sessions=sessions,
    )
    config = _config(tmp_path)

    await jobs.open()
    try:
        job = await jobs.start("video_pan", config)
        await jobs.wait(job.job_id)
    finally:
        await jobs.close()

    completed = jobs.get(job.job_id)
    assert completed is not None
    assert completed.status == "completed"
    assert camera.recording_started_at is not None
    assert camera.recording_stopped_at is not None
    assert tripod.move_started_at is not None
    assert tripod.move_finished_at is not None
    assert abs(camera.recording_started_at - tripod.move_started_at) < 0.5
    assert tripod.move_finished_at - tripod.move_started_at == pytest.approx(0.05, abs=0.05)
    assert camera.recording_stopped_at >= tripod.move_finished_at
    session = sessions.get(completed.session_id or completed.job_id)
    assert any(asset.kind == "video" for asset in session.assets)
