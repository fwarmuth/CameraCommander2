from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from cameracommander.core.errors import CameraDisconnectedError, CaptureError
from cameracommander.hardware.camera.gphoto import GphotoCameraAdapter

from .common import load_config, make_camera


def _resolve_output(output: Path, extension: str) -> Path:
    if output.exists() and output.is_dir():
        return output / f"capture_{int(time.time())}{extension}"
    if output.suffix:
        output.parent.mkdir(parents=True, exist_ok=True)
        return output
    output.mkdir(parents=True, exist_ok=True)
    return output / f"capture_{int(time.time())}{extension}"


async def _capture(
    *,
    config_path: Path | None,
    output: Path,
    model_substring: str | None,
    autofocus: bool,
    mock: bool,
) -> Path:
    if config_path is not None:
        config = load_config(config_path)
        camera = make_camera(config, mock=mock)
        if model_substring and isinstance(camera, GphotoCameraAdapter):
            camera.model_substring = model_substring
    else:
        camera = GphotoCameraAdapter(model_substring=model_substring)

    await camera.open()
    try:
        if config_path is not None:
            config = load_config(config_path)
            if config.camera.settings:
                await camera.apply_settings(config.camera.settings)
        result = await camera.capture_still(autofocus=autofocus)
        target = _resolve_output(output, result.extension)
        target.write_bytes(result.bytes_)
        return target
    finally:
        await camera.close()


def command(
    first: Annotated[
        Path,
        typer.Argument(
            help="CONFIG when OUTPUT is also supplied; otherwise OUTPUT.",
            exists=False,
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Argument(help="Output file or directory."),
    ] = None,
    model_substring: Annotated[
        str | None,
        typer.Option("--model-substring", help="Select camera by model substring."),
    ] = None,
    autofocus: Annotated[
        bool,
        typer.Option("--autofocus/--no-autofocus", help="Use camera autofocus before capture."),
    ] = False,
    mock: Annotated[
        bool,
        typer.Option("--mock", help="Use the mock camera adapter."),
    ] = False,
    mock_camera: Annotated[
        bool,
        typer.Option("--mock-camera", help="Use the mock camera adapter."),
    ] = False,
) -> None:
    config_path = first if output is not None else None
    output_path = output or first
    try:
        path = asyncio.run(
            _capture(
                config_path=config_path,
                output=output_path,
                model_substring=model_substring,
                autofocus=autofocus,
                mock=mock or mock_camera,
            )
        )
    except (OSError, ValidationError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    except CameraDisconnectedError as exc:
        typer.secho(exc.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(10) from exc
    except CaptureError as exc:
        typer.secho(exc.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(11) from exc
    typer.echo(path)


__all__ = ["command"]
