"""Runtime entity models: Job, Session, HardwareConnection, FaultEvent.

These mirror ``data-model.md`` §2–§5 and are surfaced over the REST + WebSocket
contracts. Configuration models live in :mod:`cameracommander.core.config`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .config import Angles, Configuration


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


# --- Enums ---------------------------------------------------------------


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    stopped = "stopped"


class JobKind(str, Enum):
    timelapse = "timelapse"
    video_pan = "video_pan"


class CameraState(str, Enum):
    connected = "connected"
    disconnected = "disconnected"
    error = "error"


class TripodState(str, Enum):
    connected = "connected"
    disconnected = "disconnected"
    error = "error"


class CalibrationStateValue(str, Enum):
    unknown = "unknown"
    homed = "homed"


FaultCode = Literal[
    "camera_disconnected",
    "camera_capture_failed",
    "motor_stall",
    "serial_lost",
    "disk_full",
    "tilt_limit",
    "calibration_required",
    "config_invalid",
    "user_stopped",
]


# --- Faults -------------------------------------------------------------


class FaultEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: FaultCode
    message: str
    frame_index: int | None = None
    last_position: Angles | None = None
    recoverable: bool = False


# --- Job ---------------------------------------------------------------


class JobProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frames_completed: Annotated[int, Field(ge=0)] = 0
    frames_total: Annotated[int, Field(ge=0)] = 0
    motion_pct: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    estimated_finish_at: datetime | None = None


class Job(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    kind: JobKind
    status: JobStatus = JobStatus.pending
    created_at: datetime = Field(default_factory=_utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    progress: JobProgress = Field(default_factory=JobProgress)
    last_position: Angles | None = None
    fault: FaultEvent | None = None
    cadence_warnings: int = 0
    session_id: str | None = None


# --- Hardware status --------------------------------------------------


class CameraStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: CameraState = CameraState.disconnected
    model: str | None = None
    last_error: str | None = None
    battery_pct: int | None = Field(default=None, ge=0, le=100)


class TripodStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: TripodState = TripodState.disconnected
    firmware_version: str | None = None
    protocol_compatible: bool = True
    drivers_enabled: bool = False
    position_pan_deg: float = 0.0
    position_tilt_deg: float = 0.0
    tilt_min_deg: float | None = None
    tilt_max_deg: float | None = None
    last_error: str | None = None


class CalibrationStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: CalibrationStateValue = CalibrationStateValue.unknown
    set_at: datetime | None = None


class HardwareStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    camera: CameraStatus = Field(default_factory=CameraStatus)
    tripod: TripodStatus = Field(default_factory=TripodStatus)
    calibration: CalibrationStatus = Field(default_factory=CalibrationStatus)
    active_job_id: str | None = None
    updated_at: datetime = Field(default_factory=_utcnow)


# --- Session ---------------------------------------------------------


SessionAssetKind = Literal["frame", "video", "metadata", "preview"]


class SessionAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    kind: SessionAssetKind
    size_bytes: int | None = None
    content_type: str | None = None
    label: str | None = None


class SessionMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frames_captured: int = 0
    frames_planned: int = 0
    duration_s: float = 0.0
    cadence_warnings: int = 0


class SessionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    kind: JobKind
    status: JobStatus
    created_at: datetime
    finished_at: datetime | None = None
    name: str
    tags: list[str] = Field(default_factory=list)
    frames_captured: int = 0
    frames_planned: int = 0
    flags: dict[str, bool] = Field(default_factory=dict)


class Session(SessionSummary):
    """Persisted record of a Job. Lives at ``~/.cameracommander/sessions/<id>/``."""

    model_config = ConfigDict(extra="forbid")

    configuration: Configuration
    metrics: SessionMetrics = Field(default_factory=SessionMetrics)
    assets: list[SessionAsset] = Field(default_factory=list)
    fault: FaultEvent | None = None


__all__ = [
    "CalibrationStateValue",
    "CalibrationStatus",
    "CameraState",
    "CameraStatus",
    "FaultCode",
    "FaultEvent",
    "HardwareStatus",
    "Job",
    "JobKind",
    "JobProgress",
    "JobStatus",
    "Session",
    "SessionAsset",
    "SessionAssetKind",
    "SessionMetrics",
    "SessionSummary",
    "TripodState",
    "TripodStatus",
]
