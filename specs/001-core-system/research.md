# Research: CameraCommander2 — Core System

## R001: Web UI Framework Version
- **Decision**: Svelte 5.
- **Rationale**: User-driven transition already occurred to resolve "effect_orphan" errors. Svelte 5 provides a more reactive rune-based system which may benefit the real-time Monitor view.
- **Alternatives considered**: Svelte 4 (rejected due to orphan effect issues encountered in this environment).

## R002: ffmpeg Performance on Pi Zero 2 W
- **Decision**: Out-of-process sequential assembly using `libx264` with `ultrafast` preset.
- **Rationale**: The Pi Zero 2 W lacks a hardware H.264 encoder in many distributions (or requires complex setup). CPU-based encoding is slow but reliable if performed after the capture job finishes to avoid timing jitter.
- **Alternatives considered**: In-process encoding (rejected - memory risk), Hardware encoding (deferred - depends on host OS configuration).

## R003: Disk Space Management Thresholds
- **Decision**: 200 MB Warning, 100 MB Critical (Auto-delete trigger).
- **Rationale**: 200 MB provides enough buffer for a few RAW frames if the estimate is slightly off. 100 MB is the "point of no return" where the oldest session must be purged to ensure the OS remains stable.
- **Alternatives considered**: Higher thresholds (rejected - wastes small SD card space).

## R004: Gphoto2 Locking and Threading
- **Decision**: Single hardware worker thread with an `asyncio.Lock`.
- **Rationale**: `libgphoto2` is not thread-safe. Attempting concurrent I/O results in `[-110] I/O in progress`. Serializing access ensures stability on the Pi's single-core focused architecture.
- **Alternatives considered**: Multi-process worker (rejected - complex serialization of camera handle).
