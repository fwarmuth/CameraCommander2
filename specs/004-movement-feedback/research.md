# Research: Movement Feedback and Increased Timeout

## Decision 1: Progress Message Format
- **Decision**: Use `PROGRESS <pan> <tilt>` (e.g., `PROGRESS 10.000 -5.000`).
- **Rationale**: Follows the `STATUS` message format, making it easy to parse and consistent with existing protocol patterns.
- **Alternatives considered**: `P <pan> <tilt>` (shorter but less descriptive).

## Decision 2: Firmware Progress Emission
- **Decision**: Emit `PROGRESS` every 200ms during the blocking `move_absolute` loop.
- **Rationale**: 5Hz is enough for smooth UI feedback without overwhelming the serial buffer or CPU on the ESP8266.
- **Implementation**: Use `millis()` to track the last emission time within the `while` loop.

## Decision 3: Host Timeout Handling
- **Decision**: `SerialTripodAdapter._send_blocking` will catch `ProgressReply`, call an optional callback, and reset the `deadline`.
- **Rationale**: This "touches" the timeout deadline, allowing the move to continue indefinitely as long as progress is reported. It keeps the core communication loop simple.
- **Alternatives considered**: Calculating a huge fixed timeout upfront. Rejected because it doesn't provide the requested feedback.

## Decision 4: Duration Estimation
- **Decision**: The host will estimate duration as `max(abs(delta_pan), abs(delta_tilt)) / ESTIMATED_SPEED`.
- **Rationale**: Gives the user a rough idea of how long to wait. `ESTIMATED_SPEED` will be set to a conservative 1.0 deg/s for the UI (actual default is ~1.5 deg/s).
