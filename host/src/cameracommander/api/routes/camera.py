from __future__ import annotations

import asyncio
from typing import AsyncIterator

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import StreamingResponse

from ...core.models import CameraStatus, CaptureResult
from ..deps import AppContainer, get_container

router = APIRouter()


def _active_job_locked(container: AppContainer) -> bool:
    return container.jobs.active_job_id is not None


@router.get("/settings")
async def get_camera_settings(container: AppContainer = Depends(get_container)):
    if container.camera is None:
        return {}
    return await container.camera.query_settings()


@router.post("/capture")
async def post_camera_capture(container: AppContainer = Depends(get_container)):
    if container.camera is None:
        return {"error": "no camera connected"}
    return await container.camera.capture_still()


@router.get("/preview/stream")
async def get_camera_preview_stream(container: AppContainer = Depends(get_container)):
    if container.camera is None:
        return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    stream = await container.camera.preview_stream()

    async def frames():
        async for frame in stream:
            if _active_job_locked(container):
                break
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"

    return StreamingResponse(
        frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


__all__ = ["router"]
