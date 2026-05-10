# Quickstart: Movement Feedback

## Overview
This feature adds real-time feedback for tripod movements.

## Usage (CLI)
When you issue a movement command in the `tripod` CLI, you will now see a progress indicator:

```bash
uv run cameracommander tripod test-rig.yaml
# ...
tripod: to 45 10
Moving to pan=45.000, tilt=10.000...
[====================] 100% (pan=45.000, tilt=10.000)
Done.
```

## Protocol Updates
The firmware now emits `PROGRESS <pan> <tilt>` every 200ms during moves.
The host extends its timeout deadline on every `PROGRESS` message.
