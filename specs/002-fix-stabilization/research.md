# Research: Fix Stabilization

## R001: Missing StatusReport
- **Decision**: Define `StatusReport` in `host/src/cameracommander/hardware/tripod/base.py`.
- **Rationale**: The `SerialTripodAdapter` and several tests depend on this dataclass for granular hardware status reporting. It was likely omitted during the `001-core-system` implementation phase.
- **Data Shape**:
  ```python
  @dataclass(frozen=True)
  class StatusReport:
      pan_deg: float
      tilt_deg: float
      drivers_enabled: bool
  ```

## R002: MoveResult Mismatch
- **Decision**: Align `MoveResult` in `base.py` with the usage in `serial_adapter.py`.
- **Rationale**: `SerialTripodAdapter.move_to` returns `MoveResult(pan_deg, tilt_deg, duration_s)`. The `success` and `error` fields currently in `base.py` are redundant if we use exceptions for failure (which the current implementation does).
- **Updated Data Shape**:
  ```python
  @dataclass(frozen=True)
  class MoveResult:
      pan_deg: float
      tilt_deg: float
      duration_s: float
  ```

## R003: Core Models Corruption
- **Decision**: Fix `host/src/cameracommander/core/models.py` syntax.
- **Rationale**: The `__all__` list and `CaptureResult` definition are mangled, likely due to a failed automated edit.

## R004: CLI Subcommand Registration
- **Decision**: Verify and stabilize lazy imports in \`host/src/cameracommander/cli/main.py\`.
- **Rationale**: The current \`main.py\` uses a mix of lazy and eager imports which may contribute to the \`ImportError\` cascading.

## R005: Missing Protocol Definitions
- **Decision**: Implement missing classes (\`DoneReply\`, \`ErrorReply\`, \`OkReply\`, \`StatusReply\`, \`VersionReply\`) and command functions (\`cmd_drivers\`, \`cmd_microstep\`, \`cmd_move\`, \`cmd_status\`, \`cmd_stop\`, \`cmd_version\`, \`parse_reply\`) in \`host/src/cameracommander/hardware/tripod/protocol.py\`.
- **Rationale**: The \`SerialTripodAdapter\` uses a class-based reply parsing strategy that is not implemented in the current \`protocol.py\`, leading to \`ImportError\` on \`DoneReply\`.

