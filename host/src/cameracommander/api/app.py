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
    container = AppContainer(camera=camera, tripod=tripod, bus=bus)
    
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

    app = FastAPI(
        title="CameraCommander2",
        version="0.1.0",
        lifespan=lifespan
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount routers (Phases 3-6)
    # Routes mounted below(camera_router, prefix="/api/camera", tags=["camera"])
    from .routes import health, jobs
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
    from .routes import camera, tripod
    app.include_router(camera.router, prefix="/api/camera", tags=["camera"])
    app.include_router(tripod.router, prefix="/api/tripod", tags=["tripod"])
    from .routes import sessions
    app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
    
    # Static files (Web SPA)
    web_dist = Path(__file__).parents[4] / "web" / "dist"
    if web_dist.exists():
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="static")
    
    return app


__all__ = ["create_app"]
