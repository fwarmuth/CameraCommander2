"""Disk space monitoring and protection."""

from __future__ import annotations

import shutil
from pathlib import Path
from ..core.errors import DiskFullError


class DiskGuard:
    def __init__(self, path: Path, min_free_bytes: int = 200_000_000) -> None:
        self.path = path
        self.min_free_bytes = min_free_bytes

    def assert_room_for_next_frame(self, frames_remaining: int, avg_bytes: int) -> None:
        usage = shutil.disk_usage(self.path)
        needed = max(avg_bytes, self.min_free_bytes)
        if usage.free < needed:
            raise DiskFullError(f"Insufficient disk space: {usage.free} bytes free, {needed} needed")
