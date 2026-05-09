from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from ...core.config import dump_configuration
from ...core.models import Session
from ..deps import get_container

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("/{session_id}/config", operation_id="getSessionConfig", response_model=None)
async def get_session_config(request: Request, session_id: str):
    try:
        session: Session = get_container(request).sessions.get(session_id)
    except KeyError as exc:
        raise HTTPException(404, {"error": "not_found", "message": "session not found"}) from exc
    accept = request.headers.get("accept", "")
    if "application/x-yaml" in accept:
        return Response(
            dump_configuration(session.configuration),
            media_type="application/x-yaml",
        )
    return session.configuration.model_dump(mode="json")


__all__ = ["router"]
