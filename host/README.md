# host/

Headless Python host application for CameraCommander2: orchestrates timelapse
and video-pan sequences, exposes a REST + WebSocket API consumed by the
decoupled web SPA, and ships an equivalent CLI.

Targets Python 3.12+ on Linux (Raspberry Pi Zero 2 W is the binding deployment
target). All workflows run end-to-end against the bundled mock camera and mock
firmware so the system is testable without hardware.

## Quick start (mock-only, no hardware)

```bash
cd host
uv sync
uv run cameracommander mock-firmware --port 9999 &
uv run cameracommander serve --mock --port 8000
# In another terminal:
uv run cameracommander timelapse --mock examples/timelapse_mock.yaml
```

See [`specs/001-core-system/quickstart.md`](../specs/001-core-system/quickstart.md)
for the full walk-through (mock laptop run, Pi deployment, smoke tests).

## Layout

```
src/cameracommander/
├── core/          # Pydantic models, config loader, errors, logging
├── hardware/      # CameraAdapter + TripodAdapter Protocols, real + mock impls
├── services/      # safety, timelapse, video_pan, jobs, sessions, post_process
├── api/           # FastAPI factory, routes, WebSocket fan-out
├── cli/           # Typer entrypoints
├── persistence/   # filesystem-backed session library
└── mock_firmware/ # in-process TCP server with line-protocol parity
tests/
├── contract/      # OpenAPI + firmware-protocol byte-for-byte checks
├── integration/   # full timelapse + video-pan against mocks
└── unit/          # pure logic
```
