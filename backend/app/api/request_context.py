"""Resolve current user from request: cookie session -> user dict and optional Supabase user_id/girlfriend_id."""
import logging
from uuid import UUID
from fastapi import Request

from app.api.store import get_session_user, set_session_user

_logger = logging.getLogger("request_context")


def get_current_user(request: Request) -> tuple[str | None, dict | None, UUID | None, str | None]:
    """
    Returns (session_id, user_dict, user_id_uuid, girlfriend_id_str).
    user_id_uuid and girlfriend_id_str are set when session belongs to a Supabase-backed user.

    Fallback chain:
      1. In-memory session store
      2. Supabase sessions table lookup
      3. Direct UUID parse of session cookie (for Supabase auth users where cookie = user UUID)
    """
    sid = request.cookies.get("session")
    if not sid:
        return None, None, None, None

    user = get_session_user(sid)

    # ── Fallback: session cookie IS the user UUID for Supabase-auth users ──
    if not user:
        try:
            candidate = UUID(sid)  # will raise if sid is not a valid UUID
            from app.core.supabase_client import get_supabase_admin
            sb = get_supabase_admin()
            if sb:
                # Verify session exists in Supabase and fetch details
                r = sb.table("sessions").select("*").eq("id", sid).limit(1).execute()
                if r.data and len(r.data) > 0:
                    row = r.data[0]
                    user = {
                        "id": str(row.get("user_id", sid)),
                        "user_id": str(row.get("user_id", sid)),
                        "email": row.get("email"),
                        "display_name": row.get("display_name"),
                        "current_girlfriend_id": row.get("current_girlfriend_id"),
                    }
                    # Cache in memory for subsequent calls
                    set_session_user(sid, user)
                    _logger.info("Session restored from Supabase for user %s", str(candidate)[:8])
                else:
                    # Session not in DB, but cookie is a valid UUID — create minimal user dict
                    user = {
                        "id": str(candidate),
                        "user_id": str(candidate),
                    }
                    _logger.info("Session created from UUID cookie for user %s", str(candidate)[:8])
        except (ValueError, TypeError):
            pass  # sid is not a UUID — can't do the fallback

    if not user:
        return sid, None, None, None

    user_id_uuid = None
    try:
        uid = user.get("user_id") or user.get("id")
        if uid:
            s = str(uid)
            if len(s) == 36 and s.count("-") == 4:
                user_id_uuid = UUID(s)
    except (ValueError, TypeError):
        pass
    gf_id = user.get("current_girlfriend_id")
    return sid, user, user_id_uuid, gf_id


