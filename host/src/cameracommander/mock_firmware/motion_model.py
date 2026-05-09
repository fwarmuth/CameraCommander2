"""Time-modeled motion simulator for the mock firmware.

The real ESP firmware blocks during a move until both axes settle. The mock
needs the same behaviour so host-side timing logic (capture cadence, stall
margin) is exercised against realistic latencies. The model is intentionally
simple: constant angular speed (degrees per second) plus a fixed settle delay.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MotionModel:
    """Tracks current pan/tilt and computes the time a move would take."""

    pan_deg: float = 0.0
    tilt_deg: float = 0.0
    deg_per_second: float = 60.0
    settle_delay_s: float = 0.25
    drivers_enabled: bool = True

    def expected_move_duration_s(self, target_pan_deg: float, target_tilt_deg: float) -> float:
        """Return the synthetic time a ``move_to`` should block for."""

        if self.deg_per_second <= 0:
            return 0.0
        delta = max(
            abs(target_pan_deg - self.pan_deg),
            abs(target_tilt_deg - self.tilt_deg),
        )
        return delta / self.deg_per_second + self.settle_delay_s

    def apply_move(self, target_pan_deg: float, target_tilt_deg: float) -> None:
        """Commit the new position (called once the simulated wait completes)."""

        self.pan_deg = target_pan_deg
        self.tilt_deg = target_tilt_deg

    def reset_position(self) -> None:
        """Driver enable / disable resets the position counter (FR-011)."""

        self.pan_deg = 0.0
        self.tilt_deg = 0.0


__all__ = ["MotionModel"]
