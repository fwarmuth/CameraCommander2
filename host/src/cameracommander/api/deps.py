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


from typing import Union
from fastapi import Request, WebSocket

def get_container(request: Union[Request, WebSocket]) -> AppContainer:
    return request.app.state.container


def get_event_bus(request: Union[Request, WebSocket]) -> EventBus:
    return get_container(request).bus


def get_job_manager(request: Union[Request, WebSocket]) -> Any:
    return get_container(request).jobs
