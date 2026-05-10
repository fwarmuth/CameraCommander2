"""Byte-for-byte contract tests for the firmware serial protocol parser.

Validates the formatter / parser pair in
``cameracommander.hardware.tripod.protocol`` against
``specs/004-movement-feedback/contracts/firmware-protocol.md`` v1.1.x.
"""

from __future__ import annotations

import pytest

from cameracommander.hardware.tripod.protocol import (
    LINE_TERMINATOR,
    DoneReply,
    ErrorReply,
    EstimateReply,
    OkReply,
    ProgressReply,
    ProtocolParseError,
    StatusReply,
    VersionReply,
    cmd_drivers,
    cmd_microstep,
    cmd_move,
    cmd_speed_down,
    cmd_speed_up,
    cmd_status,
    cmd_stop,
    cmd_version,
    parse_reply,
)

# --- Command formatters ---------------------------------------------------


def test_version_command_is_v_newline() -> None:
    assert cmd_version() == "V" + LINE_TERMINATOR


def test_status_command_is_s_newline() -> None:
    assert cmd_status() == "S" + LINE_TERMINATOR


def test_move_command_six_decimal_floats() -> None:
    line = cmd_move(30.0, -5.25)
    assert line == "M 30.000000 -5.250000\n"


def test_microstep_token_mapping_includes_six_for_sixteen() -> None:
    # Per protocol §4.4: token "6" means microstep-16 (keypad ergonomics).
    assert cmd_microstep(1) == "1\n"
    assert cmd_microstep(2) == "2\n"
    assert cmd_microstep(4) == "4\n"
    assert cmd_microstep(8) == "8\n"
    assert cmd_microstep(16) == "6\n"


def test_microstep_rejects_unsupported_resolutions() -> None:
    with pytest.raises(ValueError):
        cmd_microstep(3)


def test_drivers_toggle() -> None:
    assert cmd_drivers(True) == "e\n"
    assert cmd_drivers(False) == "d\n"


def test_stop_and_speed_tokens() -> None:
    assert cmd_stop() == "X\n"
    assert cmd_speed_up() == "+\n"
    assert cmd_speed_down() == "-\n"


# --- Reply parser ---------------------------------------------------------


def test_parse_version_reply() -> None:
    reply = parse_reply("VERSION 1.0.1\n")
    assert isinstance(reply, VersionReply)
    assert reply.major == 1
    assert reply.minor == 0
    assert reply.patch == 1
    assert reply.semver == "1.0.1"


def test_parse_status_reply() -> None:
    reply = parse_reply("STATUS 12.500 -3.000 1\n")
    assert isinstance(reply, StatusReply)
    assert reply.pan_deg == pytest.approx(12.5)
    assert reply.tilt_deg == pytest.approx(-3.0)
    assert reply.drivers_enabled is True


def test_parse_status_reply_drivers_disabled() -> None:
    reply = parse_reply("STATUS 0.000 0.000 0\n")
    assert isinstance(reply, StatusReply)
    assert reply.drivers_enabled is False


def test_parse_progress_reply() -> None:
    reply = parse_reply("PROGRESS 12.345 -2.000\n")
    assert isinstance(reply, ProgressReply)
    assert reply.pan_deg == pytest.approx(12.345)
    assert reply.tilt_deg == pytest.approx(-2.0)


def test_parse_estimate_reply() -> None:
    reply = parse_reply("ESTIMATE 15.4\n")
    assert isinstance(reply, EstimateReply)
    assert reply.seconds == pytest.approx(15.4)


def test_parse_done_reply() -> None:
    assert isinstance(parse_reply("DONE\n"), DoneReply)


@pytest.mark.parametrize(
    ("line", "expected_detail"),
    [
        ("OK STOP\n", "STOP"),
        ("OK MICROSTEP 16\n", "MICROSTEP 16"),
        ("OK DRIVERS ON\n", "DRIVERS ON"),
        ("OK DRIVERS OFF\n", "DRIVERS OFF"),
        ("OK SPEED\n", "SPEED"),
        ("OK ROT STEP\n", "ROT STEP"),
    ],
)
def test_parse_ok_replies(line: str, expected_detail: str) -> None:
    reply = parse_reply(line)
    assert isinstance(reply, OkReply)
    assert reply.detail == expected_detail


@pytest.mark.parametrize(
    ("line", "expected_code"),
    [
        ("ERR Syntax\n", "Syntax"),
        ("ERR Unknown\n", "Unknown"),
        ("ERR DRIVERS_DISABLED\n", "DRIVERS_DISABLED"),
        ("ERR AlreadyAtTarget\n", "AlreadyAtTarget"),
        ("ERR MotorStall\n", "MotorStall"),
    ],
)
def test_parse_error_replies(line: str, expected_code: str) -> None:
    reply = parse_reply(line)
    assert isinstance(reply, ErrorReply)
    assert reply.code == expected_code


def test_parse_reply_tolerates_crlf_input() -> None:
    """Per protocol §1: firmware tolerates `\\r\\n` on input."""

    assert isinstance(parse_reply("DONE\r\n"), DoneReply)


def test_parse_reply_rejects_unknown_shape() -> None:
    with pytest.raises(ProtocolParseError):
        parse_reply("garbage line\n")


def test_parse_reply_rejects_empty_input() -> None:
    with pytest.raises(ProtocolParseError):
        parse_reply("\n")
