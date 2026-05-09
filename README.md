# CameraCommander2

CameraCommander2 is a full rewrite of the camera motion-control stack:

- `firmware/`: ESP8266-first, ESP32-compatible Arduino firmware for the pan/tilt head.
- `host/`: Python 3.12 FastAPI service and Typer CLI for camera, tripod, jobs, and sessions.
- `web/`: Svelte static SPA served by the host after an off-device build.
- `specs/001-core-system/`: Spec Kit spec, plan, contracts, quickstart, and task tracking.

Primary references:

- Spec: `specs/001-core-system/spec.md`
- Plan: `specs/001-core-system/plan.md`
- Quickstart: `specs/001-core-system/quickstart.md`
- API contracts: `specs/001-core-system/contracts/`

## Mock End-to-End Shoot

There are two ways to run the mock environment.

### 1. One-Command Setup (Recommended)

Starts the host, mock camera, and internal mock firmware.

```bash
cd host
uv run cameracommander serve --mock --port 8000
```

### 2. Separate Terminals (for debugging)

Terminal A (Mock Firmware):
```bash
cd host
uv run cameracommander mock-firmware --port 9999 --deg-per-second 60
```

Terminal B (Host):
```bash
cd host
uv run cameracommander serve --mock-camera --mock-tripod --port 8000
```

In both cases, open `http://localhost:8000` to access the UI.

## First Hardware Steps

1. Flash firmware from `firmware/` to the ESP board.
2. Copy `host/examples/host.yaml` to `~/.cameracommander/host.yaml`.
3. Set `tripod.serial.port` to the ESP serial device, for example `/dev/ttyUSB0`.
4. Use `uv run cameracommander tripod ~/.cameracommander/host.yaml` and test tiny moves before automated jobs.

Pan is mechanically unlimited. Tilt is constrained by lens/camera cable clearance and must be set conservatively in each session config.
