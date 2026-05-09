"""Dependency injection container for the CameraCommander host."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..hardware.camera.base import CameraAdapter
    from ..hardware.tripod.base import TripodAdapter
    from .websocket import EventBus
    from ..services.jobs import JobManager


@dataclass
class AppContainer:
    """Singleton-like container for shared services and hardware adapters."""

    camera: CameraAdapter | None = None
    tripod: TripodAdapter | None = None
    bus: EventBus | None = None
    jobs: Any = None
    calibration: Any = None
    sessions: Any = None
    safety: Any = None


def get_container(app: Any) -> AppContainer:
    return app.state.container


def get_event_bus(app: Any) -> EventBus:
    return get_container(app).bus


def get_job_manager(app: Any) -> Any:
    return get_container(app).jobs
