"""Tripod abstraction protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ...core.models import TripodStatus


@dataclass(frozen=True)
class MoveResult:
    """Outcome of a motion command."""
    pan_deg: float
    tilt_deg: float
    success: bool
    error: str | None = None


@runtime_checkable
class TripodAdapter(Protocol):
    """Protocol for pan-tilt head hardware drivers (FR-005..FR-011)."""

    async def open(self) -> None:
        """Initialize serial/network connection."""
        ...

    async def close(self) -> None:
        """Close connection."""
        ...

    async def version(self) -> str:
        """Query firmware SemVer."""
        ...

    async def status(self) -> TripodStatus:
        """Fetch current angles and driver state."""
        ...

    async def move_to(self, pan: float, tilt: float) -> MoveResult:
        """Absolute move; blocks until DONE or timeout."""
        ...

    async def nudge(self, delta_pan: float, delta_tilt: float) -> MoveResult:
        """Relative move."""
        ...

    async def home(self) -> None:
        """Reset internal counters to (0,0)."""
        ...

    async def set_drivers(self, enabled: bool) -> None:
        """Enable or disable stepper outputs."""
        ...

    async def stop(self) -> None:
        """Emergency stop (X command)."""
        ...

    async def set_microstep(self, resolution: int) -> None:
        """Change resolution (1, 2, 4, 8, 16)."""
        ...
