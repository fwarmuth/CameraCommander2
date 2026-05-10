# Research: Movement Feedback and Increased Timeout

## Decision 1: Progress Message Format
- **Decision**: Use `PROGRESS <pan> <tilt>` (e.g., `PROGRESS 10.000 -5.000`).
- **Rationale**: Consistent with the `STATUS` message format, making it easy to parse and integrate into the existing protocol logic.
- **Alternatives considered**: `P <pan> <tilt>` (rejected as less descriptive).

## Decision 2: Firmware Progress Frequency
- **Decision**: Emit `PROGRESS` messages at 5Hz (every 200ms) during motion.
- **Rationale**: 5Hz provides smooth UI updates without overwhelming the serial buffer or consuming excessive CPU cycles on the ESP8266/ESP32.

## Decision 3: Host Timeout Watchdog
- **Decision**: The host serial adapter will refresh its command timeout deadline every time a `PROGRESS` message is received.
- **Rationale**: This "touches" the watchdog, allowing movements of any length to complete as long as the tripod is actively reporting progress, solving the `MotorStallError` bug.

## Decision 4: Non-blocking Firmware Architecture
- **Decision**: Refactor the firmware movement loop into a non-blocking state machine.
- **Rationale**: Necessary to satisfy the project constitution's safety requirements by ensuring the Emergency Stop (`X`) and Status (`S`) commands remain responsive while the motors are running.

## Decision 5: Duration Estimation Source
- **Decision**: The firmware will calculate the move duration estimate and emit an `ESTIMATE <seconds>` message at the start of a move.
- **Rationale**: The firmware has the most accurate information regarding its internal speed, acceleration, and microstepping parameters.

## Decision 6: UI Feedback Format
- **Decision**: The CLI will use a single, self-overwriting line (`\r`) to display position and time remaining.
- **Rationale**: Provides real-time feedback without polluting the terminal scrollback, which is critical for a clean manual control experience.

## Decision 7: Movement Error States
- **Decision**: Introduce `ERR AlreadyAtTarget` and `ERR MotorStall`.
- **Rationale**: Improves protocol robustness by allowing the host to distinguish between redundant commands and physical hardware failures.
