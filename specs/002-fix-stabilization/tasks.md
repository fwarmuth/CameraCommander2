---
description: "Task list for CameraCommander2 — Fix Stabilization"
---

# Tasks: CameraCommander2 — Fix Stabilization

**Input**: Design documents from `/specs/002-fix-stabilization/`
**Branch**: `002-fix-stabilization`

---

## Phase 1: Foundational Fixes (User Story 1)

**Goal**: Resolve the immediate `ImportError` to make the application runnable.

- [X] T001 [P] [US1] Define `StatusReport` dataclass in `host/src/cameracommander/hardware/tripod/base.py` per R001
- [X] T002 [P] [US1] Align `MoveResult` dataclass in `host/src/cameracommander/hardware/tripod/base.py` with implementation usage (add `duration_s`, remove `success`/`error`) per R002
- [X] T003 [P] [US1] Fix corrupted \`__all__\` and \`CaptureResult\` definition in \`host/src/cameracommander/core/models.py\` per R003
- [X] T008 [P] [US1] Implement missing classes and functions in \`host/src/cameracommander/hardware/tripod/protocol.py\` per R005
- [X] T004 [US1] Verify application launch with \`uv run cameracommander serve --mock\`


---

## Phase 2: Validation & Stabilization (User Story 2)

**Goal**: Ensure the system is structurally sound and no other import errors exist.

- [X] T005 [US2] Verify all CLI subcommands (`timelapse`, `pan`, `tripod`, `snapshot`) can display `--help` without crashing
- [X] T006 [US2] Run the full test suite with `uv run pytest` and ensure all tests are collected successfully

---

## Phase 3: Collection Point (User Story 3)

**Goal**: Track and fix Pi-specific deployment errors as they arise.

- [ ] T007 [US3] Placeholder for Pi-specific error resolution (to be filled when new errors are reported)

---

## Dependencies & Execution Order

- **User Story 1**: Must be completed first to allow any further testing.
- **User Story 2**: Depends on User Story 1.

## Parallel Opportunities

- T001, T002, and T003 can be performed in parallel as they affect different files or independent parts of the same file.

## Implementation Strategy

1. Fix the hardware dataclasses in `base.py` to satisfy imports.
2. Repair the `models.py` file.
3. Validate the fix by starting the mock server.
4. Perform a sweep of CLI commands and tests to ensure overall stability.
