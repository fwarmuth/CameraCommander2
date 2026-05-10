# Research: Movement Feedback and Increased Timeout

## Decision 1: Progress Message Format
- **Decision**: Use `PROGRESS <pan> <tilt>` (e.g., `PROGRESS 10.000 -5.000`).
- **Rationale**: Follows the `STATUS` message format, making it easy to parse and consistent with existing protocol patterns.
- **Alternatives considered**: `P <pan> <tilt>` (shorter but less descriptive).

## Decision 2: Firmware Progress Emission
- **Decision**: Emit `PROGRESS` every 200ms during moves.
- **Rationale**: 5Hz is enough for smooth UI feedback without overwhelming the serial buffer or CPU on the ESP8266.

## Decision 3: Host Timeout Handling
- **Decision**: `SerialTripodAdapter._send_blocking` will catch `ProgressReply`, call an optional callback, and reset the `deadline`.
- **Rationale**: This "touches" the timeout deadline, allowing the move to continue indefinitely as long as progress is reported. It keeps the core communication loop simple.

## Decision 4: Duration Estimation
- **Decision**: The firmware will calculate the estimate upon receiving `M` and emit `ESTIMATE <seconds>`.
- **Rationale**: The firmware has the most accurate information about speed and acceleration parameters.

## Decision 5: Emergency Stop Handling
- **Decision**: Full refactor of firmware motion logic to be non-blocking.
- **Rationale**: Allows the firmware to remain responsive to `X` (Emergency Stop) and `S` (Status) commands during movement, satisfying safety and observability requirements.

## Decision 6: Error Handling for Moves
- **Decision**: Firmware will emit `ERR AlreadyAtTarget` for redundant moves and `ERR MotorStall` if motion stops prematurely.
- **Rationale**: Provides clear error states to the host, allowing for better user feedback and diagnostics.
