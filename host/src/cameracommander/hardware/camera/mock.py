"""Mock camera adapter implementation."""

from __future__ import annotations

import asyncio
import io
import uuid
from datetime import datetime
from typing import AsyncIterator

from PIL import Image, ImageDraw

from ...core.config import SettingDescriptor
from ...core.models import CameraState, CameraStatus, CaptureResult


class MockCameraAdapter:
    """Simulated camera for development and CI."""

    def __init__(self) -> None:
        self._connected = False
        self._capture_count = 0

    async def open(self) -> None:
        self._connected = True

    async def close(self) -> None:
        self._connected = False

    async def status(self) -> CameraStatus:
        return CameraStatus(
            state=CameraState.connected if self._connected else CameraState.disconnected,
            model="MOCK-EOS-R5",
            battery_pct=85
        )

    async def query_settings(self) -> dict[str, SettingDescriptor]:
        return {
            "main.imgsettings.iso": SettingDescriptor(type="MENU", current="100", choices=["100", "200", "400", "800"]),
            "main.capturesettings.shutterspeed": SettingDescriptor(type="MENU", current="1/125", choices=["1/60", "1/125", "1/250"]),
        }

    async def apply_settings(self, settings: dict[str, str | int | float | bool]) -> None:
        await asyncio.sleep(0.05)

    async def capture_still(self, *, autofocus: bool = False) -> CaptureResult:
        if not self._connected:
            from ...core.errors import CameraError
            raise CameraError("Camera disconnected")
        
        self._capture_count += 1
        cid = str(uuid.uuid4())
        
        # In a real impl, we'd write to a temp file. For mock, just return meta.
        return CaptureResult(
            capture_id=cid,
            content_type="image/jpeg",
            captured_at=datetime.now(),
            size_bytes=1024 * 1024,
            download_url=f"/api/camera/captures/{cid}"
        )

    async def start_recording(self) -> None:
        pass

    async def stop_recording(self) -> None:
        pass

    async def preview_frame_jpeg(self) -> bytes:
        # Generate a synthetic JPEG
        img = Image.new("RGB", (640, 480), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        d.text((10, 10), f"MOCK PREVIEW {datetime.now().isoformat()}", fill=(255, 255, 0))
        
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    async def preview_stream(self) -> AsyncIterator[bytes]:
        while self._connected:
            yield await self.preview_frame_jpeg()
            await asyncio.sleep(0.2) # 5 fps
