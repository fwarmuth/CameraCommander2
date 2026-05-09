from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from cameracommander.api.app import create_app
from cameracommander.hardware.camera.mock import MockCameraAdapter


@pytest.mark.asyncio
async def test_camera_settings_round_trip(tmp_path: Path) -> None:
    app = create_app(camera=MockCameraAdapter(), serve_static=False, session_root=tmp_path)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        settings = await client.get("/api/camera/settings")
        update = await client.put(
            "/api/camera/settings",
            json={"settings": {"main.imgsettings.iso": 800}, "step_policy": "strict"},
        )

    assert settings.status_code == 200
    assert "main.imgsettings.iso" in settings.json()
    assert update.status_code == 200
    assert update.json()["main.imgsettings.iso"]["current"] == 800


@pytest.mark.asyncio
async def test_camera_capture_and_download(tmp_path: Path) -> None:
    app = create_app(camera=MockCameraAdapter(), serve_static=False, session_root=tmp_path)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        capture = await client.post("/api/camera/capture", json={"autofocus": False})
        body = capture.json()
        image = await client.get(body["download_url"])

    assert capture.status_code == 200
    assert body["content_type"] == "image/jpeg"
    assert body["size_bytes"] > 100
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/jpeg"
    assert image.content.startswith(b"\xff\xd8")


@pytest.mark.asyncio
async def test_camera_preview_returns_jpeg(tmp_path: Path) -> None:
    app = create_app(camera=MockCameraAdapter(), serve_static=False, session_root=tmp_path)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/camera/preview")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content.startswith(b"\xff\xd8")
