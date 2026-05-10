---
description: "Task list for Live Control and Planning Assist"
---

# Tasks: Live Control and Planning Assist

**Input**: Design documents from `/specs/003-live-control/`
**Branch**: `003-live-control`

---

## Phase 1: Foundational Stabilization

**Goal**: Ensure the backend API and hardware adapters are robust.

- [X] T001 [P] Implement structured request models (`AbsoluteMoveRequest`, `RelativeNudgeRequest`, `DriverRequest`) in `host/src/cameracommander/core/config.py`
- [X] T002 [P] Increase default serial timeout to 30s in `host/src/cameracommander/core/config.py` to support real hardware motion
- [X] T003 Update `SerialTripodAdapter` to use `expected_duration_s` for nudge commands in `host/src/cameracommander/hardware/tripod/serial_adapter.py`
- [X] T004 Implement `GphotoCameraAdapter.query_settings` tree walker in `host/src/cameracommander/hardware/camera/gphoto.py`
- [X] T005 Fix `gphoto2` capture signature and return image bytes in `host/src/cameracommander/hardware/camera/gphoto.py`

---

## Phase 2: User Story 1 — Find Tripod Keyframes (P1)

**Goal**: Operator can frame the shot using nudge controls.

- [X] T006 Implement `PUT /api/tripod/drivers` with `DriverRequest` in `host/src/cameracommander/api/routes/tripod.py`
- [X] T007 Implement `POST /api/tripod/nudge` with `RelativeNudgeRequest` in `host/src/cameracommander/api/routes/tripod.py`
- [X] T008 Add **Motors: ON/OFF** button to the nudge control grid in `web/src/views/LiveControl.svelte`
- [X] T009 Migrate `LiveControl.svelte` to Svelte 5 runes for real-time position reactivity

---

## Phase 3: User Story 2 — Verify Exposure with Test Captures (P1)

**Goal**: Operator can trigger high-res captures to check settings.

- [X] T010 Implement `POST /api/camera/capture` with image caching in `host/src/cameracommander/api/routes/camera.py`
- [X] T011 Implement `GET /api/camera/captures/{id}` to serve cached test images in `host/src/cameracommander/api/routes/camera.py`
- [X] T012 Add **Test Capture** button and **Open latest capture** link in `web/src/views/LiveControl.svelte`

---

## Phase 4: User Story 3 — Focus Assist and Organized Settings (P2)

**Goal**: Detailed camera configuration and rough framing feed.

- [X] T013 Implement MJPEG stream in `host/src/cameracommander/api/routes/camera.py` using `StreamingResponse`
- [X] T014 Implement collapsible tree grouping for camera settings in `web/src/views/LiveControl.svelte`
- [X] T015 Implement search filter for settings in `web/src/views/LiveControl.svelte`
- [X] T016 [US3] Add a curated "Quick Settings" bar directly below the Live View image in `web/src/views/LiveControl.svelte` for ISO/Aperture/Shutter/WB
- [X] T017 [US3] Ensure "Image Format" (RAW/JPEG) is included in the Planning tab and Quick Settings

---

## Phase 5: Polish & Deployment

- [X] T018 Build web assets and sync to Pi
- [X] T019 Verify that Live View automatically pauses when a Test Capture or Job is active to prevent I/O conflicts
- [ ] T020 Final verification of all User Stories on the Pi Zero 2 W with real Canon hardware
