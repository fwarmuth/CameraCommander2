"""``TripodAdapter`` protocol — the host-side abstraction for the pan-tilt head.

Real hardware lives in :mod:`cameracommander.hardware.tripod.serial_adapter`
(pyserial; supports ``socket://`` URLs to talk to the in-process mock firmware).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ...core.models import TripodStatus


@dataclass(slots=True)
class StatusReport:
    """Decoded ``STATUS <pan> <tilt> <drivers>`` reply."""

    pan_deg: float
    tilt_deg: float
    drivers_enabled: bool


@dataclass(slots=True)
class MoveResult:
    """Outcome of an absolute move."""

    pan_deg: float
    tilt_deg: float
    duration_s: float


@runtime_checkable
class TripodAdapter(Protocol):
    """Protocol every tripod implementation must satisfy."""

    async def open(self) -> None:
        """Open the serial / socket link, drain banner, and run the version handshake."""

    async def close(self) -> None:
        """Release the link. Idempotent."""

    async def status(self) -> TripodStatus:
        """Return aggregated tripod state (calibration is a separate service)."""

    async def version(self) -> str:
        """Return the firmware-reported SemVer string (FR-014)."""

    async def report(self) -> StatusReport:
        """Send ``S`` and parse the reply (FR-006)."""

    async def move_to(
        self, pan_deg: float, tilt_deg: float, *, expected_duration_s: float | None = None
    ) -> MoveResult:
        """Issue ``M <pan> <tilt>`` and wait for ``DONE`` (FR-005). Raises ``MotorStallError``."""

    async def nudge(self, *, delta_pan_deg: float = 0.0, delta_tilt_deg: float = 0.0) -> MoveResult:
        """Apply a relative move (FR-007). Convenience over move_to."""

    async def home(self) -> None:
        """Software-only homing — caller flips ``CalibrationState`` to ``homed`` (FR-040)."""

    async def set_drivers(self, enabled: bool) -> None:
        """Enable or disable stepper drivers; disabling resets known position (FR-011)."""

    async def stop(self) -> None:
        """Emergency stop (``X``) — halts both axes immediately (FR-008)."""

    async def set_microstep(self, microstep: int) -> None:
        """Set microstep resolution; values: 1, 2, 4, 8, 16."""


__all__ = ["MoveResult", "StatusReport", "TripodAdapter"]
