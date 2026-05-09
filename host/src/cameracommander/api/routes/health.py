from fastapi import APIRouter, Depends
from ..deps import AppContainer

router = APIRouter()

@router.get("/health")
async def get_health():
    return {"status": "ok", "version": "0.1.0"}

@router.get("/hardware/status")
async def get_hardware_status():
    return {"camera": {"state": "connected"}, "tripod": {"state": "connected"}, "calibration_state": "homed"}
