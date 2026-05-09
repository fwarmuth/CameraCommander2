# Implementation Plan: CameraCommander2 — Core System

**Branch**: `001-core-system` | **Date**: 2026-05-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-core-system/spec.md`

## Summary

Full rewrite of CameraCommander as three independently versioned components: an ESP-class firmware exposing a versioned serial protocol, a headless Python host application that orchestrates timelapse and video-pan sequences and exposes a REST + WebSocket API, and a decoupled browser-based UI that consumes the host API. The host application supports both real and mock hardware end-to-end so all workflows are testable without a physical camera or tripod. Configuration is YAML-only and equally usable from the CLI and the UI. The minimum-feature surface mirrors the spec's 51 functional requirements, with the architecture optimised for Linux hosts (Raspberry Pi class) and Python 3.12+.

## Technical Context

**Language/Version**: Python 3.12 (host, mock firmware, CLI); C++17 / Arduino framework on PlatformIO (firmware); TypeScript 5.x (web UI)
**Primary Dependencies**:
- Host: FastAPI, uvicorn[standard], pydantic v2, typer, pyyaml, pyserial, gphoto2 (libgphoto2 binding), pillow, piexif, loguru, ffmpeg (subprocess)
- Firmware: AccelStepper (waspinator/AccelStepper@^1.64), Arduino core for ESP8266 (default) and ESP32 (alternate target)
- Web UI: Svelte 5 + Vite + TypeScript, Tailwind CSS, native `fetch`/`WebSocket` (no global state library beyond Svelte stores)
**Storage**: Local filesystem only — captured frames in operator-configured `output_dir`; session library at `~/.cameracommander/sessions/<session-id>/` with `metadata.json`, `config.yaml`, `frames/`, optional `video.mp4`. No database.
**Testing**: pytest + pytest-asyncio + httpx for host (unit/contract/integration); PlatformIO `pio test` for firmware native tests; vitest + @testing-library/svelte for web UI; end-to-end smoke tests using mock firmware TCP server + mock camera adapter.
**Target Platform**: Linux on x86_64 development hosts and **Raspberry Pi Zero 2 W (ARM Cortex-A53 quad-core @ 1 GHz, 512 MB RAM, no GPU, single SD-card I/O channel)** as the deployment target. Raspberry Pi OS Lite (no desktop). ESP8266 (NodeMCU v3) is the primary firmware target; ESP32 is a permitted secondary target sharing the same protocol.
**Project Type**: Multi-component repository — firmware (C++), headless host (Python service + CLI), browser SPA (TypeScript). Three top-level packages, one shared protocol contract.
**Performance Goals**:
- Hardware fault detection ≤ 5 s (SC-004) — implemented via `move_blocking` timeout margin and per-call gphoto2 reconnect budget.
- Video-pan motion/recording start within 500 ms of each other (User Story 3 acceptance) — coordinator pre-arms camera REC mode, then issues `M` and toggles record in the same monotonic instant.
- Live-view preview stream ≥ 5 fps over local network for focus assist.
- Live job-progress WebSocket fan-out latency < 200 ms.
**Constraints**:
- Must run comfortably on a **Pi Zero 2 W (512 MB RAM, no GPU)**. Resident-set budget for the host process: ≤ 200 MB steady-state, ≤ 280 MB while a job runs (gphoto2 + image buffers). Single-process, single async event loop, one hardware worker thread — no multi-worker uvicorn, no Gunicorn, no preload pools.
- The **Web UI is a static SPA**; the Pi only serves the prebuilt `web/dist/` directory (FastAPI `StaticFiles`) — no Node.js, no SSR, no Vite dev server on the device. Build is performed off-device (laptop or CI).
- Avoid heavy Python deps: no pandas, numpy beyond what `pillow`/gphoto2 indirectly need, no scikit-*, no torch. Pure-Python where possible; lean on stdlib `asyncio`, `pathlib`, `shutil`, `csv`.
- Single concurrent job (FR-039); the host MUST reject overlapping launches.
- Linux-only host; no Windows/macOS support (Constitution V).
- Tilt range is operator-configured per session config; pan is mechanically unlimited (Spec Assumption).
- Only protocols the firmware exposes today (single-line ASCII over 9600 baud serial) — extensions must be backwards-compatible with `VERSION x.y.z` discovery.
- ffmpeg invocations on the Pi default to `-c:v libx264 -preset veryfast -crf 23` (Pi Zero 2 W has no hardware h264 encoder) and run **after** capture to avoid memory pressure during frame acquisition. `ffmpeg_extra` is reserved for the operator to override.
**Scale/Scope**:
- Single operator, single host, single tripod, single camera.
- Session library bounded by disk space (typical session 50–2 000 frames; 50 MB–60 GB).
- Configuration documents ≤ 32 KB YAML.
- Live-view target on Pi Zero 2 W: 5 fps MJPEG at gphoto2 preview resolution (typically 960×640). The pipeline is a direct passthrough — gphoto2 buffer → HTTP chunk — with no decode/encode on the Pi.
- Frame capture pipeline never holds more than one full-res image in Python memory (write directly to disk; do not retain the PIL handle).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. System Boundary Contracts** | PASS | Three contracts under `contracts/`: `firmware-protocol.md` (versioned serial commands, `V`/`VERSION x.y.z` discovery), `host-api.openapi.yaml` (REST), `host-events.asyncapi.yaml` (WebSocket job stream). Web UI imports only the generated API client; host imports only the firmware-protocol client. |
| **II. Hardware Abstraction (Mock-First)** | PASS | `host/src/cameracommander/hardware/camera/mock.py` and `host/src/cameracommander/hardware/tripod/mock_serial.py` (transparent `socket://` connection to the mock firmware TCP server). Mock firmware server (`host/src/cameracommander/mock_firmware/`) implements the same line protocol. CI runs full timelapse + video-pan against mocks. |
| **III. Configuration-Driven** | PASS | One YAML schema per session (Pydantic-validated). CLI `cameracommander timelapse <config.yaml>` and `cameracommander pan <config.yaml>` produce the same execution as the UI. UI generates and exports the same YAML. |
| **IV. Spec-Driven Development** | PASS | This plan derives strictly from `spec.md` (51 FR, 8 SC, 5 user stories). No feature outside the spec is included. |
| **V. Simplicity / No Premature Abstraction** | PASS | Three components correspond to the three constitutional components — no extra packages. Host is one Python package. No plugin layer, no message broker, no DB. Single-process async host with one hardware worker thread. |
| **VI. Observability** | PASS | Structured logs via loguru with `session_id`/`job_id` context; `/api/health`, `/api/hardware/status`, `/api/jobs/{id}` and the `/ws/events` channel surface job progress, hardware connection state, calibration state, and current position. Web UI Monitor view subscribes to `/ws/events`. |
| **VII. Motion Safety and Calibration** | PASS | `host/src/cameracommander/services/safety.py` enforces tilt limits at three layers: config validation (rejects bad configs before any motion — FR-009/SC-005), runtime guard around every `move_to` call, and UI-side disable of out-of-bounds nudge buttons. Calibration state is required for automated jobs (FR-010, FR-041); homing is software-only via "Set current as home" action (FR-040). Driver disable resets known position (FR-011). |

All gates pass. No `Complexity Tracking` entries needed.

### Post-Design Re-check (after Phase 1 artefacts)

Re-walked the seven principles against `research.md`, `data-model.md`, `quickstart.md`, and the four contracts under `contracts/`:

- **I — Boundary contracts**: every cross-component path is documented in `contracts/firmware-protocol.md`, `contracts/host-api.openapi.yaml`, `contracts/host-events.asyncapi.yaml`, `contracts/cli-commands.md`, and `contracts/config-schema.md`. PASS.
- **II — Mock-first**: `host-api.openapi.yaml` exposes the same endpoints whether the host runs against real hardware or `--mock`; `firmware-protocol.md` §7 binds the mock TCP server to byte-for-byte parity with the ESP firmware. PASS.
- **III — Configuration-driven**: `config-schema.md` is the single source of truth for the YAML form; the OpenAPI `Configuration` schema is generated from the same Pydantic models. CLI `validate`/`timelapse`/`pan` and the REST `/api/jobs/*` endpoints accept the same shape. PASS.
- **IV — Spec-driven**: every section of every artefact carries FR / SC references back to `spec.md`. No scope outside the spec. PASS.
- **V — Simplicity / no premature abstraction**: still three components, one Python package per component, no DB, no plugin layer, no message bus. The Pi Zero 2 W deployment-target tightening reinforces this — no extra layers were introduced to satisfy the resource budget. PASS.
- **VI — Observability**: `host-events.asyncapi.yaml` defines the live telemetry channel (hardware status, calibration changes, job progress / faults, position broadcasts, session lifecycle). Loguru sinks documented in `quickstart.md` §4.3. PASS.
- **VII — Motion safety / calibration**: `data-model.md` §6 lists the three-layer enforcement; `host-api.openapi.yaml` returns HTTP 412 for `calibration_required` and HTTP 422 for `tilt_limit`; the firmware contract preserves the `d`/`e` driver-toggle semantics that flip calibration to `unknown`. PASS.

No regressions. No new `Complexity Tracking` entries. Phase 2 (`/speckit-tasks`) may proceed.

## Project Structure

### Documentation (this feature)

```text
specs/001-core-system/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── firmware-protocol.md
│   ├── host-api.openapi.yaml
│   ├── host-events.asyncapi.yaml
│   ├── cli-commands.md
│   └── config-schema.md
├── spec.md              # Source feature specification
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
firmware/                                      # ESP-class firmware (C++ / PlatformIO)
├── platformio.ini                             # ESP8266 default + ESP32 env
├── src/
│   ├── main.cpp                               # Command parser, version banner, motion loop
│   ├── GearedStepper.cpp / .h                 # AccelStepper wrapper (kept from old impl)
│   ├── protocol.h                             # Single source of truth for FW_VERSION, command tokens
│   └── safety.cpp                             # Hard tilt clamp (firmware-level guard)
├── test/                                      # pio native tests (parser, protocol)
└── README.md

host/                                          # Headless Python host application
├── pyproject.toml                             # Python 3.12+; entry point: cameracommander
├── src/cameracommander/
│   ├── __init__.py
│   ├── core/
│   │   ├── models.py                          # Pydantic: Session, Job, JobStatus, CalibrationState, HardwareStatus
│   │   ├── config.py                          # YAML loader + schema (CameraConfig, TripodConfig, MotionConfig, SequenceConfig)
│   │   └── errors.py                          # Domain exception hierarchy
│   ├── hardware/
│   │   ├── camera/
│   │   │   ├── base.py                        # CameraAdapter protocol
│   │   │   ├── gphoto.py                      # libgphoto2-backed adapter
│   │   │   └── mock.py                        # Image-from-disk + synthetic preview adapter
│   │   └── tripod/
│   │       ├── base.py                        # TripodAdapter protocol
│   │       ├── serial_adapter.py              # pyserial; supports `socket://` URL for mock
│   │       └── protocol.py                    # Command formatting + response parsing
│   ├── services/
│   │   ├── safety.py                          # Tilt limit enforcement, calibration gating
│   │   ├── timelapse.py                       # Capture → settle → move loop (FR-015..018)
│   │   ├── video_pan.py                       # Smooth motion + REC sync (FR-019..020)
│   │   ├── calibration.py                     # set-current-as-home, state tracking
│   │   ├── jobs.py                            # Single-job runner; rejects overlapping jobs (FR-039)
│   │   ├── sessions.py                        # Filesystem-backed library
│   │   ├── post_process.py                    # ffmpeg assembly (FR-022, FR-025)
│   │   └── disk.py                            # Pre-flight + per-frame disk-space guard (FR-036)
│   ├── api/
│   │   ├── app.py                             # FastAPI factory
│   │   ├── routes/                            # camera.py, tripod.py, jobs.py, sessions.py, health.py
│   │   ├── websocket.py                       # /ws/events fan-out
│   │   └── deps.py                            # AppContainer (DI)
│   ├── cli/
│   │   ├── main.py                            # Typer app
│   │   └── commands/                          # snapshot, tripod, timelapse, pan, validate, mock_firmware, serve
│   ├── persistence/
│   │   └── sessions_fs.py                     # ~/.cameracommander/sessions store
│   └── mock_firmware/
│       ├── server.py                          # TCP server (continues old design)
│       └── motion_model.py                    # Time-modeled mock motion
├── tests/
│   ├── contract/                              # Validates host-api.openapi.yaml + firmware-protocol parser
│   ├── integration/                           # Full timelapse + video-pan against mocks
│   └── unit/                                  # Pure logic (config, safety, motion math)
└── README.md

web/                                           # Decoupled browser SPA (TypeScript + Svelte)
├── package.json
├── vite.config.ts
├── tsconfig.json
├── src/
│   ├── main.ts
│   ├── App.svelte                             # Top-level shell + routing
│   ├── lib/api/                               # OpenAPI-generated typed client (regenerated from contracts)
│   ├── lib/ws/                                # WebSocket subscription helper
│   ├── lib/stores/                            # Svelte stores for hardware status, current job, sessions
│   ├── views/
│   │   ├── LiveControl.svelte                 # Camera settings, test capture, live-view, nudge (FR-030)
│   │   ├── Planner.svelte                     # Configure + launch timelapse / video pan (FR-031)
│   │   ├── Monitor.svelte                     # Real-time job + hardware status (FR-032)
│   │   └── Library.svelte                     # Browse + reload + post-process sessions (FR-033)
│   └── components/
└── tests/                                     # vitest + @testing-library/svelte

hardware/                                      # Mechanical CAD (kept from prior repo)
└── *.FCStd, *.png

specs/                                         # Spec-Kit specifications (this directory tree)
.specify/                                      # Spec-Kit tooling (templates, scripts, hooks)
```

**Structure Decision**: Multi-component layout with one top-level directory per constitutional component (`firmware/`, `host/`, `web/`) plus the existing `hardware/` (CAD) and `specs/` (Spec-Kit). The host package is single — no premature `core/`-vs-`api/` split into separate distributions; layered modules under one `cameracommander` package give the same separation without the packaging overhead. The web app is fully decoupled: the only artefact it shares with the host is the generated TypeScript API client produced from `specs/001-core-system/contracts/host-api.openapi.yaml`.

## Complexity Tracking

> No Constitution Check violations to justify.
