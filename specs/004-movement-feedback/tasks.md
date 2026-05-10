# Tasks: Movement Feedback and Increased Timeout

**Input**: Design documents from `specs/004-movement-feedback/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

## Phase 1: Setup

- [x] T001 Finalize project structure and verify ignore files per plan.md

---

## Phase 2: Foundational

**Goal**: Establish the protocol v1.1 constants and parser support.

- [x] T002 [P] Add `PROGRESS`, `ESTIMATE`, and new error constants to `firmware/src/protocol.h`
- [x] T003 [P] Implement `ProgressReply` and `EstimateReply` data classes in `host/src/cameracommander/hardware/tripod/protocol.py`
- [x] T004 [P] Update `parse_reply` and `ErrorReply` literal in `host/src/cameracommander/hardware/tripod/protocol.py`
- [x] T005 [P] Update contract tests in `host/tests/contract/test_firmware_protocol.py` to cover new reply types

---

## Phase 3: User Story 1 - Prevent Timeouts (P1) 🎯 MVP

**Goal**: Ensure long movements do not trigger `MotorStallError` by using `PROGRESS` messages to refresh the watchdog.

**Independent Test**: Execute a movement command that exceeds the default serial timeout (e.g., 5 seconds) and verify it completes successfully without error against mock firmware.

- [x] T006 [P] [US1] Refactor firmware `move_absolute` to a non-blocking state machine in `firmware/src/main.cpp`
- [x] T007 [P] [US1] Implement periodic `PROGRESS` emission (5Hz) in `firmware/src/main.cpp` during the moving state
- [x] T008 [P] [US1] Update `SerialTripodAdapter._send_blocking` to refresh the `deadline` upon receiving `ProgressReply` in `host/src/cameracommander/hardware/tripod/serial_adapter.py`
- [x] T009 [P] [US1] Update `MockFirmwareServer` to simulate the non-blocking moving state and periodic `PROGRESS` messages in `host/src/cameracommander/mock_firmware/server.py`
- [x] T010 [US1] Create integration test for long movement timeouts in `host/tests/integration/test_movement_timeout.py`

---

## Phase 4: User Story 2 - Real-time Movement Progress (P2)

**Goal**: Display current pan/tilt position in the CLI during movement using an in-place overwritten line.

**Independent Test**: Watch the `tripod` CLI output during a move and confirm the position line updates dynamically and finishes on the same line.

- [x] T011 [P] [US2] Add `progress_callback` support to `SerialTripodAdapter.move_to` and `_send` in `host/src/cameracommander/hardware/tripod/serial_adapter.py`
- [x] T012 [US2] Implement progress callback in `tripod.py` that overwrites a single line using `\r` in `host/src/cameracommander/cli/commands/tripod.py`

---

## Phase 5: User Story 3 - Estimated Time of Completion (P3)

**Goal**: Display the firmware-calculated duration estimate at the start of a move.

**Independent Test**: Verify the CLI shows "Move started (est. Xs)..." immediately after issuing a `to` or nudge command.

- [x] T013 [P] [US3] Implement duration estimation logic and `ESTIMATE` emission in `firmware/src/main.cpp`
- [x] T014 [P] [US3] Update `MockFirmwareServer` to emit `ESTIMATE` at the start of a move in `host/src/cameracommander/mock_firmware/server.py`
- [x] T015 [US3] Update progress callback to handle `EstimateReply` and display remaining time in `host/src/cameracommander/cli/commands/tripod.py`

---

## Phase 6: Polish & Cross-cutting Concerns

- [x] T016 [P] Implement `ERR AlreadyAtTarget` logic in `firmware/src/main.cpp` and handle in CLI
- [x] T017 [P] Implement `ERR MotorStall` logic in `firmware/src/main.cpp` and handle in host
- [x] T018 [P] Verify Emergency Stop (`X`) correctly interrupts moves in progress
- [x] T019 Final verification: Run all host tests (`uv run pytest host/tests`)
- [x] T020 Final verification: Run firmware native tests (`pio test -e native`)

---

## Dependencies & Execution Order

- **Foundational (Phase 2)** must be completed before any US-specific work.
- **US1 (Phase 3)** is the MVP and should be prioritized.
- **US2 (Phase 4)** and **US3 (Phase 5)** both depend on the `PROGRESS` and `ESTIMATE` messages defined in Phase 2.

### Parallel Opportunities

- Firmware work (T002, T006, T007) and Host work (T003, T004, T008) can proceed in parallel once the contract is finalized.
- Mock server updates (T009) can happen alongside firmware refactoring.

## Implementation Strategy

1.  **Contract First**: Ensure `protocol.h` and `protocol.py` are in sync with the updated contract.
2.  **State Machine**: Focus on the firmware refactor first, as it enables all other features.
3.  **Adaptive Timeout**: Verify the timeout bug fix with integration tests before adding UI layers.
4.  **UI Feedback**: Add the CLI enhancements incrementally once the data is flowing.
