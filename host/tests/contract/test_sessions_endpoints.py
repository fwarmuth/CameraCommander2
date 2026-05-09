from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from cameracommander.api.app import create_app
from cameracommander.core.config import Configuration
from cameracommander.core.models import JobStatus
from cameracommander.hardware.camera.mock import MockCameraAdapter
from cameracommander.persistence.sessions_fs import SessionRepository


def _config(tmp_path: Path) -> Configuration:
    return Configuration.model_validate(
        {
            "metadata": {"name": "Fixture session", "tags": ["night"]},
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
                "video": {"assemble": False, "fps": 2},
            },
            "sequence": {
                "kind": "timelapse",
                "total_frames": 2,
                "interval_s": 1.0,
                "settle_time_s": 0.0,
                "start": {"pan_deg": 0.0, "tilt_deg": 0.0},
                "target": {"pan_deg": 1.0, "tilt_deg": 1.0},
            },
        }
    )


def _fixture_session(tmp_path: Path) -> tuple[SessionRepository, str, Path]:
    repo = SessionRepository(tmp_path / "sessions")
    config = _config(tmp_path)
    session = repo.create("11111111-1111-1111-1111-111111111111", config)
    session.status = JobStatus.completed
    session.frames_captured = 2
    session.metrics.frames_captured = 2
    frame = tmp_path / "frames" / "frame_0000.jpg"
    frame.parent.mkdir(parents=True, exist_ok=True)
    frame.write_bytes(b"\xff\xd8fixture\xff\xd9")
    repo.add_asset(session, path=frame, kind="frame", content_type="image/jpeg")
    repo.save(session)
    return repo, session.session_id, frame


@pytest.mark.asyncio
async def test_session_library_endpoints(tmp_path: Path) -> None:
    repo, session_id, _frame = _fixture_session(tmp_path)
    app = create_app(camera=MockCameraAdapter(), serve_static=False, session_root=repo.root)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        listed = await client.get("/api/sessions", params={"tag": "night"})
        fetched = await client.get(f"/api/sessions/{session_id}")
        config = await client.get(f"/api/sessions/{session_id}/config")
        assembled = await client.post(f"/api/sessions/{session_id}/assemble")
        asset_path = fetched.json()["assets"][0]["path"]
        asset = await client.get(f"/api/sessions/{session_id}/assets/{asset_path}")
        traversal = await client.get(f"/api/sessions/{session_id}/assets/../../etc/passwd")
        deleted = await client.delete(f"/api/sessions/{session_id}")
        missing = await client.get(f"/api/sessions/{session_id}")

    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["session_id"] == session_id
    assert fetched.status_code == 200
    assert config.status_code == 200
    assert config.json()["metadata"]["name"] == "Fixture session"
    assert assembled.status_code == 202
    assert any(item["kind"] == "video" for item in assembled.json()["assets"])
    assert asset.status_code == 200
    assert asset.headers["content-type"] == "image/jpeg"
    assert traversal.status_code == 404
    assert deleted.status_code == 204
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_session_assemble_returns_409_when_job_running(tmp_path: Path) -> None:
    repo, session_id, _frame = _fixture_session(tmp_path)
    app = create_app(camera=MockCameraAdapter(), serve_static=False, session_root=repo.root)
    app.state.container.jobs._active_job_id = "active"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/sessions/{session_id}/assemble")

    assert response.status_code == 409
    assert response.json()["error"] == "job_already_running"
