"""Auth endpoints: signup, login, logout with Supabase-first persistence."""
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
    """Create user and persist a DB-backed session when Supabase is configured.
    
    If the request has an existing guest session, the girlfriend created during
    onboarding is transferred to the new real account.
    """
    supabase = get_supabase()
    old_sid = request.cookies.get(SESSION_COOKIE)  # guest session if present
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

        # Supabase anti-enumeration: if email already exists, sign_up returns a fake user
        # with no identities. Detect this and return a proper 409 error.
        identities = getattr(user, "identities", None)
        if identities is not None and len(identities) == 0:
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists. Please log in."
            )

        user_id = str(user.id)

        # Auto-confirm email so login works immediately (no email verification needed)
        try:
            from app.core.supabase_client import get_supabase_admin
            admin = get_supabase_admin()
            if admin:
                admin.auth.admin.update_user_by_id(user_id, {"email_confirm": True})
        except Exception:
            pass  # Non-critical: user can still use the app, just can't re-login until confirmed

        # Transfer girlfriend from guest session if one was created during onboarding
        gf = get_girlfriend(old_sid) if old_sid else None

        # First set up the session so set_girlfriend can use the real user_id for DB persistence
        set_session_user(sid, {
            "id": user_id,
            "user_id": user_id,
            "email": str(body.email),
            "display_name": body.display_name,
            "plan": "free",
            "age_gate_passed": True,  # they completed onboarding
            "has_girlfriend": bool(gf),
            "current_girlfriend_id": None,
        })

        # Transfer girlfriend data to new session
        # set_girlfriend() handles Supabase persistence AND updates current_girlfriend_id
        if gf:
            from app.api.store import set_girlfriend as store_set_girlfriend
            store_set_girlfriend(sid, gf)
            # Re-read the session to get the updated current_girlfriend_id
            # and persist it to Supabase
            updated_user = get_session_user(sid) or {}
            new_gf_id = updated_user.get("current_girlfriend_id")
            logger.info(f"Signup: girlfriend transferred. new_gf_id={new_gf_id}, has_girlfriend={updated_user.get('has_girlfriend')}")
            # Explicitly persist the updated session (with correct gf id) to Supabase
            set_session_user(sid, {
                "has_girlfriend": True,
                "current_girlfriend_id": new_gf_id,
            })

        # Clear old guest session
        if old_sid:
            clear_session(old_sid)

        try:
            uid = UUID(str(user.id))
            sb.upsert_user_profile(user_id=uid, language_pref="en", display_name=body.display_name, age_gate_passed=True)
            sb.upsert_subscription(user_id=uid, plan="free")
        except Exception:
            pass

        _set_cookie(response, sid)
        return {"ok": True, "user": _user_response_from_session(sid, user_id, str(body.email), body.display_name)}

    # Fallback (non-Supabase): still create unique session id.
    gf = get_girlfriend(old_sid) if old_sid else None
    user_id = f"user-{body.email.split('@')[0]}"
    set_session_user(sid, {
        "id": user_id,
        "email": str(body.email),
        "display_name": body.display_name,
        "plan": "free",
        "age_gate_passed": True,
        "has_girlfriend": bool(gf),
        "current_girlfriend_id": None,
    })
    if gf:
        from app.api.store import set_girlfriend as store_set_girlfriend
        store_set_girlfriend(sid, gf)
    if old_sid:
        clear_session(old_sid)
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
            # If login fails, try auto-confirming email and retry (Supabase may require confirmation)
            if "Invalid login credentials" in detail or "Email not confirmed" in detail:
                try:
                    from app.core.supabase_client import get_supabase_admin
                    admin = get_supabase_admin()
                    if admin:
                        # Find user by email and auto-confirm
                        users_res = admin.auth.admin.list_users()
                        found_user = False
                        for u in (users_res or []):
                            if getattr(u, "email", None) == str(body.email):
                                found_user = True
                                confirmed = getattr(u, "email_confirmed_at", None)
                                logger.info(f"Found user {u.id}, email_confirmed_at={confirmed}")
                                if not confirmed:
                                    admin.auth.admin.update_user_by_id(str(u.id), {"email_confirm": True})
                                    logger.info(f"Auto-confirmed email for user {u.id}")
                                # Retry login
                                try:
                                    auth_res = supabase.auth.sign_in_with_password({"email": str(body.email), "password": body.password})
                                    logger.info(f"Retry login succeeded for {body.email}")
                                except Exception as retry_exc:
                                    logger.warning(f"Retry login also failed: {retry_exc}")
                                break
                        if not found_user:
                            logger.warning(f"No user found in Supabase auth with email {body.email}")
                except Exception as confirm_exc:
                    logger.error(f"Auto-confirm attempt failed: {confirm_exc}", exc_info=True)
                if not auth_res:
                    raise HTTPException(status_code=401, detail="Invalid email or password")
            else:
                raise HTTPException(status_code=401, detail=detail)

        user = getattr(auth_res, "user", None)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Hydrate session with profile data from DB
        user_id = str(user.id)
        display_name = (user.user_metadata or {}).get("display_name")

        # Try to load profile and girlfriend from Supabase
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

        # If user has a girlfriend, they must have passed age gate
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

        # If there's a girlfriend, also load it into the in-memory store
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
    """Create a temporary guest session for onboarding (no Supabase auth needed).
    
    The guest session gets a session cookie so onboarding pages work.
    At signup time (GirlfriendReveal), the session is upgraded to a real account.
    """
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
