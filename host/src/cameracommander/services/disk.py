"""Disk-space guard for capture workflows."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from ..core.errors import DiskFullError

FreeBytesProvider = Callable[[Path], int]


def _default_free_bytes(path: Path) -> int:
    path.mkdir(parents=True, exist_ok=True)
    return shutil.disk_usage(path).free


class DiskGuard:
    def __init__(
        self,
        output_dir: str | Path,
        *,
        disk_min_free_bytes: int,
        initial_avg_frame_bytes: int,
        free_bytes_provider: FreeBytesProvider = _default_free_bytes,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.disk_min_free_bytes = disk_min_free_bytes
        self.initial_avg_frame_bytes = initial_avg_frame_bytes
        self._free_bytes_provider = free_bytes_provider

    def assert_room_for_next_frame(
        self,
        *,
        frames_remaining: int,
        running_avg_bytes: int | None = None,
    ) -> None:
        avg = running_avg_bytes or self.initial_avg_frame_bytes
        required = max(frames_remaining * avg, self.disk_min_free_bytes)
        free = self._free_bytes_provider(self.output_dir)
        if free < required:
            raise DiskFullError(
                f"insufficient disk space: need {required} bytes, have {free}",
                required_bytes=required,
                free_bytes=free,
            )


__all__ = ["DiskGuard"]
