# Implementation Plan: Live Control & Setup Assist

**Branch**: `003-live-control` | **Date**: 2026-05-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-live-control/spec.md`

## Summary

Enhance the Live Control tab to provide a professional camera setup environment. This includes real-time focus control, dynamic gphoto2 settings discovery, and a high-resolution test capture workflow with zoom capability. The system is designed to handle high-density camera configurations by grouping them into a navigable tree structure.

## Technical Context

- **Host**: Python 3.12, gphoto2, FastAPI.
- **Frontend**: Svelte 5 (runes), Tailwind CSS.
- **Hardware**: Canon DSLR via USB, CH340 Tripod via Serial.

## Constitution Check

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Boundary Contracts** | PASS | Adding `POST /api/camera/focus` to the host API contract. |
| **II. Hardware Abstraction** | PASS | Mock camera supports synthetic settings discovery and dummy snapshot bytes. |
| **III. Configuration-Driven** | PASS | Setup Assist facilitates finding values for the timelapse YAML. |

## Phase 0: Outline & Research

- R001: Focus control via `manualfocusdrive`.
- R002: CSS-based zoom/pan for inspection.
- R004: Recursive gphoto2 widget tree walker.

## Phase 1: Design & Contracts

- **API**: Add `POST /api/camera/focus` (step_size: int).
- **Entities**: Refined `SettingDescriptor` to include full metadata from gphoto2.
- **UI**: `ImageInspector.svelte` for high-res zoom.

## Phase 2: Implementation (Tasks)

1.  **Refine gphoto2 adapter**: Correct `_query_settings_blocking` to walk full tree and extract choices/ranges.
2.  **Add Focus Control**: Implement `manualfocusdrive` in adapter and new API endpoint.
3.  **Enhance Web UI**:
    - Update `LiveControl.svelte` to render hierarchical tabs.
    - Implement `QuickSettingsBar` for ISO/Shutter/Aperture.
    - Implement `ImageInspector` with zoom/pan for test captures.
4.  **Auto-Stop Preview**: Ensure MJPEG stream yields to captures.

## Complexity Tracking

> No constitutional violations.
