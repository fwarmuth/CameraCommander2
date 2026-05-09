# Configuration Schema — CameraCommander2

**Branch**: `001-core-system` | **Date**: 2026-05-09
**Authoritative for**: YAML session configuration files

The config file fully describes one shoot. The same shape is consumed by the CLI, the REST API, and the web UI (via JSON). Validation is performed by the Pydantic v2 models in `host/src/cameracommander/core/config.py`; the JSON Schema is exported as the OpenAPI `Configuration` schema (`contracts/host-api.openapi.yaml`).

This file is the **single source of truth** for the YAML form. The annotated example below is the canonical reference; any Pydantic model that diverges is a bug.

---

## 1. Top-level shape

```yaml
metadata:           # required
  ...
camera:             # required (may be empty if model_substring is in operator's host.yaml)
  ...
tripod:             # required
  ...
safety:             # required
  ...
output:             # required
  ...
sequence:           # required; tagged union by `kind`
  ...
```

Any unknown top-level key is a validation error in `--strict` mode (the default). Unknown keys inside `camera.settings` are forwarded to gphoto2, where they are validated by the camera adapter at apply time.

---

## 2. Annotated example — Timelapse

```yaml
# CameraCommander2 — example timelapse configuration
# Validated by `cameracommander validate <this-file>`.

metadata:
  name: "Aurora over Kiruna"           # required, ≤ 120 chars; appears in Library
  description: |
    20-minute mock-target timelapse used for Pi-Zero performance testing.
  tags: ["aurora", "test"]              # optional, ≤ 16 entries × ≤ 40 chars
  # created_at is set by the host on first parse.

camera:
  model_substring: "EOS"                # optional; selects camera by model substring
  image_format: camera-default          # camera-default | jpeg-only | raw-only | raw+jpeg
  settings:
    main.imgsettings.iso: 800
    main.capturesettings.shutterspeed: "1/125"
    main.capturesettings.aperture: 5.6
    main.imgsettings.whitebalance: Auto

tripod:
  serial:
    port: "/dev/ttyUSB0"                # or "socket://127.0.0.1:9999" for the mock
    baudrate: 9600
    timeout: 1.0
    write_timeout: 1.0
    reconnect_interval: 2.0
    max_retries: 5
  microstep: 16                         # one of 1, 2, 4, 8, 16
  expected_protocol_major: 1            # SC-008 firmware version gate

safety:
  tilt_min_deg: -45.0                   # required; pan has no configurable limit
  tilt_max_deg: 45.0                    # must be ≥ tilt_min_deg
  move_timeout_margin_s: 2.0            # added to expected duration before stall fault (FR-037)
  disk_min_free_bytes: 200_000_000      # 200 MB floor for disk guard (FR-036)
  disk_avg_frame_bytes: 20_000_000      # initial estimate; refined live during capture

output:
  output_dir: "./output/aurora"         # created if missing
  frame_filename_template: "frame_{index:04d}{ext}"   # MUST include {index:04d} (FR-043)
  metadata_strategy: auto               # auto | exif | csv (FR-018)
  video:
    assemble: true                      # FR-022 / FR-025
    fps: 25
    format: mp4-h264                    # mp4-h264 | mov-prores | webm-vp9
    ffmpeg_extra: "-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p"

sequence:
  kind: timelapse                       # discriminator
  total_frames: 240                     # ≥ 2 (FR-015)
  interval_s: 5.0                       # > 0; must be ≥ settle_time_s
  settle_time_s: 0.5
  start:
    pan_deg: 0.0
    tilt_deg: 0.0
  target:
    pan_deg: 60.0
    tilt_deg: 20.0                      # must lie in [tilt_min_deg, tilt_max_deg]
```

---

## 3. Annotated example — Video pan

Replace the `sequence` block with:

```yaml
sequence:
  kind: video_pan                       # discriminator
  duration_s: 30.0                      # > 0
  start:
    pan_deg: 0.0
    tilt_deg: 0.0
  target:
    pan_deg: 90.0
    tilt_deg: 5.0
```

`output.video.assemble`, `output.video.fps`, and `output.frame_filename_template` are ignored for video-pan jobs (the camera writes the video directly).

---

## 4. Validation rules summary

| Rule | Source | Message |
|---|---|---|
| `metadata.name` non-empty, ≤ 120 chars | Pydantic | `metadata.name: must be 1..120 chars` |
| `tripod.microstep ∈ {1,2,4,8,16}` | Pydantic | `tripod.microstep: must be one of 1,2,4,8,16` |
| `safety.tilt_max_deg ≥ safety.tilt_min_deg` | model_validator | `safety: tilt_max_deg must be ≥ tilt_min_deg` |
| `output.frame_filename_template` contains `{index:04d}` | string check | `output.frame_filename_template: must include {index:04d} (FR-043)` |
| `output.video.fps` required when `output.video.assemble` | model_validator | `output.video.fps required when assemble=true` |
| `sequence.kind` matches discriminator | Pydantic | `sequence.kind: invalid value` |
| `sequence.settle_time_s ≤ sequence.interval_s` (timelapse) | model_validator | `sequence.settle_time_s: must be ≤ interval_s (FR-017)` |
| All keyframe and interpolated tilts in `[tilt_min_deg, tilt_max_deg]` | safety service | `sequence: interpolated tilt at frame N is outside the safety window (FR-009)` |
| `tripod.expected_protocol_major == firmware reported major` | runtime | `tripod: protocol version mismatch (firmware reports M.m.p, host expects N.x.x) (SC-008)` |

`cameracommander validate <file>` reports all violations in one pass; it does not stop at the first error.

---

## 5. Reload from session

`GET /api/sessions/{id}/config` returns the **exact** YAML/JSON used to run that session, satisfying FR-024 ("retrieve the configuration from any past session for re-use") and SC-007 ("Configuration files from one host can be transferred to another host and produce an equivalent run without modification"). The host does not strip or transform the document; what was saved is what is replayed.

---

## 6. Host configuration (host.yaml)

Persistent settings for a specific deployment (e.g. Raspberry Pi). Usually lives at `~/.cameracommander/host.yaml`.

```yaml
# CameraCommander2 — example host configuration
camera:
  model_substring: "EOS"                # default camera selector
  # image_format: camera-default        # optional override
  # settings: { ... }                   # optional persistent camera settings

tripod:
  serial:
    port: "/dev/ttyUSB0"                # persistent hardware port
  # microstep: 16                       # optional override

session_library_root: "~/.cameracommander/sessions"
```

The `serve` command defaults to loading this file if it exists. Settings in a session configuration YAML override these host-level defaults for the duration of that session.
