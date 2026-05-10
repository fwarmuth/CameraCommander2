# Feature Specification: Live Control & Setup Assist

**Feature Branch**: `003-live-control`
**Created**: 2026-05-09
**Status**: Draft
**Input**: User description: "The live Control tab is made to setup the camera settings for the current scenery. For that the user needs to be able to control the most important camera capture settings like, iso, exposure time, aperature, white-balance and lens focus. To do that in a reasonable we need two apporaches. First a live view, which is meant to give the user instant feedback about lens focus settings (they need to be done via the webinterface as well) and the tripod positions/poses. The other approach is meant for detailed capture setup, for example live view with long exposure times makes now sense, for that a real test snapshop needs to be taken and inspected closely (with zoom for example)."

## User Scenarios & Testing *(mandatory)*

### User Story 1: Framing and Focusing (Priority: P1)
As a photographer, I want to see a live preview and manually nudge the tripod and adjust lens focus so that I can perfectly compose and focus my shot before starting a long sequence.

**Why this priority**: Crucial for any successful shoot. Composition and focus are the first steps of the workflow.

**Independent Test**:
1. Open the Live Control tab.
2. Observe the live view stream.
3. Use nudge controls for Pan/Tilt and see immediate movement.
4. Adjust lens focus via UI buttons and observe focus change in the stream.

### User Story 2: Fine-Tuning Exposure (Priority: P1)
As a photographer, I want to adjust ISO, aperture, and shutter speed, and then take a full-resolution test capture to verify that my exposure settings are correct for the current lighting.

**Why this priority**: Prevents unusable captures due to exposure error, which is especially important for timelapses where lighting changes.

**Independent Test**:
1. Set specific exposure parameters (e.g., ISO 400, 1/100s, f/8).
2. Click "Test Capture".
3. View the resulting image in a high-resolution viewer with zoom capability.
4. Verify the exposure matches expectations.

### User Story 3: Long Exposure Verification (Priority: P2)
As a photographer shooting in low light, I want to take a test capture with a long exposure time (e.g., 30s) and inspect the noise and detail, as the live view will be too dark or noisy to be useful.

**Why this priority**: Essential for night/astrophotography timelapses.

**Independent Test**:
1. Set a long exposure time (e.g., 2 seconds).
2. Trigger test capture.
3. Wait for capture completion and download.
4. Inspect the image for detail and exposure balance.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a "Live Control" view with a real-time MJPEG preview stream.
- **FR-002**: System MUST allow manual tripod control (Nudge Pan/Tilt) from the Live Control view.
- **FR-003**: System MUST allow lens focus adjustment (Focus In/Out) via the web interface.
- **FR-004**: System MUST allow modification of ISO, Shutter Speed, Aperture, and White Balance.
- **FR-005**: System MUST provide a "Test Capture" action that triggers a full-resolution snapshot.
- **FR-006**: System MUST provide a high-resolution image viewer for test captures, including a zoom/magnification feature for focus/detail inspection.
- **FR-007**: System MUST automatically stop the live view stream when a high-resolution capture (snapshot or sequence frame) is in progress to prevent hardware I/O conflicts.
- **FR-008**: System MUST display the tripod's current position (Pan/Tilt) relative to home in the Live Control view.

### Key Entities

- **Quick Settings**: A subset of camera configuration (ISO, Shutter, Aperture, WB, Focus) optimized for interactive setup.
- **Test Capture**: A non-persisted (transient) high-resolution image used only for verification.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Live view stream latency is under 500ms on a standard local network.
- **SC-002**: Lens focus adjustments are reflected in the live view within 200ms of button release.
- **SC-003**: Test capture thumbnail is displayed within 2 seconds of the exposure completing.
- **SC-004**: Users can zoom into a test capture to at least 100% (1:1 pixel) magnification.

## Assumptions

- The camera supports remote focus control via the gphoto2 driver (not all lenses/cameras support this).
- The camera provides a usable live view stream via gphoto2.
- The web browser has sufficient memory to handle high-resolution image inspection.

## Constraints

- Only one hardware command (capture, move, focus) can be issued at a time due to serial/USB protocol limitations.
