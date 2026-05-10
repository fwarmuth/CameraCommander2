# Feature Specification: Live Control and Planning Assist

**Feature Branch**: `003-live-control`  
**Created**: 2026-05-09  
**Status**: Draft  
**Input**: User description: "I want a live control tab, where the user can find out which settings he needs for a timelapse recording. so i need to have a tripod section to move the tripod, and find out whats the best starting and ending positions. Another aspect is the camera settings. Goal is here that the user gets a live view, to get an rough idea of the scene and focus settings. But also be able to do test captures (real snapshots) to see if the long exposure, aperature and iso settings really fit."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find Tripod Keyframes (Priority: P1)

An operator wants to find the perfect start and end angles for a timelapse pan. They use the nudge controls in the Live Control tab to move the tripod while watching the live view. Once satisfied with a position, they note down the pan/tilt degrees shown in the UI to use in the sequence planner.

**Why this priority**: High. This is the primary method for framing a motion-control shot.

**Independent Test**: Operator can click nudge buttons, see the physical tripod move, and see the position display update in real-time in the web UI.

**Acceptance Scenarios**:

1. **Given** the tripod is homed and drivers are enabled, **When** the operator clicks "Pan +5", **Then** the tripod MUST move 5 degrees and the position display MUST reflect the new angle.
2. **Given** the Live Control tab is open, **When** the operator clicks "Reset Home", **Then** the current physical position MUST become the new (0,0) reference.

---

### User Story 2 - Verify Exposure with Test Captures (Priority: P1)

After framing the shot, the photographer needs to ensure their exposure settings (ISO, Shutter, Aperture) are correct, especially for long exposures. They trigger a "real" snapshot, wait for the download, and inspect the resulting high-res image.

**Why this priority**: High. Prevents wasting hours on a timelapse with incorrect exposure or focus.

**Independent Test**: Trigger a capture from the web UI and verify the image is downloaded and displayed for review.

**Acceptance Scenarios**:

1. **Given** a camera is connected, **When** the operator triggers a "Test Capture", **Then** the system MUST perform a full-res exposure and display the result in the browser.
2. **Given** a test capture is displayed, **When** the operator changes the ISO settings, **Then** a subsequent test capture MUST reflect the exposure change.

---

### User Story 3 - Focus Assist via Live View (Priority: P2)

The operator needs to focus the lens. They use the MJPEG live view stream for a rough compositional overview and real-time feedback while manually focusing or using software focus commands.

**Why this priority**: Medium. Crucial for setup, but secondary to the final high-res verification.

**Independent Test**: Open the Live Control tab and verify the MJPEG stream is visible and updates in real-time.

**Acceptance Scenarios**:

1. **Given** the camera supports live view, **When** the Live Control tab is active, **Then** a continuous video stream MUST be displayed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated "Live Control" tab in the web interface.
- **FR-002**: System MUST display real-time Pan and Tilt angles of the tripod head.
- **FR-003**: System MUST provide nudge controls (incremental Pan/Tilt) and a "Stop" action.
- **FR-004**: System MUST provide a "Set current as home" action for tripod calibration.
- **FR-005**: System MUST display a real-time MJPEG live view stream from the camera.
- **FR-006**: System MUST allow triggering a full-resolution test capture (snapshot).
- **FR-007**: System MUST display the result of the latest test capture for immediate review.
- **FR-008**: System MUST expose critical camera settings (ISO, Aperture, Shutter, WB) in a clearly organized panel.
- **FR-009**: System MUST automatically stop the live view stream when a capture or sequence job is active to avoid hardware conflicts.

### Key Entities

- **Calibration State**: The software-maintained position of the tripod relative to its last home point.
- **Quick Settings**: A curated list of camera parameters required for exposure planning.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tripod position display updates within 500ms of hardware motion completion.
- **SC-002**: Live view stream achieves at least 5 frames per second on the Pi Zero 2 W.
- **SC-003**: Test captures are available for browser review in under 3 seconds after the exposure completes.
- **SC-004**: Settings panel organizes 40+ camera commands into navigable groups (tabs or collapsible sections).

## Assumptions

- Homing is software-only; the user is responsible for ensuring the head is in a safe starting position.
- The camera supports standard gphoto2 preview and capture protocols.
- Network bandwidth is sufficient for an MJPEG stream on the local network.
