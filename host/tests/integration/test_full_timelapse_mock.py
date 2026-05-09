from __future__ import annotations

from pathlib import Path

import pytest

from cameracommander.core.config import Configuration
from cameracommander.hardware.camera.mock import MockCameraAdapter
from cameracommander.hardware.tripod.serial_adapter import SerialTripodAdapter
from cameracommander.mock_firmware.server import MockFirmwareServer
from cameracommander.persistence.sessions_fs import SessionRepository
from cameracommander.services.calibration import CalibrationService
from cameracommander.services.jobs import JobManager


def _config(tmp_path: Path, port: int) -> Configuration:
    return Configuration.model_validate(
        {
            "metadata": {"name": "Mock timelapse"},
            "camera": {},
            "tripod": {"serial": {"port": f"socket://127.0.0.1:{port}"}},
            "safety": {
                "tilt_min_deg": -45.0,
                "tilt_max_deg": 45.0,
                "disk_min_free_bytes": 0,
                "disk_avg_frame_bytes": 1,
            },
            "output": {
                "output_dir": str(tmp_path / "output"),
                "video": {"assemble": True, "fps": 2},
            },
            "sequence": {
                "kind": "timelapse",
                "total_frames": 3,
                "interval_s": 0.01,
                "settle_time_s": 0.0,
                "start": {"pan_deg": 0.0, "tilt_deg": 0.0},
                "target": {"pan_deg": 2.0, "tilt_deg": 2.0},
            },
        }
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_mock_timelapse_produces_frames_metadata_video_and_session(tmp_path: Path) -> None:
    sessions = SessionRepository(tmp_path / "sessions")
    calibration = CalibrationService()
    calibration.mark_homed()
    firmware = MockFirmwareServer()
    port = await firmware.start(port=0)
    config = _config(tmp_path, port)
    tripod = SerialTripodAdapter(config.tripod)
    jobs = JobManager(
        camera=MockCameraAdapter(),
        tripod=tripod,
        calibration=calibration,
        sessions=sessions,
    )
    try:
        await jobs.open()

        job = await jobs.start("timelapse", config)
        await jobs.wait(job.job_id)
    finally:
        await jobs.close()
        await firmware.stop()

    completed = jobs.get(job.job_id)
    assert completed is not None
    assert completed.status == "completed"
    assert completed.progress.frames_completed == 3

    frames = sorted((tmp_path / "output").glob("frame_*.jpg"))
    assert [p.name for p in frames] == ["frame_0000.jpg", "frame_0001.jpg", "frame_0002.jpg"]
    assert (tmp_path / "output" / "metadata.csv").exists()
    assert (tmp_path / "output" / "timelapse.mp4").exists()

    session = sessions.get(job.session_id or job.job_id)
    assert session.metrics.frames_captured == 3
    assert any(asset.kind == "video" for asset in session.assets)
