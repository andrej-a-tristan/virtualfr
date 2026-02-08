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
    """Mock login: clear old session and start fresh."""
    clear_session(SESSION_VALUE)
    user_id = f"user-{body.email.split('@')[0]}"
    set_session_user(SESSION_VALUE, {"id": user_id, "email": body.email, "display_name": None})
    response.set_cookie(
        key=SESSION_COOKIE,
        value=SESSION_VALUE,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
    )
    return {"ok": True, "user": UserResponse(id=user_id, email=body.email, display_name=None, age_gate_passed=False, has_girlfriend=False, current_girlfriend_id=None)}


@router.post("/logout")
def logout(response: Response):
    """Clear session cookie."""
    clear_session(SESSION_VALUE)
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}
