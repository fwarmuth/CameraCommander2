from __future__ import annotations
from pathlib import Path
from typing import Annotated
import typer
from ..core.logging import configure_logging, default_log_path

app = typer.Typer(help="CameraCommander2 host.")

@app.callback()
def main(
    log_level: str = "INFO",
    log_file: Path = default_log_path(),
):
    configure_logging(level=log_level.upper(), log_file=log_file)

from .commands import serve, validate, snapshot, tripod, pan, mock_firmware, timelapse
app.command(name="serve")(serve.command)
app.command(name="validate")(validate.command)
app.command(name="snapshot")(snapshot.command)
app.command(name="tripod")(tripod.command)
app.command(name="pan")(pan.command)
app.command(name="mock-firmware")(mock_firmware.command)
app.command(name="timelapse")(timelapse.command)

if __name__ == "__main__":
    app()
