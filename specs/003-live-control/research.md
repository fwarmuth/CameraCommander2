# Research: Live Control & Setup Assist

## R001: gphoto2 Focus Control
- **Decision**: Use `main.actions.manualfocusdrive` for Canon DSLRs.
- **Rationale**: This is the standard gphoto2 widget for incremental focus (nudge). It accepts integer values (typically -3 to 3) representing the size and direction of the focus motor step.
- **Alternatives considered**: `autofocusdrive` (too unpredictable for manual setup), `focusmetermode` (informational only).

## R002: High-Resolution Image Inspection in Web UI
- **Decision**: Use CSS-based transform scale (zoom) with mouse-drag panning for the test capture viewer.
- **Rationale**: Keeps the implementation simple and dependency-free while satisfying the "inspect focus" requirement. For a single image, a full tiling library like OpenSeadragon is overkill for v1 on the Pi.
- **Implementation**: A dedicated `ImageInspector.svelte` component.

## R003: MJPEG and Capture Serialization
- **Decision**: Sequential hardware lock in the Python host must prioritize Captures over Preview frames.
- **Rationale**: Captures are higher priority. The preview stream generator should check a "busy" flag or the lock before requesting the next frame. If a capture is requested, the preview stream should pause or yield a "Camera Busy" placeholder.

## R004: Dynamic Configuration Discovery
- **Decision**: Full recursive walk of the gphoto2 widget tree on startup or manual refresh.
- **Rationale**: Ensures the UI is always in sync with the connected camera's actual capabilities (ISO ranges, format options), fulfilling the "values are always valid" requirement.
