from __future__ import annotations

from fastapi import APIRouter, Request

from ...core.models import TripodStatus
from ..deps import get_container

router = APIRouter(prefix="/api/tripod", tags=["tripod"])


@router.post("/home", operation_id="postTripodHome", response_model=TripodStatus)
async def post_tripod_home(request: Request) -> TripodStatus:
    container = get_container(request)
    if container.tripod is not None:
        await container.tripod.home()
        status = await container.tripod.status()
    else:
        status = TripodStatus()
    container.calibration.mark_homed()
    await container.calibration.publish()
    return status


__all__ = ["router"]
