# Data Model: Live Control and Planning Assist

## 1. API Requests

### 1.1 AbsoluteMoveRequest
- `pan_deg`: float
- `tilt_deg`: float

### 1.2 RelativeNudgeRequest
- `delta_pan_deg`: float (default 0.0)
- `delta_tilt_deg`: float (default 0.0)

### 1.3 DriverRequest
- `enabled`: boolean

## 2. Hardware Status (UI Context)
- `calibration`: Enum (unknown, homed)
- `hardwareStatus`: Aggregate of camera and tripod state.
- `connectionState`: (online, offline)

## 3. Camera Settings
- `groups`: Record<string, Record<string, string[]>> (Tab -> SubGroup -> Keys)
- `pending`: Record<string, Any> (Unsaved UI state)
