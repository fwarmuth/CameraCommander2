from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from cameracommander.api.app import create_app
from cameracommander.hardware.camera.mock import MockCameraAdapter


def _payload(tmp_path: Path, *, target_tilt: float = 2.0) -> dict:
    return {
        "metadata": {"name": "API video pan"},
        "camera": {},
        "tripod": {"serial": {"port": "socket://127.0.0.1:9999"}},
        "safety": {
            "tilt_min_deg": -10.0,
            "tilt_max_deg": 10.0,
            "disk_min_free_bytes": 0,
            "disk_avg_frame_bytes": 1,
        },
        "output": {"output_dir": str(tmp_path / "video-pan")},
        "sequence": {
            "kind": "video_pan",
            "duration_s": 0.05,
            "start": {"pan_deg": 0.0, "tilt_deg": 0.0},
            "target": {"pan_deg": 5.0, "tilt_deg": target_tilt},
        },
    }


@pytest.mark.asyncio
async def test_post_video_pan_rejects_when_calibration_unknown(tmp_path: Path) -> None:
    app = create_app(camera=MockCameraAdapter(), serve_static=False, session_root=tmp_path)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/jobs/video-pan", json=_payload(tmp_path))

    assert response.status_code == 412
    assert response.json()["error"] == "calibration_required"


@pytest.mark.asyncio
async def test_post_video_pan_rejects_out_of_window_tilt(tmp_path: Path) -> None:
    app = create_app(camera=MockCameraAdapter(), serve_static=False, session_root=tmp_path)
    app.state.container.calibration.mark_homed()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/jobs/video-pan",
            json=_payload(tmp_path, target_tilt=90.0),
        )

    assert response.status_code == 422
