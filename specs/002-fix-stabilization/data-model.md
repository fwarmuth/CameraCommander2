# Data Model: Fix Stabilization

## 1. Hardware Entities (tripod/base.py)

### 1.1 StatusReport (New)
Detailed runtime state from the firmware.
- `pan_deg`: float
- `tilt_deg`: float
- `drivers_enabled`: boolean

### 1.2 MoveResult (Updated)
Result of a blocking motion command.
- `pan_deg`: float
- `tilt_deg`: float
- `duration_s`: float

## 2. Core Entities (core/models.py)

### 2.1 CaptureResult (Fixed)
Result of a one-shot still capture.
- `capture_id`: UUID string
- `content_type`: string
- `captured_at`: datetime
- `size_bytes`: integer
- `download_url`: string
