from __future__ import annotations

import time
from pathlib import Path

import pytest

from cameracommander.core.config import Configuration
from cameracommander.hardware.camera.mock import MockCameraAdapter
from cameracommander.persistence.sessions_fs import SessionRepository
from cameracommander.services.calibration import CalibrationService
from cameracommander.services.jobs import JobManager


class DisconnectAfterFirstFrameCamera(MockCameraAdapter):
    async def capture_still(self, *, autofocus: bool = False):
        result = await super().capture_still(autofocus=autofocus)
        self.simulate_disconnect(True)
        return result


def _config(tmp_path: Path) -> Configuration:
    return Configuration.model_validate(
        {
            "metadata": {"name": "Fault window"},
            "camera": {},
            "tripod": {"serial": {"port": "socket://127.0.0.1:9999"}},
            "safety": {
                "tilt_min_deg": -45,
                "tilt_max_deg": 45,
                "disk_min_free_bytes": 0,
                "disk_avg_frame_bytes": 1,
            },
            "output": {
                "output_dir": str(tmp_path / "frames"),
                "video": {"assemble": False, "fps": 2},
            },
            "sequence": {
                "kind": "timelapse",
                "total_frames": 3,
                "interval_s": 0.01,
                "settle_time_s": 0.0,
                "start": {"pan_deg": 0, "tilt_deg": 0},
                "target": {"pan_deg": 1, "tilt_deg": 1},
            },
        }
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_camera_disconnect_fault_detected_within_five_seconds(tmp_path: Path) -> None:
    jobs = JobManager(
        camera=DisconnectAfterFirstFrameCamera(),
        tripod=None,
        calibration=CalibrationService(),
        sessions=SessionRepository(tmp_path / "sessions"),
    )
    jobs.calibration.mark_homed()
    await jobs.open()
    started = time.monotonic()
    try:
        job = await jobs.start("timelapse", _config(tmp_path))
        await jobs.wait(job.job_id)
    finally:
        await jobs.close()

    completed = jobs.get(job.job_id)
    assert completed is not None
    assert completed.status == "failed"
    assert completed.fault is not None
    assert time.monotonic() - started < 5.0
    assert len(list((tmp_path / "frames").glob("frame_*.jpg"))) == 1
