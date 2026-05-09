"""Camera abstraction protocol."""

from __future__ import annotations

from typing import Any, AsyncIterator, Protocol, runtime_checkable

from ...core.config import SettingDescriptor
from ...core.models import CameraStatus, CaptureResult


@runtime_checkable
class CameraAdapter(Protocol):
    """Protocol for camera hardware drivers (FR-001, FR-002, FR-003, FR-004)."""

    async def open(self) -> None:
        """Initialize connection to the camera hardware."""
        ...

    async def close(self) -> None:
        """Release hardware resources."""
        ...

    async def status(self) -> CameraStatus:
        """Return the current connection and battery state."""
        ...

    async def query_settings(self) -> dict[str, SettingDescriptor]:
        """Fetch all supported gphoto2-style settings."""
        ...

    async def apply_settings(self, settings: dict[str, str | int | float | bool]) -> None:
        """Update camera parameters."""
        ...

    async def capture_still(self, *, autofocus: bool = False) -> CaptureResult:
        """Trigger a single exposure and return metadata."""
        ...

    async def start_recording(self) -> None:
        """Begin video capture."""
        ...

    async def stop_recording(self) -> None:
        """End video capture and finalize file."""
        ...

    async def preview_frame_jpeg(self) -> bytes:
        """Capture a single live-view frame as JPEG."""
        ...

    async def preview_stream(self) -> AsyncIterator[bytes]:
        """Return an infinite stream of JPEG preview frames."""
        ...
