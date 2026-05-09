"""Per-frame metadata management."""

from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime


class MetadataWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with open(self.path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "index", "pan", "tilt"])

    def add_frame(self, index: int, pan: float, tilt: float) -> None:
        with open(self.path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().isoformat(), index, pan, tilt])
