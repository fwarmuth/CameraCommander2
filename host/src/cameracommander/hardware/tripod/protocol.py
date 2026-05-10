"""Firmware serial-protocol formatter and reply parser.

Authoritative for ``contracts/firmware-protocol.md`` v1.1.x. Both the host
adapter and the in-process mock firmware import the formatter / parser from
this module so any divergence is caught at one place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

LINE_TERMINATOR = "\n"

# --- Microstep token mapping ----------------------------------------
# Per `contracts/firmware-protocol.md` §4.4: token "6" is the keypad-friendly
# label for 16x microstepping.
_MICROSTEP_TOKEN: dict[int, str] = {1: "1", 2: "2", 4: "4", 8: "8", 16: "6"}
_MICROSTEP_FROM_TOKEN: dict[str, int] = {v: k for k, v in _MICROSTEP_TOKEN.items()}


# --- Command formatters ----------------------------------------------


def cmd_version() -> str:
    """``V`` — firmware version query."""
    return "V" + LINE_TERMINATOR


def cmd_status() -> str:
    """``S`` — status request."""
    return "S" + LINE_TERMINATOR


def cmd_move(pan_deg: float, tilt_deg: float) -> str:
    """``M <pan> <tilt>`` — absolute move (degrees, 6-decimal precision)."""
    return f"M {pan_deg:.6f} {tilt_deg:.6f}{LINE_TERMINATOR}"


def cmd_microstep(microstep: int) -> str:
    """Single-token microstep command (``1``/``2``/``4``/``8``/``6``)."""
    if microstep not in _MICROSTEP_TOKEN:
        raise ValueError(f"unsupported microstep: {microstep!r}")
    return _MICROSTEP_TOKEN[microstep] + LINE_TERMINATOR


def cmd_drivers(enabled: bool) -> str:
    """``e`` (enable) / ``d`` (disable)."""
    return ("e" if enabled else "d") + LINE_TERMINATOR


def cmd_stop() -> str:
    """``X`` — global emergency stop."""
    return "X" + LINE_TERMINATOR


def cmd_speed_up() -> str:
    """``+`` — scale both axes' speed by +10%."""
    return "+" + LINE_TERMINATOR


def cmd_speed_down() -> str:
    """``-`` — scale both axes' speed by -10%."""
    return "-" + LINE_TERMINATOR


# Pan / tilt helper tokens ------------------------------------------------


def cmd_pan_step() -> str:
    return "n" + LINE_TERMINATOR


def cmd_pan_revolution() -> str:
    return "c" + LINE_TERMINATOR


def cmd_pan_toggle_direction() -> str:
    return "r" + LINE_TERMINATOR


def cmd_pan_stop() -> str:
    return "x" + LINE_TERMINATOR


def cmd_tilt_step() -> str:
    return "w" + LINE_TERMINATOR


def cmd_tilt_revolution() -> str:
    return "p" + LINE_TERMINATOR


def cmd_tilt_toggle_direction() -> str:
    return "t" + LINE_TERMINATOR


def cmd_tilt_stop() -> str:
    return "z" + LINE_TERMINATOR


# --- Reply types ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VersionReply:
    major: int
    minor: int
    patch: int

    @property
    def semver(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True, slots=True)
class StatusReply:
    pan_deg: float
    tilt_deg: float
    drivers_enabled: bool


@dataclass(frozen=True, slots=True)
class ProgressReply:
    """Intermediate position report during motion."""

    pan_deg: float
    tilt_deg: float


@dataclass(frozen=True, slots=True)
class EstimateReply:
    """Firmware's expected duration for the move."""

    seconds: float


@dataclass(frozen=True, slots=True)
class DoneReply:
    """Reply to a successful ``M`` move."""


@dataclass(frozen=True, slots=True)
class OkReply:
    detail: str  # everything after the leading "OK "


@dataclass(frozen=True, slots=True)
class ErrorReply:
    code: Literal["Syntax", "Unknown", "DRIVERS_DISABLED", "AlreadyAtTarget", "MotorStall"] | str


Reply = VersionReply | StatusReply | ProgressReply | EstimateReply | DoneReply | OkReply | ErrorReply


# --- Parser ---------------------------------------------------------------


_VERSION_RE = re.compile(r"^VERSION\s+(\d+)\.(\d+)\.(\d+)\s*$")
_STATUS_RE = re.compile(r"^STATUS\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+([01])\s*$")
_PROGRESS_RE = re.compile(r"^PROGRESS\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*$")
_ESTIMATE_RE = re.compile(r"^ESTIMATE\s+(\d+(?:\.\d+)?)\s*$")


class ProtocolParseError(ValueError):
    """Raised when the firmware emits a line that does not match any known reply shape."""


def parse_reply(line: str) -> Reply:
    """Decode a single reply line into one of the typed reply objects.

    The trailing newline is tolerated; surrounding whitespace is stripped before
    matching but the firmware's grammar itself is enforced exactly.
    """

    raw = line.rstrip("\r\n").strip()
    if not raw:
        raise ProtocolParseError("empty reply line")

    if (m := _VERSION_RE.match(raw)) is not None:
        return VersionReply(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    if (m := _STATUS_RE.match(raw)) is not None:
        return StatusReply(
            pan_deg=float(m.group(1)),
            tilt_deg=float(m.group(2)),
            drivers_enabled=m.group(3) == "1",
        )

    if (m := _PROGRESS_RE.match(raw)) is not None:
        return ProgressReply(pan_deg=float(m.group(1)), tilt_deg=float(m.group(2)))

    if (m := _ESTIMATE_RE.match(raw)) is not None:
        return EstimateReply(seconds=float(m.group(1)))

    if raw == "DONE":
        return DoneReply()

    if raw.startswith("OK"):
        # "OK", "OK STOP", "OK MICROSTEP 16", ...
        detail = raw[2:].lstrip()
        return OkReply(detail=detail)

    if raw.startswith("ERR "):
        return ErrorReply(code=raw[4:].strip())

    raise ProtocolParseError(f"unrecognised firmware reply: {raw!r}")


__all__ = [
    "LINE_TERMINATOR",
    "DoneReply",
    "ErrorReply",
    "EstimateReply",
    "OkReply",
    "ProgressReply",
    "ProtocolParseError",
    "Reply",
    "StatusReply",
    "VersionReply",
    "cmd_drivers",
    "cmd_microstep",
    "cmd_move",
    "cmd_pan_revolution",
    "cmd_pan_step",
    "cmd_pan_stop",
    "cmd_pan_toggle_direction",
    "cmd_speed_down",
    "cmd_speed_up",
    "cmd_status",
    "cmd_stop",
    "cmd_tilt_revolution",
    "cmd_tilt_step",
    "cmd_tilt_stop",
    "cmd_tilt_toggle_direction",
    "cmd_version",
    "parse_reply",
]
