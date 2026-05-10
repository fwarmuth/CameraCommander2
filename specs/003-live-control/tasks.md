---
description: "Task list for Live Control & Setup Assist"
---

# Tasks: Live Control & Setup Assist

**Input**: Design documents from `/specs/003-live-control/`
**Branch**: `003-live-control`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/host-api.openapi.yaml

**Organization**: Tasks are grouped by user story. Each phase is independently testable.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Foundational (Hardware & API)

**Purpose**: Update the core adapters and API contracts to support focus and dynamic settings.

- [X] T001 [P] Implement recursive widget tree walker in `GphotoCameraAdapter._query_settings_blocking` to extract choices, ranges, and current values in `host/src/cameracommander/hardware/camera/gphoto.py` (R004)
- [X] T002 [P] Update `SettingDescriptor` and `CameraSettings` schemas in `host/src/cameracommander/core/config.py` and `host/src/cameracommander/core/models.py` to match the refined data model (FR-004)
- [X] T003 [P] Implement `CameraAdapter.focus_nudge(step_size: int)` using `main.actions.manualfocusdrive` in `host/src/cameracommander/hardware/camera/gphoto.py` (FR-003, R001)
- [X] T004 Implement `POST /api/camera/focus` endpoint in `host/src/cameracommander/api/routes/camera.py` (FR-003)
- [X] T005 [P] Update `MockCameraAdapter` to simulate focus nudges and return enriched synthetic settings in `host/src/cameracommander/hardware/camera/mock.py` (Constitution II)
- [X] T006 Regenerate TypeScript API client in `web/src/lib/api/generated.ts` from the updated `contracts/host-api.openapi.yaml`

---

## Phase 2: User Story 1 — Framing and Focusing (P1)

**Goal**: Operator can composição and focus using live preview and manual controls.

- [X] T007 [P] [US1] Implement focus nudge buttons (In/Out) with step size selector (-3 to 3) in `web/src/views/LiveControl.svelte` (FR-003)
- [X] T008 [P] [US1] Ensure tripod position display updates in real-time using the `hardware.status` store in `web/src/views/LiveControl.svelte` (FR-008, SC-001)
- [X] T009 [US1] Implement hardware lock logic in `GphotoCameraAdapter` to prevent preview/focus/capture collisions in `host/src/cameracommander/hardware/camera/gphoto.py` (R003)

---

## Phase 3: User Story 2 — Fine-Tuning Exposure (P1)

**Goal**: Operator can verify exposure settings with high-res test captures.

- [X] T010 [P] [US2] Implement "Quick Settings" bar component for ISO, Shutter, Aperture, and WB in `web/src/components/QuickSettingsBar.svelte` (FR-004)
- [X] T011 [US2] Integrate `QuickSettingsBar` into `web/src/views/LiveControl.svelte` and wire to `api.updateCameraSettings` (FR-004, FR-008)
- [X] T012 [P] [US2] Implement `ImageInspector` component with CSS transform-based zoom and drag-to-pan in `web/src/components/ImageInspector.svelte` (FR-006, R002)
- [X] T013 [US2] Wire "Test Capture" button in `web/src/views/LiveControl.svelte` to `POST /api/camera/capture` and open the resulting image in `ImageInspector` (FR-005, FR-007)

---

## Phase 4: User Story 3 — Long Exposure & Inspection (P2)

**Goal**: High-detail verification for long exposures.

- [X] T014 [US3] Add zoom-to-fit and zoom-to-100% shortcuts to `ImageInspector.svelte` (SC-004)
- [X] T015 [US3] Implement auto-stop preview logic: the preview stream must break the loop if the hardware lock is taken by a capture in `host/src/cameracommander/api/routes/camera.py` (FR-007, R003)

---

## Phase 5: Polish

- [X] T016 [P] Add unit tests for gphoto2 settings tree walker in `host/tests/unit/test_gphoto_walker.py`
- [X] T017 [P] Add integration test for focus nudge API path in `host/tests/integration/test_focus_api.py`
- [X] T018 Final UI styling sweep: ensure Quick Settings and Image Inspector are visually consistent with the dark "camera" aesthetic in `web/src/views/LiveControl.svelte`

---

## Dependencies & Execution Order

- **Phase 1** must be complete before any UI work.
- **T009 (Hardware Lock)** is critical for system stability on the Pi.
- **T013 (Capture wiring)** depends on **T012 (ImageInspector)**.

## Parallel Opportunities

- T001, T002, T003 can run in parallel (hardware vs models vs adapter).
- T007 and T008 (UI controls) can run in parallel.
- T016 and T017 (Tests) can run in parallel.

## Implementation Strategy

1.  **Backend First**: Get the gphoto2 walker and focus logic into the API.
2.  **Mocks**: Verify the new API paths using the updated `MockCameraAdapter`.
3.  **UI Scaffolding**: Build the tree settings and focus buttons.
4.  **Verification Loop**: Build the `ImageInspector` and connect the "Test Capture" button.
5.  **Pi Test**: Deploy to the Pi Zero 2 W and verify MJPEG performance and high-res capture timing.
