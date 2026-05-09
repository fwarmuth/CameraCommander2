"""Runtime entity models: Job, Session, HardwareConnection, FaultEvent.

These mirror ``data-model.md`` sections 2-5 and are surfaced over the REST + WebSocket
contracts. Configuration models live in :mod:`cameracommander.core.config`.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, Field

from .config import Angles, Configuration


class CalibrationValue(StrEnum):
    unknown = "unknown"
    homed = "homed"


class CameraState(StrEnum):
    connected = "connected"
    disconnected = "disconnected"
    error = "error"


class CameraStatus(BaseModel):
    state: CameraState
    model: str | None = None
    last_error: str | None = None
    battery_pct: int | None = None


class TripodState(StrEnum):
    connected = "connected"
    disconnected = "disconnected"
    error = "error"


class TripodStatus(BaseModel):
    state: TripodState
    firmware_version: str | None = None
    protocol_compatible: bool = True
    drivers_enabled: bool = False
    position_pan_deg: float = 0.0
    position_tilt_deg: float = 0.0
    tilt_min_deg: float | None = None
    tilt_max_deg: float | None = None
    last_error: str | None = None


class HardwareStatus(BaseModel):
    camera: CameraStatus
    tripod: TripodStatus
    calibration_state: CalibrationValue
    active_job_id: Annotated[str, Field(description="UUID")] | None = None
    updated_at: datetime = Field(default_factory=datetime.now)


class JobKind(StrEnum):
    timelapse = "timelapse"
    video_pan = "video_pan"
    assembly = "assembly"


class JobStatus(StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    stopped = "stopped"


class JobProgress(BaseModel):
    frames_completed: int = 0
    frames_total: int = 0
    motion_pct: float = 0.0
    estimated_finish_at: datetime | None = None


class FaultEvent(BaseModel):
    code: str
    message: str
    frame_index: int | None = None
    last_position: Angles | None = None
    recoverable: bool = False


class Job(BaseModel):
    job_id: Annotated[str, Field(description="UUID")]
    kind: JobKind
    status: JobStatus
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    progress: JobProgress = Field(default_factory=JobProgress)
    last_position: Angles | None = None
    fault: FaultEvent | None = None
    session_id: Annotated[str, Field(description="UUID")] | None = None


class SessionAssetKind(StrEnum):
    frame = "frame"
    video = "video"
    metadata = "metadata"
    preview = "preview"


class SessionAsset(BaseModel):
    path: str
    kind: SessionAssetKind
    size_bytes: int | None = None
    content_type: str | None = None
    label: str | None = None


class SessionSummary(BaseModel):
    session_id: Annotated[str, Field(description="UUID")]
    kind: JobKind
    status: JobStatus
    name: str
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    finished_at: datetime | None = None
    frames_captured: int = 0
    frames_planned: int = 0
    flags: dict[str, bool] = Field(default_factory=dict)


class Session(SessionSummary):
    configuration: Configuration
    assets: list[SessionAsset] = Field(default_factory=list)
    fault: FaultEvent | None = None


class CaptureResult(BaseModel):
    """Result of a one-shot still capture."""

    capture_id: Annotated[str, Field(description="UUID")]
    content_type: str
    captured_at: datetime
    size_bytes: int
    download_url: str


__all__ = [
    "CalibrationValue",
    "CameraState",
    "CameraStatus",
    "CaptureResult",
    "FaultEvent",
    "HardwareStatus",
    "Job",
    "JobKind",
    "JobProgress",
    "JobStatus",
    "Session",
    "SessionAsset",
    "SessionAssetKind",
    "SessionSummary",
    "TripodState",
    "TripodStatus",
]
