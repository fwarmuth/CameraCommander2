"""Loguru sink configuration for the host application.

Honours XDG, defaults to ``~/.cameracommander/logs/host.log`` with daily
rotation and 7-day retention. Adds ``session_id`` and ``job_id`` extras to every
record so downstream collectors can correlate hardware events.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from loguru import logger


def default_log_path() -> Path:
    return Path.home() / ".cameracommander" / "logs" / "host.log"


def configure_logging(
    level: str = "INFO", 
    log_file: Path | None = None,
    serialize: bool = False
) -> None:
    """Configure loguru with standard console and file sinks."""
    logger.remove()
    
    # Console sink
    logger.add(
        sys.stderr, 
        level=level, 
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # File sink
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            level=level,
            rotation="00:00",
            retention="7 days",
            serialize=serialize,
            enqueue=True,
            backtrace=True,
            diagnose=True,
        )


def bind_job_logger(job_id: str, session_id: str | None = None) -> Any:
    """Return a logger that pre-binds ``job_id`` / ``session_id`` to every record."""
    return logger.bind(job_id=job_id, session_id=session_id or job_id)


__all__ = ["bind_job_logger", "configure_logging", "default_log_path", "logger"]
