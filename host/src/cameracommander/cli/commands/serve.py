from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from cameracommander.api.app import create_app
from cameracommander.core.config import (
    Angles,
    CameraConfig,
    Configuration,
    ConfigurationMetadata,
    HostConfig,
    OutputConfig,
    SafetyConfig,
    TimelapseSequenceConfig,
    TripodConfig,
    load_host_configuration,
)
from cameracommander.hardware.camera.gphoto import GphotoCameraAdapter
from cameracommander.hardware.camera.mock import MockCameraAdapter
from cameracommander.hardware.tripod.serial_adapter import SerialTripodAdapter
from cameracommander.mock_firmware.server import MockFirmwareConfig, MockFirmwareServer


def command(
    host: Annotated[str, typer.Option("--host", help="Bind address.")] = "0.0.0.0",
    port: Annotated[int, typer.Option("--port", help="Bind port.")] = 8000,
    config: Annotated[
        Path | None,
        typer.Option("--config", help="Host-level config path."),
    ] = None,
    mock: Annotated[bool, typer.Option("--mock", help="Use mock hardware.")] = False,
    mock_camera: Annotated[bool, typer.Option("--mock-camera")] = False,
    mock_tripod: Annotated[bool, typer.Option("--mock-tripod")] = False,
    reload: Annotated[bool, typer.Option("--reload", help="Enable uvicorn reload.")] = False,
) -> None:
    host_config = None
    if config:
        host_config = load_host_configuration(config)
    else:
        default_config = Path.home() / ".cameracommander" / "host.yaml"
        if default_config.exists():
            host_config = load_host_configuration(default_config)

    tripod = None
    camera = None
    mock_server = None

    if mock or mock_tripod:
        if mock:
            mock_server = _MockFirmwareThread()
            mock_server.start()
        cfg = _minimal_config("socket://127.0.0.1:9999")
        tripod = SerialTripodAdapter(cfg.tripod)
    elif host_config and host_config.tripod:
        tripod = SerialTripodAdapter(host_config.tripod)

    if mock or mock_camera:
        camera = MockCameraAdapter()
    elif host_config and host_config.camera:
        camera = GphotoCameraAdapter(model_substring=host_config.camera.model_substring)

    app = create_app(
        camera=camera,
        tripod=tripod,
        session_root=host_config.session_library_root if host_config else None,
    )
    try:
        uvicorn.run(app, host=host, port=port, reload=reload, workers=1)
    finally:
        if mock_server is not None:
            mock_server.stop()


class _MockFirmwareThread:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._server = MockFirmwareServer(MockFirmwareConfig())
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._started = threading.Event()

    def start(self) -> None:
        self._thread.start()
        self._started.wait(timeout=5)

    def stop(self) -> None:
        future = asyncio.run_coroutine_threadsafe(self._server.stop(), self._loop)
        future.result(timeout=5)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._server.start(host="127.0.0.1", port=9999))
        self._started.set()
        self._loop.run_forever()


def _minimal_config(port: str) -> Configuration:
    return Configuration(
        metadata=ConfigurationMetadata(name="serve"),
        camera=CameraConfig(),
        tripod=TripodConfig(serial={"port": port}),
        safety=SafetyConfig(tilt_min_deg=-45, tilt_max_deg=45),
        output=OutputConfig(output_dir=Path("./output")),
        sequence=TimelapseSequenceConfig(
            total_frames=2,
            interval_s=1,
            settle_time_s=0,
            start={"pan_deg": 0, "tilt_deg": 0},
            target={"pan_deg": 0, "tilt_deg": 0},
        ),
    )


__all__ = ["command"]
