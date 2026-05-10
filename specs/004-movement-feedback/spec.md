# Feature Specification: Movement Feedback and Increased Timeout

**Feature Branch**: `004-movement-feedback`  
**Created**: 2026-05-10  
**Status**: Draft  
**Input**: User description: "i want to add a new feature/fix an exisitng flaw in the firmware/tripod cli. I want to increase the timeoput for movement commands. If they are to long the tripod cli fails with: ... the movement is happening, but the cli does not wait enough. I also want to have feedback, how long it will take, and or how far the movement it."

## Clarifications

### Session 2026-05-10
- Q: What is the preferred visual format for this feedback in the `tripod` CLI? → A: Minimal: Just overwrite a single line with `pan=XX.X, tilt=YY.Y (ZZs remaining)`
- Q: Should we modify the movement loop to listen for the `X` command? → A: Full Refactor: Change firmware architecture to be fully non-blocking (async).
- Q: Where should the logic for calculating the movement duration estimate reside? → A: Firmware: Calculate on `M` command receipt and send an initial `ESTIMATE <seconds>` reply.
- Q: What should the firmware emit when no physical motion is required? → A: Emit `ERR AlreadyAtTarget` to inform the host no motion will happen.
- Q: If the firmware detects that the motors have stopped before reaching the target, how should it behave? → A: Emit `ERR MotorStall` and stop.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prevent Timeouts for Long Moves (Priority: P1)

As an operator using the `tripod` CLI, I want the system to successfully complete long movements (e.g., 90-degree pans) without crashing or reporting a timeout error, so that I can reliably control the tripod.

**Why this priority**: This is a critical bug fix. The current timeout prevents the tripod from being used for large movements, which is a core feature.

**Independent Test**: Can be tested by issuing a large movement command (e.g., `to 90 0`) and verifying it completes successfully without a `MotorStallError` even if it takes 60 seconds.

**Acceptance Scenarios**:

1. **Given** a connected tripod, **When** I issue a move command that takes 10 seconds, **Then** the CLI should wait for completion and show the final position without error.
2. **Given** a connected tripod, **When** a movement is in progress, **Then** the communication link should remain active to prevent timeout.

---

### User Story 2 - Real-time Movement Progress (Priority: P2)

As an operator, I want to see the current pan and tilt positions while the tripod is moving, so that I have visual confirmation that the command is being executed and can see how close it is to the target.

**Why this priority**: Provides essential feedback for manual control and improves the user experience.

**Independent Test**: Can be tested by watching the CLI output during a move and seeing updating position values.

**Acceptance Scenarios**:

1. **Given** a movement command is issued, **When** the tripod is moving, **Then** the CLI should display the current (pan, tilt) values and estimated time remaining by overwriting a single line in-place.
2. **Given** a movement command is issued, **When** the tripod reaches the target, **Then** the final position is displayed, the line is finalized, and the progress display terminates.

---

### User Story 3 - Estimated Time of Completion (Priority: P3)

As an operator, I want to see an estimate of how long the movement will take, so that I know how long I need to wait.

**Why this priority**: Useful context for the operator, especially for very slow or long movements.

**Independent Test**: Can be tested by checking if the CLI displays a "seconds remaining" or "total duration" estimate when a move starts.

**Acceptance Scenarios**:

1. **Given** a movement command is issued, **When** the move starts, **Then** the CLI shows an estimated duration.

---

### Edge Cases

- **Communication Loss**: If the serial cable is unplugged during a move, the CLI should still detect a timeout eventually (e.g., if no `PROGRESS` message is received for a few seconds) and report a connection error.
- **Emergency Stop**: If `X` (Global Stop) is sent while a move is in progress, the firmware MUST respond immediately, stop the motors, and the CLI should handle the `OK STOP` reply and terminate the progress display gracefully.
- **Redundant Move**: If an `M` command is issued to the current position, the firmware MUST reply `ERR AlreadyAtTarget` and not emit any `ESTIMATE` or `PROGRESS` messages. The CLI should inform the user that no movement was necessary.
- **Motor Stall**: If the firmware detects a motor stall or unexpected stop during motion, it MUST emit `ERR MotorStall` and stop all motion immediately. The host should report this as a critical hardware error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The firmware MUST emit `PROGRESS <pan> <tilt>` messages periodically (at least every 100ms) during a move command.
- **FR-002**: The host protocol parser MUST support `PROGRESS` replies.
- **FR-003**: The host serial adapter MUST handle intermediate `PROGRESS` replies by resetting the command timeout deadline.
- **FR-004**: The host serial adapter MUST allow an optional progress callback for movement commands.
- **FR-005**: The `tripod` CLI MUST display real-time position updates and time-to-completion by overwriting a single line using the progress callback.
- **FR-006**: The firmware MUST calculate and emit an `ESTIMATE <seconds>` message immediately after receiving an `M` command, before motion begins.
- **FR-007**: The system MUST support a movement timeout that is automatically extended as long as progress is being reported.
- **FR-008**: The firmware MUST implement a non-blocking motion state machine to allow processing other commands (like `X` for Emergency Stop) during movement.

### Key Entities *(include if feature involves data)*

- **ProgressReply**: A protocol message containing the current absolute pan and tilt angles in degrees.
- **EstimateReply**: A protocol message emitted by the firmware at the start of a move containing the expected duration in seconds.
- **MoveEstimate**: [DEPRECATED - now handled by EstimateReply]

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Movements up to 180 degrees (taking ~2 minutes) complete without timeout errors.
- **SC-002**: Progress updates are displayed in the CLI with a frequency of at least 5Hz (every 200ms).
- **SC-003**: The reported position in the progress feedback is accurate to within 0.1 degrees of the actual firmware position at that moment.

## Assumptions

- **Firmware Speed**: We assume the firmware moves at a constant speed defined by its configuration, allowing the host to reasonably estimate duration.
- **Single Master**: We assume only one host is controlling the tripod at a time, so progress messages are always related to the last issued command.
- **Backward Compatibility**: Older host versions will ignore the `PROGRESS` messages (treating them as unrecognized/uninteresting lines) but might still timeout if they don't have the logic to extend deadlines. This is acceptable as this feature targets the new host/firmware pair.
