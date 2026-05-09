"""Line-protocol formatter and parser for CameraCommander2 firmware (v1)."""

from __future__ import annotations

import re
from typing import NamedTuple

from ...core.errors import ProtocolVersionMismatchError


class ParsedStatus(NamedTuple):
    pan: float
    tilt: float
    drivers: bool


def format_move(pan: float, tilt: float) -> str:
    return f"M {pan:.6f} {tilt:.6f}\n"


def format_set_drivers(enabled: bool) -> str:
    return "e\n" if enabled else "d\n"


def format_microstep(res: int) -> str:
    mapping = {1: "1", 2: "2", 4: "4", 8: "8", 16: "6"}
    if res not in mapping:
        raise ValueError(f"Unsupported microstep resolution: {res}")
    return f"{mapping[res]}\n"


def parse_version(line: str) -> str:
    if match := re.match(r"^VERSION\s+([\d\.]+)", line, re.I):
        return match.group(1)
    raise ValueError(f"Invalid VERSION reply: {line!r}")


def parse_status(line: str) -> ParsedStatus:
    # STATUS <pan> <tilt> <drivers>
    parts = line.split()
    if len(parts) != 4 or parts[0].upper() != "STATUS":
        raise ValueError(f"Invalid STATUS reply: {line!r}")
    return ParsedStatus(
        pan=float(parts[1]),
        tilt=float(parts[2]),
        drivers=parts[3] == "1"
    )


def check_protocol_version(actual: str, expected_major: int) -> None:
    major = int(actual.split(".")[0])
    if major != expected_major:
        raise ProtocolVersionMismatchError(
            f"Firmware reports {actual}, host expects major {expected_major}"
        )
