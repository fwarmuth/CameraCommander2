import typer
import uvicorn
from typing import Annotated
from ...api.app import create_app
from ...hardware.camera.mock import MockCameraAdapter
from ...hardware.tripod.serial_adapter import SerialTripodAdapter
from ...core.config import SerialConfig

def command(
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port")] = 8000,
    mock: bool = False
):
    camera = None
    tripod = None
    if mock:
        camera = MockCameraAdapter()
        # Mock tripod setup would go here
    
    app = create_app(camera=camera, tripod=tripod)
    uvicorn.run(app, host=host, port=port)

__all__ = ["command"]
