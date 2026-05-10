from __future__ import annotations

import asyncio
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from ...core.config import FocusNudgeRequest
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
    meta, data = await container.camera.capture_still()
    # Cache the capture
    container.captures[meta.capture_id] = data
    # Keep only the last 5 test captures
    if len(container.captures) > 5:
        first_key = next(iter(container.captures))
        del container.captures[first_key]
    return meta


@router.get("/captures/{capture_id}")
async def get_capture_file(
    capture_id: str, container: AppContainer = Depends(get_container)
):
    if capture_id not in container.captures:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return Response(content=container.captures[capture_id], media_type="image/jpeg")


@router.get("/preview/stream")
async def get_camera_preview_stream(container: AppContainer = Depends(get_container)):
    if container.camera is None:
        return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    stream = await container.camera.preview_stream()

    async def frames():
        async for frame in stream:
            if _active_job_locked(container) or container.camera.is_busy:
                break
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"

    return StreamingResponse(
        frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.post("/focus", status_code=status.HTTP_204_NO_CONTENT)
async def post_camera_focus(
    req: FocusNudgeRequest,
    container: AppContainer = Depends(get_container),
):
    if container.camera is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="no camera connected",
        )
    await container.camera.focus_nudge(req.step_size)


__all__ = ["router"]
