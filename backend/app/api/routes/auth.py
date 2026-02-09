"""Auth endpoints: signup, login, logout (mock session cookie)."""
from fastapi import APIRouter, Response
from app.schemas.auth import SignupRequest, LoginRequest, UserResponse
from app.api.store import get_session_user, set_session_user, clear_session

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE = "session"
SESSION_VALUE = "demo"


@router.post("/signup")
def signup(body: SignupRequest, response: Response):
    """Mock signup: set session cookie."""
    user_id = f"user-{body.email.split('@')[0]}"
    set_session_user(SESSION_VALUE, {"id": user_id, "email": body.email, "display_name": body.display_name})
    response.set_cookie(
        key=SESSION_COOKIE,
        value=SESSION_VALUE,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
    )
    return {"ok": True, "user": UserResponse(id=user_id, email=body.email, display_name=body.display_name, age_gate_passed=False, has_girlfriend=False, current_girlfriend_id=None)}


@router.post("/login")
def login(body: LoginRequest, response: Response):
    """Mock login: ALWAYS preserve existing girlfriend/plan data (single-session demo).
    Never wipe data on login — only explicit logout clears everything."""
    user_id = f"user-{body.email.split('@')[0]}"
    existing = get_session_user(SESSION_VALUE)
    if existing:
        # Update identity fields but keep all girlfriend data, plan, age gate, etc.
        set_session_user(SESSION_VALUE, {"id": user_id, "email": body.email})
    else:
        # No session at all — create fresh
        set_session_user(SESSION_VALUE, {"id": user_id, "email": body.email, "display_name": None})
    # Re-read current state so response reflects reality
    user = get_session_user(SESSION_VALUE)
    has_gf = user.get("has_girlfriend", False)
    current_gf_id = user.get("current_girlfriend_id")
    age_gate = user.get("age_gate_passed", False)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=SESSION_VALUE,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
    )
    return {"ok": True, "user": UserResponse(id=user_id, email=body.email, display_name=user.get("display_name"), age_gate_passed=age_gate, has_girlfriend=has_gf, current_girlfriend_id=current_gf_id)}


@router.post("/logout")
def logout(response: Response):
    """Clear session cookie."""
    clear_session(SESSION_VALUE)
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}
