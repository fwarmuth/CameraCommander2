from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from cameracommander.api.app import create_app
from cameracommander.core.config import (
    CameraConfig,
    Configuration,
    ConfigurationMetadata,
    OutputConfig,
    SafetyConfig,
    TimelapseSequenceConfig,
    TripodConfig,
)
from cameracommander.hardware.camera.mock import MockCameraAdapter
from cameracommander.hardware.tripod.serial_adapter import SerialTripodAdapter


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
    _ = config
    tripod = None
    if mock or mock_tripod:
        cfg = _minimal_config("socket://127.0.0.1:9999")
        tripod = SerialTripodAdapter(cfg.tripod)
    app = create_app(
        camera=MockCameraAdapter() if mock or mock_camera else None,
        tripod=tripod,
    )
    uvicorn.run(app, host=host, port=port, reload=reload, workers=1)


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
