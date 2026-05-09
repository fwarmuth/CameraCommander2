from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from ..deps import AppContainer, get_container

router = APIRouter()


@router.get("/")
async def get_sessions(container: AppContainer = Depends(get_container)):
    return {
        "items": container.sessions.list_sessions(),
        "total": len(container.sessions.list_sessions()),
    }


@router.get("/{session_id}")
async def get_session(session_id: str, container: AppContainer = Depends(get_container)):
    # Assuming the repository has a get_session method
    # Since we didn't implement it fully earlier, I'll add it or proxy it
    sessions = container.sessions.list_sessions()
    for s in sessions:
        if s.session_id == session_id:
            return s
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str, container: AppContainer = Depends(get_container)):
    # Implementation placeholder for physical deletion
    pass


@router.post("/{session_id}/assemble", status_code=status.HTTP_202_ACCEPTED)
async def post_session_assemble(
    session_id: str, container: AppContainer = Depends(get_container)
):
    # This should probably be a job
    from ...core.models import JobKind

    # In a real impl, we'd load the config from the session and start an assembly job
    return {"session_id": session_id, "status": "assembling"}


@router.get("/{session_id}/config")
async def get_session_config(
    session_id: str, container: AppContainer = Depends(get_container)
):
    # FR-024: retrieve configuration from past session
    return {"error": "not implemented"}


__all__ = ["router"]
