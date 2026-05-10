"""Pydantic v2 models for the YAML session configuration.

Authoritative shape: ``specs/001-core-system/contracts/config-schema.md``.
The same models back the FastAPI ``Configuration`` request body (Constitution III).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .errors import ConfigError


class Angles(BaseModel):
    pan_deg: float
    tilt_deg: float


class ConfigurationMetadata(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    description: Annotated[str, Field(default="", max_length=2000)]
    tags: Annotated[list[str], Field(default_factory=list, max_length=16)]
    created_at: datetime = Field(default_factory=datetime.now)


class CameraConfig(BaseModel):
    model_substring: str = ""
    settings: dict[str, Any] = Field(default_factory=dict)
    image_format: Literal["camera-default", "jpeg-only", "raw-only", "raw+jpeg"] = (
        "camera-default"
    )


class SerialConfig(BaseModel):
    port: str
    baudrate: int = 9600
    timeout: float = 30.0
    write_timeout: float = 1.0
    reconnect_interval: float = 2.0
    max_retries: int = 5


class TripodConfig(BaseModel):
    serial: SerialConfig
    microstep: Literal[1, 2, 4, 8, 16] = 16
    expected_protocol_major: int = 1


class SafetyConfig(BaseModel):
    tilt_min_deg: float
    tilt_max_deg: float
    move_timeout_margin_s: float = Field(default=2.0, ge=0)
    disk_min_free_bytes: int = Field(default=200_000_000, ge=0)
    disk_avg_frame_bytes: int = Field(default=20_000_000, ge=0)

    @model_validator(mode="after")
    def validate_tilt_range(self) -> SafetyConfig:
        if self.tilt_max_deg < self.tilt_min_deg:
            raise ValueError("tilt_max_deg must be >= tilt_min_deg")
        return self


class VideoConfig(BaseModel):
    assemble: bool = False
    fps: int = Field(default=25, ge=1)
    format: Literal["mp4-h264", "mov-prores", "webm-vp9"] = "mp4-h264"
    ffmpeg_extra: str = "-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p"


class OutputConfig(BaseModel):
    output_dir: str
    frame_filename_template: str = "frame_{index:04d}{ext}"
    metadata_strategy: Literal["exif", "csv", "auto"] = "auto"
    video: VideoConfig = Field(default_factory=VideoConfig)

    @model_validator(mode="after")
    def validate_filename(self) -> OutputConfig:
        if "{index:04d}" not in self.frame_filename_template:
            raise ValueError("frame_filename_template must include {index:04d} (FR-043)")
        return self


class TimelapseSequenceConfig(BaseModel):
    kind: Literal["timelapse"] = "timelapse"
    total_frames: int = Field(ge=2)
    interval_s: float = Field(gt=0)
    settle_time_s: float = Field(default=0, ge=0)
    start: Angles
    target: Angles

    @model_validator(mode="after")
    def validate_timing(self) -> TimelapseSequenceConfig:
        if self.settle_time_s > self.interval_s:
            raise ValueError("settle_time_s: must be <= interval_s (FR-017)")
        return self


class VideoPanSequenceConfig(BaseModel):
    kind: Literal["video_pan"] = "video_pan"
    duration_s: float = Field(gt=0)
    start: Angles
    target: Angles


class AbsoluteMoveRequest(BaseModel):
    pan_deg: float
    tilt_deg: float


class RelativeNudgeRequest(BaseModel):
    delta_pan_deg: float = 0.0
    delta_tilt_deg: float = 0.0


class DriverRequest(BaseModel):
    enabled: bool


SequenceConfig = Annotated[
    TimelapseSequenceConfig | VideoPanSequenceConfig, Field(discriminator="kind")
]


class HostConfig(BaseModel):
    """Host-level persistent configuration (usually ~/.cameracommander/host.yaml)."""

    model_config = ConfigDict(extra="forbid")

    camera: CameraConfig = Field(default_factory=CameraConfig)
    tripod: TripodConfig | None = None
    session_library_root: Path = Field(
        default_factory=lambda: Path.home() / ".cameracommander" / "sessions"
    )


class Configuration(BaseModel):
    """Full, validated session configuration (FR-026)."""

    model_config = ConfigDict(extra="forbid")

    metadata: ConfigurationMetadata
    camera: CameraConfig
    tripod: TripodConfig
    safety: SafetyConfig
    output: OutputConfig
    sequence: SequenceConfig


class SettingDescriptor(BaseModel):
    """Metadata for a single camera setting widget."""

    full_path: str
    label: str
    type: Literal[
        "TEXT", "RANGE", "TOGGLE", "RADIO", "MENU", "DATE", "BUTTON", "UNKNOWN"
    ]
    current: str | float | bool | None
    choices: list[str] | None = None
    range: dict[str, float] | None = None


def load_host_configuration(source: str | Path) -> HostConfig:
    """Parse a YAML file or YAML string and return a validated ``HostConfig``.

    Wraps Pydantic ``ValidationError`` in :class:`ConfigError` so callers across
    the host can catch a single domain exception.
    """

    if isinstance(source, Path) or (
        isinstance(source, str) and "\n" not in source and Path(source).exists()
    ):
        text = Path(source).read_text(encoding="utf-8")
    else:
        text = source
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML parse error: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("Configuration root must be a YAML mapping")
    try:
        return HostConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigError(str(exc)) from exc


def load_configuration(source: str | Path) -> Configuration:
    """Parse a YAML file or YAML string and return a validated ``Configuration``.

    Wraps Pydantic ``ValidationError`` in :class:`ConfigError` so callers across
    the host can catch a single domain exception.
    """

    if isinstance(source, Path) or (isinstance(source, str) and "\n" not in source):
        text = Path(source).read_text(encoding="utf-8")
    else:
        text = source
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML parse error: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("Configuration root must be a YAML mapping")
    try:
        return Configuration.model_validate(raw)
    except Exception as exc:
        raise ConfigError(str(exc)) from exc


def dump_configuration(config: Configuration) -> str:
    """Serialize a ``Configuration`` back to YAML."""
    return yaml.dump(config.model_dump(), sort_keys=False, indent=2)


__all__ = [
    "AbsoluteMoveRequest",
    "Angles",
    "CameraConfig",
    "Configuration",
    "ConfigurationMetadata",
    "DriverRequest",
    "HostConfig",
    "OutputConfig",
    "RelativeNudgeRequest",
    "SafetyConfig",
    "SequenceConfig",
    "SerialConfig",
    "SettingDescriptor",
    "TimelapseSequenceConfig",
    "TripodConfig",
    "VideoConfig",
    "VideoPanSequenceConfig",
    "dump_configuration",
    "load_configuration",
    "load_host_configuration",
]
