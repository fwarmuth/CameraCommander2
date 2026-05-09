import typer
from pathlib import Path
from ...core.config import load_configuration

def command(config_path: Path):
    try:
        load_configuration(config_path)
        typer.secho("Configuration valid", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"Configuration invalid: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=2)

__all__ = ["command"]
