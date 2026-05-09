from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from cameracommander.core.errors import MotionLimitError, TripodError
from cameracommander.services.safety import SafetyService

from .common import load_config, make_tripod


def command(
    config: Annotated[Path, typer.Argument(help="Tripod configuration YAML.")],
    mock: Annotated[bool, typer.Option("--mock", help="Use mock hardware.")] = False,
) -> None:
    try:
        asyncio.run(_run_repl(config, mock=mock))
    except (ValueError, ValidationError, MotionLimitError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    except TripodError as exc:
        typer.secho(exc.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(12) from exc
    except KeyboardInterrupt as exc:
        raise typer.Exit(15) from exc


async def _run_repl(config_path: Path, *, mock: bool) -> None:
    config = load_config(config_path)
    tripod = make_tripod(config, mock=mock)
    safety = SafetyService.from_config(config)
    await tripod.open()

    typer.secho("Tripod REPL active. Type '?' for help.", fg=typer.colors.CYAN)

    while True:
        try:
            line = await asyncio.to_thread(input, "tripod> ")
        except EOFError:
            break

        line = line.strip().lower()
        if not line:
            continue
        if line in ("q", "quit", "exit"):
            break

        parts = line.split()
        cmd = parts[0]

        try:
            if cmd == "?":
                typer.echo("Commands: s (status), e (enable), d (disable), stop, home, <pan> <tilt>, q (quit)")
            elif cmd == "s":
                status = await tripod.status()
                typer.echo(f"Pan: {status.position_pan_deg:.3f}°, Tilt: {status.position_tilt_deg:.3f}°, Drivers: {status.drivers_enabled}")
            elif cmd == "e":
                await tripod.set_drivers(True)
                typer.echo("Drivers enabled.")
            elif cmd == "d":
                await tripod.set_drivers(False)
                typer.echo("Drivers disabled.")
            elif cmd == "stop":
                await tripod.stop()
                typer.echo("Stopped.")
            elif cmd == "home":
                await tripod.home()
                typer.echo("Homed.")
            elif len(parts) == 2:
                pan, tilt = float(parts[0]), float(parts[1])
                safety.guard_move(pan, tilt)
                await tripod.move_to(pan, tilt)
                typer.echo(f"Moved to {pan}, {tilt}")
            else:
                typer.secho("Unknown command", fg=typer.colors.RED)
        except Exception as exc:
            typer.secho(f"Error: {exc}", fg=typer.colors.RED)

    await tripod.close()


__all__ = ["command"]
