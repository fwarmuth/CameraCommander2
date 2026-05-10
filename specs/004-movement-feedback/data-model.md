# Data Model: Movement Feedback and Increased Timeout

## Entities

### ProgressReply (Protocol)
- **pan_deg**: float (current absolute pan position)
- **tilt_deg**: float (current absolute tilt position)

### MoveResult (Host)
- **pan_deg**: float (final position)
- **tilt_deg**: float (final position)
- **duration_s**: float (actual time taken)

## State Transitions
During an `M` command:
1. **Idle**: Waiting for command.
2. **Moving**: Emitting `PROGRESS` messages.
3. **Done**: Emitting `DONE`.
4. **Error**: Emitting `ERR ...` or timing out.
