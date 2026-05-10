from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import ValidationError

from cameracommander.core.errors import MotionLimitError, TripodError
from cameracommander.hardware.tripod.protocol import EstimateReply, ProgressReply
from cameracommander.services.safety import SafetyService

from .common import load_config, make_tripod


async def _print_status(tripod) -> None:
    status = await tripod.status()
    typer.echo(
        f"pan={status.position_pan_deg:.3f} "
        f"tilt={status.position_tilt_deg:.3f} "
        f"drivers={'on' if status.drivers_enabled else 'off'}"
    )


async def _run_repl(config_path: Path, *, mock: bool) -> None:
    config = load_config(config_path)
    tripod = make_tripod(config, mock=mock)
    safety = SafetyService.from_config(config)
    await tripod.open()

    estimate: float | None = None
    move_started: float | None = None

    def _on_progress(reply: Any) -> None:
        nonlocal estimate, move_started
        if isinstance(reply, EstimateReply):
            estimate = reply.seconds
            move_started = time.monotonic()
            typer.secho(f"Move started (est. {estimate:.1f}s)...", fg=typer.colors.BLUE)
        elif isinstance(reply, ProgressReply):
            rem = ""
            if estimate is not None and move_started is not None:
                elapsed = time.monotonic() - move_started
                remaining = max(0.0, estimate - elapsed)
                rem = f" ({remaining:.1f}s remaining)"
            typer.echo(
                f"\rpan={reply.pan_deg:.3f}, tilt={reply.tilt_deg:.3f}{rem}    ",
                nl=False,
            )

    try:
        typer.secho("Manual tripod control. Use q to quit.", fg=typer.colors.CYAN)
        while True:
            raw = typer.prompt("tripod").strip()
            if raw in {"q", "quit", "exit"}:
                return
            if not raw:
                continue
            if raw == "s":
                await _print_status(tripod)
                continue
            if raw == "home":
                await tripod.home()
                typer.echo("homed")
                continue
            if raw == "e":
                await tripod.set_drivers(True)
                typer.echo("drivers on")
                continue
            if raw == "d":
                await tripod.set_drivers(False)
                typer.echo("drivers off")
                continue
            if raw == "stop":
                await tripod.stop()
                typer.echo("stopped")
                continue

            parts = raw.split()
            if parts[0] == "to" and len(parts) == 3:
                pan = float(parts[1])
                tilt = float(parts[2])
                safety.guard_move(pan, tilt)
                estimate = None
                move_started = None
                await tripod.move_to(pan, tilt, progress_callback=_on_progress)
                typer.echo()  # Newline after progress
                await _print_status(tripod)
                continue
            if len(parts) == 2:
                delta_pan = float(parts[0])
                delta_tilt = float(parts[1])
                status = await tripod.status()
                safety.guard_move(
                    status.position_pan_deg + delta_pan,
                    status.position_tilt_deg + delta_tilt,
                )
                estimate = None
                move_started = None
                await tripod.nudge(
                    delta_pan_deg=delta_pan,
                    delta_tilt_deg=delta_tilt,
                    progress_callback=_on_progress,
                )
                typer.echo()  # Newline after progress
                await _print_status(tripod)
                continue
            typer.secho("unknown command", fg=typer.colors.YELLOW, err=True)
    finally:
        await tripod.close()


def command(
    config: Annotated[
        Path,
        typer.Argument(help="Configuration YAML containing a tripod block.", exists=True),
    ],
    mock: Annotated[
        bool,
        typer.Option("--mock", help="Use socket://127.0.0.1:9999 for the tripod."),
    ] = False,
) -> None:
    try:
        asyncio.run(_run_repl(config, mock=mock))
    except (ValueError, ValidationError, MotionLimitError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    except TripodError as exc:
        if exc.firmware_error == "AlreadyAtTarget":
            typer.secho("Tripod is already at the target position. No move needed.", fg=typer.colors.YELLOW)
        else:
            typer.secho(exc.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(12) from exc
    except KeyboardInterrupt as exc:
        raise typer.Exit(15) from exc


__all__ = ["command"]
