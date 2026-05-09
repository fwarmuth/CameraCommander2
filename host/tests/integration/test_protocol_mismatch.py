from __future__ import annotations

import pytest

from cameracommander.core.config import TripodConfig
from cameracommander.core.errors import ProtocolVersionMismatchError
from cameracommander.hardware.tripod.serial_adapter import SerialTripodAdapter
from cameracommander.mock_firmware.server import MockFirmwareConfig, MockFirmwareServer


@pytest.mark.integration
@pytest.mark.asyncio
async def test_protocol_version_mismatch_marks_adapter_incompatible() -> None:
    firmware = MockFirmwareServer(MockFirmwareConfig(fw_version="2.0.0"))
    port = await firmware.start(port=0)
    adapter = SerialTripodAdapter(
        TripodConfig(serial={"port": f"socket://127.0.0.1:{port}"}, expected_protocol_major=1)
    )
    try:
        with pytest.raises(ProtocolVersionMismatchError):
            await adapter.open()
        status = await adapter.status()
    finally:
        await adapter.close()
        await firmware.stop()

    assert status.protocol_compatible is False
    assert status.state == "error"
