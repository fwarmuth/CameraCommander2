"""In-process TCP server that speaks the firmware serial protocol.

Byte-for-byte parity with ``contracts/firmware-protocol.md`` v1.1.x. The host's
real serial adapter reaches the mock via ``port: socket://127.0.0.1:9999`` so
both the mock and the production code paths exercise the same parsing and
timing budget logic.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from ..core.logging import logger
from ..hardware.tripod.protocol import _MICROSTEP_FROM_TOKEN, LINE_TERMINATOR
from .motion_model import MotionModel

DEFAULT_FW_VERSION = "1.1.0"


@dataclass(slots=True)
class MockFirmwareConfig:
    """Operator-tunable knobs for the mock firmware (mirrors CLI flags)."""

    initial_pan_deg: float = 0.0
    initial_tilt_deg: float = 0.0
    microstep: int = 1
    drivers_disabled: bool = False
    deg_per_second: float = 60.0
    settle_delay_s: float = 0.25
    fw_version: str = DEFAULT_FW_VERSION
    boot_banner: bool = True


@dataclass(slots=True)
class _ConnectionState:
    motion: MotionModel
    microstep: int
    move_task: asyncio.Task | None = None


class MockFirmwareServer:
    """Async TCP server speaking the firmware line protocol."""

    def __init__(self, config: MockFirmwareConfig | None = None) -> None:
        self.config = config or MockFirmwareConfig()
        self._server: asyncio.base_events.Server | None = None

    async def start(self, host: str = "127.0.0.1", port: int = 9999) -> int:
        """Bind and start serving. Returns the actual port (useful when port=0)."""

        self._server = await asyncio.start_server(self._handle_client, host=host, port=port)
        sock = self._server.sockets[0] if self._server.sockets else None
        actual = sock.getsockname()[1] if sock else port
        logger.info("mock firmware listening on {}:{}", host, actual)
        return actual

    async def serve_forever(self) -> None:
        if self._server is None:
            raise RuntimeError("call start() before serve_forever()")
        async with self._server:
            await self._server.serve_forever()

    async def stop(self) -> None:
        if self._server is None:
            return
        self._server.close()
        await self._server.wait_closed()
        self._server = None

    # --- per-connection state -----------------------------------------

    def _new_connection_state(self) -> _ConnectionState:
        cfg = self.config
        return _ConnectionState(
            motion=MotionModel(
                pan_deg=cfg.initial_pan_deg,
                tilt_deg=cfg.initial_tilt_deg,
                deg_per_second=cfg.deg_per_second,
                settle_delay_s=cfg.settle_delay_s,
                drivers_enabled=not cfg.drivers_disabled,
            ),
            microstep=cfg.microstep,
        )

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        logger.debug("mock firmware: client connected from {}", peer)
        state = self._new_connection_state()

        if self.config.boot_banner:
            banner = f"Dual-axis turntable - firmware {self.config.fw_version}{LINE_TERMINATOR}"
            writer.write(banner.encode("ascii"))
            await writer.drain()

        try:
            while True:
                raw = await reader.readline()
                if not raw:
                    break
                # The firmware tolerates \r\n on input but emits \n only.
                line = raw.decode("ascii", errors="replace").rstrip("\r\n").strip()
                if not line:
                    continue
                await self._dispatch(line, state, writer)
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        finally:
            if state.move_task:
                state.move_task.cancel()
            writer.close()
            await writer.wait_closed()
            logger.debug("mock firmware: client {} disconnected", peer)

    # --- protocol dispatch --------------------------------------------

    def _write_reply(self, writer: asyncio.StreamWriter, reply: str) -> None:
        writer.write((reply + LINE_TERMINATOR).encode("ascii"))

    async def _dispatch(
        self, line: str, state: _ConnectionState, writer: asyncio.StreamWriter
    ) -> None:
        # Single-letter tokens are case-insensitive per protocol §4 except where
        # the token's case carries direction sign for the helper commands; we
        # match the case-sensitive helpers explicitly.
        first = line[0]
        upper_first = first.upper()
        rest = line[1:].strip()

        # `V` — version ----------------------------------------------------
        if upper_first == "V" and not rest:
            self._write_reply(writer, f"VERSION {self.config.fw_version}")
            await writer.drain()
            return

        # `S` — status -----------------------------------------------------
        if upper_first == "S" and not rest:
            drv = "1" if state.motion.drivers_enabled else "0"
            self._write_reply(
                writer, f"STATUS {state.motion.pan_deg:.3f} {state.motion.tilt_deg:.3f} {drv}"
            )
            await writer.drain()
            return

        # `M <pan> <tilt>` — absolute move --------------------------------
        if upper_first == "M":
            try:
                parts = rest.split()
                if len(parts) != 2:
                    self._write_reply(writer, "ERR Syntax")
                    await writer.drain()
                    return
                pan = float(parts[0])
                tilt = float(parts[1])
            except ValueError:
                self._write_reply(writer, "ERR Syntax")
                await writer.drain()
                return
            if not state.motion.drivers_enabled:
                self._write_reply(writer, "ERR DRIVERS_DISABLED")
                await writer.drain()
                return

            if (
                abs(state.motion.pan_deg - pan) < 0.001
                and abs(state.motion.tilt_deg - tilt) < 0.001
            ):
                self._write_reply(writer, "ERR AlreadyAtTarget")
                await writer.drain()
                return

            if state.move_task:
                state.move_task.cancel()

            wait_s = state.motion.expected_move_duration_s(pan, tilt)
            self._write_reply(writer, f"ESTIMATE {wait_s:.2f}")
            await writer.drain()

            state.move_task = asyncio.create_task(self._run_move(pan, tilt, wait_s, state, writer))
            return

        # `X` — global stop -----------------------------------------------
        if first == "X" and not rest:
            if state.move_task:
                state.move_task.cancel()
                state.move_task = None
            self._write_reply(writer, "OK STOP")
            await writer.drain()
            return

        # `+` / `-` — speed adjust ----------------------------------------
        if first in {"+", "-"} and not rest:
            self._write_reply(writer, "OK SPEED")
            await writer.drain()
            return

        # `d` / `e` — driver toggle ---------------------------------------
        if first in {"d", "e"} and not rest:
            state.motion.drivers_enabled = first == "e"
            state.motion.reset_position()  # FR-011
            self._write_reply(
                writer, "OK DRIVERS ON" if state.motion.drivers_enabled else "OK DRIVERS OFF"
            )
            await writer.drain()
            return

        # microstep selection: tokens 1, 2, 4, 8, 6 -----------------------
        if first in _MICROSTEP_FROM_TOKEN and not rest:
            res = _MICROSTEP_FROM_TOKEN[first]
            state.microstep = res
            self._write_reply(writer, f"OK MICROSTEP {res}")
            await writer.drain()
            return

        # pan-axis helpers ------------------------------------------------
        if line in {"n", "N"}:
            self._write_reply(writer, "OK ROT STEP")
        elif line in {"c", "C"}:
            self._write_reply(writer, "OK ROT REV")
        elif line in {"r", "R"}:
            self._write_reply(writer, "OK ROT DIR")
        elif line == "x":
            self._write_reply(writer, "OK ROT STOP")
        # tilt-axis helpers -----------------------------------------------
        elif line in {"w", "W"}:
            self._write_reply(writer, "OK TILT STEP")
        elif line in {"p", "P"}:
            self._write_reply(writer, "OK TILT REV")
        elif line in {"t", "T"}:
            self._write_reply(writer, "OK TILT DIR")
        elif line == "z":
            self._write_reply(writer, "OK TILT STOP")
        else:
            self._write_reply(writer, "ERR Unknown")

        await writer.drain()

    async def _run_move(
        self,
        pan: float,
        tilt: float,
        duration: float,
        state: _ConnectionState,
        writer: asyncio.StreamWriter,
    ) -> None:
        start_pan = state.motion.pan_deg
        start_tilt = state.motion.tilt_deg
        start_time = asyncio.get_event_loop().time()
        end_time = start_time + duration

        try:
            # Emit progress every 200ms
            while (now := asyncio.get_event_loop().time()) < end_time:
                await asyncio.sleep(0.2)
                # Check again if we were cancelled during sleep
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= duration:
                    break
                frac = elapsed / duration
                state.motion.pan_deg = start_pan + (pan - start_pan) * frac
                state.motion.tilt_deg = start_tilt + (tilt - start_tilt) * frac
                self._write_reply(
                    writer, f"PROGRESS {state.motion.pan_deg:.3f} {state.motion.tilt_deg:.3f}"
                )
                await writer.drain()

            await asyncio.sleep(state.motion.settle_delay_s)
            state.motion.apply_move(pan, tilt)
            self._write_reply(writer, "DONE")
            await writer.drain()
        except asyncio.CancelledError:
            pass
        finally:
            state.move_task = None


async def run_server(
    config: MockFirmwareConfig | None = None,
    host: str = "127.0.0.1",
    port: int = 9999,
) -> None:
    """Convenience helper for the CLI entrypoint."""

    server = MockFirmwareServer(config)
    await server.start(host=host, port=port)
    await server.serve_forever()


__all__ = ["DEFAULT_FW_VERSION", "MockFirmwareConfig", "MockFirmwareServer", "run_server"]
