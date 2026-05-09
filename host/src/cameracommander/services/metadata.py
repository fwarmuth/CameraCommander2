"""Per-frame metadata persistence."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

try:  # pragma: no cover - exercised when piexif is importable and JPEG accepts EXIF
    import piexif
except Exception:  # pragma: no cover
    piexif = None

from ..core.config import Configuration


class MetadataWriter:
    def __init__(self, frames_dir: Path, *, strategy: str = "auto") -> None:
        self.frames_dir = frames_dir
        self.strategy = strategy
        self.csv_path = frames_dir / "metadata.csv"

    def write_frame(
        self,
        *,
        index: int,
        image_path: Path,
        pan_deg: float,
        tilt_deg: float,
        config: Configuration,
    ) -> Path:
        settings_hash = hashlib.sha256(
            json.dumps(config.camera.settings, sort_keys=True).encode("utf-8")
        ).hexdigest()
        row = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "index": index,
            "filename": image_path.name,
            "pan": pan_deg,
            "tilt": tilt_deg,
            "settings_hash": settings_hash,
        }
        if self.strategy in {"auto", "exif"} and self._try_exif(image_path, row):
            # Keep a CSV sidecar even when EXIF succeeds so operators and tests
            # have a simple tabular metadata stream alongside frames.
            self._append_csv(row)
            return image_path
        self._append_csv(row)
        return self.csv_path

    def _try_exif(self, image_path: Path, row: dict[str, object]) -> bool:
        if piexif is None:
            return False
        try:
            exif = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
            comment = json.dumps(row, sort_keys=True)
            exif["Exif"][piexif.ExifIFD.UserComment] = (
                b"UTF8\x00\x00\x00" + comment.encode("utf-8")
            )
            piexif.insert(piexif.dump(exif), str(image_path))
            return True
        except Exception:
            if self.strategy == "exif":
                raise
            return False

    def _append_csv(self, row: dict[str, object]) -> None:
        is_new = not self.csv_path.exists()
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        with self.csv_path.open("a", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=["timestamp", "index", "filename", "pan", "tilt", "settings_hash"],
            )
            if is_new:
                writer.writeheader()
            writer.writerow(row)


__all__ = ["MetadataWriter"]
