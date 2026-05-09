---
description: "Task list for CameraCommander2 — Core System"
---

# Tasks: CameraCommander2 — Core System

**Input**: Design documents from `/specs/001-core-system/`
**Branch**: `001-core-system`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/{firmware-protocol.md, host-api.openapi.yaml, host-events.asyncapi.yaml, cli-commands.md, config-schema.md}, quickstart.md

**Tests**: Test tasks ARE included. The constitution (II — Mock-First) and the plan both require contract + integration tests against mocks; spec User Story 5 makes the mock end-to-end runs first-class. Tests are scoped to what's needed to verify each story independently — not exhaustive coverage of every helper.

**Organization**: Tasks are grouped by user story. Each user story phase is independently completable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: Maps the task to its user story (US1..US5). Setup, Foundational, and Polish phases carry no story label.
- File paths are absolute relative to the repo root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Repository scaffolding for the three components and basic toolchains. No business logic.

- [X] T001 Create top-level component directories `firmware/`, `host/`, `web/` and per-component `README.md` stubs at `firmware/README.md`, `host/README.md`, `web/README.md`
- [X] T002 [P] Create `host/pyproject.toml` declaring Python 3.12, the runtime deps from plan.md (fastapi, uvicorn[standard], pydantic v2, typer, pyyaml, pyserial, gphoto2, pillow, piexif, loguru), dev deps (pytest, pytest-asyncio, httpx, ruff, mypy), and the `cameracommander` console-script entry point
- [X] T003 [P] Create `firmware/platformio.ini` with `[env:nodemcuv2]` (ESP8266, default) and `[env:esp32]` environments, `lib_deps = waspinator/AccelStepper@^1.64`, framework=arduino, build flags for C++17
- [X] T004 [P] Create `web/package.json`, `web/vite.config.ts`, `web/tsconfig.json`, `web/svelte.config.js`, `web/tailwind.config.js`, `web/postcss.config.js` for Svelte 4 + Vite + TypeScript + Tailwind, with scripts `build`, `dev`, `test` (vitest)
- [X] T005 [P] Configure linting/formatting: `host/ruff.toml` and `host/mypy.ini` for Python; `web/.eslintrc.cjs`, `web/.prettierrc` for the SPA; root `.editorconfig`
- [X] T006 [P] Add `host/.gitignore` and `web/.gitignore` covering `.venv/`, `__pycache__/`, `node_modules/`, `dist/`, `*.egg-info`, `~/.cameracommander/` artefacts under repo

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Cross-cutting building blocks required by every user story. Mock infrastructure lives here because Constitution II makes mocks the default execution path.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Domain models & errors

- [X] T007 [P] Create domain exception hierarchy (`ConfigError`, `MotionLimitError`, `CalibrationRequiredError`, `MotorStallError`, `SerialLostError`, `CameraError`, `CaptureError`, `DiskFullError`, `JobAlreadyRunningError`, `ProtocolVersionMismatchError`, `MockOnlyError`) in `host/src/cameracommander/core/errors.py`
- [X] T008 [P] Implement Pydantic v2 models for `Configuration`, `ConfigurationMetadata`, `CameraConfig`, `TripodConfig` (with nested `serial`), `SafetyConfig`, `OutputConfig` (with nested `video`), and the discriminated `TimelapseSequenceConfig | VideoPanSequenceConfig` union per data-model.md §1 in `host/src/cameracommander/core/config.py`. Include validators: tilt-window covers all keyframes (FR-009), `settle_time_s ≤ interval_s` (FR-017), `frame_filename_template` contains `{index:04d}` (FR-043), `video.fps` required when `video.assemble` (FR-022), `total_frames ≥ 2` (FR-015)
- [X] T009 [P] Implement Pydantic models for `Job`, `JobStatus` enum, `JobProgress`, `FaultEvent`, `Session`, `SessionSummary`, `SessionAsset`, `HardwareConnection`, `CameraStatus`, `TripodStatus`, `CalibrationState` per data-model.md §2–§5 in `host/src/cameracommander/core/models.py`
- [X] T010 [P] Implement YAML loader/dumper that round-trips a `Configuration` (UTF-8, block style, `created_at` defaulted on parse) in `host/src/cameracommander/core/config.py` (extend the same module)

### Hardware abstraction protocols

- [X] T011 [P] Define `CameraAdapter` Protocol (connect, disconnect, query_settings, apply_settings, capture_still, start_recording, stop_recording, preview_frame_jpeg, preview_stream) in `host/src/cameracommander/hardware/camera/base.py`
- [X] T012 [P] Define `TripodAdapter` Protocol (connect, disconnect, version, status, move_to, nudge, home, set_drivers, stop, set_microstep) and `MoveResult`/`StatusReport` dataclasses in `host/src/cameracommander/hardware/tripod/base.py`
- [X] T013 [P] Implement firmware-protocol command formatter and reply parser (single-line ASCII per `contracts/firmware-protocol.md`: `V`, `M <pan> <tilt>`, `S`, `1/2/4/8/6`, `n/c/r/x`, `w/p/t/z`, `X`, `+`/`-`, `d`/`e`; `OK …`, `DONE`, `STATUS`, `VERSION`, `ERR …`) in `host/src/cameracommander/hardware/tripod/protocol.py`

### Application skeleton & cross-cutting infra

- [X] T014 Implement loguru sink configuration (file rotation daily, 7-day retention, `~/.cameracommander/logs/host.log`, JSON-serialisable extras carrying `session_id`/`job_id`) and global logger init in `host/src/cameracommander/core/logging.py`
- [X] T015 Implement `AppContainer` dependency-injection holder (camera adapter, tripod adapter, safety service, calibration service, jobs service, session repository, event bus) in `host/src/cameracommander/api/deps.py`
- [X] T016 Implement FastAPI factory `create_app()` (mounts routers, lifespan opens/closes adapters, serves `web/dist/` via `StaticFiles` when present, single uvicorn worker assumed) in `host/src/cameracommander/api/app.py`
- [X] T017 Implement WebSocket fan-out hub: in-memory subscription map, `subscribe`/`unsubscribe` control frames, broadcast helper `EventBus.publish(topic, payload)` per `contracts/host-events.asyncapi.yaml` in `host/src/cameracommander/api/websocket.py` and route registration in `host/src/cameracommander/api/routes/events.py`
- [X] T018 Implement Typer root app, global flags (`--log-level`, `--log-file`, `--no-banner`, `--version`), lazy subcommand registration per `contracts/cli-commands.md` in `host/src/cameracommander/cli/main.py`

### Mock infrastructure (Constitution II — required by US1–US4 testing)

- [X] T019 [P] Implement mock firmware TCP server (line-protocol parity with `contracts/firmware-protocol.md`, configurable initial pan/tilt/microstep/drivers, `--deg-per-second` motion-time simulation, `--fw-version` override, `--settle-delay`) in `host/src/cameracommander/mock_firmware/server.py` and supporting motion-time model in `host/src/cameracommander/mock_firmware/motion_model.py`
- [X] T020 [P] Implement `MockCameraAdapter` (procedural-gradient JPEG generator with frame-counter overlay for captures, bundled JPEG for preview, fake settings dict, simulated USB-disconnect toggle for fault tests) in `host/src/cameracommander/hardware/camera/mock.py`

### Foundational tests

- [X] T021 [P] Contract test: parse and re-emit every defined firmware reply / build every defined command line with the parser from T013, asserting byte-for-byte equality, in `host/tests/contract/test_firmware_protocol.py`
- [X] T022 [P] Contract test: load `specs/001-core-system/contracts/host-api.openapi.yaml` and assert FastAPI app from T016 exposes every `operationId` with matching method+path in `host/tests/contract/test_openapi_routes.py`
- [X] T023 [P] Unit test: configuration validators (tilt-window, settle/interval, filename template, fps requirement, frame minimum, microstep enum) in `host/tests/unit/test_config_validators.py`

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 — Configure and Execute a Timelapse (Priority: P1) 🎯 MVP

**Goal**: Operator configures a timelapse from YAML or the UI, launches it, watches it run, retrieves frames and assembled video. End-to-end with the mock camera + mock firmware.

**Independent Test**: With mocks running (`cameracommander mock-firmware` from T019 + a host using `MockCameraAdapter` from T020), `cameracommander timelapse specs/001-core-system/contracts/examples/timelapse_mock.yaml` produces N frames, writes per-frame metadata, assembles a video, and persists a session under `~/.cameracommander/sessions/<id>/`. The same flow is launchable from the Planner view in the UI and visible in the Monitor view.

### Tests for User Story 1 ⚠️

- [X] T024 [P] [US1] Integration test: full mock timelapse (mock firmware TCP + mock camera) via `services.jobs.JobManager.start()` produces correct frame count, ordered filenames, per-frame CSV metadata, and an MP4, in `host/tests/integration/test_full_timelapse_mock.py`
- [X] T025 [P] [US1] Contract test: `POST /api/jobs/timelapse` with a valid mock config returns 201 + Job; with calibration `unknown` returns 412; with another job running returns 409, in `host/tests/contract/test_jobs_timelapse_endpoint.py`
- [X] T026 [P] [US1] Unit test: `services.timelapse._linear_interpolate` produces tilt values inside the safety window across N frames in `host/tests/unit/test_timelapse_interpolation.py`
- [X] T027 [P] [US1] Unit test: disk-space guard halts with `disk_full` when free space drops below `max(remaining_frames * avg, disk_min_free_bytes)` in `host/tests/unit/test_disk_guard.py`

### Implementation for User Story 1

#### Real hardware adapters

- [X] T028 [P] [US1] Implement `GphotoCameraAdapter` (libgphoto2 binding, capture-no-AF, transfer-to-host, settings query/apply, 5s timeout + 1 reconnect retry per research §15) in `host/src/cameracommander/hardware/camera/gphoto.py`
- [X] T029 [P] [US1] Implement `SerialTripodAdapter` (pyserial; `socket://` URLs supported; banner drain; `V` handshake with major-version gate per SC-008; `_send` + timeout enforcement; reconnect with `reconnect_interval` and `max_retries`) in `host/src/cameracommander/hardware/tripod/serial_adapter.py`

#### Services

- [X] T030 [US1] Implement `SafetyService` (`guard_move(pan, tilt)` raises `MotionLimitError` outside tilt window; `validate_sequence(config)` for keyframes + interpolated frames; pure functions for unit testing) in `host/src/cameracommander/services/safety.py` (depends on T008, T030)
- [X] T031 [US1] Implement `CalibrationService` (`state` property, `mark_homed()` after `POST /api/tripod/home`, `mark_unknown(reason)` on driver disable / fault / boot, publishes `hardware.calibration` event via T017) in `host/src/cameracommander/services/calibration.py`
- [X] T032 [US1] Implement `DiskGuard` (pre-flight estimate, `assert_room_for_next_frame(frames_remaining, running_avg_bytes)`, threshold `max(estimate, disk_min_free_bytes)`) in `host/src/cameracommander/services/disk.py`
- [X] T033 [US1] Implement `SessionRepository` (filesystem under `~/.cameracommander/sessions/<id>/`, writes `metadata.json` + `config.yaml`, frame asset registration, list/get/delete) in `host/src/cameracommander/persistence/sessions_fs.py` and the thin service wrapper `host/src/cameracommander/services/sessions.py`
- [X] T034 [US1] Implement per-frame metadata writer: try EXIF UserComment via piexif; on failure append a row to `frames/metadata.csv` (timestamp, index, pan, tilt, settings hash); strategy `auto|exif|csv` from `OutputConfig` in `host/src/cameracommander/services/metadata.py`
- [X] T035 [US1] Implement video assembly: subprocess `ffmpeg` with profile-mapped flags (`mp4-h264` → `-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p`), `ffmpeg_extra` override, post-capture invocation, frame-rate from `OutputConfig.video.fps`, stream progress to `EventBus` topic `session.<id>.assemble` in `host/src/cameracommander/services/post_process.py`
- [X] T036 [US1] Implement `JobManager` (single-job lock raising `JobAlreadyRunningError` → HTTP 409 per FR-039; lifecycle pending→running→{completed,stopped,failed}; emits `job.<id>.state`, `job.<id>.progress`, `job.<id>.fault` events; cooperative stop flag honoured between frames; calibration gate enforced at `start()` per FR-041) in `host/src/cameracommander/services/jobs.py`
- [X] T037 [US1] Implement `TimelapseRunner` capture→settle→move loop: linear tilt interpolation (FR-016), per-frame disk guard call (T032), per-frame move-timeout enforcement using `expected_duration_s + safety.move_timeout_margin_s` (FR-037), cadence-overrun counter that proceeds without skipping (FR-038) and flips `flags.cadence_warning` when >20% per spec edge case, zero-padded filename emission (FR-043), metadata write (T034), session asset registration in `host/src/cameracommander/services/timelapse.py` (depends on T030–T036)

#### REST API endpoints (US1 scope)

- [X] T038 [P] [US1] Implement `GET /api/health` (`Health` schema, includes `active_job_id`) in `host/src/cameracommander/api/routes/health.py`
- [X] T039 [P] [US1] Implement `GET /api/hardware/status` (aggregate `HardwareStatus` from camera adapter + tripod adapter + calibration service) in `host/src/cameracommander/api/routes/health.py`
- [X] T040 [US1] Implement `POST /api/tripod/home` (calls `CalibrationService.mark_homed()`, returns updated `TripodStatus`) in `host/src/cameracommander/api/routes/tripod.py`
- [X] T041 [US1] Implement `POST /api/jobs/timelapse` (validates `Configuration` body, dispatches to `JobManager.start("timelapse", config)`, returns 201 + `Job`; maps errors to 400/409/412/503) in `host/src/cameracommander/api/routes/jobs.py`
- [X] T042 [US1] Implement `GET /api/jobs/{job_id}`, `GET /api/jobs/active`, `POST /api/jobs/{job_id}/stop` in `host/src/cameracommander/api/routes/jobs.py`
- [X] T043 [US1] Implement `GET /api/sessions/{session_id}/config` (returns the captured `Configuration` as JSON or YAML by `Accept` header — FR-024) in `host/src/cameracommander/api/routes/sessions.py`

#### CLI

- [X] T044 [P] [US1] Implement `cameracommander validate` (loads YAML, runs all Pydantic validators + `SafetyService.validate_sequence`, exits 0 or 2; `--json`, `--strict/--no-strict`) in `host/src/cameracommander/cli/commands/validate.py`
- [X] T045 [P] [US1] Implement `cameracommander timelapse` (loads config, applies `--no-video`/`--dry-run`/`--mock*` overrides, drives `JobManager` and renders single-line in-place progress, exit codes 0/2/3/9/10/11/12/15) in `host/src/cameracommander/cli/commands/timelapse.py`
- [X] T046 [P] [US1] Implement `cameracommander serve` (boots FastAPI via uvicorn, `--mock` aliases, optional `--reload`; serves `web/dist/` if present) in `host/src/cameracommander/cli/commands/serve.py`

#### Web UI (US1-only views)

- [X] T047 [P] [US1] Generate the typed TypeScript API client from `specs/001-core-system/contracts/host-api.openapi.yaml` into `web/src/lib/api/` with a thin fetch wrapper carrying `JSON.parse` + error mapping
- [X] T048 [P] [US1] Implement WebSocket subscription helper (single `/ws/events` connection, topic-based listener API, reconnect with backoff) in `web/src/lib/ws/client.ts`
- [X] T049 [P] [US1] Implement Svelte stores (`hardwareStatus`, `activeJob`, `calibration`) in `web/src/lib/stores/index.ts` wired to the WS client
- [X] T050 [US1] Implement `web/src/App.svelte` shell with view router (LiveControl/Planner/Monitor/Library tabs) and a top status bar fed by `hardwareStatus` + `calibration` stores; root mounted from `web/src/main.ts`
- [X] T051 [US1] Implement Planner view: timelapse form (camera section, tilt-limit-aware angle inputs, frame count/interval/settle, output dir, video toggles), client-side mirror of safety validators, **Set as home** button, **Launch timelapse** call to `POST /api/jobs/timelapse`, in `web/src/views/Planner.svelte`
- [X] T052 [US1] Implement Monitor view: live job progress card (frames captured / total, ETA, last position) wired to `job.<id>.progress` + `job.<id>.state` topics, **Stop** button, hardware-status panel in `web/src/views/Monitor.svelte`

#### Firmware (US1 minimum)

- [X] T053 [US1] Author `firmware/src/protocol.h` declaring `FW_VERSION`, command tokens, reply prefixes mirroring `contracts/firmware-protocol.md`
- [X] T054 [US1] Port `firmware/src/GearedStepper.h` and `firmware/src/GearedStepper.cpp` from `old_implementation/firmware/` (AccelStepper wrapper + gear-ratio + microstep handling), keep the existing public API
- [X] T055 [US1] Implement `firmware/src/main.cpp`: serial-line reader, command dispatcher (`V`, `M`, `S`, `1/2/4/8/6`, `e`, `d`, `X`, `+`, `-`), boot banner, version reply on `V`, position counter zeroed on `e`/`d`, drivers gating motion. Wire `loop()` to AccelStepper run with cooperative yields
- [X] T056 [US1] Implement `firmware/src/safety.cpp` with the build-time mechanical tilt clamp (separate from operator-config tilt window which lives host-side per research §17)
- [X] T057 [P] [US1] Add PlatformIO native test `firmware/test/test_parser.cpp` covering tokenisation of `M 12.5 -3.0`, `S`, mis-arity rejection (`ERR Syntax`), unknown-token rejection (`ERR Unknown`), and the case-insensitivity rule

**Checkpoint**: User Story 1 fully functional and testable independently. The MVP is shippable once this phase passes.

---

## Phase 4: User Story 2 — Verify Hardware and Test Camera Settings (Priority: P2)

**Goal**: Operator opens the live control view, sees camera + tripod status, queries and changes camera settings, fires a test capture, watches the live-view stream, manually nudges the tripod.

**Independent Test**: With either real or mock hardware, the LiveControl view shows current camera settings, a streaming MJPEG preview, **Test capture** returns a thumbnail in <2 s, **Nudge** moves the tripod by the entered delta and updates the displayed position; on disconnect the view shows a clear fault indicator and disables capture controls.

### Tests for User Story 2 ⚠️

- [X] T058 [P] [US2] Contract test: `GET /api/camera/settings`, `PUT /api/camera/settings`, `POST /api/camera/capture`, `GET /api/camera/preview` against `MockCameraAdapter` round-trip the schemas in `host/tests/contract/test_camera_endpoints.py`
- [X] T059 [P] [US2] Contract test: `POST /api/tripod/move`, `POST /api/tripod/nudge`, `POST /api/tripod/stop`, `PUT /api/tripod/drivers` enforce 422 (tilt limit), 412 (calibration on `move`), 409 (job lock), and 200 happy paths in `host/tests/contract/test_tripod_endpoints.py`

### Implementation for User Story 2

- [X] T060 [P] [US2] Implement `GET /api/camera/settings` and `PUT /api/camera/settings` (delegates to `CameraAdapter.query_settings`/`apply_settings`, maps validation errors to 400, disconnect to 503) in `host/src/cameracommander/api/routes/camera.py`
- [X] T061 [P] [US2] Implement `POST /api/camera/capture` and `GET /api/camera/captures/{capture_id}` (one-shot capture stored in a TTL-keyed in-memory cache + temp file; optional `save_to_session`) in `host/src/cameracommander/api/routes/camera.py`
- [X] T062 [P] [US2] Implement `GET /api/camera/preview` (single JPEG) and `GET /api/camera/preview/stream` (MJPEG `multipart/x-mixed-replace; boundary=frame`, 5 fps cap) in `host/src/cameracommander/api/routes/camera.py`
- [X] T063 [P] [US2] Implement `GET /api/tripod/status`, `POST /api/tripod/move`, `POST /api/tripod/nudge`, `POST /api/tripod/stop`, `PUT /api/tripod/drivers` — all guarded by `SafetyService` and the active-job lock; `move` requires `homed` calibration but `nudge` is allowed under `unknown` (with a logged warning per cli-commands.md) in `host/src/cameracommander/api/routes/tripod.py`
- [X] T064 [P] [US2] Implement `cameracommander snapshot` CLI (lazy gphoto2 import, `--model-substring`, `--no-autofocus`, exit codes 0/2/10/11) in `host/src/cameracommander/cli/commands/snapshot.py`
- [X] T065 [P] [US2] Implement `cameracommander tripod` REPL CLI (relative `<pan> <tilt>`, `to <pan> <tilt>`, `home`, `e`/`d`, `s`, `stop`, `q`) in `host/src/cameracommander/cli/commands/tripod.py`
- [X] T066 [US2] Implement LiveControl view: camera-settings panel (settings table from `/api/camera/settings`, edit + apply), MJPEG `<img src="/api/camera/preview/stream">`, **Test capture** button, **Nudge** controls (pan/tilt buttons with safety-aware enable state), connection-fault banner that disables capture when camera/tripod state is `error` or `disconnected`, in `web/src/views/LiveControl.svelte`
- [X] T067 [US2] Add periodic `tripod.position` event publication (≤1 Hz idle, ≤4 Hz during a job per host-events.asyncapi.yaml) in `host/src/cameracommander/services/tripod_polling.py` and wire into `AppContainer` lifespan

**Checkpoint**: User Stories 1 AND 2 both work independently. Operator can prep a shoot end-to-end via UI or CLI.

---

## Phase 5: User Story 3 — Execute a Video Pan (Priority: P3)

**Goal**: Smooth motion + camera REC sync from start angle to target angle over a defined duration.

**Independent Test**: With mocks, `cameracommander pan video_pan_mock.yaml` (or `POST /api/jobs/video-pan` from the UI) starts mock recording and mock motion within 500 ms of each other, runs for the configured duration, stops both, and persists a session with the recorded video asset.

### Tests for User Story 3 ⚠️

- [X] T068 [P] [US3] Integration test: full mock video pan asserts motion-start vs recording-start delta < 500 ms (User Story 3 acceptance #1), motion completes at `duration_s ± tolerance`, recording stops after motion, in `host/tests/integration/test_full_video_pan_mock.py`
- [X] T069 [P] [US3] Contract test: `POST /api/jobs/video-pan` rejects out-of-window tilt with 422; rejects when calibration `unknown` with 412; in `host/tests/contract/test_jobs_video_pan_endpoint.py`

### Implementation for User Story 3

- [X] T070 [US3] Implement `VideoPanRunner`: pre-arm camera REC mode → issue `M target` and `start_recording` in the same monotonic instant (≤500 ms drift target) → await motion `DONE` → `stop_recording` → register session with the produced video, with stall-timeout enforcement matching `move_timeout_margin_s`, in `host/src/cameracommander/services/video_pan.py`
- [X] T071 [US3] Implement `POST /api/jobs/video-pan` in `host/src/cameracommander/api/routes/jobs.py` (mirrors timelapse error mapping)
- [X] T072 [P] [US3] Implement `cameracommander pan` CLI (same option scheme as `timelapse` minus `--no-video`, exit codes 0/2/3/10/11/12/15) in `host/src/cameracommander/cli/commands/pan.py`
- [X] T073 [US3] Extend Planner view with a **Video Pan** mode: discriminator-aware form (duration_s instead of frames/interval, no output.video block surfaced), launches `POST /api/jobs/video-pan`, in `web/src/views/Planner.svelte`

**Checkpoint**: All three execution modes (still capture, timelapse, video pan) are operational.

---

## Phase 6: User Story 4 — Browse the Session Library (Priority: P4)

**Goal**: After a shoot, the operator can list completed sessions, inspect their metadata and configuration, reload settings into the planner, and trigger post-capture video assembly.

**Independent Test**: With at least one session on disk, the Library view lists it with timestamp + frame count + flags, **Inspect** opens its config, **Reload settings** pre-populates the Planner form, **Assemble video** on a session without a video produces one and updates the asset list. SC-006 (locate, inspect, reload < 60 s) is achievable.

### Tests for User Story 4 ⚠️

- [ ] T074 [P] [US4] Contract test: `GET /api/sessions`, `GET /api/sessions/{id}`, `DELETE /api/sessions/{id}`, `GET /api/sessions/{id}/config`, `POST /api/sessions/{id}/assemble`, `GET /api/sessions/{id}/assets/{asset_path}` against a fixture session library in `host/tests/contract/test_sessions_endpoints.py`

### Implementation for User Story 4

- [ ] T075 [P] [US4] Implement session listing/get/delete handlers (paged, newest-first, optional `tag` filter) in `host/src/cameracommander/api/routes/sessions.py`
- [ ] T076 [US4] Implement `POST /api/sessions/{id}/assemble` — reuses T035; runs under the single-job lock; emits `session.<id>.assemble` events; returns 202 + `Session`; handles 409 when capture is running, in `host/src/cameracommander/api/routes/sessions.py`
- [ ] T077 [P] [US4] Implement `GET /api/sessions/{id}/assets/{asset_path}` with safe path resolution (no traversal outside session dir) in `host/src/cameracommander/api/routes/sessions.py`
- [ ] T078 [US4] Implement Library view: paginated table (newest first, badges for flags `cadence_warning`/`partial_due_to_disk`/`fault`), session detail drawer with embedded config viewer, **Reload settings** that navigates to Planner with the config pre-loaded (URL param or store hand-off), **Assemble video** button wired to `POST .../assemble`, in `web/src/views/Library.svelte`
- [ ] T079 [P] [US4] Bridge Library→Planner reload: extend the Planner form (T051) to accept an initial `Configuration` (from store or query param) and prefill fields without hitting the server again

**Checkpoint**: Spec User Stories 1–4 are independently usable.

---

## Phase 7: User Story 5 — Develop and Test Without Physical Hardware (Priority: P5)

**Goal**: A developer can run the full stack against mocks. The mock-firmware command is operator-facing, the `--mock` flags are wired through CLI + `serve`, and the full quickstart §2 sequence works on a laptop.

**Independent Test**: From a clean clone, `cameracommander mock-firmware --port 9999 &` followed by `cameracommander serve --mock` and a browser at `http://localhost:8000` produces a working timelapse run end-to-end with no hardware. CI runs `pytest tests/integration/` and passes (US1 + US3 mock integration tests defined above).

### Tests for User Story 5 ⚠️

- [ ] T080 [P] [US5] Smoke test: `cameracommander mock-firmware` starts on a free port, accepts a TCP connection, replies to `V` with the expected `VERSION`, processes a basic `M` round-trip honouring `--deg-per-second` (asserting the `DONE` reply latency), in `host/tests/integration/test_mock_firmware_cli.py`
- [ ] T081 [P] [US5] End-to-end test: `cameracommander serve --mock` boots the API, the API client (T047) lists hardware as `connected (mock)`, a timelapse launched via `POST /api/jobs/timelapse` reaches `completed` and the resulting session is queryable via `GET /api/sessions`, in `host/tests/integration/test_serve_mock_e2e.py`

### Implementation for User Story 5

- [ ] T082 [P] [US5] Implement `cameracommander mock-firmware` CLI wrapping T019 (all options from cli-commands.md §`mock-firmware`, foreground SIGINT-clean shutdown) in `host/src/cameracommander/cli/commands/mock_firmware.py`
- [ ] T083 [US5] Wire `--mock`, `--mock-camera`, `--mock-tripod` flags through `serve`, `timelapse`, `pan`, `snapshot` (in their respective T046/T045/T072/T064 commands) so the AppContainer (T015) swaps `MockCameraAdapter` and rewrites `tripod.serial.port` to `socket://127.0.0.1:9999` before adapter open. `--mock` on `serve` additionally spawns the mock firmware server in-process
- [ ] T084 [P] [US5] Add example mock configurations: `host/examples/timelapse_mock.yaml` and `host/examples/video_pan_mock.yaml` matching `contracts/config-schema.md` defaults adapted for mock paths
- [ ] T085 [P] [US5] Document the full mock workflow in `host/README.md` and cross-link `quickstart.md §2`

**Checkpoint**: All five user stories independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Production readiness on the Pi Zero 2 W deployment target and final spec/SC validation.

- [ ] T086 [P] Validate the Pi Zero 2 W resource budget: idle RSS ≤ 200 MB, in-job RSS ≤ 280 MB; record measurements in `specs/001-core-system/notes/pi-zero-rss.md` (run on a real Pi or `qemu-system-aarch64` if necessary)
- [ ] T087 [P] Add `firmware/test/test_safety_clamp.cpp` covering the build-time mechanical tilt clamp from T056
- [ ] T088 [P] Author top-level `README.md` summarising components, links to spec/plan/quickstart, and reproducing the quickstart §2 commands verbatim
- [ ] T089 [P] Author `web/README.md` covering the off-device build (`npm ci && npm run build`) and the deploy-as-static-bundle expectation
- [ ] T090 Run `quickstart.md §6` smoke tests (`pytest tests/integration/test_full_timelapse_mock.py`, `pytest tests/integration/test_full_video_pan_mock.py`, `pytest tests/contract/`) and fix any failures
- [ ] T091 [P] Add `host/examples/host.yaml` template for the Pi-side config referenced by `quickstart.md §4.2`
- [ ] T092 Add a `cameracommander serve --mock` warning when `web/dist/` is missing (logged once, with the build instruction) per cli-commands.md §`serve`
- [ ] T093 Verify SC-008 protocol-version mismatch path: integration test that boots mock firmware with `--fw-version 2.0.0`, asserts host disconnects, marks `tripod.protocol_compatible=false`, surfaces the operator-visible error before any command, in `host/tests/integration/test_protocol_mismatch.py`
- [ ] T094 Verify SC-004 5-second fault detection: integration test that simulates camera disconnect mid-timelapse via `MockCameraAdapter`'s disconnect toggle (T020), asserts `job.<id>.fault` event fires within 5 s, partial frames remain on disk, in `host/tests/integration/test_fault_detection_window.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: starts immediately
- **Foundational (Phase 2)**: depends on Phase 1; **blocks all user stories**
- **User Story 1 (Phase 3, P1, MVP)**: depends on Phase 2
- **User Story 2 (Phase 4, P2)**: depends on Phase 2; integrates with US1's `JobManager` lock for 409 behaviour
- **User Story 3 (Phase 5, P3)**: depends on Phase 2; reuses `JobManager` from US1 (T036) and `SerialTripodAdapter` from US1 (T029)
- **User Story 4 (Phase 6, P4)**: depends on Phase 2 and on US1's `SessionRepository` (T033) + assembly service (T035)
- **User Story 5 (Phase 7, P5)**: depends on Phase 2 (T019/T020 mocks); validates mock paths through US1+US3 implementations
- **Polish (Phase 8)**: depends on the user stories selected for the release

### Within Each User Story

- Tests written and observed failing before implementation (where tests are present)
- Adapters → services → endpoints/CLI → UI views
- Foundation models (Phase 2) before everything

### Critical cross-story dependencies

- US2's `/api/tripod/move` (T063) needs `CalibrationService` from US1 (T031) — wait or stub
- US3's `VideoPanRunner` (T070) needs `JobManager` from US1 (T036)
- US4's `Library → Planner reload` (T079) modifies the Planner form built in US1 (T051)
- US5's flag wiring (T083) modifies CLI commands from US1/US2/US3 (T045/T046/T064/T072)

### Parallel Opportunities

- All Phase 1 tasks marked [P] run in parallel (T002–T006 alongside T001's directory create)
- Phase 2 model/protocol/mocks tasks marked [P] (T007–T013, T019–T023) run in parallel; T014–T018 form a small serial spine
- Within US1: adapters T028/T029 in parallel; routes T038–T043 mostly parallel within `routes/jobs.py` and `routes/tripod.py` files; tests T024–T027 in parallel; firmware T053–T057 mostly parallel except T055 depends on T053+T054
- US2, US3, US4 can be staffed in parallel by separate developers once US1 lands
- US5 polish (examples, docs) parallel to US5 CLI wiring

---

## Parallel Example: User Story 1 — Adapters + Tests Kickoff

```bash
# Once Phase 2 is complete, fire these in parallel for US1:
Task: "T024 Integration test for full mock timelapse — host/tests/integration/test_full_timelapse_mock.py"
Task: "T025 Contract test for POST /api/jobs/timelapse — host/tests/contract/test_jobs_timelapse_endpoint.py"
Task: "T026 Unit test for tilt interpolation — host/tests/unit/test_timelapse_interpolation.py"
Task: "T027 Unit test for disk-space guard — host/tests/unit/test_disk_guard.py"
Task: "T028 Implement GphotoCameraAdapter — host/src/cameracommander/hardware/camera/gphoto.py"
Task: "T029 Implement SerialTripodAdapter — host/src/cameracommander/hardware/tripod/serial_adapter.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 (Setup) and Phase 2 (Foundational) — including mocks (T019/T020) and contract tests (T021–T023)
2. Phase 3 (US1) — full timelapse against mocks, then validate against real hardware
3. **STOP and VALIDATE**: run `cameracommander timelapse host/examples/timelapse_mock.yaml` and watch a session appear in the Library
4. Demo / ship MVP

### Incremental Delivery

1. Setup + Foundational → mocks alive
2. + US1 → MVP (timelapse end-to-end, CLI + UI)
3. + US2 → operator can prep a shoot interactively (LiveControl + Test capture + Nudge)
4. + US3 → video pan mode
5. + US4 → Library + post-capture assembly
6. + US5 → polished mock workflow + CI integration tests
7. Polish → Pi Zero 2 W validation, README, SC verification

### Parallel Team Strategy

After Phase 2 lands:

- Developer A: US1 host-side (T028–T046, T053–T057)
- Developer B: US1 web-side (T047–T052), then US4 (T078–T079)
- Developer C: US2 (T058–T067)
- Developer D: US3 (T068–T073) once US1 `JobManager` (T036) is on `main`

---

## Notes

- [P] tasks operate on different files with no incomplete dependency.
- [Story] label maps each task to its user story for traceability against `spec.md`.
- All FR / SC references are inline against the relevant tasks.
- Calibration must be `homed` before any automated job (FR-041); `cameracommander tripod`, `POST /api/tripod/nudge`, and the LiveControl manual nudge are the only motion paths allowed under `unknown` calibration.
- The single-job lock is enforced in `JobManager` (T036); every endpoint that takes the hardware (`/api/camera/capture`, `/api/tripod/move`, `/api/tripod/nudge`, `/api/tripod/drivers`, both `/api/jobs/*`, `/api/sessions/{id}/assemble`) consults it.
- The Pi Zero 2 W resource budget (≤ 200 MB idle / ≤ 280 MB during a job) is the binding deployment constraint — re-check after each story lands.
