# Tasks: Movement Feedback and Increased Timeout

**Input**: Design documents from `specs/004-movement-feedback/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Finalize updated protocol contract in `specs/004-movement-feedback/contracts/firmware-protocol.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

- [ ] T002 [P] Add `PROGRESS`, `ESTIMATE`, and `ERR AlreadyAtTarget` constants to `firmware/src/protocol.h`
- [ ] T003 [P] Implement `ProgressReply` and `EstimateReply` and update `parse_reply` in `host/src/cameracommander/hardware/tripod/protocol.py`
- [ ] T004 [P] Update unit tests in `host/tests/unit/hardware/tripod/test_protocol.py` for new reply types

---

## Phase 3: User Story 1 - Prevent Timeouts (P1) 🎯 MVP

- [ ] T005 [P] [US1] Refactor firmware `move_absolute` in `firmware/src/main.cpp` to use a non-blocking state machine
- [ ] T006 [P] [US1] Implement periodic `PROGRESS` emission in firmware during motion
- [ ] T007 [P] [US1] Update `_send_blocking` in `host/src/cameracommander/hardware/tripod/serial_adapter.py` to recognize `ProgressReply` and refresh the `deadline`
- [ ] T008 [P] [US1] Update `host/src/cameracommander/mock_firmware/server.py` to simulate `PROGRESS` messages
- [ ] T009 [US1] Create integration test `host/tests/integration/test_movement_timeout.py`

---

## Phase 4: User Story 2 - Real-time Movement Progress (P2)

- [ ] T010 [P] [US2] Add `progress_callback` support to `SerialTripodAdapter.move_to` and `_send` in `host/src/cameracommander/hardware/tripod/serial_adapter.py`
- [ ] T011 [US2] Update `_run_repl` in `host/src/cameracommander/cli/commands/tripod.py` to use a callback that overwrites a single line in-place

---

## Phase 5: User Story 3 - Estimated Time of Completion (P3)

- [ ] T012 [P] [US3] Implement `ESTIMATE` emission in firmware at the start of `M` command
- [ ] T013 [P] [US3] Update `SerialTripodAdapter` to capture `EstimateReply` and pass it to the progress callback
- [ ] T014 [US3] Update `tripod` CLI to display the estimate from the firmware

---

## Phase 6: Edge Cases & Polish

- [ ] T015 [P] Implement `ERR AlreadyAtTarget` in firmware and handle in host
- [ ] T016 [P] Implement `ERR MotorStall` in firmware and handle in host
- [ ] T017 [P] Verify `X` (Emergency Stop) works during motion
- [ ] T018 Run all host and firmware tests
