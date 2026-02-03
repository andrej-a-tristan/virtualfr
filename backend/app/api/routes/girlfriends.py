"""Girlfriend CRUD (create, get current) with mock storage."""
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.schemas.girlfriend import CreateGirlfriendRequest, GirlfriendResponse
from app.api.store import get_session_user, get_girlfriend, set_girlfriend

router = APIRouter(prefix="/girlfriends", tags=["girlfriends"])


def _session_id(request: Request) -> str | None:
    return request.cookies.get("session")


@router.post("")
def create_girlfriend(request: Request, body: CreateGirlfriendRequest):
    """Create current girlfriend from displayName + traits."""
    sid = _session_id(request)
    if not sid or not get_session_user(sid):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    traits = body.traits.model_dump()
    gf_id = "gf-1"
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    gf = {
        "id": gf_id,
        "display_name": body.display_name,
        "traits": traits,
        "created_at": now,
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
