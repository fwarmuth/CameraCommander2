# Testing and Deployment Guide

This guide walks you through the transition from a "safe" mock environment on your laptop to a live deployment on your Raspberry Pi and ESP board hardware.

---

## Part 1: The "Lab" Phase (Testing with Mocks)

Before touching any hardware, verify the entire stack on your laptop using the built-in mocks.

1.  **Bootstrap the Host:**
    ```bash
    cd host
    uv sync
    ```

2.  **Build the Web UI (Laptop Only):**
    The Pi is too slow for building; always do this on your laptop.
    ```bash
    cd ../web
    npm ci
    npm run build   # This creates web/dist/
    ```

3.  **Run the Mock Stack:**

    There are two ways to run the mock environment. **Choose one:**

    **Option A: The "One-Command" Setup (Simpler)**
    This command starts the host, a mock camera, *and* an internal mock firmware server all at once.
    \`\`\`bash
    cd host
    uv run cameracommander serve --mock --port 8000
    \`\`\`

    **Option B: The "Separate Terminals" Setup (More Control)**
    Use this if you want to see the firmware logs separately or customize the mock motor speed.
    *   **Terminal A (Mock Firmware):**
        \`\`\`bash
        cd host
        uv run cameracommander mock-firmware --port 9999 --deg-per-second 60
        \`\`\`
    *   **Terminal B (Host):**
        \`\`\`bash
        cd host
        uv run cameracommander serve --mock-camera --mock-tripod --port 8000
        \`\`\`

**Validation:** In both cases, open \`http://localhost:8000\`, go to **Live Control**. You should see \`connected (mock)\` and be able to "move" the virtual motors.


---

## Part 2: The "Hangar" Phase (Hardware Setup & CLI Testing)

Now, connect your ESP board (ESP8266 or ESP32) to your laptop to flash it and perform a "smoke test" via the CLI.

0. **Install PlatformIO:**
    \`\`\`bash
    uv python install 3.11
    uv tool install --python 3.11 platformio
    \`\`\`

    And if using WSL, pass through your USB serial device:
    \`\`\`bash
    usbipd list
    usbipd bind --busid <busid>
    usbipd attach --wsl --busid <busid>
    \`\`\`

1.  **Flash the Firmware:**
    Choose the command that matches your hardware:

    **For ESP8266 (NodeMCU):**
    \`\`\`bash
    cd firmware
    pio run -e nodemcuv2 --target upload
    \`\`\`

    **For ESP32:**
    \`\`\`bash
    cd firmware
    pio run -e esp32 --target upload
    \`\`\`

2.  **Verify via Serial Monitor:**
    \`\`\`bash
    pio device monitor
    \`\`\`
    *   Press the reset button on the ESP. You should see a boot banner like \`CAMERACOMMANDER v1.0.x\`.
    *   Type \`V\` and press enter; it should respond with \`VERSION 1.0.x\`.

3.  **Interactive Tripod Test (Laptop -> Real ESP):**
    Identify your serial port (e.g., \`/dev/ttyUSB0\` or \`/dev/cu.usbserial-xxx\`). The CLI requires a configuration file to know which port to use.

    Create a temporary file named \`test-rig.yaml\`:
    \`\`\`yaml
    metadata:
      name: "rig-test"
    tripod:
      serial:
        port: "/dev/ttyUSB0"  # <-- Change this to your port
    camera:
      model_substring: "MOCK"
    safety:
      tilt_min_deg: -45
      tilt_max_deg: 45
    output:
      output_dir: "./output"
    sequence:
      total_frames: 2
      interval_s: 1
      settle_time_s: 0
      start: { pan_deg: 0, tilt_deg: 0 }
      target: { pan_deg: 0, tilt_deg: 0 }
    \`\`\`

    Then run the tripod REPL:
    \`\`\`bash
    cd host
    uv run cameracommander tripod test-rig.yaml
    \`\`\`
    *   Type \`e\` to enable motors (listen for the click/hum).
    *   Type \`1 0\` to move Pan 1 degree.
    *   Type \`0 1\` to move Tilt 1 degree.
    *   Type \`s\` to see the current status.
    *   Type \`d\` to disable motors.
    *   Type \`q\` to quit.

---

## Part 3: The "Field" Phase (Deploying to Raspberry Pi)

Finally, move the "Brain" (the Python host) to your Raspberry Pi.

1.  **Prepare the Pi:**
    Ensure Python 3.12 and `uv` are installed. Add your user to the `dialout` group to access the serial port:
    ```bash
    sudo usermod -aG dialout $USER
    # Log out and back in for this to take effect!
    ```

2.  **Deploy from Laptop to Pi:**
    Use `rsync` to push the code and the pre-built web bundle.
    ```bash
    # Run this from your LAPTOP root directory
    rsync -avz --delete \
      --exclude '.venv' --exclude 'node_modules' \
      ./host/ ./web/dist \
      pi@cameracmd.local:/opt/cameracommander/
    ```

3.  **Configure on Pi:**
    Create a config file at `~/.cameracommander/host.yaml`:
    ```yaml
    camera:
      model_substring: "EOS" # Or whatever your camera identifies as
    tripod:
      serial:
        port: "/dev/ttyUSB0"
    session_library_root: "~/.cameracommander/sessions"
    ```

4.  **Run on Pi:**
    ```bash
    cd /opt/cameracommander/host
    uv sync
    uv run cameracommander serve --port 8000
    ```

## Summary of Small Steps
1.  **Mocks:** Verify logic on laptop.
2.  **Flash:** ESP board is alive? (\`pio device monitor\`)
3.  **REPL:** Can I move a motor via CLI? (\`uv run cameracommander tripod\`)
4.  **Validate:** Is my YAML job file correct? (\`uv run cameracommander validate my-job.yaml\`)
5.  **Deploy:** Sync to Pi and run \`serve\`.
