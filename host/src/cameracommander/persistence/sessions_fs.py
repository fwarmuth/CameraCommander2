"""Filesystem-based session storage."""

from __future__ import annotations

import json
from pathlib import Path
from ..core.models import Session, SessionSummary, JobStatus, JobKind


class SessionRepository:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _session_path(self, sid: str) -> Path:
        return self.root / sid

    def list_sessions(self) -> list[SessionSummary]:
        summaries = []
        for p in self.root.iterdir():
            if p.is_dir() and (p / "metadata.json").exists():
                with open(p / "metadata.json") as f:
                    data = json.load(f)
                    summaries.append(SessionSummary.model_validate(data))
        return sorted(summaries, key=lambda s: s.created_at, reverse=True)

    def save_session(self, session: Session) -> None:
        path = self._session_path(session.session_id)
        path.mkdir(parents=True, exist_ok=True)
        with open(path / "metadata.json", "w") as f:
            f.write(session.model_dump_json(indent=2))
