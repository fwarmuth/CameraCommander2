from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ...core.errors import (
    CalibrationRequiredError,
    JobAlreadyRunningError,
    MotionLimitError,
    TripodError,
)
from ...core.models import CalibrationStateValue, TripodStatus
from ..deps import get_container

router = APIRouter(prefix="/api/tripod", tags=["tripod"])


def _error(code: str, message: str, **details: object) -> dict[str, object]:
    return {"error": code, "message": message, "details": details}


def _active_job_locked(container: object) -> bool:
    jobs = getattr(container, "jobs", None)
    if jobs is None:
        return False
    return jobs.active() is not None or getattr(jobs, "_active_job_id", None) is not None


def _require_tripod(container: object):
    tripod = getattr(container, "tripod", None)
    if tripod is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            _error("tripod_disconnected", "tripod adapter is not configured"),
        )
    return tripod


def _guard_job_lock(container: object) -> JSONResponse | None:
    if _active_job_locked(container):
        exc = JobAlreadyRunningError("hardware is locked by an active job")
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_409_CONFLICT,
        )
    return None


class AbsoluteMoveRequest(BaseModel):
    pan_deg: float
    tilt_deg: float


class RelativeNudgeRequest(BaseModel):
    delta_pan_deg: float = 0.0
    delta_tilt_deg: float = 0.0


class DriversRequest(BaseModel):
    enabled: bool


@router.get("/status", operation_id="getTripodStatus", response_model=TripodStatus)
async def get_tripod_status(request: Request) -> TripodStatus:
    tripod = _require_tripod(get_container(request))
    return await tripod.status()


async def _status_after(container: object) -> TripodStatus:
    return await _require_tripod(container).status()


def _guard_move(container: object, pan_deg: float, tilt_deg: float) -> JSONResponse | None:
    safety = getattr(container, "safety", None)
    if safety is None:
        return None
    try:
        safety.guard_move(pan_deg, tilt_deg)
    except MotionLimitError as exc:
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=422,
        )
    return None


@router.post("/move", operation_id="postTripodMove", response_model=TripodStatus)
async def post_tripod_move(request: Request, body: AbsoluteMoveRequest) -> TripodStatus:
    container = get_container(request)
    if error := _guard_job_lock(container):
        return error
    tripod = _require_tripod(container)
    calibration = getattr(container, "calibration", None)
    if calibration is not None and calibration.status.state != CalibrationStateValue.homed:
        exc = CalibrationRequiredError("calibration is unknown")
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_412_PRECONDITION_FAILED,
        )
    if error := _guard_move(container, body.pan_deg, body.tilt_deg):
        return error
    try:
        await tripod.move_to(body.pan_deg, body.tilt_deg)
        return await _status_after(container)
    except TripodError as exc:
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@router.post("/nudge", operation_id="postTripodNudge", response_model=TripodStatus)
async def post_tripod_nudge(request: Request, body: RelativeNudgeRequest) -> TripodStatus:
    container = get_container(request)
    if error := _guard_job_lock(container):
        return error
    tripod = _require_tripod(container)
    current = await tripod.status()
    target_pan = current.position_pan_deg + body.delta_pan_deg
    target_tilt = current.position_tilt_deg + body.delta_tilt_deg
    if error := _guard_move(container, target_pan, target_tilt):
        return error
    try:
        await tripod.nudge(delta_pan_deg=body.delta_pan_deg, delta_tilt_deg=body.delta_tilt_deg)
        return await _status_after(container)
    except TripodError as exc:
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


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


@router.put("/drivers", operation_id="putTripodDrivers", response_model=TripodStatus)
async def put_tripod_drivers(request: Request, body: DriversRequest) -> TripodStatus:
    container = get_container(request)
    if error := _guard_job_lock(container):
        return error
    tripod = _require_tripod(container)
    try:
        await tripod.set_drivers(body.enabled)
        if not body.enabled and container.calibration is not None:
            container.calibration.mark_unknown("drivers disabled")
            await container.calibration.publish()
        return await _status_after(container)
    except TripodError as exc:
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@router.post("/stop", operation_id="postTripodStop", response_model=TripodStatus)
async def post_tripod_stop(request: Request) -> TripodStatus:
    container = get_container(request)
    if error := _guard_job_lock(container):
        return error
    tripod = _require_tripod(container)
    try:
        await tripod.stop()
        if container.calibration is not None:
            container.calibration.mark_unknown("manual stop")
            await container.calibration.publish()
        return await _status_after(container)
    except TripodError as exc:
        return JSONResponse(
            _error(exc.code, exc.message, **exc.details),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


__all__ = ["router"]
