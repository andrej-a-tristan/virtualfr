"""Auth endpoints: signup, login, logout. Uses Supabase Auth when configured."""
import logging
import uuid as uuid_mod
from uuid import UUID
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from app.schemas.auth import SignupRequest, LoginRequest, UserResponse
from app.api.store import get_session_user, set_session_user, clear_session
from app.core.supabase_client import get_supabase_admin, get_supabase, is_supabase_configured
from app.api.supabase_store import upsert_user_profile

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

SESSION_COOKIE = "session"
SESSION_VALUE = "demo"


def _set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=86400 * 7,
    )


def _user_response(id: str, email: str, display_name: str | None = None, age_gate_passed: bool = False, has_girlfriend: bool = False, current_girlfriend_id: str | None = None):
    return {
        "ok": True,
        "user": {
            "id": id,
            "email": email,
            "display_name": display_name,
            "age_gate_passed": age_gate_passed,
            "has_girlfriend": has_girlfriend,
            "current_girlfriend_id": current_girlfriend_id,
        },
    }


@router.post("/signup")
def signup(body: SignupRequest, response: Response):
    """Signup: Supabase Auth when configured, else mock session."""
    if is_supabase_configured():
        try:
            admin = get_supabase_admin()
        except Exception as e:
            logger.exception("Supabase admin client: %s", e)
            return JSONResponse(status_code=500, content={"error": f"Server config error: {e}"})
        if admin:
            try:
                auth_res = admin.auth.admin.create_user({
                    "email": body.email,
                    "password": body.password,
                    "email_confirm": True,
                    "user_metadata": {"display_name": body.display_name or ""},
                })
                user = auth_res.user
                if not user or not user.id:
                    return JSONResponse(status_code=400, content={"error": "Signup failed"})
                user_id = str(user.id)
                try:
                    upsert_user_profile(UUID(user_id), "en")
                except Exception as e:
                    logger.warning("upsert_user_profile: %s", e)
                session_id = str(uuid_mod.uuid4())
                set_session_user(
                    session_id,
                    {
                        "id": user_id,
                        "user_id": user_id,
                        "email": body.email,
                        "display_name": body.display_name or None,
                        "age_gate_passed": False,
                        "current_girlfriend_id": None,
                    },
                )
                _set_session_cookie(response, session_id)
                return _user_response(user_id, body.email, body.display_name, False, False, None)
            except Exception as e:
                msg = str(e).lower()
                logger.exception("Signup failed for %s: %s", body.email, e)
                if "already" in msg or "exists" in msg or "registered" in msg:
                    return JSONResponse(status_code=400, content={"error": "Email already registered"})
                return JSONResponse(status_code=500, content={"error": str(e)})

    user_id = f"user-{body.email.split('@')[0]}"
    set_session_user(SESSION_VALUE, {"id": user_id, "email": body.email, "display_name": body.display_name})
    _set_session_cookie(response, SESSION_VALUE)
    return _user_response(user_id, body.email, body.display_name, False, False, None)


@router.post("/login")
def login(body: LoginRequest, response: Response):
    """Login: Supabase Auth when configured, else mock session (preserves existing data)."""
    if is_supabase_configured():
        try:
            client = get_supabase()
        except Exception as e:
            logger.exception("Supabase client: %s", e)
            return JSONResponse(status_code=500, content={"error": f"Server config error: {e}"})
        if client:
            try:
                auth_res = client.auth.sign_in_with_password({"email": body.email, "password": body.password})
                user = auth_res.user
                if not user or not user.id:
                    return JSONResponse(status_code=401, content={"error": "Invalid credentials"})
                user_id = str(user.id)
                try:
                    upsert_user_profile(UUID(user_id), "en")
                except Exception as e:
                    logger.warning("upsert_user_profile on login: %s", e)
                session_id = str(uuid_mod.uuid4())
                gf = None
                try:
                    from app.api.supabase_store import get_current_girlfriend
                    gf = get_current_girlfriend(UUID(user_id))
                except Exception:
                    pass
                metadata = getattr(user, "user_metadata", None) or {}
                display_name = metadata.get("display_name") if isinstance(metadata, dict) else None
                gf_id_str = str(gf["id"]) if gf and gf.get("id") else None
                set_session_user(
                    session_id,
                    {
                        "id": user_id,
                        "user_id": user_id,
                        "email": body.email,
                        "display_name": display_name,
                        "age_gate_passed": False,
                        "current_girlfriend_id": gf_id_str,
                    },
                )
                _set_session_cookie(response, session_id)
                return _user_response(user_id, body.email, display_name, False, bool(gf), gf_id_str)
            except Exception as e:
                msg = str(e).lower()
                logger.exception("Login failed for %s: %s", body.email, e)
                if "invalid" in msg or "credentials" in msg or "email" in msg or "password" in msg:
                    return JSONResponse(status_code=401, content={"error": "Invalid email or password"})
                return JSONResponse(status_code=500, content={"error": str(e)})

    # Mock fallback: preserve existing girlfriend/plan data
    user_id = f"user-{body.email.split('@')[0]}"
    existing = get_session_user(SESSION_VALUE)
    if existing:
        set_session_user(SESSION_VALUE, {"id": user_id, "email": body.email})
    else:
        set_session_user(SESSION_VALUE, {"id": user_id, "email": body.email, "display_name": None})
    user = get_session_user(SESSION_VALUE)
    has_gf = user.get("has_girlfriend", False)
    current_gf_id = user.get("current_girlfriend_id")
    age_gate = user.get("age_gate_passed", False)
    _set_session_cookie(response, SESSION_VALUE)
    return _user_response(user_id, body.email, user.get("display_name"), age_gate, has_gf, current_gf_id)


@router.post("/logout")
def logout(request: Request, response: Response):
    """Clear session cookie."""
    sid = request.cookies.get(SESSION_COOKIE) or SESSION_VALUE
    clear_session(sid)
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}
