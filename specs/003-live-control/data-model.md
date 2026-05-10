# Data Model: Live Control & Setup Assist

## 1. Camera Entities

### 1.1 FocusNudgeRequest
Input for lens focus adjustment.
- `step_size`: Integer (-3 to 3)

### 1.2 SettingDescriptor (Refined)
Shared with Core System but enriched here.
- `full_path`: String (e.g., "main.imgsettings.iso")
- `label`: String (e.g., "ISO Speed")
- `type`: Enum (TEXT, RANGE, TOGGLE, RADIO, MENU, DATE, BUTTON)
- `current`: Any
- `choices`: List[Any] (optional)
- `range`: Dict{min, max, step} (optional)

## 2. UI State

### 2.1 LiveControlState
- `view_mode`: Enum (preview, snapshot)
- `zoom_level`: Float (1.0 to 4.0)
- `pan_offset`: {x, y}
