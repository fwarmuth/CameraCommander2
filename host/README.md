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

## Full Mock Workflow

Terminal A:

```bash
cd host
uv run cameracommander mock-firmware --port 9999 --deg-per-second 60
```

Terminal B:

```bash
cd host
uv run cameracommander serve --mock --port 8000
```

Terminal C:

```bash
cd host
uv run cameracommander timelapse --mock examples/timelapse_mock.yaml
uv run cameracommander pan --mock examples/video_pan_mock.yaml
```

The same mock stack is available through the web UI at `http://localhost:8000`
after building `../web/dist/`. The workflow mirrors quickstart §2.

## First Rig Deployment

Use `examples/host.yaml` as the Pi-side template. Copy it to
`~/.cameracommander/host.yaml`, set `tripod.serial.port` to the ESP serial
device, and start cautiously:

```bash
uv run cameracommander validate examples/timelapse_mock.yaml
uv run cameracommander tripod ~/.cameracommander/host.yaml
```

In the tripod REPL, start with `s`, `e`, tiny relative moves such as `1 0`, and
`stop`. Keep USB power stable and verify the firmware banner reports protocol
major `1` before automated jobs.

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
