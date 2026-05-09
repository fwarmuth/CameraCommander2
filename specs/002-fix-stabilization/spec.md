# Feature Specification: Fix Stabilization

**Feature Branch**: `002-fix-stabilization`  
**Created**: 2026-05-09  
**Status**: Draft  
**Input**: User description: "I need to create a fix branch, because right now its in a state where it can not be launched. uv run cameracommander serve --port 8000 --host 0.0.0.0 ImportError: cannot import name 'StatusReport' from 'cameracommander.hardware.tripod.base'. I want this to be a Collection point for errors... lets start with this one. I guess there will be more following."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fix Startup ImportError (Priority: P1)

A developer or operator attempts to launch the CameraCommander host application using the `serve` command, but the application crashes immediately due to a missing import (`StatusReport`). The operator wants the application to launch successfully so they can use the web interface and manual controls.

**Why this priority**: High. This is a "blocker" bug. Without the ability to start the server, the entire system is unusable.

**Independent Test**: Can be fully tested by running `uv run cameracommander serve --mock` and verifying the process starts without Python tracebacks and reaches the "Uvicorn running" state.

**Acceptance Scenarios**:

1. **Given** the current codebase with the broken import, **When** `uv run cameracommander serve` is executed, **Then** the application MUST NOT crash with an `ImportError` for `StatusReport`.
2. **Given** the fix is applied, **When** the server starts, **Then** the hardware adapters SHOULD initialize correctly (mock or real) based on the provided configuration.

---

### User Story 2 - Stabilize and Validate Core Imports (Priority: P2)

As a developer, I want to ensure that all core modules (API, CLI, Hardware) are correctly linked and that no other hidden `ImportError` or `ModuleNotFoundError` issues exist in the recently rewritten core system.

**Why this priority**: Medium. Ensures that the fix for US1 isn't just a "whack-a-mole" patch and that the system is structurally sound for the next phase of deployment.

**Independent Test**: Can be tested by running the full test suite (`pytest`) and verifying that the test collection phase succeeds without import errors.

**Acceptance Scenarios**:

1. **Given** the fix branch, **When** `uv run pytest` is executed, **Then** all tests SHOULD be collected and executed without encountering module-level crashes.

---

### User Story 3 - Collection Point for Deployment Errors (Priority: P3)

As an operator deploying to the Raspberry Pi, I want a dedicated path to record and resolve unexpected environment-specific or runtime errors that weren't caught during mock-based development.

**Why this priority**: Medium. Captures the "collection point" requirement from the user.

**Independent Test**: Success is defined by the resolution of at least one new error discovered during live deployment.

**Acceptance Scenarios**:

1. **Given** a new error found on the Pi, **When** reported in this branch, **Then** a corresponding fix MUST be implemented and verified.

---

### Edge Cases

- **Missing dependencies on the Pi**: The system should provide clear error messages if a required library (like `gphoto2` or `pyserial`) is missing or has the wrong version.
- **Port conflicts**: If the requested port (e.g., 8000) is already in use, the system should exit gracefully with a helpful message.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST resolve the `ImportError` for `StatusReport` in `host/src/cameracommander/hardware/tripod/serial_adapter.py`.
- **FR-002**: System MUST ensure `cameracommander.hardware.tripod.base` correctly defines or removes references to `StatusReport` based on the final protocol design.
- **FR-003**: System MUST be able to launch the `serve` command on both laptop (mock) and Pi (hardware) without module-level crashes.
- **FR-004**: All subcommands (`timelapse`, `pan`, `tripod`, `snapshot`) MUST be importable and runnable without immediate failure.

### Key Entities *(include if feature involves data)*

- **Host Process**: The running Python application instance.
- **Hardware Adapters**: The internal objects representing the Camera and Tripod links.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Application launches and reaches "Application startup complete" state in under 5 seconds.
- **SC-002**: 100% of defined CLI commands can be invoked (displaying `--help`) without crashing.
- **SC-003**: The test suite (`pytest`) completes collection phase in under 3 seconds.

## Assumptions

- The issue is a result of a naming mismatch or missing definition in the `001-core-system` rewrite.
- The environment has all required system-level libraries installed (libgphoto2, etc.).
- Deployment target remains the Raspberry Pi Zero 2 W.
