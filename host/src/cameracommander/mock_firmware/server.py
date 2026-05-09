"""Mock firmware TCP server with line-protocol parity."""

from __future__ import annotations

import asyncio
from typing import Any

from .motion_model import MotionModel, MotionState


class MockFirmwareConfig:
    def __init__(
        self, 
        deg_per_second: float = 10.0,
        fw_version: str = "1.0.1",
        settle_delay_s: float = 0.1
    ) -> None:
        self.deg_per_second = deg_per_second
        self.fw_version = fw_version
        self.settle_delay_s = settle_delay_s


class MockFirmwareServer:
    """TCP server that speaks the CameraCommander2 serial protocol."""

    def __init__(self, config: MockFirmwareConfig) -> None:
        self.cfg = config
        self.model = MotionModel(MotionState(deg_per_second=config.deg_per_second))
        self._server: Any = None

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        # Drain banner (simulation)
        writer.write(f"Dual-axis turntable – firmware {self.cfg.fw_version}\n".encode())
        await writer.drain()

        while True:
            line = await reader.readline()
            if not line:
                break
            
            cmd = line.decode().strip().upper()
            if not cmd:
                continue

            reply = "ERR Unknown\n"
            
            if cmd == "V":
                reply = f"VERSION {self.cfg.fw_version}\n"
            elif cmd == "S":
                reply = f"STATUS {self.model.state.pan:.3f} {self.model.state.tilt:.3f} {1 if self.model.state.drivers_enabled else 0}\n"
            elif cmd == "E":
                self.model.state.drivers_enabled = True
                self.model.state.pan = 0.0
                self.model.state.tilt = 0.0
                reply = "OK DRIVERS ON\n"
            elif cmd == "D":
                self.model.state.drivers_enabled = False
                self.model.state.pan = 0.0
                self.model.state.tilt = 0.0
                reply = "OK DRIVERS OFF\n"
            elif cmd.startswith("M "):
                try:
                    _, p, t = cmd.split()
                    await self.model.move_to(float(p), float(t))
                    await asyncio.sleep(self.cfg.settle_delay_s)
                    reply = "DONE\n"
                except Exception:
                    reply = "ERR Syntax\n"
            elif cmd == "X":
                reply = "OK STOP\n"
            
            writer.write(reply.encode())
            await writer.drain()

        writer.close()
        await writer.wait_closed()

    async def start(self, host: str = "127.0.0.1", port: int = 9999) -> None:
        self._server = await asyncio.start_server(self._handle_client, host=host, port=port)
        await self._server.serve_forever()


async def run_server(cfg: MockFirmwareConfig, host: str, port: int) -> None:
    server = MockFirmwareServer(cfg)
    await server.start(host, port)
