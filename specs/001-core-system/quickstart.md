# Quickstart — CameraCommander2

**Branch**: `001-core-system` | **Date**: 2026-05-09
**Audience**: developers cloning the repo for the first time, on a laptop or directly on the Pi Zero 2 W.

This walks you through (a) running the full stack against the mock camera + mock firmware on any Linux laptop, and (b) deploying to a Raspberry Pi Zero 2 W with real hardware.

---

## 0. Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12.x | `pyenv install 3.12` if your distro is older. |
| `uv` | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `pio` (PlatformIO Core) | latest | Only needed to build/flash the ESP firmware. |
| Node.js | 20.x LTS | Only needed to build the web UI bundle (off-device). |
| `ffmpeg` | 6+ | Required for video assembly; `apt install ffmpeg`. |
| `libgphoto2-dev` | latest | Headers for `python-gphoto2`; `apt install libgphoto2-dev`. |

The Pi target uses Raspberry Pi OS Lite (Bookworm). The web UI bundle is **always** built off-device and copied to `web/dist/` before deployment.

---

## 1. Clone and bootstrap (5 min)

```bash
git clone https://github.com/<you>/CameraCommander2.git
cd CameraCommander2
git checkout 001-core-system     # this branch
```

The repo layout (post-implementation):

```
firmware/   host/   web/   hardware/   specs/
```

Bootstrap the host:

```bash
cd host
uv sync                          # creates .venv with pinned deps
uv run cameracommander --version
```

Bootstrap the web UI (laptop only):

```bash
cd ../web
npm ci
npm run build                    # produces web/dist/
```

---

## 2. Mock end-to-end shoot (laptop, no hardware)

There are two ways to run the mock environment.

### Option A: The "One-Command" Setup (Simpler)

This command starts the host, a mock camera, *and* an internal mock firmware server all at once.

\`\`\`bash
cd host
uv run cameracommander serve --mock --port 8000
\`\`\`

### Option B: The "Separate Terminals" Setup (More Control)

Use this if you want to see the firmware logs separately or customize the mock motor speed.

**Terminal A — mock firmware**
\`\`\`bash
cd host
uv run cameracommander mock-firmware --port 9999 --deg-per-second 60
\`\`\`

**Terminal B — host with mock camera**
\`\`\`bash
cd host
uv run cameracommander serve --mock-camera --mock-tripod --port 8000
\`\`\`

**In the UI (http://localhost:8000):**
1. Open **Live Control** → confirm camera shows \`connected (mock)\`, tripod shows \`connected v1.0.1\`.
2. Click **Set current as home** → calibration goes from \`unknown\` to \`homed\`.
3. Open **Planner** → fill in the form (or paste the example from \`contracts/config-schema.md\`) → **Launch timelapse**.
4. Open **Monitor** → watch progress; the WebSocket pushes updates every captured frame.
5. Open **Library** → after completion, the new session appears with frames + assembled video.

CLI-only equivalent (no UI):

```bash
cd host
uv run cameracommander mock-firmware --port 9999 &
MOCK_PID=$!
uv run cameracommander timelapse --mock specs/001-core-system/contracts/examples/timelapse_mock.yaml
kill $MOCK_PID
```

(The example file referenced above lives in `host/examples/timelapse_mock.yaml` after Phase 2; the YAML in `contracts/config-schema.md` is the canonical reference.)

---

## 3. Validating a configuration

```bash
uv run cameracommander validate ./my-shoot.yaml
```

`validate` is offline-only — it reads the file, runs all Pydantic validators and the tilt-window safety check, and exits `0` (valid) or `2` (invalid). Add `--json` to print the canonical document on success.

---

## 4. Real-hardware setup (Pi Zero 2 W)

### 4.1 Pi-side OS prep

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv libgphoto2-dev ffmpeg git
sudo usermod -aG dialout $USER         # serial port access
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="04a9", MODE="0666"' | \
  sudo tee /etc/udev/rules.d/90-camera.rules
sudo udevadm control --reload-rules
```

(Replace the `idVendor` with `lsusb` output for your camera.)

### 4.2 Deploy the host

From your laptop:

```bash
# Build the web bundle and rsync the whole thing.
(cd web && npm ci && npm run build)
rsync -avz --delete \
  --exclude '.venv' --exclude 'node_modules' \
  ./host/ ./web/dist \
  pi@cameracmd.local:/opt/cameracommander/
```

On the Pi:

```bash
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

### 4.3 systemd unit

```ini
# /etc/systemd/system/cameracommander.service
[Unit]
Description=CameraCommander host
After=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/cameracommander/host
ExecStart=/home/pi/.local/bin/uv run cameracommander serve --port 8000
Restart=on-failure
LimitNOFILE=2048

[Install]
WantedBy=multi-user.target
```

`sudo systemctl enable --now cameracommander`. Logs land in `~pi/.cameracommander/logs/host.log`.

---

## 5. Flashing the ESP firmware

```bash
cd firmware
pio run                       # build for nodemcuv2 (ESP8266) by default
pio run -e esp32              # alternate target
pio run --target upload       # flash whatever board is plugged in
pio device monitor             # watch the boot banner and protocol traffic
```

The firmware emits the boot banner described in `contracts/firmware-protocol.md`. Once the host connects, you should see the host issue `V` and receive `VERSION 1.0.x`.

---

## 6. Smoke tests (CI also runs these)

```bash
cd host
uv run pytest tests/integration/test_full_timelapse_mock.py
uv run pytest tests/integration/test_full_video_pan_mock.py
uv run pytest tests/contract/                        # OpenAPI + protocol checks
```

Expected runtime on a laptop: ~30 s. On a Pi Zero 2 W: ~3 min (the integration tests deliberately throttle the mock to realistic speeds).

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `tripod: protocol version mismatch` on connect | Firmware older than `expected_protocol_major` | Flash a compatible firmware build, or temporarily lower `tripod.expected_protocol_major` (not recommended for production). |
| `calibration_required` on job launch | Calibration is `unknown` | Click **Set current as home** in the UI, or `POST /api/tripod/home` from the CLI / curl. |
| `disk_full` halt during a long shoot | Output disk filled below `safety.disk_min_free_bytes` | Bigger SD card, or trim earlier sessions via Library. |
| MJPEG live-view choppy on Pi | gphoto2 preview throughput limit | Reduce camera preview resolution; live-view is capped at 5 fps server-side anyway. |
| `camera_disconnected` during a sequence | USB power glitch or sleep | Ensure the camera's auto-off is disabled; consider a powered USB hub. |
| `motor_stall` mid-move | Torque budget exceeded, mechanical bind, or serial dropout | Reduce the per-frame angular delta, increase `safety.move_timeout_margin_s`, or check the serial cable. |
| `frame_overrun` warnings on every frame | `interval_s` shorter than capture+settle+move | Increase `interval_s` or reduce motion delta per frame. |

---

## 8. Where to look next

- **Spec**: `specs/001-core-system/spec.md`
- **Plan**: `specs/001-core-system/plan.md` (you're here)
- **Decisions**: `specs/001-core-system/research.md`
- **Entities**: `specs/001-core-system/data-model.md`
- **Contracts**: `specs/001-core-system/contracts/`
- **Tasks**: generated next via `/speckit-tasks`
