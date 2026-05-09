from fastapi import APIRouter, status, Response
from ...core.models import CameraStatus, CaptureResult
import asyncio

router = APIRouter()

@router.get("/settings")
async def get_camera_settings():
    return {
        "main.imgsettings.iso": {"type": "MENU", "current": "100", "choices": ["100", "200", "400", "800"]},
        "main.capturesettings.shutterspeed": {"type": "MENU", "current": "1/125", "choices": ["1/60", "1/125", "1/250"]}
    }

@router.post("/capture")
async def post_camera_capture():
    return {"capture_id": "test", "content_type": "image/jpeg", "captured_at": "now", "size_bytes": 100, "download_url": ""}

@router.get("/preview/stream")
async def get_camera_preview_stream():
    async def frames():
        while True:
            # MJPEG stream logic would go here
            await asyncio.sleep(0.2)
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\nFRAME_BYTES\r\n"
    
    return Response(content=frames(), media_type="multipart/x-mixed-replace; boundary=frame")
