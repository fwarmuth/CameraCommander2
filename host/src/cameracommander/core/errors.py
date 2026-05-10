"""Domain exception hierarchy for CameraCommander2."""

from __future__ import annotations


class CameraCommanderError(Exception):
    """Base exception for all CameraCommander2 errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigError(CameraCommanderError):
    """Raised when configuration is invalid or missing required fields."""


class MotionLimitError(CameraCommanderError):
    """Raised when a move would exceed hardware or safety limits."""


class CalibrationRequiredError(CameraCommanderError):
    """Raised when an automated job is attempted without calibration."""


class MotorStallError(CameraCommanderError):
    """Raised when the firmware fails to complete a move in time."""


class SerialLostError(CameraCommanderError):
    """Raised when communication with the firmware is interrupted."""


class CameraError(CameraCommanderError):
    """Raised when gphoto2 encounters a hardware or driver error."""


class CaptureError(CameraCommanderError):
    """Raised when a still or video capture fails."""


class DiskFullError(CameraCommanderError):
    """Raised when available disk space is below safety threshold."""


class JobAlreadyRunningError(CameraCommanderError):
    """Raised when overlapping jobs are requested."""


class ProtocolVersionMismatchError(CameraCommanderError):
    """Raised when firmware reports an incompatible protocol major version."""

    def __init__(self, message: str, expected_major: int, actual: str) -> None:
        super().__init__(message)
        self.expected_major = expected_major
        self.actual = actual


class TripodError(CameraCommanderError):
    """Raised when the tripod encountered a hardware or protocol error."""

    def __init__(self, message: str, firmware_error: str | None = None) -> None:
        super().__init__(message)
        self.firmware_error = firmware_error


class MockOnlyError(CameraCommanderError):
    """Raised when a mock-specific feature is used in real hardware mode."""
