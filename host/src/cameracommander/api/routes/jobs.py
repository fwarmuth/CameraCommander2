from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from ...core.config import Configuration, TimelapseSequenceConfig, VideoPanSequenceConfig
from ...core.errors import CalibrationRequiredError, JobAlreadyRunningError, MotionLimitError
from ...core.models import Job
from ...services.safety import SafetyService
from ..deps import get_container

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _error(code: str, message: str, **details: object) -> dict[str, object]:
    return {"error": code, "message": message, "details": details}


@router.post(
    "/timelapse",
    operation_id="postTimelapseJob",
    response_model=Job,
    status_code=status.HTTP_201_CREATED,
)
async def post_timelapse_job(request: Request, config: Configuration) -> Job:
    if not isinstance(config.sequence, TimelapseSequenceConfig):
        raise HTTPException(400, _error("config_invalid", "configuration is not timelapse"))
    jobs = get_container(request).jobs
    try:
        return await jobs.start("timelapse", config)
    except CalibrationRequiredError as exc:
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_412_PRECONDITION_FAILED,
        )
    except JobAlreadyRunningError as exc:
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_409_CONFLICT,
        )


@router.post(
    "/video-pan",
    operation_id="postVideoPanJob",
    response_model=Job,
    status_code=status.HTTP_201_CREATED,
)
async def post_video_pan_job(request: Request, config: Configuration) -> Job:
    if not isinstance(config.sequence, VideoPanSequenceConfig):
        raise HTTPException(400, _error("config_invalid", "configuration is not video_pan"))
    try:
        SafetyService.from_config(config).validate_sequence(config)
    except MotionLimitError as exc:
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=422,
        )
    jobs = get_container(request).jobs
    try:
        return await jobs.start("video_pan", config)
    except CalibrationRequiredError as exc:
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_412_PRECONDITION_FAILED,
        )
    except JobAlreadyRunningError as exc:
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_409_CONFLICT,
        )


@router.get("/active", operation_id="getActiveJob", response_model=Job | None)
async def get_active_job(request: Request) -> Job | None:
    return get_container(request).jobs.active()


@router.get("/{job_id}", operation_id="getJob", response_model=Job)
async def get_job(request: Request, job_id: str) -> Job:
    job = get_container(request).jobs.get(job_id)
    if job is None:
        raise HTTPException(404, _error("not_found", "job not found"))
    return job


@router.post("/{job_id}/stop", operation_id="postJobStop", response_model=Job)
async def post_job_stop(request: Request, job_id: str) -> Job:
    jobs = get_container(request).jobs
    if jobs.get(job_id) is None:
        raise HTTPException(404, _error("not_found", "job not found"))
    return await jobs.stop(job_id)


__all__ = ["router"]
