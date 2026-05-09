"""Software-only calibration state tracking."""

from __future__ import annotations

from datetime import UTC, datetime

from ..api.websocket import EventBus
from ..core.models import CalibrationStateValue, CalibrationStatus


class CalibrationService:
    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._status = CalibrationStatus()
        self._event_bus = event_bus

    @property
    def status(self) -> CalibrationStatus:
        return self._status

    @property
    def is_homed(self) -> bool:
        return self._status.state == CalibrationStateValue.homed

    def mark_homed(self) -> CalibrationStatus:
        self._status = CalibrationStatus(
            state=CalibrationStateValue.homed,
            set_at=datetime.now(tz=UTC),
        )
        return self._status

    def mark_unknown(self, reason: str = "") -> CalibrationStatus:
        self._status = CalibrationStatus(state=CalibrationStateValue.unknown)
        return self._status

    async def publish(self) -> None:
        if self._event_bus is not None:
            await self._event_bus.publish(
                "hardware.calibration",
                self._status.model_dump(mode="json"),
            )


__all__ = ["CalibrationService"]
