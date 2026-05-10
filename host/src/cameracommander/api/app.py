"""FastAPI factory for the CameraCommander host.

The factory keeps the surface narrow: build the app, mount the routers,
register lifespan hooks that open and close hardware adapters, and serve the
prebuilt web SPA from ``web/dist/`` when present.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ..core.errors import CameraCommanderError

from ..hardware.camera.base import CameraAdapter
from ..hardware.tripod.base import TripodAdapter
from ..core.logging import logger
from .deps import AppContainer
from .websocket import EventBus


def create_app(
    camera: CameraAdapter | None = None,
    tripod: TripodAdapter | None = None,
    session_root: Path | None = None,
) -> FastAPI:
    """Factory to create the FastAPI application instance."""

    logger.info("creating app with camera={}, tripod={}", camera is not None, tripod is not None)
    bus = EventBus()
    from ..persistence.sessions_fs import SessionRepository
    from ..services.calibration import CalibrationService
    from ..services.disk import DiskGuard
    from ..services.jobs import JobManager
    from ..services.safety import SafetyService

    if session_root is None:
        session_root = Path.home() / ".cameracommander" / "sessions"

    from ..services.tripod_polling import TripodPositionPublisher

    calibration = CalibrationService(bus)
    safety = SafetyService(tilt_min=-90, tilt_max=90)  # Default
    disk = DiskGuard(session_root)
    sessions = SessionRepository(session_root)

    jobs = JobManager(
        bus=bus,
        camera=camera,
        tripod=tripod,
        calibration=calibration,
        safety=safety,
        disk=disk,
    )

    publisher = TripodPositionPublisher(tripod=tripod, jobs=jobs, event_bus=bus)

    container = AppContainer(
        camera=camera,
        tripod=tripod,
        bus=bus,
        jobs=jobs,
        calibration=calibration,
        safety=safety,
        sessions=sessions,
    )

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Connect hardware
        if container.camera:
            await container.camera.open()
        if container.tripod:
            await container.tripod.open()
            publisher.start()

        yield

        # Cleanup hardware
        await publisher.stop()
        if container.camera:
            await container.camera.close()
        if container.tripod:
            await container.tripod.close()

    app = FastAPI(title="CameraCommander2", version="0.1.0", lifespan=lifespan)
    app.state.container = container

    @app.exception_handler(CameraCommanderError)
    async def domain_exception_handler(request: Request, exc: CameraCommanderError):
        # Map class name to snake_case error code
        import re

        error_code = re.sub(
            r"(?<!^)(?=[A-Z])", "_", exc.__class__.__name__.replace("Error", "")
        ).lower()

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": error_code,
                "message": exc.message,
                "details": getattr(exc, "__dict__", {}),
            },
        )

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
