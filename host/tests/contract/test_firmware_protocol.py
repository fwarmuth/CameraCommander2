import pytest
from cameracommander.hardware.tripod.protocol import format_move, parse_status, ParsedStatus

def test_format_move():
    assert format_move(10.5, -5.0) == "M 10.500000 -5.000000\n"

def test_parse_status_valid():
    line = "STATUS 12.345 -6.789 1\n"
    expected = ParsedStatus(pan=12.345, tilt=-6.789, drivers=True)
    assert parse_status(line) == expected

def test_parse_status_invalid():
    with pytest.raises(ValueError, match="Invalid STATUS reply"):
        parse_status("OK NOTHING")
