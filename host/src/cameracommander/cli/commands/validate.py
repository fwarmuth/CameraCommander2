from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from cameracommander.core.config import load_configuration
from cameracommander.core.errors import ConfigError
from cameracommander.services.safety import SafetyService


def command(
    config: Annotated[Path, typer.Argument(help="Configuration YAML to validate.")],
    emit_json: Annotated[bool, typer.Option("--json", help="Print canonical JSON.")] = False,
    strict: Annotated[
        bool,
        typer.Option("--strict/--no-strict", help="Reject unknown keys."),
    ] = True,
) -> None:
    _ = strict
    try:
        parsed = load_configuration(config)
        SafetyService.from_config(parsed).validate_sequence(parsed)
    except ConfigError as exc:
        typer.secho(exc.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    if emit_json:
        typer.echo(parsed.model_dump_json(indent=2))
    else:
        typer.echo(f"valid: {config}")


__all__ = ["command"]
