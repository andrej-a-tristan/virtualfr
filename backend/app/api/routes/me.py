"""Current user and age-gate endpoints."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from app.schemas.auth import UserResponse
from app.api.deps import get_current_user
from app.api.store import get_session_user, set_session_user, get_girlfriend

SESSION_COOKIE = "session"

def _age_gate(user): return user.get("age_gate_passed", False)

router = APIRouter(prefix="/me", tags=["me"])


@router.get("")
def me(request: Request, response: Response):
    """Return current user + flags (age_gate_passed, has_girlfriend)."""
    user = get_current_user(request, response)
    if not user:
        resp = JSONResponse(status_code=401, content={"error": "session_expired"})
        resp.delete_cookie(SESSION_COOKIE)
        return resp

    sid = request.cookies.get(SESSION_COOKIE)
    gf = get_girlfriend(sid)

    # Try to get language_pref from user profile or Supabase
    language_pref = user.get("language_pref", "en")
    if language_pref == "en":
        try:
            from app.core.supabase_client import get_supabase_admin
            from app.api.supabase_store import get_user_profile
            user_id = user.get("user_id") or user.get("id")
            admin = get_supabase_admin()
            if admin and user_id:
                profile = get_user_profile(user_id)
                if profile:
                    language_pref = profile.get("language_pref", "en")
        except Exception:
            pass

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
def age_gate(request: Request, response: Response):
    """Set age_gate_passed=True for current session."""
    user = get_current_user(request, response)
    if not user:
        resp = JSONResponse(status_code=401, content={"error": "session_expired"})
        resp.delete_cookie(SESSION_COOKIE)
        return resp
    sid = request.cookies.get(SESSION_COOKIE)
    set_session_user(sid, {"age_gate_passed": True})

    # Persist to Supabase
    try:
        from app.core.supabase_client import get_supabase_admin
        admin = get_supabase_admin()
        if admin and user.get("user_id"):
            admin.table("users_profile").update({"age_gate_passed": True}).eq("user_id", user["user_id"]).execute()
    except Exception:
        pass

    return {"ok": True}
