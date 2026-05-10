# Data Model: Movement Feedback and Increased Timeout

## Entities

### ProgressReply (Protocol)
Represents an intermediate position report from the firmware.
- **pan_deg**: float (absolute pan in degrees)
- **tilt_deg**: float (absolute tilt in degrees)

### EstimateReply (Protocol)
Represents the firmware's calculation of move duration.
- **seconds**: float (expected time to complete the move)

### MoveResult (Host Service Layer)
Updated to include estimated vs actual duration.
- **pan_deg**: float (final absolute pan)
- **tilt_deg**: float (final absolute tilt)
- **estimated_duration_s**: float (from EstimateReply)
- **actual_duration_s**: float (measured by host)

## State Transitions

### Firmware Motion State Machine
1. **Idle**: Motors stopped, listening for commands.
2. **Receiving Move**: `M` command received.
   - Calculate duration → Emit `ESTIMATE`.
   - If at target → Emit `ERR AlreadyAtTarget`, return to **Idle**.
   - Start motors → Transition to **Moving**.
3. **Moving**: Motors running.
   - Every 200ms → Emit `PROGRESS`.
   - `X` received → Stop motors, emit `OK STOP`, return to **Idle**.
   - `S` received → Emit `STATUS`, remain in **Moving**.
   - Target reached → Transition to **Settling**.
   - Stall detected → Emit `ERR MotorStall`, return to **Idle**.
4. **Settling**: Motors stopped, waiting for vibrations to dampen.
   - After `SETTLE_DELAY_MS` → Emit `DONE`, return to **Idle**.
