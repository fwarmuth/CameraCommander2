from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from cameracommander.core.errors import CalibrationRequiredError, ConfigError
from cameracommander.persistence.sessions_fs import SessionRepository
from cameracommander.services.calibration import CalibrationService
from cameracommander.services.jobs import JobManager
from cameracommander.services.safety import SafetyService

from .common import load_config, make_camera, make_tripod


def command(
    config: Annotated[Path, typer.Argument(help="Timelapse configuration YAML.")],
    no_video: Annotated[bool, typer.Option("--no-video", help="Skip ffmpeg assembly.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Validate only.")] = False,
    mock: Annotated[bool, typer.Option("--mock", help="Use all mock hardware.")] = False,
    mock_camera: Annotated[bool, typer.Option("--mock-camera", help="Use mock camera.")] = False,
    mock_tripod: Annotated[bool, typer.Option("--mock-tripod", help="Use mock tripod port.")] = False,
) -> None:
    try:
        cfg = load_config(config)
        if no_video:
            cfg.output.video.assemble = False
        SafetyService.from_config(cfg).validate_sequence(cfg)
    except ConfigError as exc:
        typer.secho(exc.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    if dry_run:
        typer.echo("valid timelapse configuration")
        return
    asyncio.run(_run(cfg, mock_camera=mock or mock_camera, mock_tripod=mock or mock_tripod))


async def _run(cfg, *, mock_camera: bool, mock_tripod: bool) -> None:
    calibration = CalibrationService()
    calibration.mark_homed()
    jobs = JobManager(
        camera=make_camera(cfg, mock=mock_camera),
        tripod=make_tripod(cfg, mock=mock_tripod),
        calibration=calibration,
        sessions=SessionRepository(),
    )
    try:
        await jobs.open()
        job = await jobs.start("timelapse", cfg)
        last = -1
        while jobs.get(job.job_id).status == "running":
            current = jobs.get(job.job_id).progress.frames_completed
            total = jobs.get(job.job_id).progress.frames_total
            if current != last:
                pct = current / total * 100 if total else 0
                typer.echo(f"\rCaptured {current}/{total} ({pct:5.1f}%)", nl=False)
                last = current
            await asyncio.sleep(0.1)
        await jobs.wait(job.job_id)
        final = jobs.get(job.job_id)
        typer.echo()
        if final.status != "completed":
            raise typer.Exit(11)
        typer.echo(f"completed: {final.session_id}")
    except CalibrationRequiredError as exc:
        typer.secho(exc.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(3) from exc
    finally:
        await jobs.close()


__all__ = ["command"]
