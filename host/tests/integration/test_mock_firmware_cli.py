from __future__ import annotations

import asyncio
import time

import pytest

from cameracommander.mock_firmware.server import MockFirmwareConfig, MockFirmwareServer


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mock_firmware_replies_version_and_timed_move() -> None:
    server = MockFirmwareServer(MockFirmwareConfig(deg_per_second=10.0, settle_delay_s=0.0))
    port = await server.start(port=0)
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        await reader.readline()  # boot banner

        writer.write(b"V\n")
        await writer.drain()
        version = (await reader.readline()).decode("ascii").strip()

        started = time.monotonic()
        writer.write(b"M 2 0\n")
        await writer.drain()
        
        replies = []
        while True:
            line = (await reader.readline()).decode("ascii").strip()
            replies.append(line)
            if line == "DONE" or line.startswith("ERR"):
                break
        
        elapsed = time.monotonic() - started
        writer.close()
        await writer.wait_closed()
    finally:
        await server.stop()

    assert version == "VERSION 1.1.0"
    assert replies[0].startswith("ESTIMATE")
    assert replies[-1] == "DONE"
    assert elapsed == pytest.approx(0.2, abs=0.2)
