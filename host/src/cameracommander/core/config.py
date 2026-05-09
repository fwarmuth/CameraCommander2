"""Pydantic v2 models for the YAML session configuration.

Authoritative shape: ``specs/001-core-system/contracts/config-schema.md``.
The same models back the FastAPI ``Configuration`` request body (Constitution III).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from .errors import ConfigError

# --- Common -----------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


class Angles(BaseModel):
    """An absolute (pan, tilt) keyframe in degrees."""

    model_config = ConfigDict(extra="forbid")

    pan_deg: float
    tilt_deg: float


class ConfigurationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=120)]
    description: Annotated[str, Field(default="", max_length=2000)] = ""
    tags: Annotated[
        list[Annotated[str, Field(max_length=40)]],
        Field(default_factory=list, max_length=16),
    ]
    created_at: datetime = Field(default_factory=_utcnow)


# --- Camera -----------------------------------------------------------------


class CameraConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_substring: str | None = None
    settings: dict[str, str | int | float | bool] = Field(default_factory=dict)
    image_format: Literal["camera-default", "jpeg-only", "raw-only", "raw+jpeg"] = (
        "camera-default"
    )


# --- Tripod -----------------------------------------------------------------


class SerialConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    port: str
    baudrate: int = 9600
    timeout: float = 1.0
    write_timeout: float = 1.0
    reconnect_interval: float = 2.0
    max_retries: int = 5


class TripodConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    serial: SerialConfig
    microstep: Literal[1, 2, 4, 8, 16] = 16
    expected_protocol_major: int = 1


# --- Safety -----------------------------------------------------------------


class SafetyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tilt_min_deg: float
    tilt_max_deg: float
    move_timeout_margin_s: Annotated[float, Field(ge=0)] = 2.0
    disk_min_free_bytes: Annotated[int, Field(ge=0)] = 200_000_000
    disk_avg_frame_bytes: Annotated[int, Field(ge=0)] = 20_000_000

    @model_validator(mode="after")
    def _check_window(self) -> SafetyConfig:
        if self.tilt_max_deg < self.tilt_min_deg:
            raise ValueError("safety: tilt_max_deg must be ≥ tilt_min_deg")
        return self


# --- Output -----------------------------------------------------------------


_FRAME_INDEX_RE = re.compile(r"\{index:0\d+d\}")


class VideoConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assemble: bool = True
    fps: Annotated[int, Field(ge=1)] = 25
    format: Literal["mp4-h264", "mov-prores", "webm-vp9"] = "mp4-h264"
    ffmpeg_extra: str = ""


class OutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output_dir: Path
    frame_filename_template: str = "frame_{index:04d}{ext}"
    metadata_strategy: Literal["exif", "csv", "auto"] = "auto"
    video: VideoConfig = Field(default_factory=VideoConfig)

    @field_validator("frame_filename_template")
    @classmethod
    def _check_index(cls, value: str) -> str:
        if not _FRAME_INDEX_RE.search(value):
            raise ValueError(
                "output.frame_filename_template: must include zero-padded "
                "{index:0Nd} placeholder (FR-043)"
            )
        return value

    @model_validator(mode="after")
    def _check_video(self) -> OutputConfig:
        if self.video.assemble and self.video.fps < 1:
            raise ValueError("output.video.fps required when assemble=true (FR-022)")
        return self


# --- Sequence ---------------------------------------------------------------


class TimelapseSequenceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["timelapse"] = "timelapse"
    total_frames: Annotated[int, Field(ge=2)]
    interval_s: Annotated[float, Field(gt=0)]
    settle_time_s: Annotated[float, Field(ge=0)]
    start: Angles
    target: Angles

    @model_validator(mode="after")
    def _check_settle(self) -> TimelapseSequenceConfig:
        if self.settle_time_s > self.interval_s:
            raise ValueError("sequence.settle_time_s: must be ≤ interval_s (FR-017)")
        return self


class VideoPanSequenceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["video_pan"] = "video_pan"
    duration_s: Annotated[float, Field(gt=0)]
    start: Angles
    target: Angles


SequenceConfig = Annotated[
    TimelapseSequenceConfig | VideoPanSequenceConfig,
    Field(discriminator="kind"),
]


# --- Configuration root ----------------------------------------------------


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
    camera: CameraConfig = Field(default_factory=CameraConfig)
    tripod: TripodConfig
    safety: SafetyConfig
    output: OutputConfig
    sequence: SequenceConfig

    @model_validator(mode="after")
    def _check_tilt_window(self) -> Configuration:
        lo = self.safety.tilt_min_deg
        hi = self.safety.tilt_max_deg
        for label, ang in (("start", self.sequence.start), ("target", self.sequence.target)):
            if not (lo <= ang.tilt_deg <= hi):
                raise ValueError(
                    f"sequence.{label}.tilt_deg ({ang.tilt_deg}) outside "
                    f"safety window [{lo}, {hi}] (FR-009)"
                )
        if isinstance(self.sequence, TimelapseSequenceConfig):
            n = self.sequence.total_frames
            t0 = self.sequence.start.tilt_deg
            t1 = self.sequence.target.tilt_deg
            for i in range(n):
                # Linear interpolation across N frames; the first and last sit on the keyframes.
                t = t0 if n == 1 else t0 + (t1 - t0) * (i / (n - 1))
                if not (lo <= t <= hi):
                    raise ValueError(
                        f"sequence: interpolated tilt at frame {i} ({t:.4f}) outside "
                        f"safety window [{lo}, {hi}] (FR-009)"
                    )
        return self


# --- YAML loader / dumper --------------------------------------------------


def load_host_configuration(source: str | Path) -> HostConfig:
    """Parse a YAML file or YAML string and return a validated ``HostConfig``.

    Wraps Pydantic ``ValidationError`` in :class:`ConfigError` so callers across
    the host can catch a single domain exception.
    """

    if isinstance(source, Path) or (isinstance(source, str) and "\n" not in source and Path(source).exists()):
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

    if isinstance(source, Path) or (isinstance(source, str) and "\n" not in source and Path(source).exists()):
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
    """Serialise a ``Configuration`` back to YAML.

    Used by the session library to persist the exact document that ran the shoot
    (FR-024 / SC-007).
    """

    payload: dict[str, Any] = config.model_dump(mode="json", exclude_none=False)
    return yaml.safe_dump(payload, sort_keys=False, default_flow_style=False)


__all__ = [
    "Angles",
    "CameraConfig",
    "Configuration",
    "ConfigurationMetadata",
    "HostConfig",
    "OutputConfig",
    "SafetyConfig",
    "SequenceConfig",
    "SerialConfig",
    "TimelapseSequenceConfig",
    "TripodConfig",
    "VideoConfig",
    "VideoPanSequenceConfig",
    "dump_configuration",
    "load_configuration",
    "load_host_configuration",
]
