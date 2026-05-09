from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from ...core.config import Configuration
from ...core.models import Job, JobKind, JobStatus
from ..deps import AppContainer, get_container

router = APIRouter()


@router.post("/timelapse", status_code=status.HTTP_201_CREATED)
async def post_timelapse_job(
    config: Configuration, container: AppContainer = Depends(get_container)
):
    try:
        return await container.jobs.start(JobKind.timelapse, config)
    except Exception as exc:
        # Simplification: in a real impl, we'd map domain exceptions to 409, 412, etc.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/video-pan", status_code=status.HTTP_201_CREATED)
async def post_video_pan_job(
    config: Configuration, container: AppContainer = Depends(get_container)
):
    try:
        return await container.jobs.start(JobKind.video_pan, config)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/active")
async def get_active_job(container: AppContainer = Depends(get_container)):
    if container.jobs.active_job_id is None:
        return None
    return container.jobs.get(container.jobs.active_job_id)


@router.get("/{job_id}")
async def get_job(job_id: str, container: AppContainer = Depends(get_container)):
    try:
        return container.jobs.get(job_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")


@router.post("/{job_id}/stop")
async def post_job_stop(job_id: str, container: AppContainer = Depends(get_container)):
    await container.jobs.stop(job_id)
    return {"status": "stopping"}


__all__ = ["router"]
