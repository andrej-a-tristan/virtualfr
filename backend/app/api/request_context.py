"""Resolve current user from request: cookie session -> user dict and optional Supabase user_id/girlfriend_id."""
from uuid import UUID
from fastapi import Request

from app.api.store import get_session_user


def get_current_user(request: Request) -> tuple[str | None, dict | None, UUID | None, str | None]:
    """
    Returns (session_id, user_dict, user_id_uuid, girlfriend_id_str).
    user_id_uuid and girlfriend_id_str are set when session belongs to a Supabase-backed user.
    """
    sid = request.cookies.get("session")
    if not sid:
        return None, None, None, None
    user = get_session_user(sid)
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


