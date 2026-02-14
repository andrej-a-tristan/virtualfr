"""Shared dependencies for API routes.

Provides session validation with automatic guest session recovery.
"""
import logging
from uuid import uuid4

from fastapi import Request, Response

from app.api.store import get_session_user, set_session_user

logger = logging.getLogger(__name__)

SESSION_COOKIE = "session"


def _session_id(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE)


def get_current_user(request: Request, response: Response | None = None) -> dict | None:
    """Get the current user from session, with automatic recovery.

    1. Check in-memory store
    2. Try to restore from Supabase DB (for real users after server restart)
    3. For guest sessions that were lost: auto-create a new guest session

    Returns the user dict or None if no valid session exists.
    """
    sid = _session_id(request)
    if not sid:
        return None

    # 1. Check in-memory store
    user = get_session_user(sid)
    if user:
        return user

    # 2. Try to restore from Supabase DB (real user sessions)
    user = _try_restore_from_db(sid)
    if user:
        return user

    # 3. If session ID looks like a guest session, auto-recreate it
    if sid.startswith("sess-"):
        user = _recreate_guest_session(sid)
        if user:
            logger.info(f"Auto-recreated guest session {sid[:16]}...")
            return user

    # 4. Session is truly lost — clear the stale cookie
    if response:
        response.delete_cookie(SESSION_COOKIE)

    return None


def _try_restore_from_db(sid: str) -> dict | None:
    """Restore a real user session from Supabase after server restart."""
    try:
        from app.core.supabase_client import get_supabase_admin
        from app.api.store import set_girlfriend, set_session_girlfriend_id

        admin = get_supabase_admin()
        if not admin:
            return None

        sess_res = admin.table("sessions").select("*").eq("id", sid).maybe_single().execute()
        if not sess_res or not sess_res.data:
            return None

        sess = sess_res.data
        user_id = sess.get("user_id")
        if not user_id:
            return None

        # Load profile
        profile = {}
        try:
            prof_res = admin.table("users_profile").select("*").eq("user_id", user_id).maybe_single().execute()
            if prof_res.data:
                profile = prof_res.data
        except Exception:
            pass

        # Load girlfriend
        gf_id = None
        gf_data = None
        try:
            gf_res = admin.table("girlfriends").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
            if gf_res.data:
                gf_data = gf_res.data[0]
                gf_id = gf_data["id"]
        except Exception:
            pass

        age_gate = profile.get("age_gate_passed", False) or bool(gf_id)
        user_data = {
            "id": user_id,
            "user_id": user_id,
            "email": sess.get("email", ""),
            "display_name": sess.get("display_name") or profile.get("display_name"),
            "plan": profile.get("plan", "free"),
            "age_gate_passed": age_gate,
            "has_girlfriend": bool(gf_id),
            "current_girlfriend_id": gf_id,
        }
        set_session_user(sid, user_data)

        if gf_data:
            set_girlfriend(sid, gf_data)
            set_session_girlfriend_id(sid, gf_id)

        logger.info(f"Restored session {sid[:16]}... for user {user_id[:8]}...")
        return user_data
    except Exception as exc:
        logger.warning(f"Failed to restore session from DB: {exc}")
        return None


def _recreate_guest_session(sid: str) -> dict | None:
    """Re-create a guest session that was lost (e.g., server hot-reload).

    Guest sessions are in-memory only and not persisted to DB.
    When they're lost, we create a fresh guest user under the same session ID
    so the browser cookie still works.
    """
    try:
        guest_id = f"guest-{uuid4().hex[:12]}"
        user_data = {
            "id": guest_id,
            "user_id": guest_id,
            "email": "",
            "display_name": None,
            "plan": "free",
            "age_gate_passed": True,
            "has_girlfriend": False,
            "current_girlfriend_id": None,
            "is_guest": True,
        }
        set_session_user(sid, user_data)
        return user_data
    except Exception as exc:
        logger.warning(f"Failed to recreate guest session: {exc}")
        return None
