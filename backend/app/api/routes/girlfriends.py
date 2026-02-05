"""Girlfriend CRUD (create, get current) with Supabase or in-memory storage."""
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.schemas.girlfriend import CreateGirlfriendRequest, GirlfriendResponse
from app.api.store import get_girlfriend, set_girlfriend, set_session_girlfriend_id
from app.api.request_context import get_current_user
from app.core.supabase_client import get_supabase_admin
from app.api.supabase_store import create_girlfriend as sb_create_girlfriend, get_current_girlfriend as sb_get_current_girlfriend, upsert_habit_profile
from app.services.big_five import map_traits_to_big_five
from uuid import UUID

router = APIRouter(prefix="/girlfriends", tags=["girlfriends"])


@router.post("")
def create_girlfriend(request: Request, body: CreateGirlfriendRequest):
    """Create current girlfriend from displayName + traits."""
    sid, user, user_id, _ = get_current_user(request)
    if not sid or not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    traits = body.traits.model_dump()
    use_sb = get_supabase_admin() and user_id is not None
    if use_sb and user_id:
        try:
            gf = sb_create_girlfriend(user_id, body.display_name, traits)
            gf_uuid = UUID(str(gf["id"]))
            # Compute and store Big Five scores from traits
            big_five_scores = map_traits_to_big_five(traits)
            upsert_habit_profile(user_id, gf_uuid, {"big_five": big_five_scores})
            set_session_girlfriend_id(sid, str(gf["id"]))
            return GirlfriendResponse(**gf)
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})
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
def get_current_girlfriend_route(request: Request):
    """Return current girlfriend or 404."""
    sid, user, user_id, _ = get_current_user(request)
    if not sid or not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    use_sb = get_supabase_admin() and user_id is not None
    if use_sb and user_id:
        gf = sb_get_current_girlfriend(user_id)
    else:
        gf = get_girlfriend(sid)
    if not gf:
        return JSONResponse(status_code=404, content={"error": "no_girlfriend"})
    return GirlfriendResponse(**gf)
