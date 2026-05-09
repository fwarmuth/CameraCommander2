from fastapi import APIRouter
from ...core.models import TripodStatus

router = APIRouter()

@router.get("/status")
async def get_tripod_status():
    return {"state": "connected", "position_pan_deg": 0, "position_tilt_deg": 0}

@router.post("/nudge")
async def post_tripod_nudge(delta_pan: float = 0, delta_tilt: float = 0):
    return {"pan": delta_pan, "tilt": delta_tilt, "success": True}
