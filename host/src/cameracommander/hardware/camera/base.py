"""``CameraAdapter`` protocol — the host-side abstraction for cameras.

Concrete implementations live in :mod:`cameracommander.hardware.camera.gphoto`
(real cameras via libgphoto2) and :mod:`cameracommander.hardware.camera.mock`
(synthetic frames for development and CI). Constitution II requires both code
paths to satisfy the same protocol.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from ...core.models import CameraStatus


@dataclass(slots=True)
class SettingDescriptor:
    """Describes one gphoto2 widget the camera exposes."""

    type: str  # "TEXT" | "RANGE" | "TOGGLE" | "RADIO" | "MENU" | "DATE" | "BUTTON" | "UNKNOWN"
    current: str | int | float | bool | None
    choices: list[str] | None = None
    range: tuple[float, float, float] | None = None  # (min, max, step)


@dataclass(slots=True)
class CaptureResult:
    """Result of a still capture: file bytes plus content metadata."""

    content_type: str
    bytes_: bytes
    captured_at: float  # unix seconds (monotonic-equivalent)
    extension: str  # ".jpg" | ".cr3" | ".nef" | ...
    extra: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class CameraAdapter(Protocol):
    """Protocol every camera implementation must satisfy."""

    async def open(self) -> None:
        """Acquire the camera handle. Idempotent."""

    async def close(self) -> None:
        """Release the camera handle. Idempotent."""

    async def status(self) -> CameraStatus:
        """Return the current camera state (used by ``GET /api/hardware/status``)."""

    async def query_settings(self) -> dict[str, SettingDescriptor]:
        """Return all gphoto2 widget paths and their current values."""

    async def apply_settings(self, settings: dict[str, str | int | float | bool]) -> None:
        """Apply a partial settings update. Raises ``CaptureError`` on rejection."""

    async def capture_still(self, *, autofocus: bool = False) -> CaptureResult:
        """Trigger a single still capture and return its bytes (FR-002)."""

    async def start_recording(self) -> None:
        """Start camera video recording (FR-003)."""

    async def stop_recording(self) -> None:
        """Stop camera video recording (FR-003)."""

    async def preview_frame_jpeg(self) -> bytes:
        """Return one JPEG live-view frame (FR-004)."""

    async def preview_stream(self) -> AsyncIterator[bytes]:
        """Yield JPEG frames continuously for the MJPEG endpoint (FR-004)."""


__all__ = ["CameraAdapter", "CaptureResult", "SettingDescriptor"]
