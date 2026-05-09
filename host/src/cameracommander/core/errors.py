"""Domain exception hierarchy for the CameraCommander host application.

Every cross-cutting failure mode in the spec maps to one of these classes;
API/CLI layers translate them into HTTP status codes and CLI exit codes.
"""

from __future__ import annotations


class CameraCommanderError(Exception):
    """Base class for all domain errors raised inside the host application."""

    code: str = "internal_error"

    def __init__(self, message: str = "", **details: object) -> None:
        super().__init__(message)
        self.message = message or self.__class__.__name__
        self.details: dict[str, object] = dict(details)


# --- Configuration / validation -------------------------------------------------


class ConfigError(CameraCommanderError):
    """Configuration document failed validation (FR-028)."""

    code = "config_invalid"


# --- Motion safety / calibration ------------------------------------------------


class MotionLimitError(CameraCommanderError):
    """A motion command would exceed the configured tilt safety window (FR-009)."""

    code = "tilt_limit"


class CalibrationRequiredError(CameraCommanderError):
    """An automated job requires homed calibration but state is unknown (FR-041)."""

    code = "calibration_required"


# --- Tripod / firmware ---------------------------------------------------------


class TripodError(CameraCommanderError):
    """Generic tripod / firmware fault — superclass for the more specific ones."""

    code = "tripod_error"


class MotorStallError(TripodError):
    """A move command did not complete within the expected duration plus margin (FR-037)."""

    code = "motor_stall"


class SerialLostError(TripodError):
    """Serial / TCP link to the firmware was lost mid-operation."""

    code = "serial_lost"


class ProtocolVersionMismatchError(TripodError):
    """Firmware reported a major protocol version the host is not compatible with (SC-008)."""

    code = "protocol_version_mismatch"


# --- Camera --------------------------------------------------------------------


class CameraError(CameraCommanderError):
    """Generic camera-side fault."""

    code = "camera_error"


class CameraDisconnectedError(CameraError):
    """Camera is not (or no longer) connected."""

    code = "camera_disconnected"


class CaptureError(CameraError):
    """A still or video capture attempt failed (FR-002)."""

    code = "camera_capture_failed"


# --- Resources / scheduling ----------------------------------------------------


class DiskFullError(CameraCommanderError):
    """Available disk space dropped below the safety threshold (FR-036)."""

    code = "disk_full"


class JobAlreadyRunningError(CameraCommanderError):
    """A second job launch was rejected because one is already running (FR-039)."""

    code = "job_already_running"


# --- Mock-only -----------------------------------------------------------------


class MockOnlyError(CameraCommanderError):
    """An operation is only valid against a mock adapter (used in tests / CI)."""

    code = "mock_only"


__all__ = [
    "CameraCommanderError",
    "ConfigError",
    "MotionLimitError",
    "CalibrationRequiredError",
    "TripodError",
    "MotorStallError",
    "SerialLostError",
    "ProtocolVersionMismatchError",
    "CameraError",
    "CameraDisconnectedError",
    "CaptureError",
    "DiskFullError",
    "JobAlreadyRunningError",
    "MockOnlyError",
]
