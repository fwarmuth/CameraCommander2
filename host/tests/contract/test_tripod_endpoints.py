from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from cameracommander.api.app import create_app
from cameracommander.core.models import TripodState, TripodStatus
from cameracommander.hardware.camera.mock import MockCameraAdapter
from cameracommander.hardware.tripod.base import MoveResult, StatusReport
from cameracommander.services.safety import SafetyService


@dataclass
class FakeTripod:
    pan: float = 0.0
    tilt: float = 0.0
    drivers_enabled: bool = True
    opened: bool = False
    stopped: bool = False

    async def open(self) -> None:
        self.opened = True

    async def close(self) -> None:
        self.opened = False

    async def status(self) -> TripodStatus:
        return TripodStatus(
            state=TripodState.connected,
            firmware_version="1.0.1",
            drivers_enabled=self.drivers_enabled,
            position_pan_deg=self.pan,
            position_tilt_deg=self.tilt,
        )

    async def version(self) -> str:
        return "1.0.1"

    async def report(self) -> StatusReport:
        return StatusReport(self.pan, self.tilt, self.drivers_enabled)

    async def move_to(
        self,
        pan_deg: float,
        tilt_deg: float,
        *,
        expected_duration_s: float | None = None,
    ) -> MoveResult:
        self.pan = pan_deg
        self.tilt = tilt_deg
        return MoveResult(pan_deg=pan_deg, tilt_deg=tilt_deg, duration_s=0.0)

    async def nudge(
        self,
        *,
        delta_pan_deg: float = 0.0,
        delta_tilt_deg: float = 0.0,
    ) -> MoveResult:
        return await self.move_to(self.pan + delta_pan_deg, self.tilt + delta_tilt_deg)

    async def home(self) -> None:
        self.pan = 0.0
        self.tilt = 0.0

    async def set_drivers(self, enabled: bool) -> None:
        self.drivers_enabled = enabled
        self.pan = 0.0
        self.tilt = 0.0

    async def stop(self) -> None:
        self.stopped = True

    async def set_microstep(self, microstep: int) -> None:
        return None


def _app(tmp_path: Path, tripod: FakeTripod | None = None):
    app = create_app(
        camera=MockCameraAdapter(),
        tripod=tripod or FakeTripod(),
        serve_static=False,
        session_root=tmp_path,
    )
    app.state.container.safety = SafetyService(tilt_min_deg=-10.0, tilt_max_deg=10.0)
    return app


@pytest.mark.asyncio
async def test_tripod_manual_endpoints_happy_paths(tmp_path: Path) -> None:
    tripod = FakeTripod()
    app = _app(tmp_path, tripod)
    app.state.container.calibration.mark_homed()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        status = await client.get("/api/tripod/status")
        move = await client.post("/api/tripod/move", json={"pan_deg": 5.0, "tilt_deg": 4.0})
        nudge = await client.post(
            "/api/tripod/nudge",
            json={"delta_pan_deg": 1.0, "delta_tilt_deg": -2.0},
        )
        drivers = await client.put("/api/tripod/drivers", json={"enabled": False})
        stop = await client.post("/api/tripod/stop")

    assert status.status_code == 200
    assert move.status_code == 200
    assert move.json()["position_tilt_deg"] == 4.0
    assert nudge.status_code == 200
    assert nudge.json()["position_pan_deg"] == 6.0
    assert nudge.json()["position_tilt_deg"] == 2.0
    assert drivers.status_code == 200
    assert drivers.json()["drivers_enabled"] is False
    assert stop.status_code == 200
    assert tripod.stopped is True


@pytest.mark.asyncio
async def test_tripod_move_requires_calibration_but_nudge_does_not(tmp_path: Path) -> None:
    app = _app(tmp_path)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        move = await client.post("/api/tripod/move", json={"pan_deg": 1.0, "tilt_deg": 1.0})
        nudge = await client.post(
            "/api/tripod/nudge",
            json={"delta_pan_deg": 1.0, "delta_tilt_deg": 1.0},
        )

    assert move.status_code == 412
    assert move.json()["error"] == "calibration_required"
    assert nudge.status_code == 200


@pytest.mark.asyncio
async def test_tripod_tilt_limit_and_job_lock(tmp_path: Path) -> None:
    app = _app(tmp_path)
    app.state.container.calibration.mark_homed()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        out_of_range = await client.post(
            "/api/tripod/move",
            json={"pan_deg": 1.0, "tilt_deg": 90.0},
        )
        app.state.container.jobs._active_job_id = "locked"
        locked = await client.post("/api/tripod/stop")

    assert out_of_range.status_code == 422
    assert out_of_range.json()["error"] == "tilt_limit"
    assert locked.status_code == 409
    assert locked.json()["error"] == "job_already_running"
