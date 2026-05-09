"""Typer entry-point for ``cameracommander``.

Subcommands import lazily so ``cameracommander --help`` does not pull
``gphoto2``, ``pyserial``, or any other heavy dependency on a Pi. Each command
module registers itself by exposing an ``app`` Typer instance or a callable;
this file just wires the names into the root.
"""

from __future__ import annotations

from importlib import import_module
from typing import Annotated

import typer

from .. import __version__
from ..core.logging import LogLevel, configure_logging

app = typer.Typer(
    name="cameracommander",
    help=(
        "CameraCommander2 — motorised pan-tilt head orchestration "
        "(timelapse, video pan, mock-driven development)."
    ),
    no_args_is_help=True,
    add_completion=False,
)

# A small registry of (name, dotted_module_path, attribute) to import lazily.
# Concrete commands land during the per-user-story phases; the names are listed
# here so `cameracommander --help` reports the full surface and the foundational
# tests can assert dispatch wiring.
_LAZY_COMMANDS: dict[str, tuple[str, str]] = {
    "snapshot": ("cameracommander.cli.commands.snapshot", "command"),
    "tripod": ("cameracommander.cli.commands.tripod", "command"),
    "timelapse": ("cameracommander.cli.commands.timelapse", "command"),
    "pan": ("cameracommander.cli.commands.pan", "command"),
    "validate": ("cameracommander.cli.commands.validate", "command"),
    "mock-firmware": ("cameracommander.cli.commands.mock_firmware", "command"),
    "serve": ("cameracommander.cli.commands.serve", "command"),
}


def _print_banner() -> None:
    typer.secho("CameraCommander2 — host", fg=typer.colors.CYAN, bold=True)
    typer.secho(f"  version {__version__}", dim=True)


@app.callback()
def _root(
    log_level: Annotated[
        LogLevel,
        typer.Option(
            "--log-level",
            help="Loguru sink level.",
            case_sensitive=False,
        ),
    ] = "INFO",
    log_file: Annotated[
        str,
        typer.Option(
            "--log-file",
            help="Path for the file sink (use '-' to log only to stderr).",
        ),
    ] = "",
    no_banner: Annotated[
        bool, typer.Option("--no-banner", help="Suppress the startup banner.")
    ] = False,
    show_version: Annotated[
        bool, typer.Option("--version", help="Print host SemVer and exit.")
    ] = False,
) -> None:
    """Global flags applied to every subcommand."""

    if show_version:
        typer.echo(__version__)
        raise typer.Exit(0)

    configure_logging(level=log_level, file_path=log_file or None)

    if not no_banner:
        _print_banner()


def _missing_command(name: str, module_path: str) -> None:
    typer.secho(
        f"command '{name}' not yet implemented (module {module_path} missing)",
        fg=typer.colors.YELLOW,
        err=True,
    )
    raise typer.Exit(2)


def _register_lazy(name: str, module_path: str, attr: str) -> None:
    """Register implemented command modules and placeholders for missing ones."""

    try:
        mod = import_module(module_path)
    except ModuleNotFoundError:
        app.command(name=name)(lambda: _missing_command(name, module_path))
        return
    target = getattr(mod, attr, None)
    if target is None:
        app.command(name=name)(lambda: _missing_command(name, module_path))
        return
    app.command(name=name)(target)


for _name, (_mod, _attr) in _LAZY_COMMANDS.items():
    _register_lazy(_name, _mod, _attr)


__all__ = ["app"]
