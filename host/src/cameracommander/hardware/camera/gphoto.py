"""gphoto2-backed camera adapter.

The module is import-safe on machines without a camera attached; the native
``gphoto2`` binding is imported only when the adapter opens.
"""

from __future__ import annotations

import asyncio
import contextlib
import re
import tempfile
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from ...core.errors import CameraDisconnectedError, CameraError, CaptureError
from ...core.models import CameraState, CameraStatus
from .base import CaptureResult, SettingDescriptor


class GphotoCameraAdapter:
    def __init__(self, *, model_substring: str | None = None) -> None:
        self.model_substring = model_substring
        self._gp: Any = None
        self._context: Any = None
        self._camera: Any = None
        self._model: str | None = None
        self._port_path: str | None = None
        self._last_error: str | None = None
        self._lock = asyncio.Lock()

    async def open(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._open_blocking)

    async def close(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._close_blocking)

    async def status(self) -> CameraStatus:
        # This method is read-only for local state, no lock needed
        state = CameraState.connected if self._camera is not None else CameraState.disconnected
        return CameraStatus(state=state, model=self._model, last_error=self._last_error)

    async def query_settings(self) -> dict[str, SettingDescriptor]:
        async with self._lock:
            return await asyncio.to_thread(self._query_settings_blocking)

    async def apply_settings(self, settings: dict[str, str | int | float | bool]) -> None:
        async with self._lock:
            await asyncio.to_thread(self._apply_settings_blocking, settings)

    async def capture_still(self, *, autofocus: bool = False) -> CaptureResult:
        async with self._lock:
            return await asyncio.to_thread(self._capture_blocking, autofocus)

    async def start_recording(self) -> None:
        # apply_settings handles its own lock
        await self.apply_settings({"main.actions.movie": 1})

    async def stop_recording(self) -> None:
        # apply_settings handles its own lock
        await self.apply_settings({"main.actions.movie": 0})

    async def preview_frame_jpeg(self) -> bytes:
        async with self._lock:
            return await asyncio.to_thread(self._preview_blocking)

    async def preview_stream(self) -> AsyncIterator[bytes]:
        async def _stream() -> AsyncIterator[bytes]:
            while True:
                yield await self.preview_frame_jpeg()
                await asyncio.sleep(0.2)

        return _stream()

    def _ensure_gp(self) -> Any:
        if self._gp is None:
            try:
                import gphoto2 as gp  # type: ignore
            except Exception as exc:  # pragma: no cover - depends on host libs
                raise CameraDisconnectedError(f"gphoto2 binding unavailable: {exc}") from exc
            self._gp = gp
        return self._gp

    def _open_blocking(self) -> None:
        gp = self._ensure_gp()
        self._context = gp.Context()
        camera_list = gp.check_result(gp.gp_camera_autodetect(self._context))
        discovered: list[tuple[str, str]] = []
        for index in range(camera_list.count()):
            discovered.append((camera_list.get_name(index), camera_list.get_value(index)))
        if self.model_substring:
            matches = [
                item
                for item in discovered
                if self.model_substring.lower() in item[0].lower()
            ]
        else:
            matches = discovered[:1]
        if not matches:
            raise CameraDisconnectedError("no gphoto2-compatible camera detected")
        if len(matches) > 1:
            raise CameraError(f"multiple cameras match {self.model_substring!r}")

        self._model, self._port_path = matches[0]
        abilities = gp.CameraAbilitiesList()
        abilities.load()
        ability = abilities.get_abilities(abilities.lookup_model(self._model))
        ports = gp.PortInfoList()
        ports.load()
        port_info = ports.get_info(ports.lookup_path(self._port_path))
        camera = gp.Camera()
        camera.set_abilities(ability)
        camera.set_port_info(port_info)
        try:
            camera.init()
        except Exception as exc:
            self._last_error = str(exc)
            raise CameraDisconnectedError(f"could not initialise camera: {exc}") from exc
        self._camera = camera

    def _close_blocking(self) -> None:
        if self._camera is None:
            return
        try:
            self._camera.exit()
        finally:
            self._camera = None

    def _require_camera(self) -> tuple[Any, Any]:
        gp = self._ensure_gp()
        if self._camera is None:
            raise CameraDisconnectedError("camera is not open")
        return gp, self._camera

    def _query_settings_blocking(self) -> dict[str, SettingDescriptor]:
        gp, camera = self._require_camera()
        root = gp.check_result(gp.gp_camera_get_config(camera, self._context))
        settings: dict[str, SettingDescriptor] = {}

        def walk(widget: Any, prefix: str = "") -> None:
            for idx in range(widget.count_children()):
                child = widget.get_child(idx)
                name = child.get_name()
                path = f"{prefix}.{name}" if prefix else name
                if child.count_children():
                    walk(child, path)
                    continue
                current = None
                with contextlib.suppress(Exception):
                    current = child.get_value()
                choices = None
                if hasattr(child, "count_choices"):
                    try:
                        choices = [child.get_choice(i) for i in range(child.count_choices())]
                    except Exception:
                        choices = None
                settings[path] = SettingDescriptor(
                    type=str(child.get_type()),
                    current=current,
                    choices=choices,
                )

        walk(root)
        return settings

    def _find_widget(self, root: Any, path: str) -> Any:
        node = root
        for part in path.split("."):
            node = node.get_child_by_name(part)
        return node

    def _apply_settings_blocking(self, settings: dict[str, str | int | float | bool]) -> None:
        gp, camera = self._require_camera()
        root = gp.check_result(gp.gp_camera_get_config(camera, self._context))
        for key, value in settings.items():
            try:
                self._find_widget(root, key).set_value(value)
            except Exception as exc:
                raise CameraError(f"setting {key!r} failed: {exc}") from exc
        gp.check_result(gp.gp_camera_set_config(camera, root, self._context))

    def _preview_blocking(self) -> bytes:
        gp, camera = self._require_camera()
        camera_file = gp.check_result(gp.gp_file_new())
        gp.check_result(gp.gp_camera_capture_preview(camera, camera_file, self._context))
        return bytes(gp.check_result(gp.gp_file_get_data_and_size(camera_file)))

    def _capture_blocking(self, autofocus: bool) -> CaptureResult:
        if autofocus:
            return self._capture_regular_blocking()
        try:
            return self._capture_no_af_blocking()
        except CameraError:
            raise
        except Exception:
            return self._capture_regular_blocking()

    def _capture_regular_blocking(self) -> CaptureResult:
        gp, camera = self._require_camera()
        try:
            path = gp.check_result(gp.gp_camera_capture(camera, gp.GP_CAPTURE_IMAGE, self._context))
            camera_file = gp.check_result(
                gp.gp_camera_file_get(
                    camera,
                    path.folder,
                    path.name,
                    gp.GP_FILE_TYPE_NORMAL,
                    self._context,
                )
            )
            data = bytes(gp.check_result(gp.gp_file_get_data_and_size(camera_file)))
            extension = Path(path.name).suffix or ".jpg"
            return CaptureResult(
                content_type=_content_type(extension),
                bytes_=data,
                captured_at=time.time(),
                extension=extension,
            )
        except Exception as exc:
            raise CaptureError(f"capture failed: {exc}") from exc

    def _capture_no_af_blocking(self) -> CaptureResult:
        gp, camera = self._require_camera()
        try:
            self._apply_settings_blocking({"main.actions.eosremoterelease": "Immediate"})
            event_type, event_data = gp.check_result(
                gp.gp_camera_wait_for_event(camera, 5000, self._context)
            )
            while event_type != gp.GP_EVENT_FILE_ADDED:
                event_type, event_data = gp.check_result(
                    gp.gp_camera_wait_for_event(camera, 5000, self._context)
                )
            camera_file = gp.check_result(
                gp.gp_camera_file_get(
                    camera,
                    event_data.folder,
                    event_data.name,
                    gp.GP_FILE_TYPE_NORMAL,
                    self._context,
                )
            )
            data = bytes(gp.check_result(gp.gp_file_get_data_and_size(camera_file)))
            with tempfile.NamedTemporaryFile(delete=True):
                pass
            self._apply_settings_blocking({"main.actions.eosremoterelease": "Release Full"})
            extension = Path(event_data.name).suffix or ".jpg"
            return CaptureResult(
                content_type=_content_type(extension),
                bytes_=data,
                captured_at=time.time(),
                extension=extension,
            )
        except Exception as exc:
            raise CaptureError(f"no-AF capture failed: {exc}") from exc


def _content_type(extension: str) -> str:
    ext = extension.lower()
    if ext in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if re.match(r"\.cr[23]$", ext):
        return "image/x-canon-cr3"
    if ext == ".nef":
        return "image/x-nikon-nef"
    return "application/octet-stream"


__all__ = ["GphotoCameraAdapter"]
