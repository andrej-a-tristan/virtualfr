"""In-memory session store keyed by cookie value. No DB."""
from typing import Any

# session_id -> user dict (id, email, display_name, age_gate_passed, girlfriend_id, etc.)
_sessions: dict[str, dict[str, Any]] = {}
# girlfriend data per session
_girlfriends: dict[str, dict[str, Any]] = {}


def get_session_user(session_id: str) -> dict[str, Any] | None:
    return _sessions.get(session_id)


def set_session_user(session_id: str, data: dict[str, Any]) -> None:
    existing = _sessions.get(session_id) or {}
    _sessions[session_id] = {**existing, **data}


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
    _girlfriends.pop(session_id, None)


def get_girlfriend(session_id: str) -> dict[str, Any] | None:
    return _girlfriends.get(session_id)


def set_girlfriend(session_id: str, data: dict[str, Any]) -> None:
    _girlfriends[session_id] = data
    # Update user's has_girlfriend flag
    user = _sessions.get(session_id)
    if user:
        user["has_girlfriend"] = True
        user["current_girlfriend_id"] = data.get("id")
