# Tasks: Movement Feedback and Increased Timeout

**Input**: Design documents from `specs/004-movement-feedback/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Finalize design artifacts

- [ ] T001 Finalize updated protocol contract in `specs/004-movement-feedback/contracts/firmware-protocol.md`
- [ ] T002 Update `AGENTS.md` and `GEMINI.md` to point to the new plan (already done)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure for the new `PROGRESS` message

- [ ] T003 [P] Add `PROGRESS` reply constant to `firmware/src/protocol.h`
- [ ] T004 [P] Implement `ProgressReply` and update `parse_reply` in `host/src/cameracommander/hardware/tripod/protocol.py`
- [ ] T005 [P] Add `test_parse_progress_reply` to `host/tests/contract/test_firmware_protocol.py` (if applicable) or a new unit test in `host/tests/unit/hardware/tripod/test_protocol.py`

---

## Phase 3: User Story 1 - Prevent Timeouts (P1) 🎯 MVP

**Goal**: Keep the serial connection alive during long moves

**Independent Test**: Verify that a 90-degree move (taking >60s) completes without `MotorStallError`.

- [ ] T006 [P] [US1] Update `move_absolute` in `firmware/src/main.cpp` to emit `PROGRESS <pan> <tilt>` every 200ms
- [ ] T007 [P] [US1] Update `_send_blocking` in `host/src/cameracommander/hardware/tripod/serial_adapter.py` to recognize `ProgressReply` and refresh the `deadline`
- [ ] T008 [P] [US1] Update `host/src/cameracommander/mock_firmware/server.py` to simulate `PROGRESS` messages during motion
- [ ] T009 [US1] Create integration test `host/tests/integration/test_movement_timeout.py` that performs a slow move against the mock firmware

**Checkpoint**: User Story 1 functional - no more timeouts for long moves.

---

## Phase 4: User Story 2 - Real-time Movement Progress (P2)

**Goal**: Provide live position feedback in the CLI

**Independent Test**: Watch the CLI during a move and verify position updates are printed.

- [ ] T010 [P] [US2] Add `progress_callback` support to `SerialTripodAdapter.move_to` and `_send` in `host/src/cameracommander/hardware/tripod/serial_adapter.py`
- [ ] T011 [US2] Update `_run_repl` in `host/src/cameracommander/cli/commands/tripod.py` to pass a callback that prints current position during moves
- [ ] T012 [US2] Enhance progress printing in `host/src/cameracommander/cli/commands/tripod.py` to use a single line (overwrite with `\r`)

**Checkpoint**: User Story 2 functional - live feedback in CLI.

---

## Phase 5: User Story 3 - Estimated Time of Completion (P3)

**Goal**: Show the operator how much time remains

**Independent Test**: Verify the CLI shows "Estimated duration: Xs" when a move starts.

- [ ] T013 [P] [US3] Implement `estimate_duration(pan, tilt)` helper in `host/src/cameracommander/hardware/tripod/serial_adapter.py` using conservative 1.0 deg/s speed
- [ ] T014 [US3] Update `tripod` CLI in `host/src/cameracommander/cli/commands/tripod.py` to display the estimate at the start of a move

**Checkpoint**: All user stories functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T015 [P] Update `docs/TESTING_AND_DEPLOYMENT.md` if protocol changes require special hardware testing
- [ ] T016 Final documentation review in `specs/004-movement-feedback/quickstart.md`
- [ ] T017 [P] Run all host tests: `uv run pytest host/tests`
- [ ] T018 Run firmware native tests: `pio test -e native` (if relevant to protocol changes)

---

## Dependencies & Execution Order

- **T003, T004** are blockers for US1 implementation.
- **T006, T007, T008** implement the core "timeout refresh" logic.
- **T010** is a blocker for US2.
- **T013** is a blocker for US3.

### Parallel Opportunities
- Firmware (T003, T006) and Host (T004, T007, T008) work can proceed in parallel once the protocol is defined.
- Unit tests (T005) can be written in parallel with implementation.

---

## Implementation Strategy
1. **Foundation**: Get the `PROGRESS` message defined and parsed on both ends.
2. **MVP**: Fix the timeout bug first (US1). This is the highest value.
3. **Feedback**: Add the UI layers (US2, US3) to leverage the new protocol data.
