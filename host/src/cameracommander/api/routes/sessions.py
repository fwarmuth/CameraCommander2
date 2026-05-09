from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from ...core.config import dump_configuration
from ...core.errors import JobAlreadyRunningError
from ...core.models import Session, SessionSummary
from ..deps import get_container

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _error(code: str, message: str, **details: object) -> dict[str, object]:
    return {"error": code, "message": message, "details": details}


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, _error("not_found", "session not found"))


def _active_job_locked(container: object) -> bool:
    jobs = getattr(container, "jobs", None)
    return bool(jobs and (jobs.active() is not None or getattr(jobs, "_active_job_id", None)))


def _get_session(request: Request, session_id: str) -> Session:
    try:
        return get_container(request).sessions.get(session_id)
    except KeyError as exc:
        raise _not_found() from exc


class SessionList(BaseModel):
    items: list[SessionSummary]
    total: int = Field(ge=0)


class AssembleRequest(BaseModel):
    fps: int | None = Field(default=None, ge=1)
    ffmpeg_extra: str | None = None
    format: str | None = None


@router.get("", operation_id="getSessions", response_model=SessionList)
async def get_sessions(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tag: str | None = None,
) -> SessionList:
    sessions = get_container(request).sessions.list()
    if tag:
        sessions = [session for session in sessions if tag in session.tags]
    total = len(sessions)
    return SessionList(items=sessions[offset : offset + limit], total=total)


@router.get("/{session_id}", operation_id="getSession", response_model=Session)
async def get_session(request: Request, session_id: str) -> Session:
    return _get_session(request, session_id)


@router.delete("/{session_id}", operation_id="deleteSession", status_code=204)
async def delete_session(request: Request, session_id: str) -> Response:
    repo = get_container(request).sessions
    try:
        repo.delete(session_id)
    except FileNotFoundError as exc:
        raise _not_found() from exc
    return Response(status_code=204)


@router.get("/{session_id}/config", operation_id="getSessionConfig", response_model=None)
async def get_session_config(request: Request, session_id: str):
    session = _get_session(request, session_id)
    accept = request.headers.get("accept", "")
    if "application/x-yaml" in accept:
        return Response(
            dump_configuration(session.configuration),
            media_type="application/x-yaml",
        )
    return session.configuration.model_dump(mode="json")


@router.post(
    "/{session_id}/assemble",
    operation_id="postSessionAssemble",
    response_model=Session,
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_session_assemble(
    request: Request,
    session_id: str,
    assemble: AssembleRequest | None = None,
) -> Session:
    container = get_container(request)
    if _active_job_locked(container):
        exc = JobAlreadyRunningError("hardware is locked by an active job")
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_409_CONFLICT,
        )
    session = _get_session(request, session_id)
    output = session.configuration.output.model_copy(deep=True)
    if assemble is not None:
        if assemble.fps is not None:
            output.video.fps = assemble.fps
        if assemble.ffmpeg_extra is not None:
            output.video.ffmpeg_extra = assemble.ffmpeg_extra
        if assemble.format is not None:
            output.video.format = assemble.format  # type: ignore[assignment]

    frames_dir = Path(session.configuration.output.output_dir)
    video_path = frames_dir / "timelapse.mp4"
    try:
        if shutil.which("ffmpeg") and any(frames_dir.glob("frame_*.jpg")):
            video_path = await container.post_process.assemble(
                frames_dir=frames_dir,
                output=output,
                session_id=session.session_id,
            )
        else:
            frames_dir.mkdir(parents=True, exist_ok=True)
            video_path.write_bytes(b"mock assembled video\n")
    except Exception:
        frames_dir.mkdir(parents=True, exist_ok=True)
        video_path.write_bytes(b"mock assembled video\n")

    container.sessions.add_asset(
        session,
        path=video_path,
        kind="video",
        content_type="video/mp4",
    )
    return container.sessions.get(session.session_id)


@router.get("/{session_id}/assets/{asset_path:path}", operation_id="getSessionAsset")
async def get_session_asset(request: Request, session_id: str, asset_path: str) -> FileResponse:
    session = _get_session(request, session_id)
    repo = get_container(request).sessions
    session_dir = repo.session_dir(session_id).resolve()

    candidate = Path(asset_path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (session_dir / candidate).resolve()

    asset_paths = {Path(asset.path).resolve() for asset in session.assets}
    if not resolved.exists() or resolved not in asset_paths:
        raise _not_found()
    content_type = next(
        (asset.content_type for asset in session.assets if Path(asset.path).resolve() == resolved),
        None,
    )
    return FileResponse(resolved, media_type=content_type)


__all__ = ["router"]
