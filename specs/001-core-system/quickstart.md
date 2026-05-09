# Quickstart — CameraCommander2

**Branch**: `001-core-system` | **Date**: 2026-05-09
**Audience**: developers cloning the repo for the first time, on a laptop or directly on the Pi Zero 2 W.

This walks you through (a) running the full stack against mocks on your laptop and (b) deploying to the Pi with real hardware.

---

## 1. Prerequisites (Laptop)

- Python 3.12+ (managed via `uv`)
- Node.js 20+ (for building the Web UI)
- `ffmpeg` (for video assembly)

```bash
# Install uv if missing
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and enter
git clone <repo-url> CameraCommander2
cd CameraCommander2
```

---

## 2. Mock end-to-end shoot (laptop, no hardware)

There are two ways to run the mock environment.

### Option A: The "One-Command" Setup (Simpler)

This command starts the host, a mock camera, *and* an internal mock firmware server all at once.

```bash
cd host
uv run cameracommander serve --mock --port 8000
```

### Option B: The "Separate Terminals" Setup (More Control)

Use this if you want to see the firmware logs separately or customize the mock motor speed.

**Terminal A — mock firmware**
```bash
cd host
uv run cameracommander mock-firmware --port 9999 --deg-per-second 60
```

**Terminal B — host with mock camera**
```bash
cd host
uv run cameracommander serve --mock-camera --mock-tripod --port 8000
```

**In the UI (http://localhost:8000):**
1. Open **Live Control** → confirm camera shows `connected (mock)`, tripod shows `connected v1.0.1`.
2. Click **Set current as home** → calibration goes from `unknown` to `homed`.
3. Open **Planner** → fill in the form (or paste the example from `contracts/config-schema.md`) → **Launch timelapse**.
4. Open **Monitor** → watch progress; the WebSocket pushes updates every captured frame.
5. Open **Library** → after completion, the new session appears with frames + assembled video.

---

## 3. Building the Web UI

The Pi serves static files from `web/dist/`. You must build them once on your laptop before deployment.

```bash
cd web
npm ci
npm run build
```

---

## 4. Deploying to the Pi Zero 2 W

### 4.1 Syncing the code

```bash
# From laptop root
rsync -avz --delete \
  --exclude '.venv' --exclude 'node_modules' \
  ./host/ ./web/dist \
  pi@cameracmd.local:/opt/cameracommander/
```

### 4.2 Initial run

```bash
ssh pi@cameracmd.local
cd /opt/cameracommander/host
uv sync                                # ARM wheels installed automatically
uv run cameracommander serve --port 8000 --config ~/.cameracommander/host.yaml
```

The `host.yaml` lives in `~/.cameracommander/`:

```yaml
camera:
  model_substring: "EOS"
tripod:
  serial:
    port: "/dev/ttyUSB0"
session_library_root: "~/.cameracommander/sessions"
```

---

## 5. Flashing the ESP firmware

```bash
cd firmware
pio run                       # build for nodemcuv2 (ESP8266) by default
pio run -e esp32              # alternate target
pio run -e nodemcuv2 --target upload  # flash ESP8266
pio run -e esp32 --target upload      # flash ESP32
pio device monitor             # watch the boot banner and protocol traffic
```

The firmware emits the boot banner described in `contracts/firmware-protocol.md`. Once the host connects, you should see the host issue `V` and receive `VERSION 1.0.x`.

---

## 6. Smoke Tests

Validate your environment and hardware adapters without the full UI.

```bash
cd host
# Unit tests
uv run pytest tests/unit/

# Contract tests (requires ffmpeg)
uv run pytest tests/contract/

# Integration tests (starts mock firmware in background)
uv run pytest tests/integration/
```
