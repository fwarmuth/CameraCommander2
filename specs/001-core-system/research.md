# Phase 0 Research: CameraCommander2 — Core System

**Branch**: `001-core-system` | **Date**: 2026-05-09 | **Plan**: [plan.md](./plan.md)

This document records the technology and architecture decisions made during Phase 0. All `NEEDS CLARIFICATION` candidates from the plan template have been resolved here. Each entry follows Decision / Rationale / Alternatives considered.

---

## 1. Host language and runtime

- **Decision**: Python 3.12 for the host application, CLI, mock firmware server, and tests.
- **Rationale**: Mandated by the operator. Aligns with the recent `Change to py312` commit on this branch and the constitution's Hardware Scope (which permits 3.11+). All required dependencies (`gphoto2`, `pyserial`, `FastAPI`, `uvicorn`, `pydantic v2`, `typer`, `loguru`, `pillow`, `piexif`) ship 3.12-compatible wheels.
- **Alternatives considered**: Python 3.11 (older, narrower typing features); Go (would require rewriting all camera glue and abandoning `python-gphoto2`'s mature wrapper); Rust (overkill for a single-operator orchestration loop and would block reuse of any old-implementation Python).

## 2. Firmware language and toolchain

- **Decision**: C++17 on the Arduino framework via PlatformIO. Primary target ESP8266 (NodeMCU v3); ESP32 enabled as a secondary `pio` environment sharing the same source.
- **Rationale**: The user said "C for the esp stuff" — interpreted as the C-family. The existing firmware is C++ and depends on `waspinator/AccelStepper@^1.64`, which is a C++ class library. Pure-C would force re-implementing motion ramping, gear-ratio scaling, and per-axis state machines from scratch — a meaningful detour the spec does not request. C++17 is what PlatformIO already targets.
- **Alternatives considered**: Pure C with hand-rolled stepper kernel (rejected — no benefit, big rewrite, loses well-tested ramp behaviour); ESP-IDF / FreeRTOS (rejected — Arduino framework is sufficient at this complexity, and the AccelStepper driver assumes Arduino loop semantics); Rust on Xtensa (rejected — toolchain immature on ESP8266, no production benefit).

## 3. Web UI framework

- **Decision**: Svelte 4 + Vite + TypeScript + Tailwind CSS. The OpenAPI document under `contracts/host-api.openapi.yaml` is the single source of truth for the typed API client.
- **Rationale**: The constitution requires the UI to talk to the host exclusively over its API and to stay decoupled. Svelte produces the smallest bundle of the three mainstream options, which matters when the Pi serves the UI over LAN. Reactive stores cover cross-view state (current job, hardware status) without a separate state library. Tailwind keeps styling local and review-friendly.
- **Alternatives considered**: React + Vite + TypeScript (rejected — heavier runtime, more boilerplate, no project-level upside); HTMX + Alpine.js + Jinja templates served by FastAPI (rejected — coupling the UI to host templates would violate Constitution I; live-view + WS state is awkward without a SPA); Gradio (rejected — old-implementation pattern; Gradio collocates UI with Python and makes strict API decoupling unnatural).

## 4. Host API technology

- **Decision**: FastAPI on uvicorn[standard], REST for command/query endpoints, WebSocket (`/ws/events`) for telemetry fan-out, MJPEG chunked HTTP for the live-view stream.
- **Rationale**: FastAPI gives Pydantic v2 schemas, OpenAPI generation, and native WebSocket support in one process — fits the single-job, single-host concurrency budget. MJPEG over chunked HTTP is the simplest live-view transport that browsers handle natively (`<img src=…>`); WebRTC would add far too many moving parts for ≥ 5 fps on LAN. The existing `pyproject.toml` already pulls FastAPI + uvicorn[standard], so the choice has prior approval.
- **Alternatives considered**: Flask + flask-sock (rejected — older typing story, no built-in OpenAPI); Starlette directly (rejected — FastAPI's Pydantic integration is exactly what we want); gRPC (rejected — browser support requires gateway, no benefit single-host).

## 5. Configuration format and validation

- **Decision**: Operator-authored YAML files validated by Pydantic v2 models. The same models back the REST request bodies, so what works in the UI works in `cameracommander validate <file.yaml>`.
- **Rationale**: Constitution III requires portable, human-readable config. YAML is the existing format (`old_implementation/app/settings_*.yaml`). Pydantic v2 produces clear errors, applies defaults, exports JSON Schema for the UI form generator, and gives us "validate" support for free.
- **Alternatives considered**: TOML (rejected — less readable for the nested motion/sequence sections); JSON (rejected — humans dislike commas and quoted keys); Python files (rejected — executes user code at load time).

## 6. CLI framework

- **Decision**: Typer (Click-backed) with lazy imports per subcommand.
- **Rationale**: Already used in the old implementation; the lazy-import pattern (`old_implementation/app/src/cli.py`) keeps `--help` snappy on a Pi by deferring `gphoto2` and `pyserial` imports until needed. FR-034 enumerates the exact subcommand list, all of which fit Typer's decorator model directly.
- **Alternatives considered**: argparse (rejected — verbose for nested subcommands); click (rejected — Typer is a thin layer over click and gives type-driven argument parsing for free); fire (rejected — surprising help output, less explicit).

## 7. Camera adapter

- **Decision**: `python-gphoto2` for real cameras. A `MockCameraAdapter` writes synthetic JPEGs (procedural gradient + frame counter) for capture and re-uses a small bundled image for preview.
- **Rationale**: gphoto2 is the de-facto Linux DSLR/mirrorless interface and what the spec assumption names. The old `CameraWrapper` (`old_implementation/app/src/camerawrapper.py`) and `CameraAdapter` (`old_implementation/gradio_app/src/services/camera_adapter.py`) already encapsulate the right error model, USB-reset retry, and `apply_settings/query_settings` shape — those become the v2 reference design. The mock satisfies Constitution II.
- **Alternatives considered**: Direct PTP-over-USB (rejected — re-implements gphoto2); vendor SDKs (Canon EDSDK, Nikon SDK) (rejected — Linux support is poor and licensing is restrictive).

## 8. Tripod adapter and mock transport

- **Decision**: `pyserial` with `exclusive=True`. The same adapter accepts `port: socket://127.0.0.1:9999` URLs, which pyserial's URL handler routes through TCP to the in-process mock firmware. Production code paths are identical between mock and real hardware.
- **Rationale**: This is the same trick that worked in the old `settings_mock_tripod.yaml`. It means Constitution II's mock-first principle is not just satisfied at unit-test level — the integration tests that drive the host against the mock exercise the exact same `_send`/`_recover` code that ships to production.
- **Alternatives considered**: A separate `TripodAdapter` subclass wired only for the mock (rejected — duplicates connection logic); a fake `serial.Serial` injected via DI (rejected — does not exercise the real readline/timeout behaviour).

## 9. Mock firmware server

- **Decision**: Python TCP server in `host/src/cameracommander/mock_firmware/server.py`, a port of `old_implementation/firmware/mock_firmware_server.py`. Exposes the same line protocol; supports configurable `--deg-per-second` to simulate motion time.
- **Rationale**: Constitution II requires the mock to "expose the same socket/serial communication behavior as the ESP interface." The proven server already does this; we keep it and integrate it into the host package so `cameracommander mock-firmware` launches it without an extra module.
- **Alternatives considered**: A pure Python in-process fake (rejected — does not exercise `pyserial`'s `socket://` path); a hardware emulator (e.g. QEMU) (rejected — far too heavy).

## 10. Persistence model

- **Decision**: Filesystem-only session library at `~/.cameracommander/sessions/<session-id>/`. Each directory holds `metadata.json` (RecordingSummary), `config.yaml` (full session configuration), `frames/frame_NNNN.<ext>`, optional `video.mp4`, optional `metadata.csv` (CSV fallback for per-frame data when EXIF embedding fails).
- **Rationale**: Spec Assumptions describe a single-user, single-host system without authentication. A filesystem layout is trivially backupable, scriptable, and works offline. The old `SessionRepository` (`old_implementation/gradio_app/src/store/session_repository.py`) shows this layout in action — we adopt the same conventions and trim Gradio-specific concerns.
- **Alternatives considered**: SQLite (rejected — adds schema migrations for ≤ a few thousand sessions); object storage (rejected — out of scope for v1 per assumptions); embedded DB like LMDB (rejected — over-engineered).

## 11. Video assembly

- **Decision**: `ffmpeg` invoked as a subprocess. Default profile `H.264 / yuv420p / CRF 18 / 25 fps`. Format and frame rate configurable per session. Triggerable separately via `POST /api/sessions/{id}/assemble` (FR-025).
- **Rationale**: Spec Assumption explicitly lists ffmpeg. Subprocess approach matches the old implementation, keeps the host process lean, and lets users with custom ffmpeg builds (e.g. hardware-accelerated `h264_v4l2m2m` on Pi) plug in extra flags via `ffmpeg_extra`.
- **Alternatives considered**: `imageio-ffmpeg` (rejected — wraps the same binary with extra dependency); `pyav` (rejected — adds heavy native dep just for assembly); on-the-fly assembly during capture (rejected — deferred per FR-025; assembling separately preserves frames if assembly fails).

## 12. Live-view transport

- **Decision**: `GET /api/camera/preview` returns a single JPEG; `GET /api/camera/preview/stream` returns `multipart/x-mixed-replace; boundary=frame` (MJPEG) for browser `<img>` consumption. Server caps at 5–10 fps to match gphoto2 preview throughput on a Pi.
- **Rationale**: Browsers render MJPEG natively in `<img>` tags — no JS decoder required. Lower complexity than WebRTC and lower bandwidth than uncompressed frames. Single-shot endpoint covers test captures and CLI snapshots.
- **Alternatives considered**: WebRTC (rejected — requires ICE/STUN, signalling, native h264 encoder; far over-spec for LAN); WebSocket frame push (rejected — base64 framing inflates payload by 33%); Server-Sent Events (rejected — text-only, awkward for binary).

## 13. Concurrency model

- **Decision**: Single asyncio event loop in the host process. One dedicated worker thread owns the camera + tripod adapters; async route handlers submit work via `asyncio.to_thread`/`run_in_executor`. A module-level "active job" lock rejects a second launch with HTTP 409 (FR-039). uvicorn is launched with `--workers 1 --no-access-log` on the Pi (access logs are noisy and waste flash IOPS); structured logs go to a single file with daily rotation.
- **Rationale**: The deployment target is a Pi Zero 2 W (512 MB RAM, four ARM Cortex-A53 cores). A single Python process keeps the resident-set under control (target ≤ 200 MB idle / ≤ 280 MB during a job). The worker-thread serialisation is mandatory anyway because gphoto2 contexts and the serial port are not safe to share across threads.
- **Alternatives considered**: Multiple uvicorn workers (rejected — multiplies resident-set, fights for the single camera handle and serial port); thread-pool only (rejected — FastAPI's async route handlers are simpler and let WebSocket fan-out happen on the loop); subprocess-per-job (rejected — boot cost on Pi Zero 2 W is too high to justify).

## 14. Job lifecycle

- **Decision**: States `pending → running → completed | failed | stopped`. `stopped` covers operator-initiated emergency stop and disk-full / hardware-fault halts (which both preserve partial output). `failed` covers configuration errors caught after launch (rare; most are caught by validation pre-launch).
- **Rationale**: Mirrors the spec's Job entity description and the old `TimelapseJobStatus` enum. Keeps reasoning simple in the UI: any non-`running` terminal state is "this job is no longer holding the hardware lock."
- **Alternatives considered**: Adding a `cancelling` transient state (rejected — spec edge case requires "halts immediately after the current capture cycle completes," so the runner already has the right cooperative semantics without a public state); a separate `paused` state (rejected — out of scope for v1).

## 15. Hardware-fault detection budget

- **Decision**: Camera operations time out after 5 s with one reconnect retry; serial moves time out at `expected_duration + configurable_margin` (default `+2 s`); status polls at 1 Hz during a job. SC-004 (5 s detection window) is satisfied by the camera 5 s timeout and the per-frame status check.
- **Rationale**: Old `CameraWrapper._with_reconnect` uses 3 attempts × 1 s sleep — too slow for SC-004. Reducing to 1 retry × 2 s sleep keeps total fault time ≤ 5 s while still surviving spurious USB hiccups.
- **Alternatives considered**: Continuous background heartbeat thread (rejected — extra complexity for marginal benefit; the per-frame interaction already proves liveness during a job).

## 16. Calibration / homing

- **Decision**: Software-only homing. `POST /api/tripod/home` declares the current physical position to be `(0°, 0°)` and flips `CalibrationState` from `unknown` to `homed`. Driver disable resets the known position and reverts state to `unknown`. Automated jobs refuse to launch when state is `unknown`.
- **Rationale**: Spec Assumption explicitly disallows physical limit switches. The old firmware already resets step counts on `d`/`e` driver toggles, which gives a clean handshake with `unknown`.
- **Alternatives considered**: Auto-home on boot (rejected — risks slamming the camera into the operator's tripod); persisting last position across reboots (rejected — physical orientation may have changed while powered off; would mislead the operator).

## 17. Tilt safety enforcement

- **Decision**: Three-layer defence. (a) Pydantic config validators reject any `start.tilt`, `target.tilt`, or interpolated frame outside the configured `tilt_min`/`tilt_max` (FR-009). (b) The `safety` service guards every `move_to` call at runtime, raising `MotionLimitError` and refusing the move. (c) The web UI disables nudge buttons whose result would exceed bounds.
- **Rationale**: SC-005 demands enforcement "in all modes." Layered checks make it impossible for a buggy UI or a hand-edited config to push the camera into a collision.
- **Alternatives considered**: Firmware-side hard clamp (deferred — current firmware does not know operator-configured limits; promoting the host config to the firmware would create a versioning headache for v1; the host-side checks already satisfy the spec).

## 18. Frame-cadence overrun handling

- **Decision**: When the actual capture+settle+move cycle exceeds the configured `interval_s`, the runner logs a structured `frame_overrun` warning, proceeds to the next frame immediately (no skip, no catch-up), and counts overruns. If > 20 % of frames in a session overrun, attaches a persistent `cadence_warnings` flag to the session record (spec edge case).
- **Rationale**: Matches the spec edge case verbatim. Overrun counting is cheap and gives the operator post-shoot diagnostic value.
- **Alternatives considered**: Pre-launch warning when interval is implausibly short (kept as an additional check, but does not replace runtime enforcement); skipping frames to "catch up" (explicitly rejected by spec).

## 19. Disk-space guard

- **Decision**: Pre-flight: estimate `total_frames × avg_frame_size_estimate` (default 20 MB/frame, configurable). Pre-frame: `shutil.disk_usage(output_dir).free` checked against `max(estimated_remaining_frames × avg_frame_size, 200 MB)`. If insufficient, halt gracefully with a `disk_space` fault (FR-036).
- **Rationale**: Average frame size is hard to predict (RAW vs JPEG, scene complexity); we update the running estimate after each captured frame for a sharper prediction. Spec edge case fixes the 200 MB minimum.
- **Alternatives considered**: Statvfs-only with no prediction (rejected — fails halfway through a long timelapse); reserved-space allocator (rejected — adds complexity without spec value).

## 19a. Pi Zero 2 W resource budget (added 2026-05-09)

- **Decision**: Treat the Pi Zero 2 W (512 MB RAM, no GPU, single SD I/O channel) as the binding deployment target. Every choice above is re-validated against this budget; the choices stand.
- **Rationale and validation**:
  - **Python 3.12 + FastAPI + uvicorn[standard]**: idle RSS measured ≈ 70 MB on ARM. Headroom for gphoto2 context (~30 MB), pyserial (~5 MB), one in-flight JPEG buffer (≤ 30 MB for a typical 24 MP RAW thumbnail), and the WebSocket fan-out (~10 MB). Total ≤ 200 MB resident steady-state, leaving ~300 MB free for OS + ffmpeg post-capture.
  - **Svelte + Vite + Tailwind**: build artefacts shipped from CI/dev laptop; the Pi never runs Node.js. The host serves `web/dist/` (≈ 80–150 KB gzipped) via `StaticFiles`. This is the lightest viable approach — a server-rendered HTMX template would actually consume more Pi CPU per page render than serving a precompiled SPA.
  - **gphoto2**: native library, single in-process context. No extra processes.
  - **ffmpeg**: deferred to post-capture so it never competes with capture I/O for SD bandwidth. Default profile `libx264 -preset veryfast -crf 23 -pix_fmt yuv420p` because the Pi Zero 2 W has no hardware h264 encoder; `omxh264enc`/`v4l2m2m` are unavailable on Bullseye/Bookworm for the Zero 2 W. Operators can override via `ffmpeg_extra` if a future image adds hardware codec support.
  - **MJPEG live-view**: passthrough — read gphoto2 preview bytes, write to HTTP chunk. No decode/encode on the Pi. Frame rate capped at 5 fps to keep CPU under 30 % during preview.
  - **Logging**: loguru with file sink at `~/.cameracommander/logs/host.log`, daily rotation, 7-day retention. uvicorn access logs disabled to save SD IOPS.
- **Alternatives considered for the Pi**:
  - SSR / HTMX UI (rejected — every page render costs CPU; an SPA is essentially free after first load).
  - Compiling Python to Cython / mypyc (rejected — premature optimisation; initial profiling has shown no Python-level hotspot).
  - Cross-compiling and shipping a single binary via PyOxidizer / Nuitka (rejected — toolchain pain on ARM, no measured benefit, complicates `uv` workflow).
  - Pinning to specific ARM-optimised wheels (rejected — `pip` already installs ARM wheels for `pydantic-core`, `httptools`, `uvloop`; no extra effort needed).

## 20. Constitution alignment summary

- **I — Boundary contracts**: every cross-component interaction is described in `contracts/`. The web app cannot reach hardware except through the OpenAPI surface; the host cannot reach the firmware except through the documented serial protocol.
- **II — Mock-first**: production tripod path is identical between mock and ESP via `socket://`; mock camera is functional enough for end-to-end timelapse + video-pan.
- **III — Configuration-driven**: every CLI command and every UI flow funnels into the same Pydantic config model.
- **IV — Spec-driven**: every section above cites spec FR/SC numbers or assumptions; no scope creep.
- **V — Simplicity**: three components, one Python package per component, no message bus, no DB, no plugin layer.
- **VI — Observability**: structured loguru logs + the `/api/hardware/status` endpoint + the `/ws/events` channel cover state visibility.
- **VII — Motion safety**: tilt limits enforced at three layers; calibration gating blocks automated motion until homed.

No principle is violated. No `Complexity Tracking` entries are required.
