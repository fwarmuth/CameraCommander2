from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from cameracommander.mock_firmware.server import MockFirmwareConfig, run_server


def command(
    host: Annotated[str, typer.Option("--host", help="Bind address.")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", help="Bind port.")] = 9999,
    initial_pan: Annotated[float, typer.Option("--initial-pan")] = 0.0,
    initial_tilt: Annotated[float, typer.Option("--initial-tilt")] = 0.0,
    microstep: Annotated[int, typer.Option("--microstep")] = 1,
    drivers_disabled: Annotated[bool, typer.Option("--drivers-disabled")] = False,
    deg_per_second: Annotated[float, typer.Option("--deg-per-second")] = 60.0,
    settle_delay: Annotated[float, typer.Option("--settle-delay")] = 0.25,
    fw_version: Annotated[str, typer.Option("--fw-version")] = "1.0.1",
) -> None:
    cfg = MockFirmwareConfig(
        initial_pan_deg=initial_pan,
        initial_tilt_deg=initial_tilt,
        microstep=microstep,
        drivers_disabled=drivers_disabled,
        deg_per_second=deg_per_second,
        settle_delay_s=settle_delay,
        fw_version=fw_version,
    )
    try:
        asyncio.run(run_server(cfg, host=host, port=port))
    except KeyboardInterrupt as exc:
        raise typer.Exit(0) from exc


__all__ = ["command"]
