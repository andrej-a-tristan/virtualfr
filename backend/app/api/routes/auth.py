"""Auth endpoints: signup, login, logout with Supabase-first persistence.

Account required — no guest sessions.
"""
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request, Response

from app.schemas.auth import SignupRequest, LoginRequest, UserResponse
from app.api.store import get_session_user, set_session_user, clear_session, get_girlfriend
from app.core.supabase_client import get_supabase
from app.api import supabase_store as sb

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

SESSION_COOKIE = "session"


def _new_session_id() -> str:
    return f"sess-{uuid4().hex}"


def _set_cookie(response: Response, sid: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=sid,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=86400 * 7,
    )


def _user_response_from_session(sid: str, fallback_id: str, fallback_email: str, fallback_name: str | None) -> UserResponse:
    user = get_session_user(sid) or {}
    gf = get_girlfriend(sid)
    return UserResponse(
        id=str(user.get("id") or fallback_id),
        email=str(user.get("email") or fallback_email),
        display_name=user.get("display_name", fallback_name),
        age_gate_passed=bool(user.get("age_gate_passed", False)),
        has_girlfriend=bool(gf),
        current_girlfriend_id=(gf or {}).get("id"),
    )


@router.post("/signup")
def signup(body: SignupRequest, request: Request, response: Response):
    """Create user account. User then proceeds to onboarding."""
    supabase = get_supabase()
    sid = _new_session_id()

    if supabase:
        try:
            auth_res = supabase.auth.sign_up({"email": str(body.email), "password": body.password})
        except Exception as exc:
            detail = str(exc)
            if "already registered" in detail.lower():
                raise HTTPException(status_code=409, detail="An account with this email already exists. Please log in.")
            raise HTTPException(status_code=400, detail=detail)

        user = getattr(auth_res, "user", None)
        if not user:
            raise HTTPException(status_code=400, detail="Signup failed")

        identities = getattr(user, "identities", None)
        if identities is not None and len(identities) == 0:
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists. Please log in."
            )

        user_id = str(user.id)

        # Auto-confirm email so login works immediately
        try:
            from app.core.supabase_client import get_supabase_admin
            admin = get_supabase_admin()
            if admin:
                admin.auth.admin.update_user_by_id(user_id, {"email_confirm": True})
        except Exception:
            pass

        set_session_user(sid, {
            "id": user_id,
            "user_id": user_id,
            "email": str(body.email),
            "display_name": body.display_name,
            "plan": "free",
            "age_gate_passed": True,
            "has_girlfriend": False,
            "current_girlfriend_id": None,
        })

        try:
            uid = UUID(str(user.id))
            sb.upsert_user_profile(user_id=uid, language_pref="en", display_name=body.display_name, age_gate_passed=True)
            sb.upsert_subscription(user_id=uid, plan="free")
        except Exception:
            pass

        _set_cookie(response, sid)
        return {"ok": True, "user": _user_response_from_session(sid, user_id, str(body.email), body.display_name)}

    # Fallback (non-Supabase)
    user_id = f"user-{body.email.split('@')[0]}"
    set_session_user(sid, {
        "id": user_id,
        "email": str(body.email),
        "display_name": body.display_name,
        "plan": "free",
        "age_gate_passed": True,
        "has_girlfriend": False,
        "current_girlfriend_id": None,
    })
    _set_cookie(response, sid)
    return {"ok": True, "user": _user_response_from_session(sid, user_id, str(body.email), body.display_name)}


@router.post("/login")
def login(body: LoginRequest, response: Response):
    """Login with Supabase password auth; fallback to local mock when disabled."""
    supabase = get_supabase()
    sid = _new_session_id()

    if supabase:
        auth_res = None
        try:
            auth_res = supabase.auth.sign_in_with_password({"email": str(body.email), "password": body.password})
        except Exception as exc:
            detail = str(exc)
            logger.warning(f"Login failed for {body.email}: {detail}")
            if "Invalid login credentials" in detail or "Email not confirmed" in detail:
                try:
                    from app.core.supabase_client import get_supabase_admin
                    admin = get_supabase_admin()
                    if admin:
                        users_res = admin.auth.admin.list_users()
                        found_user = False
                        for u in (users_res or []):
                            if getattr(u, "email", None) == str(body.email):
                                found_user = True
                                confirmed = getattr(u, "email_confirmed_at", None)
                                if not confirmed:
                                    admin.auth.admin.update_user_by_id(str(u.id), {"email_confirm": True})
                                try:
                                    auth_res = supabase.auth.sign_in_with_password({"email": str(body.email), "password": body.password})
                                except Exception:
                                    pass
                                break
                        if not found_user:
                            logger.warning(f"No user found with email {body.email}")
                except Exception as confirm_exc:
                    logger.error(f"Auto-confirm attempt failed: {confirm_exc}", exc_info=True)
                if not auth_res:
                    raise HTTPException(status_code=401, detail="Invalid email or password")
            else:
                raise HTTPException(status_code=401, detail=detail)

        user = getattr(auth_res, "user", None)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        user_id = str(user.id)
        display_name = (user.user_metadata or {}).get("display_name")

        profile = {}
        gf_id = None
        try:
            from app.core.supabase_client import get_supabase_admin
            admin = get_supabase_admin()
            if admin:
                prof_res = admin.table("users_profile").select("*").eq("user_id", user_id).maybe_single().execute()
                if prof_res.data:
                    profile = prof_res.data
                    display_name = profile.get("display_name") or display_name

                gf_res = admin.table("girlfriends").select("id,display_name").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
                if gf_res.data:
                    gf_id = gf_res.data[0]["id"]
        except Exception:
            pass

        age_gate = profile.get("age_gate_passed", False) or bool(gf_id)
        set_session_user(sid, {
            "id": user_id,
            "user_id": user_id,
            "email": str(body.email),
            "display_name": display_name,
            "plan": profile.get("plan", "free"),
            "age_gate_passed": age_gate,
            "has_girlfriend": bool(gf_id),
            "current_girlfriend_id": gf_id,
        })

        if gf_id:
            try:
                from app.api.store import set_girlfriend, set_session_girlfriend_id
                admin = get_supabase_admin()
                if admin:
                    gf_full = admin.table("girlfriends").select("*").eq("id", gf_id).maybe_single().execute()
                    if gf_full.data:
                        set_girlfriend(sid, gf_full.data)
                        set_session_girlfriend_id(sid, gf_id)
            except Exception:
                pass

        _set_cookie(response, sid)
        return {"ok": True, "user": _user_response_from_session(sid, user_id, str(body.email), display_name)}

    # Fallback (non-Supabase)
    user_id = f"user-{body.email.split('@')[0]}"
    set_session_user(sid, {"id": user_id, "email": str(body.email)})
    _set_cookie(response, sid)
    return {"ok": True, "user": _user_response_from_session(sid, user_id, str(body.email), None)}


@router.post("/guest")
def guest_session(response: Response):
    """Create a temporary guest session for onboarding."""
    sid = _new_session_id()
    guest_id = f"guest-{uuid4().hex[:12]}"
    set_session_user(sid, {
        "id": guest_id,
        "user_id": guest_id,
        "email": "",
        "display_name": None,
        "plan": "free",
        "age_gate_passed": True,
        "has_girlfriend": False,
        "current_girlfriend_id": None,
        "is_guest": True,
    })
    _set_cookie(response, sid)
    return {
        "ok": True,
        "user": UserResponse(
            id=guest_id,
            email="",
            display_name=None,
            age_gate_passed=True,
            has_girlfriend=False,
            current_girlfriend_id=None,
        ),
    }


@router.post("/logout")
def logout(request: Request, response: Response):
    """Clear active session cookie and server-side session row."""
    sid = request.cookies.get(SESSION_COOKIE)
    if sid:
        clear_session(sid)
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}
