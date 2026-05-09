"""Dependency-injection container for the host application.

The :class:`AppContainer` holds the long-lived adapters and services. The
FastAPI app stashes one on ``app.state.container`` during ``lifespan`` setup and
the route modules retrieve fields through the lightweight :func:`get_*` helpers
below. Keeping it a plain dataclass instead of a third-party DI library matches
Constitution V (no premature abstraction).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request

from .websocket import EventBus

if TYPE_CHECKING:
    from ..hardware.camera.base import CameraAdapter
    from ..hardware.tripod.base import TripodAdapter


@dataclass(slots=True)
class AppContainer:
    """Holds the singletons that route handlers depend on."""

    event_bus: EventBus
    camera: "CameraAdapter | None" = None
    tripod: "TripodAdapter | None" = None
    # The remaining services (safety, calibration, jobs, sessions, disk_guard,
    # post_process) attach in later tasks (US1 phase) — they're optional here so
    # foundational tests can build a minimal AppContainer without them.
    safety: object | None = None
    calibration: object | None = None
    jobs: object | None = None
    sessions: object | None = None
    disk_guard: object | None = None
    post_process: object | None = None


def get_container(app_or_request: FastAPI | Request) -> AppContainer:
    """Return the container attached to the app's state."""

    app = app_or_request.app if isinstance(app_or_request, Request) else app_or_request
    container: AppContainer | None = getattr(app.state, "container", None)
    if container is None:
        raise RuntimeError("AppContainer not initialised; did the lifespan run?")
    return container


def get_event_bus(app_or_request: FastAPI | Request) -> EventBus:
    return get_container(app_or_request).event_bus


__all__ = ["AppContainer", "get_container", "get_event_bus"]
