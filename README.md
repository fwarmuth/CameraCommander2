# CameraCommander2

Full rewrite of the motorized camera motion-control stack.

- **firmware/**: ESP8266/ESP32 Arduino code.
- **host/**: Python FastAPI + Typer CLI.
- **web/**: Svelte 5 browser interface.

## Quickstart

```bash
cd host
uv run cameracommander serve --mock
```
