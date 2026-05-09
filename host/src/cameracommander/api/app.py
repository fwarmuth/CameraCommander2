"""FastAPI factory for the CameraCommander host.

The factory keeps the surface narrow: build the app, mount the routers,
register lifespan hooks that open and close hardware adapters, and serve the
prebuilt web SPA from ``web/dist/`` if it's present alongside the host. Heavy
service wiring (jobs, safety, calibration) lands during the User Story 1 phase;
this module is the foundational scaffold.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ..core.logging import logger
from ..hardware.camera.mock import MockCameraAdapter
from ..persistence.sessions_fs import SessionRepository
from ..services.calibration import CalibrationService
from ..services.jobs import JobManager
from ..services.post_process import VideoAssembler
from .deps import AppContainer
from .routes.events import router as events_router
from .routes.health import router as health_router
from .routes.jobs import router as jobs_router
from .routes.sessions import router as sessions_router
from .routes.tripod import router as tripod_router
from .websocket import EventBus

if TYPE_CHECKING:
    from ..hardware.camera.base import CameraAdapter
    from ..hardware.tripod.base import TripodAdapter
else:
    CameraAdapter = object
    TripodAdapter = object


def _resolve_web_dist() -> Path | None:
    """Locate ``web/dist/`` relative to the running host package.

    The Pi-side deploy puts ``host/`` and ``web/dist/`` as siblings under
    ``/opt/cameracommander/``; in development they're siblings in the repo. If
    no build is present, return None — the host then exposes only the API and
    logs a one-time warning.
    """

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "web" / "dist"
        if candidate.is_dir():
            return candidate
        # Stop searching once we've passed the repo root.
        if (parent / ".git").exists() or (parent / "host").is_dir():
            return candidate if candidate.is_dir() else None
    return None


def create_app(
    *,
    camera: CameraAdapter | None = None,
    tripod: TripodAdapter | None = None,
    session_root: str | Path | None = None,
    serve_static: bool = True,
) -> FastAPI:
    """Build the FastAPI application.

    Adapters are passed in (rather than constructed inside) so the CLI's
    ``--mock`` flags can swap implementations cleanly. Route modules added in
    later phases (jobs, sessions, camera, tripod) attach via the same factory.
    """

    event_bus = EventBus()
    camera_adapter = camera or MockCameraAdapter()
    calibration = CalibrationService(event_bus)
    sessions = SessionRepository(session_root)
    jobs = JobManager(
        camera=camera_adapter,
        tripod=tripod,
        calibration=calibration,
        sessions=sessions,
        event_bus=event_bus,
    )
    post_process = VideoAssembler(event_bus)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if camera_adapter is not None:
            await camera_adapter.open()
        if tripod is not None:
            await tripod.open()
        try:
            yield
        finally:
            if tripod is not None:
                with contextlib.suppress(Exception):
                    await tripod.close()
            if camera_adapter is not None:
                with contextlib.suppress(Exception):
                    await camera_adapter.close()

    app = FastAPI(
        title="CameraCommander2 Host API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.container = AppContainer(
        event_bus=event_bus,
        camera=camera_adapter,
        tripod=tripod,
        calibration=calibration,
        jobs=jobs,
        sessions=sessions,
        post_process=post_process,
    )

    app.include_router(events_router)
    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(tripod_router)
    app.include_router(sessions_router)

    if serve_static:
        dist = _resolve_web_dist()
        if dist is not None:
            app.mount("/", StaticFiles(directory=dist, html=True), name="web")
        else:
            logger.warning(
                "web/dist/ not found alongside host/; serving API only. "
                "Build the SPA with `cd web && npm ci && npm run build`."
            )

    return app


__all__ = ["create_app"]
