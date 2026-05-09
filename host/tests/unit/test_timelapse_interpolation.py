from __future__ import annotations

from cameracommander.core.config import Angles
from cameracommander.services.timelapse import _linear_interpolate


def test_linear_interpolate_keeps_tilt_inside_window() -> None:
    frames = list(
        _linear_interpolate(
            start=Angles(pan_deg=0.0, tilt_deg=-10.0),
            target=Angles(pan_deg=40.0, tilt_deg=10.0),
            total_frames=5,
        )
    )

    assert [round(p.tilt_deg, 3) for p in frames] == [-10.0, -5.0, 0.0, 5.0, 10.0]
    assert all(-10.0 <= p.tilt_deg <= 10.0 for p in frames)
    assert frames[0].pan_deg == 0.0
    assert frames[-1].pan_deg == 40.0
