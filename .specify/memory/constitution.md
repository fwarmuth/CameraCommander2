# CameraCommander2 Constitution

## Application Goal

CameraCommander2 is a motorized camera orchestration system. It controls a two-axis (pan + tilt) stepper motor tripod head and a DSLR/mirrorless camera to execute automated sequences:
1. **Timelapse Photography**: Interpolated motion between start and target angles with capture-settle-move cycles.
2. **Video/Movie Panning**: Smooth, continuous pan/tilt motion while the camera is in video recording mode.

The system is built as a headless host application running on Linux (e.g. Raspberry Pi), exposing a clean API for a fully decoupled web-based interface.

## System Components

The system is composed of three distinct, independently versioned components:

1. **Firmware** — Runs on an ESP-class microcontroller; the current hardware uses an ESP8266, and the rewrite must remain compatible with ESP8266 while allowing ESP32 as a target. It controls stepper motors for pan and tilt and exposes a serial command protocol.
2. **Host Application (Headless)** — Python 3.12+ process on a Linux host; controls the camera via gphoto2; orchestrates sequences (timelapse or video); manages sessions; exposes a clean API (REST/WebSocket); and provides a CLI for scriptable operation without the web UI.
3. **Web UI (Client)** — Independent browser-based application that communicates with the Host Application via its API for configuration, live manual control, planning, and monitoring.

## Core Principles

### I. System Boundary Contracts
Each component boundary is governed by an explicit, versioned contract. The firmware exposes a versioned serial protocol. The host app is **strictly headless** and exposes a public API that the UI consumes. No component may assume knowledge of another component's internals.

### II. Hardware Abstraction (Mock-First)
Every hardware dependency — camera (gphoto2), tripod (serial/ESP8266/ESP32) — must have a fully functional software mock or emulator. The tripod mock must expose the same socket/serial communication behavior as the ESP interface. The camera mock must support development and automated testing without keeping a physical camera powered on. All development and testing must be achievable without physical hardware attached.

### III. Configuration-Driven
All session parameters (camera settings, motion start/target, sequence cadence, output options) must be fully expressible in a portable, version-controlled configuration file (YAML or equivalent). The UI generates and validates configs. Configs must remain usable independently of the UI.

### IV. Spec-Driven Development
Features begin as written specifications. No implementation work starts without an approved spec. Plans and task lists gate code; implementation details are derived from specs, not the other way around.

### V. Simplicity and No Premature Abstraction
Implement only what the current spec requires. Target Linux-based systems exclusively to minimize OS-specific complexity. Use Python as the primary language for the host application.

### VI. Observability
The system must surface its own state clearly: job progress, hardware connection status, current camera and tripod settings. This applies both in the web UI and via structured logs from the host application.

### VII. Motion Safety and Calibration
The system must model mechanical limits explicitly before executing motion. Pan may be treated as mechanically unlimited unless a future hardware revision defines limits. Tilt must enforce configurable safe bounds because the camera lens, body, and cables can collide or snag. Calibration/homing state, current position assumptions, driver enable/disable state, and emergency stop behavior must be visible to operators and respected by automated sequences.

## Minimum Feature Requirements

**Camera Control**
- Apply camera settings: ISO, aperture, shutter speed, white balance.
- Trigger capture (still) and retrieve images.
- **Video Mode**: Start/stop movie recording.
- Support live-view / focus aids.

**Tripod Control**
- Absolute pan and tilt positioning (degrees).
- Status query (current angles, driver state).
- Manual nudge (step-level control from UI).
- **Motion Profiles**: Support both discrete "Shoot-Move-Shoot" (timelapse) and smooth "Continuous" motion (video).
- Emergency stop.
- Configurable tilt safety limits and calibration state checks before automated motion.

**CLI**
- Provide command-line workflows for core operations: camera snapshot/test capture, tripod/manual control, timelapse execution, configuration validation, and mock/development mode startup.
- CLI workflows must use the same host application services and configuration model as the API/UI.

**Timelapse Sequencing**
- Configurable: total frames, interval, settle time, start/target angles.
- Interpolated motion: tripod moves between frames.
- Capture → settle → move cycle per frame.

**Video Panning**
- Execute a smooth pan/tilt motion over a specific duration while the camera records.
- Synchronized start/stop of motion and recording.

**Output & Post-Processing**
- Images stored to a configurable output directory with metadata.
- Video assembly from captured timelapse frames (ffmpeg).
- Session library: browseable history of completed runs.

**Web UI**
- **Decoupled Architecture**: Communicates exclusively via the Host API.
- Live control: camera settings, manual tripod nudge, focus helpers.
- Planner: configure and launch timelapse or video jobs.
- Monitor: in-flight job progress, hardware status.
- Library: browse past sessions, reload settings.

**Mock / Development Mode**
- Mock camera adapter (no gphoto2 required).
- Mock firmware server (TCP socket, speaks the same serial protocol as the ESP8266/ESP32).
- Development mode must allow both camera and tripod mocks to be used together so end-to-end workflows can run without physical hardware.

## Hardware Scope

- **Firmware**: ESP8266 currently installed; ESP32 is an allowed future target. Firmware controls A4988/TMC stepper drivers for a two-axis (pan + tilt) head.
- **Host**: Linux host (e.g. Debian/Raspberry Pi OS) with Python 3.11+, gphoto2, ffmpeg.

## Governance

This constitution supersedes all other project-level guidance. Amendments require updating this document and reviewing all dependent artifacts.

**Version**: 1.1.0 | **Ratified**: 2026-05-09 | **Last Amended**: 2026-05-09
