# Implementation Plan: Movement Feedback and Increased Timeout

**Branch**: `004-movement-feedback` | **Date**: 2026-05-10 | **Spec**: [specs/004-movement-feedback/spec.md](spec.md)
**Input**: Feature specification from `/specs/004-movement-feedback/spec.md`

## Summary

This feature addresses the movement timeout issue by refactoring the firmware to use a non-blocking (async) state machine for motion. This allows the firmware to periodically emit `PROGRESS` messages and handle concurrent commands like `X` (Emergency Stop) or `S` (Status) during a move. The firmware will also calculate and provide an initial `ESTIMATE` for the move duration. The host will handle these messages to provide real-time feedback in the CLI (via overwritten single lines) and automatically extend the command timeout deadline as long as progress is being made.

## Technical Context

**Language/Version**: Python 3.12+, C++ (Arduino/ESP8266/ESP32)  
**Primary Dependencies**: `pyserial`, `asyncio`, `typer` (Host); `AccelStepper` (Firmware)  
**Storage**: N/A  
**Testing**: `pytest` (Host), `unity` (Firmware native tests)  
**Target Platform**: ESP8266/ESP32 (Tripod), Linux (Host)
**Project Type**: Embedded + CLI  
**Performance Goals**: 5Hz progress updates (every 200ms)  
**Constraints**: Must maintain backward compatibility with v1.x protocol (ignoring new lines).  
**Scale/Scope**: Protocol v1.1 addition + Firmware async refactor + Host adapter logic + CLI UI update.

## Constitution Check

- **Boundary Contracts**: PASS. Updated `firmware-protocol.md` to v1.1.
- **Hardware Abstraction**: PASS. Mock firmware will be updated to match the new async behavior and message types.
- **Spec-Driven**: PASS. Spec is complete and clarified.
- **Simplicity**: PASS. Minimal UI feedback, standard state machine pattern in firmware.
- **Observability**: PASS. Real-time progress satisfies the core observability principle.
- **Motion Safety**: PASS. Non-blocking architecture ensures Emergency Stop is responsive during moves.

## Project Structure

### Documentation (this feature)

```text
specs/004-movement-feedback/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── firmware-protocol.md # Updated contract
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
firmware/
├── src/
│   ├── main.cpp         # Refactor move_absolute to async state machine
│   └── protocol.h       # Define PROGRESS, ESTIMATE, ERR constants
└── test/                # Update parser tests

host/
├── src/cameracommander/
│   ├── hardware/tripod/
│   │   ├── protocol.py  # Handle ProgressReply, EstimateReply
│   │   └── serial_adapter.py # Handle intermediate replies, refresh timeout
│   ├── cli/commands/
│   │   └── tripod.py    # Display overwritten single-line progress
│   └── mock_firmware/
│       └── server.py    # Simulate async motion and PROGRESS messages
└── tests/
    ├── contract/        # Test protocol v1.1 updates
    ├── integration/     # test_movement_timeout.py
    └── unit/            # Test adapter progress handling
```
