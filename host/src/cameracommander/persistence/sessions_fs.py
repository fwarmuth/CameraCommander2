"""Filesystem-backed session repository."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..core.config import Configuration, dump_configuration
from ..core.models import JobKind, JobStatus, Session, SessionAsset, SessionMetrics


class SessionRepository:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or "~/.cameracommander/sessions").expanduser()
        self.root.mkdir(parents=True, exist_ok=True)

    def session_dir(self, session_id: str) -> Path:
        return self.root / session_id

    def create(self, session_id: str, config: Configuration) -> Session:
        session = Session(
            session_id=session_id,
            kind=JobKind(config.sequence.kind),
            status=JobStatus.running,
            created_at=config.metadata.created_at,
            name=config.metadata.name,
            tags=list(config.metadata.tags),
            frames_planned=getattr(config.sequence, "total_frames", 0),
            configuration=config,
            metrics=SessionMetrics(
                frames_planned=getattr(config.sequence, "total_frames", 0),
            ),
        )
        path = self.session_dir(session_id)
        path.mkdir(parents=True, exist_ok=True)
        (path / "config.yaml").write_text(dump_configuration(config), encoding="utf-8")
        self.save(session)
        return session

    def save(self, session: Session) -> None:
        path = self.session_dir(session.session_id)
        path.mkdir(parents=True, exist_ok=True)
        (path / "metadata.json").write_text(
            session.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def get(self, session_id: str) -> Session:
        path = self.session_dir(session_id) / "metadata.json"
        if not path.exists():
            raise KeyError(session_id)
        return Session.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self) -> list[Session]:
        sessions: list[Session] = []
        for meta in self.root.glob("*/metadata.json"):
            try:
                sessions.append(Session.model_validate_json(meta.read_text(encoding="utf-8")))
            except Exception:
                continue
        return sorted(sessions, key=lambda item: item.created_at, reverse=True)

    def delete(self, session_id: str) -> None:
        shutil.rmtree(self.session_dir(session_id))

    def add_asset(
        self,
        session: Session,
        *,
        path: Path,
        kind: str,
        label: str | None = None,
        content_type: str | None = None,
    ) -> Session:
        asset = SessionAsset(
            path=str(path),
            kind=kind,  # type: ignore[arg-type]
            size_bytes=path.stat().st_size if path.exists() else None,
            label=label,
            content_type=content_type,
        )
        session.assets.append(asset)
        self.save(session)
        return session


__all__ = ["SessionRepository"]
