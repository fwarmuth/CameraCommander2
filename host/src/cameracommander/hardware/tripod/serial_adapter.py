"""Pyserial-backed tripod adapter.

Supports normal serial ports and pyserial URL handlers such as
``socket://127.0.0.1:9999`` so the mock firmware exercises the same code path
as real ESP hardware.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import serial

from ...core.config import TripodConfig
from ...core.errors import (
    MotorStallError,
    ProtocolVersionMismatchError,
    SerialLostError,
    TripodError,
)
from ...core.models import TripodState, TripodStatus
from .base import MoveResult, StatusReport
from .protocol import (
    DoneReply,
    ErrorReply,
    OkReply,
    StatusReply,
    VersionReply,
    cmd_drivers,
    cmd_microstep,
    cmd_move,
    cmd_status,
    cmd_stop,
    cmd_version,
    parse_reply,
)


class SerialTripodAdapter:
    def __init__(self, config: TripodConfig) -> None:
        self.config = config
        self._serial: serial.SerialBase | None = None
        self._firmware_version: str | None = None
        self._pan_deg = 0.0
        self._tilt_deg = 0.0
        self._drivers_enabled = False
        self._protocol_compatible = True
        self._last_error: str | None = None
        self._lock = asyncio.Lock()

    async def open(self) -> None:
        await asyncio.to_thread(self._open_blocking)
        version = await self.version()
        major = int(version.split(".", 1)[0])
        if major != self.config.expected_protocol_major:
            self._protocol_compatible = False
            self._last_error = f"tripod protocol version mismatch: {version}"
            raise ProtocolVersionMismatchError(
                f"tripod protocol version mismatch: {version}",
                expected_major=self.config.expected_protocol_major,
                actual=version,
            )
        await self.set_microstep(self.config.microstep)
        await self.report()

    async def close(self) -> None:
        if self._serial is not None:
            await asyncio.to_thread(self._serial.close)
            self._serial = None

    async def status(self) -> TripodStatus:
        try:
            if not self._protocol_compatible:
                state = TripodState.error
            elif self._serial is not None and self._serial.is_open:
                await self.report()
                state = TripodState.connected
            else:
                state = TripodState.disconnected
        except Exception as exc:
            state = TripodState.error
            self._last_error = str(exc)
        return TripodStatus(
            state=state,
            firmware_version=self._firmware_version,
            protocol_compatible=self._protocol_compatible,
            drivers_enabled=self._drivers_enabled,
            position_pan_deg=self._pan_deg,
            position_tilt_deg=self._tilt_deg,
            last_error=self._last_error,
        )

    async def version(self) -> str:
        reply = await self._send(cmd_version(), expected=VersionReply)
        self._firmware_version = reply.semver
        return reply.semver

    async def report(self) -> StatusReport:
        reply = await self._send(cmd_status(), expected=StatusReply)
        self._pan_deg = reply.pan_deg
        self._tilt_deg = reply.tilt_deg
        self._drivers_enabled = reply.drivers_enabled
        return StatusReport(reply.pan_deg, reply.tilt_deg, reply.drivers_enabled)

    async def move_to(
        self,
        pan_deg: float,
        tilt_deg: float,
        *,
        expected_duration_s: float | None = None,
    ) -> MoveResult:
        started = time.monotonic()
        reply = await self._send(
            cmd_move(pan_deg, tilt_deg),
            expected=DoneReply,
            timeout_override=expected_duration_s,
        )
        if not isinstance(reply, DoneReply):  # pragma: no cover - type guard
            raise MotorStallError("move did not complete")
        duration = time.monotonic() - started
        self._pan_deg = pan_deg
        self._tilt_deg = tilt_deg
        return MoveResult(pan_deg=pan_deg, tilt_deg=tilt_deg, duration_s=duration)

    async def nudge(
        self,
        *,
        delta_pan_deg: float = 0.0,
        delta_tilt_deg: float = 0.0,
    ) -> MoveResult:
        return await self.move_to(
            self._pan_deg + delta_pan_deg,
            self._tilt_deg + delta_tilt_deg,
        )

    async def home(self) -> None:
        self._pan_deg = 0.0
        self._tilt_deg = 0.0

    async def set_drivers(self, enabled: bool) -> None:
        await self._send(cmd_drivers(enabled), expected=OkReply)
        self._drivers_enabled = enabled
        self._pan_deg = 0.0
        self._tilt_deg = 0.0

    async def stop(self) -> None:
        await self._send(cmd_stop(), expected=OkReply)

    async def set_microstep(self, microstep: int) -> None:
        await self._send(cmd_microstep(microstep), expected=OkReply)

    def _open_blocking(self) -> None:
        serial_cfg = self.config.serial
        kwargs: dict[str, Any] = {
            "baudrate": serial_cfg.baudrate,
            "timeout": serial_cfg.timeout,
            "write_timeout": serial_cfg.write_timeout,
        }
        if not serial_cfg.port.startswith("socket://"):
            kwargs["exclusive"] = True
        last_exc: Exception | None = None
        for _ in range(serial_cfg.max_retries + 1):
            try:
                self._serial = serial.serial_for_url(serial_cfg.port, **kwargs)
                return
            except serial.SerialException as exc:
                last_exc = exc
                time.sleep(serial_cfg.reconnect_interval)
        raise SerialLostError(f"could not open serial port: {last_exc}")

    async def _send(
        self,
        command: str,
        *,
        expected: type,
        timeout_override: float | None = None,
    ):
        async with self._lock:
            return await asyncio.to_thread(
                self._send_blocking,
                command,
                expected,
                timeout_override,
            )

    def _send_blocking(self, command: str, expected: type, timeout_override: float | None):
        ser = self._serial
        if ser is None or not ser.is_open:
            raise SerialLostError("serial port is not open")
        old_timeout = ser.timeout
        if timeout_override is not None:
            ser.timeout = max(float(old_timeout or 0), timeout_override + 1.0)
        try:
            ser.write(command.encode("ascii"))
            ser.flush()
            deadline = time.monotonic() + float(ser.timeout or 1.0) + 0.5
            while time.monotonic() < deadline:
                raw = ser.readline()
                if not raw:
                    continue
                line = raw.decode("ascii", errors="replace").strip()
                try:
                    reply = parse_reply(line)
                except ValueError:
                    # Boot banners are intentionally ignored.
                    continue
                if isinstance(reply, ErrorReply):
                    raise TripodError(f"firmware error: {reply.code}", firmware_error=reply.code)
                if isinstance(reply, expected):
                    return reply
                raise TripodError(f"unexpected reply to {command.strip()}: {line}")
            raise MotorStallError(f"timeout waiting for reply to {command.strip()}")
        except serial.SerialException as exc:
            raise SerialLostError(str(exc)) from exc
        finally:
            ser.timeout = old_timeout


__all__ = ["SerialTripodAdapter"]
