from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from ...core.models import HardwareStatus
from ..deps import AppContainer, get_container

router = APIRouter()


@router.get("/health")
async def get_health():
    return {"status": "ok", "version": "0.1.0"}


@router.get("/hardware/status")
async def get_hardware_status(
    container: AppContainer = Depends(get_container),
) -> HardwareStatus:
    camera = await container.camera.status() if container.camera else None
    tripod = await container.tripod.status() if container.tripod else None

    # Fallback to disconnected status if adapters are missing
    from ...core.models import (
        CalibrationValue,
        CameraState,
        CameraStatus,
        TripodState,
        TripodStatus,
    )

    if camera is None:
        camera = CameraStatus(state=CameraState.disconnected)
    if tripod is None:
        tripod = TripodStatus(state=TripodState.disconnected)

    return HardwareStatus(
        camera=camera,
        tripod=tripod,
        calibration_state=container.calibration.state,
        active_job_id=container.jobs.active_job_id,
        updated_at=datetime.now(tz=UTC),
    )


__all__ = ["router"]
