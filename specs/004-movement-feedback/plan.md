# Implementation Plan: Movement Feedback and Increased Timeout

**Branch**: `004-movement-feedback` | **Date**: 2026-05-10 | **Spec**: [specs/004-movement-feedback/spec.md](spec.md)
**Input**: Feature specification from `/specs/004-movement-feedback/spec.md`

## Summary

This feature addresses the movement timeout issue by introducing a periodic `PROGRESS` message from the firmware during motion. The host will handle these messages to provide real-time feedback in the CLI and automatically extend the command timeout deadline as long as progress is being made.

## Technical Context

**Language/Version**: Python 3.12+, C++ (Arduino/ESP8266/ESP32)  
**Primary Dependencies**: `pyserial`, `asyncio`, `typer` (Host); `AccelStepper` (Firmware)  
**Storage**: N/A  
**Testing**: `pytest` (Host), `unity` (Firmware native tests)  
**Target Platform**: ESP8266/ESP32 (Tripod), Linux (Host)
**Project Type**: Embedded + CLI  
**Performance Goals**: 5-10Hz progress updates (every 100-200ms)  
**Constraints**: Must maintain backward compatibility with v1.x protocol; older hosts should ignore new progress messages.  
**Scale/Scope**: Small protocol addition + adapter logic + CLI UI update.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Boundary Contracts**: PASS. The `PROGRESS` message is an additive change to the serial protocol.
- **Hardware Abstraction**: PASS. The mock firmware will be updated to simulate `PROGRESS` messages.
- **Spec-Driven**: PASS. Feature spec is complete and validated.
- **Simplicity**: PASS. Minimal changes to existing communication loop.

## Project Structure

### Documentation (this feature)

```text
specs/004-movement-feedback/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (empty/small)
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── firmware-protocol.md # Updated contract
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
firmware/
├── src/
│   ├── main.cpp         # Update move_absolute to emit PROGRESS
│   └── protocol.h       # Define PROGRESS reply token
└── test/                # Add/update parser tests

host/
├── src/cameracommander/
│   ├── hardware/tripod/
│   │   ├── protocol.py  # Handle ProgressReply
│   │   └── serial_adapter.py # Handle intermediate replies, extend timeout
│   ├── cli/commands/
│   │   └── tripod.py    # Display progress feedback
│   └── mock_firmware/
│       └── server.py    # Simulate PROGRESS messages
└── tests/
    ├── contract/        # Test protocol updates
    ├── unit/            # Test adapter logic
    └── integration/     # End-to-end progress test
```

**Structure Decision**: Standard single-project layout for both firmware and host as defined in the constitution.
