"""Unit tests for the Pydantic v2 configuration validators.

Covers each rule listed in ``data-model.md §6 Validation rules cross-reference``
plus the YAML loader / dumper round trip.
"""

from __future__ import annotations

import pytest

from cameracommander.core.config import (
    Configuration,
    dump_configuration,
    load_configuration,
)
from cameracommander.core.errors import ConfigError


def _base_yaml(*, sequence_block: str | None = None) -> str:
    seq = sequence_block or """
sequence:
  kind: timelapse
  total_frames: 10
  interval_s: 5.0
  settle_time_s: 0.5
  start: { pan_deg: 0.0, tilt_deg: 0.0 }
  target: { pan_deg: 30.0, tilt_deg: 10.0 }
"""
    return f"""
metadata:
  name: "Test"
camera: {{}}
tripod:
  serial:
    port: "socket://127.0.0.1:9999"
safety:
  tilt_min_deg: -45.0
  tilt_max_deg: 45.0
output:
  output_dir: "./out"
{seq}
""".strip() + "\n"


def test_baseline_config_parses() -> None:
    cfg = load_configuration(_base_yaml())
    assert isinstance(cfg, Configuration)
    assert cfg.metadata.name == "Test"
    assert cfg.sequence.kind == "timelapse"


def test_yaml_round_trip_preserves_shape() -> None:
    cfg1 = load_configuration(_base_yaml())
    text = dump_configuration(cfg1)
    cfg2 = load_configuration(text)
    assert cfg1.model_dump(mode="json") == cfg2.model_dump(mode="json")


def test_total_frames_minimum() -> None:
    bad = _base_yaml(
        sequence_block="""
sequence:
  kind: timelapse
  total_frames: 1
  interval_s: 5.0
  settle_time_s: 0.5
  start: { pan_deg: 0.0, tilt_deg: 0.0 }
  target: { pan_deg: 30.0, tilt_deg: 10.0 }
"""
    )
    with pytest.raises(ConfigError):
        load_configuration(bad)


def test_settle_time_must_be_le_interval() -> None:
    bad = _base_yaml(
        sequence_block="""
sequence:
  kind: timelapse
  total_frames: 10
  interval_s: 1.0
  settle_time_s: 5.0
  start: { pan_deg: 0.0, tilt_deg: 0.0 }
  target: { pan_deg: 30.0, tilt_deg: 10.0 }
"""
    )
    with pytest.raises(ConfigError, match="FR-017"):
        load_configuration(bad)


def test_filename_template_must_include_zero_padded_index() -> None:
    bad = _base_yaml().replace(
        'output_dir: "./out"',
        'output_dir: "./out"\n  frame_filename_template: "frame_{index}.jpg"',
    )
    with pytest.raises(ConfigError, match="FR-043"):
        load_configuration(bad)


def test_tilt_window_rejects_out_of_range_keyframe() -> None:
    bad = _base_yaml(
        sequence_block="""
sequence:
  kind: timelapse
  total_frames: 10
  interval_s: 5.0
  settle_time_s: 0.5
  start: { pan_deg: 0.0, tilt_deg: 0.0 }
  target: { pan_deg: 30.0, tilt_deg: 90.0 }
"""
    )
    with pytest.raises(ConfigError, match="FR-009"):
        load_configuration(bad)


def test_tilt_window_rejects_interpolated_excursion() -> None:
    """An interpolated frame can leave the tilt window even if both keyframes are inside."""

    bad = _base_yaml().replace("tilt_max_deg: 45.0", "tilt_max_deg: 5.0").replace(
        "tilt_deg: 10.0", "tilt_deg: 4.0"
    )
    # Keyframes are inside [-45, 5] (start tilt 0, target tilt 4) — but if we
    # increase the target above the window we should be rejected.
    bad2 = bad.replace("tilt_deg: 4.0", "tilt_deg: 6.0")
    with pytest.raises(ConfigError, match="FR-009"):
        load_configuration(bad2)


def test_safety_window_must_be_ordered() -> None:
    bad = _base_yaml().replace("tilt_min_deg: -45.0", "tilt_min_deg: 50.0")
    with pytest.raises(ConfigError):
        load_configuration(bad)


def test_video_pan_sequence_parses() -> None:
    cfg = load_configuration(
        _base_yaml(
            sequence_block="""
sequence:
  kind: video_pan
  duration_s: 30.0
  start: { pan_deg: 0.0, tilt_deg: 0.0 }
  target: { pan_deg: 90.0, tilt_deg: 5.0 }
"""
        )
    )
    assert cfg.sequence.kind == "video_pan"
    assert cfg.sequence.duration_s == 30.0


def test_microstep_enum_enforced() -> None:
    bad = _base_yaml().replace(
        'serial:\n    port: "socket://127.0.0.1:9999"',
        'serial:\n    port: "socket://127.0.0.1:9999"\n  microstep: 3',
    )
    with pytest.raises(ConfigError):
        load_configuration(bad)


def test_unknown_top_level_key_rejected() -> None:
    bad = _base_yaml() + "extra: { foo: bar }\n"
    with pytest.raises(ConfigError):
        load_configuration(bad)
