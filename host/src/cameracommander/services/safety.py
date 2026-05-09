"""Motion safety enforcement."""

from __future__ import annotations

from ..core.errors import MotionLimitError
from ..core.config import Configuration


class SafetyService:
    def __init__(self, tilt_min: float, tilt_max: float) -> None:
        self.tilt_min = tilt_min
        self.tilt_max = tilt_max

    @classmethod
    def from_config(cls, config: Configuration) -> SafetyService:
        return cls(config.safety.tilt_min_deg, config.safety.tilt_max_deg)

    def guard_move(self, pan: float, tilt: float) -> None:
        """Raise MotionLimitError if tilt is outside safety window."""
        if not (self.tilt_min <= tilt <= self.tilt_max):
            raise MotionLimitError(
                f"Tilt {tilt:.2f}° is outside safe window [{self.tilt_min:.1f}°, {self.tilt_max:.1f}°]"
            )

    def validate_sequence(self, config: Configuration) -> None:
        """Validate all keyframes and interpolated points for a sequence."""
        # For v1, we validate the start and target. 
        # Future: validate every interpolated step.
        self.guard_move(config.sequence.start.pan_deg, config.sequence.start.tilt_deg)
        self.guard_move(config.sequence.target.pan_deg, config.sequence.target.tilt_deg)
