# Quickstart: Movement Feedback

## Overview
This feature introduces real-time position feedback and automatic timeout extensions for long tripod movements.

## Prerequisites
- Host Application (Python 3.12+)
- Updated Firmware (v1.1.0+) or Mock Firmware

## Manual Control via CLI
Launch the manual control REPL:

```bash
uv run cameracommander tripod test-rig.yaml
```

Issue a large movement:

```text
tripod: to 90 0
Move started (est. 60.0s)...
pan=45.234, tilt=0.000 (30.0s remaining)
```

The position line will update in-place every 200ms until the move completes.

## Emergency Stop
During a long move, press `X` (or use the `stop` command from another terminal/UI) to abort immediately:

```text
tripod: stop
OK STOP
(Motion stopped instantly)
```

## Protocol Examples

### Successful Move
1. **Host**: `M 30.0 0.0\n`
2. **Firmware**: `ESTIMATE 20.0\n`
3. **Firmware**: `PROGRESS 5.0 0.0\n` (repeated)
4. **Firmware**: `DONE\n`

### Emergency Stop
1. **Host**: `M 30.0 0.0\n`
2. **Firmware**: `ESTIMATE 20.0\n`
3. **Firmware**: `PROGRESS 2.0 0.0\n`
4. **Host**: `X\n`
5. **Firmware**: `OK STOP\n`
