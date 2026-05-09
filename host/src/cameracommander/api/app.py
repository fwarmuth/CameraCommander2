"""FastAPI factory for the CameraCommander host.

The factory keeps the surface narrow: build the app, mount the routers,
register lifespan hooks that open and close hardware adapters, and serve the
prebuilt web SPA from ``web/dist/`` when present.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .deps import AppContainer
from .websocket import EventBus
from ..hardware.camera.base import CameraAdapter
from ..hardware.tripod.base import TripodAdapter


def create_app(
    camera: CameraAdapter | None = None,
    tripod: TripodAdapter | None = None,
) -> FastAPI:
    """Factory to create the FastAPI application instance."""

    bus = EventBus()
    from ..services.calibration import CalibrationService
    from ..services.disk import DiskGuard
    from ..services.jobs import JobManager
    from ..services.safety import SafetyService

    calibration = CalibrationService(bus)
    safety = SafetyService(tilt_min=-90, tilt_max=90)  # Default
    disk = DiskGuard(Path.home() / ".cameracommander" / "sessions")
    jobs = JobManager(
        bus=bus,
        camera=camera,
        tripod=tripod,
        calibration=calibration,
        safety=safety,
        disk=disk,
    )

    container = AppContainer(
        camera=camera,
        tripod=tripod,
        bus=bus,
        jobs=jobs,
        calibration=calibration,
        safety=safety,
    )

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Connect hardware
        if container.camera:
            await container.camera.open()
        if container.tripod:
            await container.tripod.open()

        yield

        # Cleanup hardware
        if container.camera:
            await container.camera.close()
        if container.tripod:
            await container.tripod.close()

    app = FastAPI(title="CameraCommander2", version="0.1.0", lifespan=lifespan)
    app.state.container = container

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from .routes import camera, events, health, jobs, sessions, tripod

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
    app.include_router(camera.router, prefix="/api/camera", tags=["camera"])
    app.include_router(tripod.router, prefix="/api/tripod", tags=["tripod"])
    app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
    app.include_router(events.router, tags=["events"])

    # Static files (Web SPA) - must be last
    web_dist = Path(__file__).parents[4] / "web" / "dist"
    if web_dist.exists():
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="static")
    
    return app


__all__ = ["create_app"]
