"""Current user and age-gate endpoints."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.schemas.auth import UserResponse
from app.api.store import set_session_user, get_girlfriend
from app.api.request_context import get_current_user
from app.core.supabase_client import get_supabase_admin
from app.api.supabase_store import get_user_profile, get_current_girlfriend

def _age_gate(user): return user.get("age_gate_passed", False)

router = APIRouter(prefix="/me", tags=["me"])


@router.get("")
def me(request: Request):
    """Return current user + flags (age_gate_passed, has_girlfriend)."""
    sid, user, user_id, gf_id = get_current_user(request)
    if not sid or not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    use_sb = get_supabase_admin() and user_id is not None
    if use_sb:
        gf = get_current_girlfriend(user_id) if user_id else None
        profile = get_user_profile(user_id) if user_id else None
        language_pref = (profile or {}).get("language_pref", "en")
    else:
        gf = get_girlfriend(sid)
        language_pref = user.get("language_pref", "en")
    has_gf = bool(gf)
    current_gf_id = gf["id"] if gf else None
    age_gate = _age_gate(user)
    return UserResponse(
        id=user["id"],
        email=user["email"],
        display_name=user.get("display_name"),
        age_gate_passed=age_gate,
        has_girlfriend=has_gf,
        current_girlfriend_id=current_gf_id,
        language_pref=language_pref,
    )


@router.post("/age-gate")
def age_gate(request: Request):
    """Set age_gate_passed=True for current session."""
    sid, user, _, _ = get_current_user(request)
    if not sid or not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    set_session_user(sid, {"age_gate_passed": True})
    return {"ok": True}
