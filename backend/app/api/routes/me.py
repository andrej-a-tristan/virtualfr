"""Current user and age-gate endpoints."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.schemas.auth import UserResponse
from app.api.store import get_session_user, set_session_user, get_girlfriend

def _age_gate(user): return user.get("age_gate_passed", False)

router = APIRouter(prefix="/me", tags=["me"])


def _session_id(request: Request) -> str | None:
    return request.cookies.get("session")


@router.get("")
def me(request: Request):
    """Return current user + flags (age_gate_passed, has_girlfriend)."""
    sid = _session_id(request)
    if not sid:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    user = get_session_user(sid)
    if not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    has_gf = bool(get_girlfriend(sid))
    age_gate = _age_gate(user)
    return UserResponse(
        id=user["id"],
        email=user["email"],
        display_name=user.get("display_name"),
        age_gate_passed=age_gate,
        has_girlfriend=has_gf,
    )


@router.post("/age-gate")
def age_gate(request: Request):
    """Set age_gate_passed=True for current session."""
    sid = _session_id(request)
    if not sid:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    set_session_user(sid, {"age_gate_passed": True})
    return {"ok": True}
