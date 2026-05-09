"""Line-protocol formatter and parser for CameraCommander2 firmware (v1)."""

from __future__ import annotations

from dataclasses import dataclass

from ...core.errors import ProtocolVersionMismatchError


@dataclass(frozen=True)
class DoneReply:
    pass


@dataclass(frozen=True)
class ErrorReply:
    code: str


@dataclass(frozen=True)
class OkReply:
    message: str


@dataclass(frozen=True)
class StatusReply:
    pan_deg: float
    tilt_deg: float
    drivers_enabled: bool


@dataclass(frozen=True)
class VersionReply:
    semver: str


def cmd_drivers(enabled: bool) -> str:
    return "e\n" if enabled else "d\n"


def cmd_microstep(res: int) -> str:
    mapping = {1: "1", 2: "2", 4: "4", 8: "8", 16: "6"}
    if res not in mapping:
        raise ValueError(f"Unsupported microstep resolution: {res}")
    return f"{mapping[res]}\n"


def cmd_move(pan: float, tilt: float) -> str:
    return f"M {pan:.6f} {tilt:.6f}\n"


# Aliases for tests
format_move = cmd_move
ParsedStatus = StatusReply


def parse_status(line: str) -> StatusReply:
    reply = parse_reply(line)
    if isinstance(reply, StatusReply):
        return reply
    raise ValueError(f"Not a status reply: {line}")


def cmd_status() -> str:
    return "S\n"


def cmd_stop() -> str:
    return "X\n"


def cmd_version() -> str:
    return "V\n"


def parse_reply(line: str) -> DoneReply | ErrorReply | OkReply | StatusReply | VersionReply:
    line = line.strip()
    if not line:
        raise ValueError("Empty reply")

    upper = line.upper()
    if upper == "DONE":
        return DoneReply()

    if upper.startswith("ERR"):
        parts = line.split(None, 1)
        code = parts[1] if len(parts) > 1 else "Unknown"
        return ErrorReply(code=code)

    if upper.startswith("OK"):
        parts = line.split(None, 1)
        msg = parts[1] if len(parts) > 1 else ""
        return OkReply(message=msg)

    if upper.startswith("STATUS"):
        parts = line.split()
        if len(parts) != 4:
            raise ValueError(f"Invalid STATUS reply: {line}")
        return StatusReply(
            pan_deg=float(parts[1]),
            tilt_deg=float(parts[2]),
            drivers_enabled=parts[3] == "1",
        )

    if upper.startswith("VERSION"):
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"Invalid VERSION reply: {line}")
        return VersionReply(semver=parts[1])

    raise ValueError(f"Unknown reply format: {line}")


def check_protocol_version(actual: str, expected_major: int) -> None:
    major = int(actual.split(".")[0])
    if major != expected_major:
        raise ProtocolVersionMismatchError(
            f"Firmware reports {actual}, host expects major {expected_major}"
        )
