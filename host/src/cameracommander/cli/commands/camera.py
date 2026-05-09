from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from cameracommander.core.errors import CameraError
from .common import load_config, make_camera


def command(
    config: Annotated[Path, typer.Argument(help="Camera configuration YAML.")],
    mock: Annotated[bool, typer.Option("--mock", help="Use mock hardware.")] = False,
) -> None:
    """Interactive camera control REPL."""
    try:
        asyncio.run(_run_repl(config, mock=mock))
    except (ValueError, ValidationError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    except CameraError as exc:
        typer.secho(exc.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(10) from exc
    except KeyboardInterrupt as exc:
        raise typer.Exit(15) from exc


async def _run_repl(config_path: Path, *, mock: bool) -> None:
    config = load_config(config_path)
    camera = make_camera(config, mock=mock)
    await camera.open()

    typer.secho("Camera REPL active. Type '?' for help.", fg=typer.colors.CYAN)

    while True:
        try:
            line = await asyncio.to_thread(input, "camera> ")
        except EOFError:
            break

        line = line.strip()
        if not line:
            continue
        if line.lower() in ("q", "quit", "exit"):
            break

        parts = line.split()
        cmd = parts[0].lower()

        try:
            if cmd == "?":
                typer.echo("Commands: s (status), ls (list settings), set <key> <value>, c (capture), p (preview), v+ (start rec), v- (stop rec), q (quit)")
            elif cmd == "s":
                status = await camera.status()
                typer.echo(f"Model: {status.model}, State: {status.state}, Battery: {status.battery_pct}%")
            elif cmd == "ls":
                settings = await camera.query_settings()
                for key, desc in settings.items():
                    choices = f" [{', '.join(desc.choices)}]" if desc.choices else ""
                    typer.echo(f"{key} = {desc.current}{choices}")
            elif cmd == "set":
                if len(parts) < 3:
                    typer.secho("Usage: set <key> <value>", fg=typer.colors.RED)
                    continue
                key = parts[1]
                value = " ".join(parts[2:])
                await camera.apply_settings({key: value})
                typer.echo(f"Applied {key}={value}")
            elif cmd == "c":
                res = await camera.capture_still()
                typer.echo(f"Captured: {res.capture_id} ({res.size_bytes} bytes)")
            elif cmd == "p":
                jpeg = await camera.preview_frame_jpeg()
                output = Path("preview_test.jpg")
                output.write_bytes(jpeg)
                typer.echo(f"Preview saved to {output.absolute()}")
            elif cmd == "v+":
                await camera.start_recording()
                typer.echo("Recording started.")
            elif cmd == "v-":
                await camera.stop_recording()
                typer.echo("Recording stopped.")
            else:
                typer.secho("Unknown command", fg=typer.colors.RED)
        except Exception as exc:
            typer.secho(f"Error: {exc}", fg=typer.colors.RED)

    await camera.close()


__all__ = ["command"]
