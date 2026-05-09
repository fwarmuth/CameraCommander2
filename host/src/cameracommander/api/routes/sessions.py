from fastapi import APIRouter, status
router = APIRouter()

@router.get("/")
async def get_sessions():
    return {"items": [], "total": 0}

@router.get("/{session_id}")
async def get_session(session_id: str):
    return {"session_id": session_id}

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str):
    pass

@router.post("/{session_id}/assemble", status_code=status.HTTP_202_ACCEPTED)
async def post_session_assemble(session_id: str):
    return {"session_id": session_id, "status": "assembling"}
