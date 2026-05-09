# Feature Specification: CameraCommander2 — Core System

**Feature Branch**: `001-core-system`
**Created**: 2026-05-09
**Status**: Draft
**Input**: Full system rewrite of CameraCommander — motorized camera orchestration for timelapse and video panning

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Configure and Execute a Timelapse (Priority: P1)

A photographer wants to create a timelapse of a landscape at dawn. They open the web UI, set camera exposure parameters (ISO, shutter speed, aperture), define a start and target angle for the pan/tilt head, set the number of frames and interval, then launch the sequence. The system automatically moves the tripod head, captures each frame, and assembles the frames into a video file. The photographer can monitor progress in the UI and retrieve the final video from the session library.

**Why this priority**: This is the primary use case the system exists to solve. Without automated timelapse capture with synchronized motion, the system has no purpose.

**Independent Test**: Fully testable with mock camera and mock tripod. The sequence starts, frames are captured at the correct interval, the tripod moves between frames, metadata is written per frame, and a video file is produced at the end.

**Acceptance Scenarios**:

1. **Given** a valid configuration file with 10 frames, 10 s interval, start pan 0° / tilt 0°, target pan 60° / tilt 20°, **When** the user launches the timelapse, **Then** the system captures 10 frames each separated by the configured interval, moves the tripod incrementally between frames, writes metadata alongside each image, and assembles a final video.
2. **Given** a running timelapse sequence, **When** the operator requests an emergency stop, **Then** the sequence halts immediately after the current capture cycle completes, motion stops, and partial output is preserved.
3. **Given** a configuration with a tilt target that exceeds the configured safe limit, **When** the user attempts to launch the sequence, **Then** the system rejects the configuration with a clear error before any motion occurs.
4. **Given** the camera disconnects mid-sequence, **When** the next capture is attempted, **Then** the system detects the failure, stops the sequence, and reports the hardware fault with the last completed frame count.

---

### User Story 2 — Verify Hardware and Test Camera Settings Before a Shoot (Priority: P2)

Before starting a long unattended timelapse, the operator wants to verify the hardware is connected, check the live view to focus the lens, adjust camera settings, and make test exposures. They also want to manually nudge the tripod to frame the shot.

**Why this priority**: A misconfigured camera or misaligned tripod will ruin an entire sequence. Manual verification and adjustment before launch is essential for reliable results.

**Independent Test**: Testable with physical hardware or mock adapters. Operator can open the live control view, adjust ISO/shutter/aperture, trigger a test capture, see a thumbnail, and nudge the tripod by defined step increments.

**Acceptance Scenarios**:

1. **Given** the hardware is connected, **When** the operator opens the live control view, **Then** current camera settings are displayed and a live-view image is available for focus verification.
2. **Given** the live control view is open, **When** the operator changes ISO and triggers a test capture, **Then** the camera applies the new ISO setting and the captured image is immediately available for review.
3. **Given** the live control view is open, **When** the operator sends a nudge command (e.g. pan right 5°), **Then** the tripod moves by exactly that amount and the current position is updated in the UI.
4. **Given** no camera is connected, **When** the operator opens the live control view, **Then** the UI displays a clear hardware fault indicator and disables capture controls.

---

### User Story 3 — Execute a Video Pan (Priority: P3)

A videographer wants to capture a smooth panning shot while the camera records video. They define a start angle, a target angle, and a total motion duration. The system starts camera video recording and the tripod motion simultaneously, holds the motion for the defined duration, and then stops both.

**Why this priority**: Video panning extends the system's value beyond still timelapse. It shares the hardware platform but requires continuous rather than discrete motion and tight start/stop coordination with video recording.

**Independent Test**: Testable independently by configuring a video pan job with mock hardware. Verifies that motion starts and stops in sync with the recording trigger, that motion is smooth (no discrete steps visible), and that the output video file is saved.

**Acceptance Scenarios**:

1. **Given** a valid video pan configuration (start 0°, target 90°, duration 30 s), **When** the operator launches the job, **Then** camera video recording and tripod motion start within 500 ms of each other, the tripod moves smoothly to the target angle over the defined duration, and recording stops when motion completes.
2. **Given** a running video pan, **When** the operator requests an emergency stop, **Then** both motion and video recording stop immediately and the partial video file is preserved.
3. **Given** a video pan configuration, **When** the tilt component would exceed the safe tilt limit, **Then** the system rejects the configuration before launch.

---

### User Story 4 — Browse the Session Library and Repeat a Run (Priority: P4)

After a shoot, the photographer wants to review completed sessions, inspect the settings used, and either load those settings to repeat the same shot or use them as a starting point for a new configuration.

**Why this priority**: Repeatability and configuration management save time on repeat shoots and support iterative creative workflows. Session history also serves as a log for troubleshooting.

**Independent Test**: Testable independently by examining the session library after a completed run. Operator can list sessions, open one, view its metadata and settings, and export its configuration for re-use.

**Acceptance Scenarios**:

1. **Given** a completed timelapse session, **When** the operator opens the session library, **Then** the session appears with its timestamp, frame count, and output artefacts.
2. **Given** a session in the library, **When** the operator selects "reload settings," **Then** the planner is pre-populated with the exact settings from that session.
3. **Given** a session in the library, **When** the operator requests video assembly for a completed session (where it was not assembled at capture time), **Then** the system assembles the frames into a video and attaches it to the session record.

---

### User Story 5 — Develop and Test Without Physical Hardware (Priority: P5)

A developer working on the system wants to run the full application stack — host app, firmware communication layer, and web UI — without a camera or tripod attached. Mock adapters replace both hardware devices. All timelapse and video pan workflows execute end-to-end.

**Why this priority**: Development on embedded hardware without mocks is slow and brittle. Reliable mock coverage enables fast iteration, CI, and contributes directly to correctness of all other stories.

**Independent Test**: Testable by starting the system in development mode with mock adapters enabled. A full timelapse sequence and a video pan sequence complete successfully without hardware.

**Acceptance Scenarios**:

1. **Given** development mode is active (both camera and tripod mocks enabled), **When** the operator launches a timelapse, **Then** the sequence completes successfully, producing placeholder frames and a final video, with no hardware required.
2. **Given** development mode is active, **When** the operator sends manual tripod nudge commands from the UI, **Then** the mock tripod updates its virtual position and reflects it in status responses.
3. **Given** development mode is active, **When** the mock firmware server is started on a configurable port, **Then** the host application connects to it transparently using the same protocol as real hardware.

---

### Edge Cases

- **Camera powers off or disconnects mid-sequence**: The system detects the failure on the next capture attempt, halts the sequence immediately, preserves all frames captured so far, and reports the fault with the count of completed frames. The operator can assemble a partial video from the library.
- **Motor stall / move timeout**: If a firmware move command does not complete within the expected duration plus a configurable margin, the system treats it as a fault, halts the sequence, and marks calibration state as unknown. Re-homing is required before the next automated run.
- **Disk full during timelapse**: The system checks available disk space before each capture. If the remaining space is insufficient for at least one additional frame (estimated from the average frame size of completed frames, minimum threshold 200 MB), the sequence is halted gracefully with a disk-space warning. All completed frames are preserved.
- **Serial connection lost mid-sequence**: Treated identically to a move timeout — sequence halted, fault reported, calibration state marked unknown. The operator must reconnect and re-home before continuing.
- **Configured interval shorter than actual capture + move time**: The system logs a per-frame timing overrun warning and proceeds to the next capture immediately without artificial delay. It does not skip frames or attempt to "catch up." If more than 20% of frames in a session overran, a persistent session-level warning is attached to the session record.
- **Cold start / no calibration data**: Automated sequences are blocked. The operator must explicitly use the "Set current position as home (0°, 0°)" action. This designates wherever the head is physically pointing as the coordinate origin. No physical limit switches are assumed.
- **Second sequence launched while one is running**: The system rejects the request immediately with a clear "sequence already running" error. The running sequence is unaffected.

---

## Requirements *(mandatory)*

### Functional Requirements

**Camera Control**
- **FR-001**: System MUST allow operators to set camera exposure parameters (ISO, aperture, shutter speed, white balance) before and during a session.
- **FR-002**: System MUST trigger still image capture and transfer captured images to the host storage.
- **FR-003**: System MUST start and stop camera video recording.
- **FR-004**: System MUST provide a live-view image stream for focus and framing verification.

**Tripod Control**
- **FR-005**: System MUST move the pan/tilt head to any specified absolute position (degrees) within defined limits.
- **FR-006**: System MUST report current pan and tilt position and driver enable/disable state on demand.
- **FR-007**: System MUST accept operator nudge commands (discrete step increments) from the UI.
- **FR-008**: System MUST immediately stop all motion on emergency stop command.
- **FR-009**: System MUST enforce configurable tilt safety limits and refuse motion commands that would exceed them.
- **FR-010**: System MUST track and expose calibration/homing state; automated sequences MUST be blocked when the position is unknown (uncalibrated).
- **FR-011**: System MUST support enabling and disabling stepper motor drivers; disabling resets the known position.

**Firmware Protocol**
- **FR-012**: The firmware MUST expose a versioned, human-readable serial command protocol.
- **FR-013**: The firmware MUST support both discrete (shoot-move-shoot) and continuous smooth motion profiles.
- **FR-014**: The firmware MUST report its protocol version on request so the host can detect incompatible firmware.

**Timelapse Sequencing**
- **FR-015**: System MUST execute a timelapse sequence with configurable: total frame count, interval between frames, settle time after each move, start angle, and target angle.
- **FR-016**: System MUST interpolate tripod position linearly between start and target across all frames.
- **FR-017**: System MUST follow a fixed capture → settle → move cycle per frame.
- **FR-018**: System MUST write metadata (timestamp, position, settings) alongside each captured frame.

**Video Panning**
- **FR-019**: System MUST execute a video pan: smooth motion from a start angle to a target angle over a defined duration while the camera records video.
- **FR-020**: System MUST synchronize camera recording start/stop with motion start/stop.

**Output & Post-Processing**
- **FR-021**: System MUST store all captured images in a configurable output directory with a consistent naming scheme.
- **FR-022**: System MUST assemble timelapse frames into a video file with configurable frame rate and format.
- **FR-023**: System MUST maintain a persistent session library with session metadata, configuration, and output artefacts.
- **FR-024**: Users MUST be able to retrieve the configuration from any past session for re-use.
- **FR-025**: Video assembly MUST be triggerable separately from capture (allowing post-capture assembly).

**Configuration**
- **FR-026**: All session parameters (camera, motion, sequence, output) MUST be expressible in a portable, human-readable configuration file.
- **FR-027**: Configuration files MUST be usable independently of the web UI (e.g. via CLI).
- **FR-028**: System MUST validate configuration files and report specific errors before any execution begins.

**Web UI**
- **FR-029**: Web UI MUST communicate with the host application exclusively via its public API; no direct hardware access from the UI layer.
- **FR-030**: Web UI MUST provide a live control view: camera settings, test capture, live-view, manual tripod nudge.
- **FR-031**: Web UI MUST provide a planner: configure and launch timelapse or video pan jobs.
- **FR-032**: Web UI MUST provide a monitor: real-time job progress, hardware connection status, current position.
- **FR-033**: Web UI MUST provide a session library: list, inspect, reload settings, trigger post-processing.

**CLI**
- **FR-034**: System MUST provide CLI commands for: test capture (snapshot), interactive tripod control, timelapse execution, and configuration validation.
- **FR-035**: CLI commands MUST use the same underlying services and configuration model as the web UI and API.

**Fault Handling**
- **FR-036**: System MUST monitor available disk space before each frame capture; if insufficient space remains for at least one additional frame, the sequence MUST halt with a disk-space warning and preserve all completed frames.
- **FR-037**: If a firmware move command does not complete within the expected duration plus a configurable margin, the system MUST halt the sequence, mark calibration state as unknown, and report the fault.
- **FR-038**: If the actual capture-settle-move cycle time exceeds the configured interval, the system MUST proceed to the next frame immediately and log a timing overrun warning; it MUST NOT skip frames or attempt to catch up.
- **FR-039**: System MUST reject a second sequence launch while one is already running, with a clear error that does not affect the running sequence.

**Calibration**
- **FR-040**: System MUST provide a "set current position as home" action that designates the tripod's current physical position as the (0°, 0°) coordinate origin.
- **FR-041**: Automated sequences MUST be blocked and the operator notified when calibration state is unknown.

**Image Handling**
- **FR-042**: The system MUST capture and store images in whatever format the camera is currently configured for (JPEG, RAW, or RAW+JPEG); no format is forced by the system.
- **FR-043**: Timelapse frames MUST be stored with zero-padded sequential filenames (e.g. `frame_0001.jpg`) to ensure correct sort order for assembly and external tools.

**Development & Testing Mode**
- **FR-044**: System MUST provide a mock camera adapter that simulates capture and live-view without physical hardware.
- **FR-045**: System MUST provide a mock firmware server (network socket) that implements the same protocol as the ESP firmware.
- **FR-046**: Mock camera and mock firmware MUST be operable simultaneously for full end-to-end workflow testing without hardware.

---

### Key Entities

- **Session**: A complete recorded run — includes settings, per-frame metadata, raw images, and optionally an assembled video. Identified by a unique ID and creation timestamp.
- **Configuration**: A portable document that fully describes a shoot — camera settings, motion parameters, sequence type, and output options. Can be loaded, saved, exported, and shared.
- **Job**: A running or scheduled sequence (timelapse or video pan) with a lifecycle: pending → running → completed / failed / stopped.
- **Hardware Connection**: Runtime state of camera and tripod links — connected, disconnected, error — surfaced in the UI and API.
- **Calibration State**: Whether the tripod's current position is known (homed/calibrated) or unknown (requires homing before automated motion).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A complete timelapse run (configure → launch → monitor → retrieve output) is achievable without any operator intervention after launch, with output delivered as both individual frames and a compiled video.
- **SC-002**: All core workflows (timelapse, video pan, test capture, tripod control) are executable via configuration file and CLI without opening the web UI.
- **SC-003**: The full system operates in development mode without physical hardware — all end-to-end workflow tests pass using mock adapters.
- **SC-004**: Any hardware fault (camera disconnection, serial loss, driver fault) is detected and surfaced to the operator within 5 seconds.
- **SC-005**: Tilt safety limits are enforced in all modes (manual nudge, automated sequence, video pan) — no motion command can exceed the configured safe range.
- **SC-006**: An operator can locate a past session, inspect its settings, and reload them into the planner in under 60 seconds.
- **SC-007**: Configuration files from one host can be transferred to another host and produce an equivalent run without modification (hardware settings aside).
- **SC-008**: A firmware protocol version mismatch is detected at connection time and reported to the operator before any command is issued.

---

## Assumptions

- The system runs on a Linux host (e.g. Raspberry Pi OS, Debian); no Windows or macOS support is required for the host application or CLI.
- Camera integration uses gphoto2; only gphoto2-compatible DSLR and mirrorless cameras are in scope.
- The tripod hardware uses an ESP8266 or ESP32 microcontroller with A4988 or TMC stepper drivers; this firmware is part of the rewrite scope.
- Video assembly uses ffmpeg installed on the host; users without ffmpeg can capture frames but not assemble video.
- Default assembled video format is H.264 MP4 at 25 fps; both format and frame rate are configurable per session.
- The web UI is served by the host application over the local network; remote access (internet-facing) is out of scope for v1.
- Pan axis is mechanically unlimited and has no configurable limit; only tilt requires configurable safety limits.
- Homing is software-only: "set current position as home" designates the current physical position as 0°/0°. No physical limit switches or endstops are assumed.
- A fixed-position timelapse (no pan/tilt motion, only time-based capture) is supported by setting start and target angles to identical values.
- Single-user operation: no multi-user concurrency, authentication, or role management is required for v1.
- Only one job (timelapse or video pan) may run at a time; concurrent jobs are out of scope.
- Position state is maintained in software (step counting); hardware encoders are not assumed.
- Disk space fault threshold defaults to 200 MB remaining; this value is configurable.
