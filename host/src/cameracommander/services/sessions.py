"""Thin service wrapper around the filesystem session repository."""

from __future__ import annotations

from ..persistence.sessions_fs import SessionRepository

__all__ = ["SessionRepository"]
