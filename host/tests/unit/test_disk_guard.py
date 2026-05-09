from __future__ import annotations

import pytest

from cameracommander.core.errors import DiskFullError
from cameracommander.services.disk import DiskGuard


def test_disk_guard_halts_when_free_space_below_threshold() -> None:
    guard = DiskGuard(
        output_dir=".",
        disk_min_free_bytes=200,
        initial_avg_frame_bytes=50,
        free_bytes_provider=lambda _: 149,
    )

    with pytest.raises(DiskFullError) as exc_info:
        guard.assert_room_for_next_frame(frames_remaining=3, running_avg_bytes=50)

    assert exc_info.value.details["required_bytes"] == 200
    assert exc_info.value.details["free_bytes"] == 149


def test_disk_guard_uses_larger_remaining_frame_estimate() -> None:
    guard = DiskGuard(
        output_dir=".",
        disk_min_free_bytes=200,
        initial_avg_frame_bytes=50,
        free_bytes_provider=lambda _: 249,
    )

    with pytest.raises(DiskFullError) as exc_info:
        guard.assert_room_for_next_frame(frames_remaining=5, running_avg_bytes=50)

    assert exc_info.value.details["required_bytes"] == 250
