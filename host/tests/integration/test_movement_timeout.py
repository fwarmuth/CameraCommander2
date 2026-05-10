"""Integration test for movement timeout with progress feedback.

Verifies that long moves (longer than the default serial timeout) do not
trigger MotorStallError because the PROGRESS messages refresh the deadline.
"""

from __future__ import annotations

import asyncio
import pytest

from cameracommander.core.config import SerialConfig, TripodConfig
from cameracommander.core.errors import TripodError
from cameracommander.hardware.tripod.serial_adapter import SerialTripodAdapter
from cameracommander.mock_firmware.server import MockFirmwareConfig, MockFirmwareServer


@pytest.mark.asyncio
async def test_long_move_does_not_timeout() -> None:
    # 1. Setup mock firmware with very slow movement.
    # 5 degrees at 1.0 deg/s = 5 seconds.
    fw_cfg = MockFirmwareConfig(
        deg_per_second=1.0,
        settle_delay_s=0.1,
        initial_pan_deg=0.0,
        initial_tilt_deg=0.0,
    )
    server = MockFirmwareServer(fw_cfg)
    port = await server.start(port=0)
    
    try:
        # 2. Setup adapter with a short 1s timeout.
        # Without PROGRESS feedback, a 5s move would timeout.
        tripod_cfg = TripodConfig(
            serial=SerialConfig(
                port=f"socket://127.0.0.1:{port}",
                timeout=1.0,
            )
        )
        adapter = SerialTripodAdapter(tripod_cfg)
        await adapter.open()
        
        # 3. Execute move and verify it completes without error.
        res = await adapter.move_to(5.0, 0.0)
        assert res.pan_deg == pytest.approx(5.0)
        assert res.duration_s >= 5.0
        
        await adapter.close()
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_emergency_stop_interrupts_move() -> None:
    fw_cfg = MockFirmwareConfig(deg_per_second=1.0)
    server = MockFirmwareServer(fw_cfg)
    port = await server.start(port=0)
    
    try:
        tripod_cfg = TripodConfig(serial=SerialConfig(port=f"socket://127.0.0.1:{port}"))
        adapter = SerialTripodAdapter(tripod_cfg)
        await adapter.open()
        
        # Start a move.
        move_task = asyncio.create_task(adapter.move_to(10.0, 0.0))
        
        # Wait for motion to start.
        await asyncio.sleep(0.5)
        
        # Send emergency stop.
        await adapter.stop()
        
        # The move task should now raise the aborted error.
        with pytest.raises(TripodError, match="motion aborted by emergency stop"):
            await move_task
        
        await adapter.close()
    finally:
        await server.stop()
