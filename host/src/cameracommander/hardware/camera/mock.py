"""Mock camera adapter — synthetic frames for development and CI.

Generates a procedural-gradient JPEG with a frame counter overlay for each
capture, and a small synthetic JPEG for live-view. Implements the same
``CameraAdapter`` protocol as the gphoto2 implementation. A simulated
disconnect toggle is exposed for fault-handling tests (SC-004 detection).
"""

from __future__ import annotations

import asyncio
import io
import time
from collections.abc import AsyncIterator

from PIL import Image, ImageDraw, ImageFont

from ...core.errors import CameraDisconnectedError, CaptureError
from ...core.models import CameraState, CameraStatus
from .base import CaptureResult, SettingDescriptor


class MockCameraAdapter:
    """Synthetic camera; satisfies :class:`CameraAdapter`."""

    DEFAULT_RESOLUTION = (1280, 800)
    PREVIEW_RESOLUTION = (640, 400)

    def __init__(
        self,
        *,
        model: str = "MockEOS R-Sim",
        resolution: tuple[int, int] = DEFAULT_RESOLUTION,
        preview_resolution: tuple[int, int] = PREVIEW_RESOLUTION,
        preview_fps: int = 5,
    ) -> None:
        self._model = model
        self._resolution = resolution
        self._preview_resolution = preview_resolution
        self._preview_interval_s = 1.0 / max(1, preview_fps)
        self._frame_counter = 0
        self._is_open = False
        self._is_recording = False
        self._is_disconnected = False
        self._settings: dict[str, str | int | float | bool] = {
            "main.imgsettings.iso": 400,
            "main.capturesettings.shutterspeed": "1/125",
            "main.capturesettings.aperture": 5.6,
            "main.imgsettings.whitebalance": "Auto",
        }

    # --- diagnostics ---------------------------------------------------

    def simulate_disconnect(self, disconnected: bool = True) -> None:
        """Flip the simulated camera between connected/disconnected for fault tests."""

        self._is_disconnected = disconnected

    # --- lifecycle -----------------------------------------------------

    async def open(self) -> None:
        if self._is_disconnected:
            raise CameraDisconnectedError("mock camera is in simulated-disconnect state")
        self._is_open = True

    async def close(self) -> None:
        self._is_open = False

    async def status(self) -> CameraStatus:
        state = (
            CameraState.disconnected
            if self._is_disconnected
            else (CameraState.connected if self._is_open else CameraState.disconnected)
        )
        return CameraStatus(state=state, model=self._model, battery_pct=87)

    # --- settings ------------------------------------------------------

    async def query_settings(self) -> dict[str, SettingDescriptor]:
        return {
            key: SettingDescriptor(type="TEXT", current=val) for key, val in self._settings.items()
        }

    async def apply_settings(self, settings: dict[str, str | int | float | bool]) -> None:
        if self._is_disconnected:
            raise CameraDisconnectedError()
        self._settings.update(settings)

    # --- capture / record ---------------------------------------------

    async def capture_still(self, *, autofocus: bool = False) -> CaptureResult:
        if self._is_disconnected:
            raise CameraDisconnectedError()
        if not self._is_open:
            raise CaptureError("camera is not open")

        self._frame_counter += 1
        img = self._render_frame(self._resolution, label=f"FRAME {self._frame_counter:04d}")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=88)
        return CaptureResult(
            content_type="image/jpeg",
            bytes_=buf.getvalue(),
            captured_at=time.time(),
            extension=".jpg",
            extra={"autofocus": autofocus, "settings": dict(self._settings)},
        )

    async def start_recording(self) -> None:
        if self._is_disconnected:
            raise CameraDisconnectedError()
        self._is_recording = True

    async def stop_recording(self) -> None:
        self._is_recording = False

    # --- live view ----------------------------------------------------

    async def preview_frame_jpeg(self) -> bytes:
        if self._is_disconnected:
            raise CameraDisconnectedError()
        img = self._render_frame(self._preview_resolution, label="LIVE")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        return buf.getvalue()

    async def preview_stream(self) -> AsyncIterator[bytes]:
        async def _gen() -> AsyncIterator[bytes]:
            while True:
                if self._is_disconnected:
                    raise CameraDisconnectedError()
                yield await self.preview_frame_jpeg()
                await asyncio.sleep(self._preview_interval_s)

        return _gen()

    # --- internals ----------------------------------------------------

    def _render_frame(self, size: tuple[int, int], *, label: str) -> Image.Image:
        w, h = size
        img = Image.new("RGB", size, color=(0, 0, 0))
        # Procedural gradient so successive frames are visually distinguishable.
        pixels = img.load()
        if pixels is not None:
            phase = (self._frame_counter * 7) % 256
            for y in range(h):
                row_r = (y * 255 // max(h - 1, 1) + phase) % 256
                for x in range(w):
                    col_b = (x * 255 // max(w - 1, 1)) & 0xFF
                    pixels[x, y] = (row_r, (row_r + col_b) // 2, col_b)
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default()
        except OSError:  # pragma: no cover - load_default is always available
            font = None
        text = f"{label}  pan/tilt mock  ts={int(time.time())}"
        draw.text((12, 12), text, fill=(255, 255, 255), font=font)
        return img


__all__ = ["MockCameraAdapter"]
