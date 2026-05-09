"""Tilt safety enforcement for host-side motion commands."""

from __future__ import annotations

from collections.abc import Iterable

from ..core.config import Angles, Configuration, TimelapseSequenceConfig
from ..core.errors import MotionLimitError


class SafetyService:
    """Pure safety checks shared by API, CLI, and runners."""

    def __init__(self, *, tilt_min_deg: float, tilt_max_deg: float) -> None:
        self.tilt_min_deg = tilt_min_deg
        self.tilt_max_deg = tilt_max_deg

    @classmethod
    def from_config(cls, config: Configuration) -> SafetyService:
        return cls(
            tilt_min_deg=config.safety.tilt_min_deg,
            tilt_max_deg=config.safety.tilt_max_deg,
        )

    def guard_move(self, pan_deg: float, tilt_deg: float) -> None:
        if not (self.tilt_min_deg <= tilt_deg <= self.tilt_max_deg):
            raise MotionLimitError(
                f"tilt {tilt_deg} outside safety window "
                f"[{self.tilt_min_deg}, {self.tilt_max_deg}]",
                pan_deg=pan_deg,
                tilt_deg=tilt_deg,
                tilt_min_deg=self.tilt_min_deg,
                tilt_max_deg=self.tilt_max_deg,
            )

    def validate_points(self, points: Iterable[Angles]) -> None:
        for point in points:
            self.guard_move(point.pan_deg, point.tilt_deg)

    def validate_sequence(self, config: Configuration) -> None:
        sequence = config.sequence
        if isinstance(sequence, TimelapseSequenceConfig):
            from .timelapse import _linear_interpolate

            self.validate_points(
                _linear_interpolate(
                    start=sequence.start,
                    target=sequence.target,
                    total_frames=sequence.total_frames,
                )
            )
            return
        self.validate_points([sequence.start, sequence.target])


__all__ = ["SafetyService"]
