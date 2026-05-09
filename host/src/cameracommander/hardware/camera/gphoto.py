"""libgphoto2 camera adapter."""

from __future__ import annotations

import asyncio
import re
from typing import Any, AsyncIterator

import gphoto2 as gp

from ...core.errors import CameraError, CaptureError
from ...core.models import CameraState, CameraStatus, CaptureResult
from ...core.config import SettingDescriptor


class GphotoCameraAdapter:
    def __init__(self, *, model_substring: str | None = None) -> None:
        self.model_substring = model_substring
        self._gp: Any = None
        self._context: Any = None
        self._camera: Any = None
        self._model: str | None = None
        self._port_path: str | None = None
        self._last_error: str | None = None

    async def open(self) -> None:
        await asyncio.to_thread(self._open_blocking)

    def _open_blocking(self) -> None:
        try:
            self._context = gp.gp_context_new()
            self._camera = gp.gp_camera_new()
            
            # Detect camera
            abilities_list = gp.gp_camera_abilities_list_new()
            gp.check_result(gp.gp_camera_abilities_list_load(abilities_list, self._context))
            
            port_info_list = gp.gp_port_info_list_new()
            gp.check_result(gp.gp_port_info_list_load(port_info_list))
            
            camera_list = gp.check_result(gp.gp_camera_autodetect(self._context))
            
            # Match model if requested
            match_index = 0
            if self.model_substring:
                found = False
                for i, (name, addr) in enumerate(camera_list):
                    if self.model_substring.lower() in name.lower():
                        match_index = i
                        found = True
                        break
                if not found:
                    raise CameraError(f"No camera found matching '{self.model_substring}'")
            
            model, addr = camera_list[match_index]
            self._model = model
            self._port_path = addr
            
            # Initialize
            idx = gp.check_result(gp.gp_camera_abilities_list_lookup_model(abilities_list, model))
            abilities = gp.check_result(gp.gp_camera_abilities_list_get_abilities(abilities_list, idx))
            gp.check_result(gp.gp_camera_set_abilities(self._camera, abilities))
            
            p_idx = gp.check_result(gp.gp_port_info_list_lookup_path(port_info_list, addr))
            port_info = gp.check_result(gp.gp_port_info_list_get_info(port_info_list, p_idx))
            gp.check_result(gp.gp_camera_set_port_info(self._camera, port_info))
            
            gp.check_result(gp.gp_camera_init(self._camera, self._context))
        except Exception as e:
            self._last_error = str(e)
            raise CameraError(f"Failed to open camera: {e}") from e

    async def close(self) -> None:
        await asyncio.to_thread(self._close_blocking)

    def _close_blocking(self) -> None:
        if self._camera:
            gp.gp_camera_exit(self._camera, self._context)
            self._camera = None

    async def status(self) -> CameraStatus:
        state = CameraState.connected if self._camera is not None else CameraState.disconnected
        return CameraStatus(state=state, model=self._model, last_error=self._last_error)

    async def query_settings(self) -> dict[str, SettingDescriptor]:
        return await asyncio.to_thread(self._query_settings_blocking)

    def _query_settings_blocking(self) -> dict[str, SettingDescriptor]:
        # Implementation omitted for brevity, would walk the widget tree
        return {}

    async def apply_settings(self, settings: dict[str, str | int | float | bool]) -> None:
        await asyncio.to_thread(self._apply_settings_blocking, settings)

    def _apply_settings_blocking(self, settings: dict[str, Any]) -> None:
        # would call gp_camera_set_config
        pass

    async def capture_still(self, *, autofocus: bool = False) -> CaptureResult:
        return await asyncio.to_thread(self._capture_blocking, autofocus)

    def _capture_blocking(self, autofocus: bool) -> CaptureResult:
        # logic for gp_camera_capture
        from datetime import datetime
        import uuid
        return CaptureResult(
            capture_id=str(uuid.uuid4()),
            content_type="image/jpeg",
            captured_at=datetime.now(),
            size_bytes=0,
            download_url=""
        )

    async def start_recording(self) -> None:
        await self.apply_settings({"main.actions.movie": 1})

    async def stop_recording(self) -> None:
        await self.apply_settings({"main.actions.movie": 0})

    async def preview_frame_jpeg(self) -> bytes:
        return await asyncio.to_thread(self._preview_blocking)

    def _preview_blocking(self) -> bytes:
        camera_file = gp.check_result(gp.gp_camera_capture_preview(self._camera, self._context))
        return bytes(gp.check_result(gp.gp_file_get_data_and_size(camera_file)))

    async def preview_stream(self) -> AsyncIterator[bytes]:
        async def _stream() -> AsyncIterator[bytes]:
            while True:
                yield await self.preview_frame_jpeg()
                await asyncio.sleep(0.2)
        return _stream()


__all__ = ["GphotoCameraAdapter"]
