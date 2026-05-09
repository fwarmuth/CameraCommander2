import pytest
from pydantic import ValidationError
from cameracommander.core.config import Configuration, SafetyConfig, TimelapseSequenceConfig, Angles

def test_safety_config_tilt_range():
    # Valid
    SafetyConfig(tilt_min_deg=-45, tilt_max_deg=45)
    # Invalid
    with pytest.raises(ValidationError, match="tilt_max_deg must be >= tilt_min_deg"):
        SafetyConfig(tilt_min_deg=10, tilt_max_deg=0)

def test_timelapse_sequence_timing():
    angles = Angles(pan_deg=0, tilt_deg=0)
    # Valid
    TimelapseSequenceConfig(total_frames=10, interval_s=5, settle_time_s=1, start=angles, target=angles)
    # Invalid: settle > interval
    with pytest.raises(ValidationError, match="settle_time_s: must be <= interval_s"):
         TimelapseSequenceConfig(total_frames=10, interval_s=1, settle_time_s=2, start=angles, target=angles)
