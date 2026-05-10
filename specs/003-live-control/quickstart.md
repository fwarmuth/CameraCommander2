# Quickstart — Live Control Verification

## 1. Local Testing (Mock)

1. Start mock firmware: `uv run cameracommander mock-firmware --port 9999`
2. Start host in mock mode: `uv run cameracommander serve --mock --port 8000`
3. Open browser: `http://localhost:8000`
4. Go to **Live Control**.
5. Toggle **Motors: ON**.
6. Click Nudge buttons and verify position updates.

## 2. Hardware Verification (Pi)

1. Ensure Canon camera and ESP tripod are connected.
2. Verify `~/.cameracommander/host.yaml` exists with correct ports.
3. Start server: `uv run cameracommander serve --port 8000 --host 0.0.0.0`
4. Open UI from laptop.
5. In **Live Control**, search for "ISO" and change it.
6. Trigger **Test Capture** and verify high-res image appears.
