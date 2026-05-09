from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from cameracommander.api.app import create_app
from cameracommander.core.config import Configuration
from cameracommander.hardware.camera.mock import MockCameraAdapter
from cameracommander.services.calibration import CalibrationService


def _config_payload(tmp_path: Path) -> dict:
    return {
        "metadata": {"name": "API test"},
        "camera": {},
        "tripod": {"serial": {"port": "socket://127.0.0.1:9999"}},
        "safety": {
            "tilt_min_deg": -45.0,
            "tilt_max_deg": 45.0,
            "disk_min_free_bytes": 0,
            "disk_avg_frame_bytes": 1,
        },
        "output": {
            "output_dir": str(tmp_path / "frames"),
            "video": {"assemble": False, "fps": 25},
        },
        "sequence": {
            "kind": "timelapse",
            "total_frames": 2,
            "interval_s": 0.01,
            "settle_time_s": 0.0,
            "start": {"pan_deg": 0.0, "tilt_deg": 0.0},
            "target": {"pan_deg": 1.0, "tilt_deg": 1.0},
        },
    }


@pytest.mark.asyncio
async def test_post_timelapse_returns_412_when_calibration_unknown(tmp_path: Path) -> None:
    app = create_app(camera=MockCameraAdapter(), serve_static=False, session_root=tmp_path)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/jobs/timelapse", json=_config_payload(tmp_path))

    assert response.status_code == 412
    assert response.json()["error"] == "calibration_required"


@pytest.mark.asyncio
async def test_post_timelapse_returns_201_for_valid_mock_config(tmp_path: Path) -> None:
    app = create_app(camera=MockCameraAdapter(), serve_static=False, session_root=tmp_path)
    app.state.container.calibration.mark_homed()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/jobs/timelapse", json=_config_payload(tmp_path))

    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "timelapse"
    assert body["status"] in {"running", "completed"}


@pytest.mark.asyncio
async def test_post_timelapse_returns_409_when_another_job_running(tmp_path: Path) -> None:
    app = create_app(camera=MockCameraAdapter(), serve_static=False, session_root=tmp_path)
    calibration: CalibrationService = app.state.container.calibration
    calibration.mark_homed()
    app.state.container.jobs._active_job_id = "already-running"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/jobs/timelapse", json=_config_payload(tmp_path))

    assert response.status_code == 409
    assert response.json()["error"] == "job_already_running"


def test_contract_payload_is_valid_configuration(tmp_path: Path) -> None:
    assert Configuration.model_validate(_config_payload(tmp_path)).sequence.kind == "timelapse"
