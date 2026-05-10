# Research: Live Control and Planning Assist

## R001: Tripod Motion Timeouts
- **Decision**: Set default hardware communication timeout to 30 seconds.
- **Rationale**: Long pan/tilt moves on real hardware can exceed the standard 1s serial timeout. The host must wait for the firmware to emit `DONE`.
- **Implementation**: Updated `SerialConfig.timeout` and added `expected_duration_s` to nudge commands.

## R002: Camera Settings Organization
- **Decision**: Implement a collapsible tree-like structure in the UI.
- **Rationale**: DSLR cameras expose 40+ settings via gphoto2. A flat list is unusable. Grouping by path prefixes (e.g., `capturesettings`, `imgsettings`) with expand/collapse toggles improves discoverability.
- **Implementation**: Svelte 5 logic to group keys by path segments and a search bar for filtering.

## R003: Test Capture Reliability
- **Decision**: Correct the `gphoto2.gp_camera_file_get` argument sequence and return image data to host.
- **Rationale**: Previous implementation passed the context where a `CameraFile` object was expected.
- **Implementation**: Fixed `GphotoCameraAdapter._capture_blocking` to create a new `gp_file` container and return the raw bytes alongside metadata.

## R004: MJPEG Streaming
- **Decision**: Use FastAPI `StreamingResponse` with an async generator.
- **Rationale**: Directly returning the generator caused encoding errors in Starlette.
- **Implementation**: Updated `get_camera_preview_stream` to yield correctly formatted multipart chunks.
