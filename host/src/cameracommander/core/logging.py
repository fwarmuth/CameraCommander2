"""Loguru sink configuration for the host application.

Honours XDG, defaults to ``~/.cameracommander/logs/host.log`` with daily
rotation and 7-day retention. Adds ``session_id`` and ``job_id`` extras to every
record so downstream consumers can grep / aggregate by job.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal

from loguru import logger

LogLevel = Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

_DEFAULT_FILE_FMT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{extra[session_id]} | {extra[job_id]} | "
    "{name}:{function}:{line} - {message}"
)
_DEFAULT_STDERR_FMT = (
    "<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def default_log_path() -> Path:
    """Return ``~/.cameracommander/logs/host.log`` (overridable via XDG)."""

    base = os.environ.get("CAMERACOMMANDER_LOG_DIR")
    if base:
        return Path(base) / "host.log"
    return Path.home() / ".cameracommander" / "logs" / "host.log"


def configure_logging(
    *,
    level: LogLevel = "INFO",
    file_path: Path | str | None = None,
    stderr: bool = True,
) -> None:
    """Configure loguru sinks for the host process.

    ``file_path="-"`` disables the file sink (logs only to stderr); useful for
    one-shot CLI commands and tests.
    """

    logger.remove()

    if stderr:
        logger.add(
            sys.stderr,
            level=level,
            format=_DEFAULT_STDERR_FMT,
            enqueue=False,
            backtrace=False,
            diagnose=False,
        )

    if file_path != "-":
        target = Path(file_path) if file_path is not None else default_log_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            target,
            level=level,
            format=_DEFAULT_FILE_FMT,
            rotation="00:00",  # daily
            retention="7 days",
            compression=None,
            enqueue=True,
            backtrace=False,
            diagnose=False,
        )

    # Bind defaults so the {extra[session_id]} / {extra[job_id]} tokens never
    # fail to format on records that don't override them.
    logger.configure(extra={"session_id": "-", "job_id": "-"})


def bind_job_logger(job_id: str, session_id: str | None = None):  # type: ignore[no-untyped-def]
    """Return a logger that pre-binds ``job_id`` / ``session_id`` to every record."""

    return logger.bind(job_id=job_id, session_id=session_id or job_id)


__all__ = ["bind_job_logger", "configure_logging", "default_log_path", "logger"]
