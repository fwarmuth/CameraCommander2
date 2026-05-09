"""Calibration and homing state management."""

from __future__ import annotations

from datetime import datetime
from ..core.models import CalibrationValue


class CalibrationService:
    def __init__(self, bus: Any = None) -> None:
        self._bus = bus
        self._state = CalibrationValue.unknown
        self._last_home_at: datetime | None = None

    @property
    def state(self) -> CalibrationValue:
        return self._state

    def mark_homed(self) -> None:
        self._state = CalibrationValue.homed
        self._last_home_at = datetime.now()
        if self._bus:
            asyncio.create_task(self._bus.publish("hardware.calibration", {"state": "homed"}))

    def mark_unknown(self, reason: str | None = None) -> None:
        self._state = CalibrationValue.unknown
        if self._bus:
            asyncio.create_task(self._bus.publish("hardware.calibration", {"state": "unknown", "reason": reason}))
