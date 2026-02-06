"""In-memory session store keyed by cookie value. When Supabase is configured, sessions are also persisted so login survives backend restart."""
from typing import Any
from uuid import UUID

from app.core.supabase_client import get_supabase_admin
from app.api import supabase_store as sb

# session_id -> user dict (id, email, display_name; for Supabase also user_id UUID, current_girlfriend_id)
_sessions: dict[str, dict[str, Any]] = {}
# session_id -> girlfriend data (in-memory fallback)
_girlfriends: dict[str, dict[str, Any]] = {}
# session_id -> relationship_state dict
_relationship_state: dict[str, dict[str, Any]] = {}
# session_id -> list of message dicts
_messages: dict[str, list[dict[str, Any]]] = {}
# session_id -> habit_profile dict
_habit_profile: dict[str, dict[str, Any]] = {}


def get_session_user(session_id: str) -> dict[str, Any] | None:
    user = _sessions.get(session_id)
    if user:
        return user
    if get_supabase_admin() and session_id:
        user = sb.get_session(session_id)
        if user:
            _sessions[session_id] = user
            return user
    return None


def set_session_user(session_id: str, data: dict[str, Any]) -> None:
    existing = _sessions.get(session_id) or {}
    out = {**existing, **data}
    if "user_id" in out and isinstance(out["user_id"], UUID):
        out["user_id"] = str(out["user_id"])
    _sessions[session_id] = out
    if get_supabase_admin() and (out.get("user_id") or out.get("id")):
        try:
            sb.set_session(session_id, out)
        except Exception:
            pass  # don't fail login if sessions table write fails (e.g. table missing)


def set_session_girlfriend_id(session_id: str, girlfriend_id: str) -> None:
    existing = _sessions.get(session_id) or {}
    existing["current_girlfriend_id"] = girlfriend_id
    _sessions[session_id] = existing
    if get_supabase_admin():
        try:
            sb.set_session(session_id, existing)
        except Exception:
            pass


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
    _girlfriends.pop(session_id, None)
    _relationship_state.pop(session_id, None)
    _messages.pop(session_id, None)
    _habit_profile.pop(session_id, None)
    if get_supabase_admin():
        try:
            sb.delete_session(session_id)
        except Exception:
            pass


def get_girlfriend(session_id: str) -> dict[str, Any] | None:
    return _girlfriends.get(session_id)


def set_girlfriend(session_id: str, data: dict[str, Any]) -> None:
    _girlfriends[session_id] = data
    # Update user's has_girlfriend flag
    user = _sessions.get(session_id)
    if user:
        user["has_girlfriend"] = True
        user["current_girlfriend_id"] = data.get("id")


def get_relationship_state(session_id: str) -> dict[str, Any] | None:
    return _relationship_state.get(session_id)


def set_relationship_state(session_id: str, data: dict[str, Any]) -> None:
    _relationship_state[session_id] = data


def get_messages(session_id: str) -> list[dict[str, Any]]:
    return _messages.get(session_id) or []


def append_message(session_id: str, msg: dict[str, Any]) -> None:
    if session_id not in _messages:
        _messages[session_id] = []
    _messages[session_id].append(msg)


def get_habit_profile(session_id: str) -> dict[str, Any]:
    return _habit_profile.get(session_id) or {}


def set_habit_profile(session_id: str, data: dict[str, Any]) -> None:
    _habit_profile[session_id] = data
