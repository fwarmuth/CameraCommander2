from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from ...core.models import TripodStatus
from ..deps import AppContainer, get_container

router = APIRouter()


@router.get("/status")
async def get_tripod_status(container: AppContainer = Depends(get_container)):
    if container.tripod is None:
        return {"state": "disconnected"}
    return await container.tripod.status()


@router.post("/nudge")
async def post_tripod_nudge(
    delta_pan: float = 0.0,
    delta_tilt: float = 0.0,
    container: AppContainer = Depends(get_container),
):
    if container.tripod is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="no tripod connected",
        )
    return await container.tripod.nudge(delta_pan_deg=delta_pan, delta_tilt_deg=delta_tilt)


@router.post("/move")
async def post_tripod_move(
    pan: float,
    tilt: float,
    container: AppContainer = Depends(get_container),
):
    if container.tripod is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="no tripod connected",
        )
    if container.calibration.state != "homed":
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="calibration_required",
        )
    container.safety.guard_move(pan, tilt)
    return await container.tripod.move_to(pan, tilt)


@router.post("/stop")
async def post_tripod_stop(container: AppContainer = Depends(get_container)):
    if container.tripod is None:
        return
    await container.tripod.stop()


@router.put("/drivers")
async def put_tripod_drivers(
    enabled: bool,
    container: AppContainer = Depends(get_container),
):
    if container.tripod is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="no tripod connected",
        )
    await container.tripod.set_drivers(enabled)
    if not enabled:
        container.calibration.mark_unknown("drivers_disabled")
    return await container.tripod.status()


@router.post("/home")
async def post_tripod_home(container: AppContainer = Depends(get_container)):
    if container.tripod is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="no tripod connected",
        )
    await container.tripod.home()
    container.calibration.mark_homed()
    return await container.tripod.status()


__all__ = ["router"]
