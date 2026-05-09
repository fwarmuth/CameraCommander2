from __future__ import annotations

import time

from fastapi import APIRouter, Request

from ... import __version__
from ...core.models import HardwareStatus, TripodStatus
from ..deps import get_container

router = APIRouter(prefix="/api", tags=["health"])
_START = time.monotonic()


@router.get("/health", operation_id="getHealth")
async def get_health(request: Request) -> dict[str, object]:
    container = get_container(request)
    active = container.jobs.active() if container.jobs is not None else None
    return {
        "status": "ok",
        "version": __version__,
        "uptime_s": time.monotonic() - _START,
        "active_job_id": active.job_id if active else None,
    }


@router.get("/hardware/status", operation_id="getHardwareStatus", response_model=HardwareStatus)
async def get_hardware_status(request: Request) -> HardwareStatus:
    container = get_container(request)
    camera = await container.camera.status() if container.camera is not None else None
    tripod = await container.tripod.status() if container.tripod is not None else TripodStatus()
    calibration = container.calibration.status if container.calibration is not None else None
    active = container.jobs.active() if container.jobs is not None else None
    return HardwareStatus(
        camera=camera or HardwareStatus().camera,
        tripod=tripod,
        calibration=calibration or HardwareStatus().calibration,
        active_job_id=active.job_id if active else None,
    )


__all__ = ["router"]
