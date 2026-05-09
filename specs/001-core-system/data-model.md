# Data Model: CameraCommander2 — Core System

## 1. Configuration (YAML / Pydantic)
The authority for one "shoot".

### 1.1 Metadata
- `name`: String (required, 1-120 chars)
- `description`: String (optional)
- `tags`: List[String] (optional)
- `created_at`: DateTime (default: now)

### 1.2 CameraConfig
- `model_substring`: String (optional, e.g. "700D")
- `settings`: Dict[String, Any] (gphoto2 paths)
- `image_format`: Enum (camera-default, jpeg, raw, raw+jpeg)

### 1.3 TripodConfig
- `serial`: SerialConfig (port, baudrate, timeout)
- `microstep`: Enum (1, 2, 4, 8, 16)
- `expected_protocol_major`: Integer (default: 1)

### 1.4 SafetyConfig
- `tilt_min_deg`: Float
- `tilt_max_deg`: Float
- `move_timeout_margin_s`: Float (default: 2.0)
- `disk_min_free_bytes`: Integer (default: 200MB)

### 1.5 SequenceConfig (Discriminator: kind)
- **Timelapse**: `total_frames`, `interval_s`, `settle_time_s`, `start` (Angles), `target` (Angles)
- **VideoPan**: `duration_s`, `start` (Angles), `target` (Angles)

## 2. Session (Persisted)
A record of a completed or partial shoot.

- `session_id`: UUID
- `config`: Configuration (as run)
- `status`: Enum (completed, failed, partial)
- `assets`: List[Asset] (frames, metadata.csv, video.mp4)
- `metrics`: StartTime, EndTime, FrameCount, CadenceOverruns

## 3. Job (Runtime)
Active execution state.

- `job_id`: UUID
- `kind`: Enum (timelapse, video_pan, assembly)
- `status`: Enum (pending, running, completed, failed, stopped)
- `progress`: Dict (current_frame, total_frames, elapsed_s, remaining_s)
- `fault`: FaultEvent (optional)

## 4. Hardware Connection
- `state`: Enum (connected, disconnected, error)
- `model`: String (reported by device)
- `last_error`: String (optional)

## 5. Calibration State
- `is_homed`: Boolean
- `last_home_at`: DateTime (optional)
- `current_pan_deg`: Float (relative to home)
- `current_tilt_deg`: Float (relative to home)
