"""Time-mode-based motion simulation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class MotionState:
    pan: float = 0.0
    tilt: float = 0.0
    drivers_enabled: bool = False
    microstep: int = 16
    deg_per_second: float = 10.0


class MotionModel:
    """Predicts DONE timing and manages virtual position."""

    def __init__(self, state: MotionState) -> None:
        self.state = state
        self._lock = asyncio.Lock()

    async def move_to(self, pan: float, tilt: float) -> None:
        async with self._lock:
            delta_pan = abs(pan - self.state.pan)
            delta_tilt = abs(tilt - self.state.tilt)
            max_delta = max(delta_pan, delta_tilt)
            
            duration = max_delta / self.state.deg_per_second
            await asyncio.sleep(duration)
            
            self.state.pan = pan
            self.state.tilt = tilt
