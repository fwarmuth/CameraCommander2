"""Shared CLI helpers."""

from __future__ import annotations

from pathlib import Path

from cameracommander.core.config import Configuration, load_configuration
from cameracommander.hardware.camera.gphoto import GphotoCameraAdapter
from cameracommander.hardware.camera.mock import MockCameraAdapter
from cameracommander.hardware.tripod.serial_adapter import SerialTripodAdapter


def load_config(path: Path) -> Configuration:
    return load_configuration(path)


def make_camera(config: Configuration, *, mock: bool = False):
    if mock:
        return MockCameraAdapter()
    return GphotoCameraAdapter(model_substring=config.camera.model_substring)


def make_tripod(config: Configuration, *, mock: bool = False):
    if mock:
        patched = config.model_copy(deep=True)
        patched.tripod.serial.port = "socket://127.0.0.1:9999"
        return SerialTripodAdapter(patched.tripod)
    return SerialTripodAdapter(config.tripod)


__all__ = ["load_config", "make_camera", "make_tripod"]
