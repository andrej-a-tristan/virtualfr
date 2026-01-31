"""Girlfriend CRUD (create, get current) with mock storage."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.schemas.girlfriend import TraitsPayload, GirlfriendResponse
from app.api.store import get_session_user, get_girlfriend, set_girlfriend

router = APIRouter(prefix="/girlfriends", tags=["girlfriends"])


def _session_id(request: Request) -> str | None:
    return request.cookies.get("session")


@router.post("")
def create_girlfriend(request: Request, body: TraitsPayload):
    """Create current girlfriend from traits payload."""
    sid = _session_id(request)
    if not sid or not get_session_user(sid):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    traits = body.model_dump()
    gf = {
        "id": "gf-1",
        "name": "Luna",
        "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=luna",
        "traits": traits,
        "created_at": "2025-01-01T00:00:00Z",
    }
    set_girlfriend(sid, gf)
    return GirlfriendResponse(**gf)


@router.get("/current")
def get_current_girlfriend(request: Request):
    """Return current girlfriend or 404."""
    sid = _session_id(request)
    if not sid or not get_session_user(sid):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    gf = get_girlfriend(sid)
    if not gf:
        return JSONResponse(status_code=404, content={"error": "no_girlfriend"})
    return GirlfriendResponse(**gf)
