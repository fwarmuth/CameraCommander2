# Implementation Plan: Live Control and Planning Assist

**Branch**: `003-live-control` | **Date**: 2026-05-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-live-control/spec.md`

## Summary
Complete the implementation and stabilization of the Live Control interface. This includes fixing motion timeouts, organizing high-density camera settings into a tree view, and ensuring test captures reliably download and display for exposure verification.

## Technical Context
- **Frontend**: Svelte 5 with runes ($state, $derived).
- **Backend**: FastAPI with `StreamingResponse` for MJPEG.
- **Hardware**: `libgphoto2` and `pyserial`.

## Constitution Check
| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. System Boundary Contracts** | PASS | Using structured JSON requests for nudge/drivers. |
| **II. Hardware Abstraction** | PASS | Both mock and real adapters support capture and nudge. |
| **III. Configuration-Driven** | PASS | Planning tab highlights settings needed for YAML creation. |

## Phase 0: Research
- Decision: Use 30s serial timeout (R001).
- Decision: Nested grouping for settings UI (R002).
- Decision: Correct `gp_camera_file_get` signature (R003).

## Phase 1: Design
- **Entities**: `DriverRequest`, `RelativeNudgeRequest`.
- **UI**: Collapsible tree view with search.

## Phase 2: Implementation
- **Task 1**: Stabilize Tripod API (nudge payload and timeouts).
- **Task 2**: Refine Camera Settings UI (Svelte 5 runes + tree logic).
- **Task 3**: Fix Test Capture pipeline (caching and download).
