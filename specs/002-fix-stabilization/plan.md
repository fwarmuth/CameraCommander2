# Implementation Plan: Fix Stabilization

**Branch**: `002-fix-stabilization` | **Date**: 2026-05-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-fix-stabilization/spec.md`

## Summary
Resolve immediate startup blocker (`ImportError`) by restoring missing hardware dataclasses and stabilizing the core model definitions. This phase ensures the application is runnable and provides a foundation for Pi-side stabilization.

## Technical Context
**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, Pydantic v2, Typer, Pyserial
**Testing**: pytest

## Constitution Check
| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. System Boundary Contracts** | PASS | Aligning internal dataclasses with documented protocol expectations. |
| **II. Hardware Abstraction** | PASS | Fixing `TripodAdapter` protocol definitions. |
| **III. Configuration-Driven** | PASS | No changes to config schema. |
| **IV. Spec-Driven Development** | PASS | Plan derived from `spec.md`. |

## Phase 0: Research
- Decision: Restore `StatusReport` and update `MoveResult` in `hardware/tripod/base.py`.
- Decision: Fix syntax in `core/models.py`.

## Phase 1: Design
- **Entities**: `StatusReport`, `MoveResult`, `CaptureResult`.
- **Contracts**: No API changes; internal alignment only.

## Phase 2: Implementation
- **Task 1**: Update `hardware/tripod/base.py`.
- **Task 2**: Fix `core/models.py`.
- **Task 3**: Verify `cli/main.py` imports.

## Complexity Tracking
> No violations.
