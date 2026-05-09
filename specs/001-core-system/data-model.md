# Phase 1 Data Model: CameraCommander2 — Core System

**Branch**: `001-core-system` | **Date**: 2026-05-09 | **Plan**: [plan.md](./plan.md)

This document defines the entities the host application owns, their fields, validation rules, lifecycles, and on-disk persistence. Unless noted otherwise, every type is represented as a Pydantic v2 model in `host/src/cameracommander/core/models.py`. FR/SC references point to `spec.md`.

---

## 1. Configuration

The fully validated, portable description of a shoot. Authored as YAML, validated by the host before any hardware command runs (FR-026, FR-028, SC-007).

```text
Configuration
├── metadata: ConfigurationMetadata
├── camera: CameraConfig
├── tripod: TripodConfig
├── safety: SafetyConfig
├── output: OutputConfig
└── sequence: TimelapseSequenceConfig | VideoPanSequenceConfig    (discriminated union on `kind`)
```

### 1.1 ConfigurationMetadata

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | `str` (max 120) | yes | Operator-visible label. Stored on the Session record. |
| `description` | `str` (max 2 000) | no | Free-form notes. |
| `tags` | `list[str]` (each ≤ 40 chars, ≤ 16 items) | no | Drives Library filtering. |
| `created_at` | `datetime` (UTC, ISO 8601) | auto | Set on parse if absent. |

### 1.2 CameraConfig

Forwarded verbatim to the active `CameraAdapter.apply_settings`. Schema is open-ended because gphoto2 widget paths vary by model, but the adapter rejects unknown keys at apply-time.

| Field | Type | Required | Notes |
|---|---|---|---|
| `model_substring` | `str` | no | If set, the adapter selects a connected camera whose model contains this substring (FR-001). |
| `settings` | `dict[str, str \| int \| float \| bool]` | no | Direct gphoto2 paths, e.g. `main.imgsettings.iso: 800`. Validated by the camera adapter at apply time. |
| `image_format` | `Literal["camera-default", "jpeg-only", "raw-only", "raw+jpeg"]` | no | Default `"camera-default"`. The system never forces a format (FR-042); this hint configures the camera if the operator wants explicit control. |

### 1.3 TripodConfig

| Field | Type | Required | Notes |
|---|---|---|---|
| `serial.port` | `str` | yes | Path (`/dev/ttyUSB0`) or `socket://host:port` URL for the mock (FR-045, FR-046). |
| `serial.baudrate` | `int` (default 9600) | no | Must match firmware. |
| `serial.timeout` | `float` (default 1.0) | no | Read timeout. |
| `serial.write_timeout` | `float` (default 1.0) | no | |
| `serial.reconnect_interval` | `float` (default 2.0) | no | |
| `serial.max_retries` | `int` (default 5) | no | |
| `microstep` | `Literal[1,2,4,8,16]` (default 16) | no | Sent on connect. |
| `expected_protocol_major` | `int` (default 1) | no | Host refuses connection if firmware reports a different major (SC-008). |

### 1.4 SafetyConfig

| Field | Type | Required | Notes |
|---|---|---|---|
| `tilt_min_deg` | `float` | yes | Inclusive lower bound. |
| `tilt_max_deg` | `float` | yes | Inclusive upper bound. Must be ≥ `tilt_min_deg`. |
| `move_timeout_margin_s` | `float` (default 2.0, ≥ 0) | no | Added to expected duration before a move-stall fault fires (FR-037). |
| `disk_min_free_bytes` | `int` (default 200 000 000, ≥ 0) | no | Floor of the disk-space guard (FR-036, spec edge case). |
| `disk_avg_frame_bytes` | `int` (default 20 000 000, ≥ 0) | no | Initial estimate; refined live during capture. |

Pan has no configurable limit (Spec Assumption); attempting to set one is a validation error.

### 1.5 OutputConfig

| Field | Type | Required | Notes |
|---|---|---|---|
| `output_dir` | `path` | yes | Directory for per-shoot frames; created if missing. |
| `frame_filename_template` | `str` (default `frame_{index:04d}{ext}`) | no | Validated to contain a zero-padded `{index:04d}` placeholder (FR-043). |
| `metadata_strategy` | `Literal["exif", "csv", "auto"]` (default `"auto"`) | no | `"auto"` tries EXIF UserComment first, falls back to CSV (FR-018). |
| `video.assemble` | `bool` (default `true`) | no | Whether to assemble after capture (FR-022, FR-025). |
| `video.fps` | `int` (default 25, > 0) | no | Required when `assemble` is true. |
| `video.format` | `Literal["mp4-h264", "mov-prores", "webm-vp9"]` (default `"mp4-h264"`) | no | Maps to ffmpeg flag presets. |
| `video.ffmpeg_extra` | `str` | no | Operator escape hatch. |

### 1.6 TimelapseSequenceConfig (`kind: "timelapse"`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `kind` | `Literal["timelapse"]` | yes | Discriminator. |
| `total_frames` | `int` (≥ 2) | yes | FR-015. |
| `interval_s` | `float` (> 0) | yes | Period between captures. |
| `settle_time_s` | `float` (≥ 0) | yes | Pause after each move (FR-017). Must satisfy `settle_time_s ≤ interval_s`. |
| `start.pan_deg` | `float` | yes | Absolute, degrees. |
| `start.tilt_deg` | `float` | yes | Must lie in `[tilt_min_deg, tilt_max_deg]`. |
| `target.pan_deg` | `float` | yes | |
| `target.tilt_deg` | `float` | yes | Must lie in `[tilt_min_deg, tilt_max_deg]`. |

Validator: linearly interpolated frames (FR-016) MUST stay inside the tilt window. A fixed-position timelapse is supported by setting `start == target` (Spec Assumption).

### 1.7 VideoPanSequenceConfig (`kind: "video_pan"`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `kind` | `Literal["video_pan"]` | yes | Discriminator. |
| `duration_s` | `float` (> 0) | yes | Total motion duration. |
| `start.pan_deg` | `float` | yes | |
| `start.tilt_deg` | `float` | yes | Must lie in tilt window. |
| `target.pan_deg` | `float` | yes | |
| `target.tilt_deg` | `float` | yes | Must lie in tilt window. |

The motion path is straight-line in (pan, tilt) space; tilt-window enforcement at endpoints implies enforcement along the path.

---

## 2. Job

A running or scheduled execution. Lifecycle, ownership, and concurrency rules are described here; the configuration that drives the Job lives on the related Session record.

### 2.1 Fields

| Field | Type | Notes |
|---|---|---|
| `job_id` | `str` (UUIDv7) | Stable identifier; doubles as the Session ID once persisted. |
| `kind` | `Literal["timelapse", "video_pan"]` | Mirrors the sequence config. |
| `status` | `JobStatus` | See lifecycle below. |
| `created_at` | `datetime` | UTC. |
| `started_at` | `datetime \| null` | Set on first frame / motion start. |
| `finished_at` | `datetime \| null` | Set on terminal transition. |
| `progress.frames_completed` | `int` | Timelapse only. |
| `progress.frames_total` | `int` | Timelapse only. |
| `progress.motion_pct` | `float` (0..1) | Video pan only. |
| `progress.estimated_finish_at` | `datetime \| null` | Optional, derived. |
| `last_position` | `(pan_deg, tilt_deg)` | Updated on every move. |
| `fault` | `FaultEvent \| null` | Set when status enters `failed` or `stopped` due to fault. |
| `output.frames_dir` | `path` | Mirrors OutputConfig.output_dir. |
| `output.video_path` | `path \| null` | Set after assembly. |
| `cadence_warnings` | `int` | Count of frames where cycle time exceeded `interval_s` (Timelapse only). Drives session-level warning when > 20 % (spec edge case). |

### 2.2 Lifecycle

```
                    POST /api/jobs/*           validate
                          │                        │
                          ▼                        ▼
                       pending ────────────► failed (validation rejected)
                          │
                          ▼
                       running ────► stopped  (operator emergency stop, OR disk full, OR fault)
                          │
                          ▼
                      completed
```

Transitions:

- `pending → running` — Hardware locks acquired, calibration gate satisfied (FR-041), first capture/move issued. SC-008 firmware-version handshake happens before this transition.
- `running → completed` — Timelapse: all frames captured. Video pan: motion finished. Optional video assembly may follow but does not block status; assembly progress lives on the Session.
- `running → stopped` — Cooperative emergency stop (FR-008), disk-space fault (FR-036), interval overrun does NOT stop the job (FR-038).
- `running → failed` — Camera-side hard fault, motor stall (FR-037), serial loss (treated identically to stall per spec edge case). On `failed`, calibration is marked `unknown` and re-homing is required.

Concurrency: at most one Job in `running` at a time across the host (FR-039). A second launch returns HTTP 409 with `{"error": "job_already_running", "active_job_id": "..."}`.

### 2.3 FaultEvent

| Field | Type | Notes |
|---|---|---|
| `code` | `Literal["camera_disconnected", "camera_capture_failed", "motor_stall", "serial_lost", "disk_full", "tilt_limit", "calibration_required", "config_invalid", "user_stopped"]` | |
| `message` | `str` | Human-readable. |
| `frame_index` | `int \| null` | If during a Timelapse. |
| `last_position` | `(pan_deg, tilt_deg) \| null` | |
| `recoverable` | `bool` | True for `user_stopped` and `disk_full`; false for the calibration-resetting faults. |

---

## 3. Session

The persisted record of a Job. Created when a Job starts capturing (so `pending → running` produces one). Lives on disk under `~/.cameracommander/sessions/<session_id>/`.

### 3.1 Fields

| Field | Type | Notes |
|---|---|---|
| `session_id` | `str` (== `job_id`) | |
| `kind` | `Literal["timelapse", "video_pan"]` | |
| `created_at` | `datetime` | |
| `finished_at` | `datetime \| null` | |
| `status` | Mirrors final `JobStatus`. | |
| `configuration` | Embedded `Configuration` document | What ran. Used by FR-024 "reload settings". |
| `metrics.frames_captured` | `int` | |
| `metrics.frames_planned` | `int` | |
| `metrics.duration_s` | `float` | |
| `metrics.cadence_warnings` | `int` | Spec edge case >20% threshold flips `flags.cadence_warning = true`. |
| `flags` | `dict[str, bool]` | e.g. `{"cadence_warning": true, "partial_due_to_disk": true}`. |
| `assets` | `list[SessionAsset]` | |
| `fault` | `FaultEvent \| null` | If terminal status was non-completed. |

### 3.2 SessionAsset

| Field | Type | Notes |
|---|---|---|
| `path` | `str` | Repository-relative. |
| `kind` | `Literal["frame", "video", "metadata", "preview"]` | |
| `size_bytes` | `int \| null` | |
| `content_type` | `str \| null` | MIME-style. |
| `label` | `str \| null` | UI label. |

### 3.3 On-disk layout

```
~/.cameracommander/sessions/<session_id>/
├── metadata.json          # Session record (this entity, JSON-serialised)
├── config.yaml            # The original Configuration (FR-024 reload)
├── frames/                # frame_NNNN.jpg | .nef | .arw …
│   └── frame_0000.jpg
├── frames/metadata.csv    # CSV fallback when EXIF embed failed
└── video.mp4              # Optional rendered output
```

---

## 4. HardwareConnection

Runtime state surfaced via `GET /api/hardware/status` and `WS /ws/events` topic `hardware.status` (FR-006, FR-029, FR-032).

| Field | Type | Notes |
|---|---|---|
| `camera.state` | `Literal["connected", "disconnected", "error"]` | |
| `camera.model` | `str \| null` | |
| `camera.last_error` | `str \| null` | |
| `camera.battery_pct` | `int \| null` | If reported. |
| `tripod.state` | `Literal["connected", "disconnected", "error"]` | |
| `tripod.firmware_version` | `str \| null` | E.g. `"1.0.1"`. |
| `tripod.protocol_compatible` | `bool` | False blocks all motion (SC-008). |
| `tripod.drivers_enabled` | `bool` | FR-011. |
| `tripod.position_pan_deg` | `float \| null` | |
| `tripod.position_tilt_deg` | `float \| null` | |
| `tripod.last_error` | `str \| null` | |
| `tripod.tilt_limits` | `(min, max) \| null` | Mirrors active `SafetyConfig` if a job is staged. |
| `calibration.state` | `Literal["unknown", "homed"]` | FR-010, FR-040. |
| `calibration.set_at` | `datetime \| null` | |
| `active_job_id` | `str \| null` | Mirrors the locked job, if any. |
| `updated_at` | `datetime` | |

### 4.1 State transitions

```
camera/tripod:    disconnected ⇄ connected
                       │              │
                       └────► error ◄─┘   (blocks motion / capture; recovery via re-init)
calibration:      unknown ──(POST /api/tripod/home)──► homed
                  homed   ──(driver disable / fault) ──► unknown   (FR-011, fault)
```

---

## 5. CalibrationState

A field on `HardwareConnection.calibration` (no separate table); listed here because the constitution treats it as a first-class concern (Principle VII).

- `unknown` — automated jobs blocked (FR-041); manual nudge from the UI is allowed but logged with a warning.
- `homed` — automated jobs may run.

---

## 6. Validation rules cross-reference

| Rule | Where enforced | FR/SC |
|---|---|---|
| Tilt window covers all keyframes and interpolated frames | `Configuration` validator + `safety.guard_move()` runtime check | FR-009, SC-005 |
| `total_frames ≥ 2` (timelapse) | `TimelapseSequenceConfig` validator | FR-015 |
| `settle_time_s ≤ interval_s` | `TimelapseSequenceConfig` validator | FR-017 |
| `frame_filename_template` contains zero-padded `{index:04d}` | `OutputConfig` validator | FR-043 |
| `video.fps` required when `video.assemble` | `OutputConfig` validator | FR-022 |
| Calibration must be `homed` before `pending → running` | `services.jobs.JobManager.start()` | FR-010, FR-041 |
| Firmware protocol major must match `expected_protocol_major` | `TripodAdapter._handshake()` | SC-008 |
| Disk space sufficient pre-launch and pre-frame | `services.disk.guard_*()` | FR-036 |
| Move completes within `expected + margin` | `services.timelapse._await_move()` / `services.video_pan` | FR-037 |
| Capture cadence overruns are logged but never skip frames | `services.timelapse` | FR-038 |
| Second job rejected with HTTP 409 | `services.jobs.JobManager.start()` | FR-039 |

---

## 7. Identity and time

- IDs are UUIDv7 (sortable by creation time). The host generates them; clients never propose IDs.
- All persisted timestamps are UTC ISO 8601 (`2026-05-09T18:32:11.123456Z`). The UI converts to local time for display.
- All `*_deg` fields are signed floats with at most 6 decimals on the wire.
