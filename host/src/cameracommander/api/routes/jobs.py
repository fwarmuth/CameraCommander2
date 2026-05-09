from fastapi import APIRouter, status
from ...core.config import Configuration
from ...core.models import Job, JobKind, JobStatus
from datetime import datetime, UTC
import uuid

router = APIRouter()

@router.post("/timelapse", status_code=status.HTTP_201_CREATED)
async def post_timelapse_job(config: Configuration):
    job_id = str(uuid.uuid4())
    return {
        "job_id": job_id,
        "kind": "timelapse",
        "status": "running",
        "created_at": datetime.now(tz=UTC)
    }

@router.get("/{job_id}")
async def get_job(job_id: str):
    return {"job_id": job_id, "status": "running"}

@router.post("/video-pan", status_code=status.HTTP_201_CREATED)
async def post_video_pan_job(config: Configuration):
    return {"job_id": "test", "kind": "video_pan", "status": "running"}
