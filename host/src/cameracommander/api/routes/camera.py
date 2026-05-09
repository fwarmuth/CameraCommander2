from __future__ import annotations

import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from ...core.errors import CameraCommanderError, CameraError, CaptureError, JobAlreadyRunningError
from ...hardware.camera.base import SettingDescriptor
from ..deps import get_container

router = APIRouter(prefix="/api/camera", tags=["camera"])


def _error(code: str, message: str, **details: object) -> dict[str, object]:
    return {"error": code, "message": message, "details": details}


def _active_job_locked(container: object) -> bool:
    jobs = getattr(container, "jobs", None)
    if jobs is None:
        return False
    return jobs.active() is not None or getattr(jobs, "_active_job_id", None) is not None


def _settings_payload(settings: dict[str, SettingDescriptor]) -> dict[str, dict[str, object]]:
    payload: dict[str, dict[str, object]] = {}
    for key, descriptor in settings.items():
        item: dict[str, object] = {
            "type": descriptor.type,
            "current": descriptor.current,
            "choices": descriptor.choices,
        }
        if descriptor.range is not None:
            item["range"] = {
                "min": descriptor.range[0],
                "max": descriptor.range[1],
                "step": descriptor.range[2],
            }
        else:
            item["range"] = None
        payload[key] = item
    return payload


class CameraSettingsUpdate(BaseModel):
    settings: dict[str, str | int | float | bool]
    step_policy: Literal["strict", "snap"] = "strict"


class CaptureRequest(BaseModel):
    autofocus: bool = False
    save_to_session: str | None = None


class CaptureResultResponse(BaseModel):
    capture_id: str
    content_type: str
    captured_at: datetime
    size_bytes: int = Field(ge=0)
    download_url: str


@router.get("/settings", operation_id="getCameraSettings")
async def get_camera_settings(request: Request) -> dict[str, dict[str, object]]:
    container = get_container(request)
    if container.camera is None:
        return JSONResponse(
            _error("camera_disconnected", "camera adapter is not configured"),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    try:
        return _settings_payload(await container.camera.query_settings())
    except CameraError as exc:
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@router.put("/settings", operation_id="putCameraSettings")
async def put_camera_settings(
    request: Request,
    update: CameraSettingsUpdate,
) -> dict[str, dict[str, object]]:
    container = get_container(request)
    if container.camera is None:
        return JSONResponse(
            _error("camera_disconnected", "camera adapter is not configured"),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    try:
        await container.camera.apply_settings(update.settings)
        return _settings_payload(await container.camera.query_settings())
    except CaptureError as exc:
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except CameraError as exc:
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@router.post("/capture", operation_id="postCameraCapture", response_model=CaptureResultResponse)
async def post_camera_capture(
    request: Request,
    capture_request: CaptureRequest | None = None,
) -> CaptureResultResponse:
    container = get_container(request)
    if _active_job_locked(container):
        exc = JobAlreadyRunningError("hardware is locked by an active job")
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_409_CONFLICT,
        )
    if container.camera is None:
        return JSONResponse(
            _error("camera_disconnected", "camera adapter is not configured"),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    body = capture_request or CaptureRequest()
    try:
        result = await container.camera.capture_still(autofocus=body.autofocus)
    except CaptureError:
        await container.camera.open()
        result = await container.camera.capture_still(autofocus=body.autofocus)
    except CameraError as exc:
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    capture_id = str(uuid.uuid4())
    suffix = result.extension or ".jpg"
    path = Path(tempfile.gettempdir()) / f"cameracommander-capture-{capture_id}{suffix}"
    path.write_bytes(result.bytes_)
    captures = container.camera_captures
    if captures is not None:
        captures[capture_id] = (path, result.content_type)
    return CaptureResultResponse(
        capture_id=capture_id,
        content_type=result.content_type,
        captured_at=datetime.fromtimestamp(result.captured_at, tz=UTC),
        size_bytes=len(result.bytes_),
        download_url=f"/api/camera/captures/{capture_id}",
    )


@router.get("/captures/{capture_id}", operation_id="getCaptureFile")
async def get_capture_file(request: Request, capture_id: str) -> FileResponse:
    captures = get_container(request).camera_captures or {}
    record = captures.get(capture_id)
    if record is None or not record[0].exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, _error("not_found", "capture not found"))
    return FileResponse(record[0], media_type=record[1])


@router.get("/preview", operation_id="getCameraPreview")
async def get_camera_preview(request: Request) -> Response:
    container = get_container(request)
    if container.camera is None:
        return JSONResponse(
            _error("camera_disconnected", "camera adapter is not configured"),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    try:
        return Response(await container.camera.preview_frame_jpeg(), media_type="image/jpeg")
    except CameraError as exc:
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@router.get("/preview/stream", operation_id="getCameraPreviewStream")
async def get_camera_preview_stream(request: Request) -> StreamingResponse:
    container = get_container(request)
    if container.camera is None:
        return JSONResponse(
            _error("camera_disconnected", "camera adapter is not configured"),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    try:
        stream = await container.camera.preview_stream()
    except CameraCommanderError as exc:
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    async def frames():
        async for frame in stream:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"

    return StreamingResponse(
        frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


__all__ = ["router"]
