from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from cameracommander.api.app import create_app
from cameracommander.core.config import Configuration
from cameracommander.hardware.camera.mock import MockCameraAdapter
from cameracommander.hardware.tripod.serial_adapter import SerialTripodAdapter
from cameracommander.mock_firmware.server import MockFirmwareServer


def _payload(tmp_path: Path, port: int) -> dict:
    return {
        "metadata": {"name": "Serve mock E2E"},
        "camera": {},
        "tripod": {"serial": {"port": f"socket://127.0.0.1:{port}"}},
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
            "total_frames": 2,
            "interval_s": 0.01,
            "settle_time_s": 0.0,
            "start": {"pan_deg": 0, "tilt_deg": 0},
            "target": {"pan_deg": 1, "tilt_deg": 1},
        },
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_serve_mock_app_runs_timelapse_and_lists_session(tmp_path: Path) -> None:
    firmware = MockFirmwareServer()
    port = await firmware.start(port=0)
    config = Configuration.model_validate(_payload(tmp_path, port))
    app = create_app(
        camera=MockCameraAdapter(),
        tripod=SerialTripodAdapter(config.tripod),
        serve_static=False,
        session_root=tmp_path / "sessions",
    )
    try:
        async with app.router.lifespan_context(app):
            app.state.container.calibration.mark_homed()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                status = await client.get("/api/hardware/status")
                started = await client.post("/api/jobs/timelapse", json=_payload(tmp_path, port))
                job_id = started.json()["job_id"]
                await app.state.container.jobs.wait(job_id)
                completed = await client.get(f"/api/jobs/{job_id}")
                sessions = await client.get("/api/sessions")
    finally:
        await firmware.stop()

    assert status.status_code == 200
    assert status.json()["camera"]["state"] == "connected"
    assert status.json()["tripod"]["state"] == "connected"
    assert started.status_code == 201
    assert completed.json()["status"] == "completed"
    assert sessions.json()["total"] == 1
