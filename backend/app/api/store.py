"""In-memory session store keyed by cookie value.
Supports multiple girlfriends per session with per-girlfriend messages and relationship state.
When Supabase is configured, sessions are also persisted so login survives backend restart."""
from typing import Any
from uuid import UUID

from app.core.supabase_client import get_supabase_admin
from app.api import supabase_store as sb
from app.services.relationship_progression import RelationshipProgressState
from app.schemas.intimacy import IntimacyState
from app.schemas.trust_intimacy import TrustIntimacyState
from app.services.achievement_engine import AchievementProgress

# session_id -> user dict (id, email, display_name; for Supabase also user_id UUID, current_girlfriend_id)
_sessions: dict[str, dict[str, Any]] = {}
# session_id -> list of girlfriend dicts  (multi-girl support)
_all_girlfriends: dict[str, list[dict[str, Any]]] = {}
# (session_id, girlfriend_id) -> relationship_state dict
_relationship_state: dict[tuple[str, str], dict[str, Any]] = {}
# (session_id, girlfriend_id) -> list of message dicts
_messages: dict[tuple[str, str], list[dict[str, Any]]] = {}
# (session_id, girlfriend_id) -> habit_profile dict
_habit_profile: dict[tuple[str, str], dict[str, Any]] = {}
# (session_id, girlfriend_id) -> list of gallery item dicts
_gallery: dict[tuple[str, str], list[dict[str, Any]]] = {}
# (session_id, girlfriend_id) -> RelationshipProgressState
_relationship_progress: dict[tuple[str, str], RelationshipProgressState] = {}
# (session_id, girlfriend_id) -> IntimacyState
_intimacy_state: dict[tuple[str, str], IntimacyState] = {}
# (session_id, girlfriend_id) -> TrustIntimacyState
_trust_intimacy_state: dict[tuple[str, str], TrustIntimacyState] = {}
# (session_id, girlfriend_id) -> AchievementProgress
_achievement_progress: dict[tuple[str, str], AchievementProgress] = {}


# ── Session / User ────────────────────────────────────────────────────────────

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
            pass


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
    # Clear all girlfriend data for this session
    gfs = _all_girlfriends.pop(session_id, [])
    for gf in gfs:
        gf_id = gf.get("id", "")
        _relationship_state.pop((session_id, gf_id), None)
        _messages.pop((session_id, gf_id), None)
        _habit_profile.pop((session_id, gf_id), None)
        _gallery.pop((session_id, gf_id), None)
        _relationship_progress.pop((session_id, gf_id), None)
        _intimacy_state.pop((session_id, gf_id), None)
        _trust_intimacy_state.pop((session_id, gf_id), None)
    if get_supabase_admin():
        try:
            sb.delete_session(session_id)
        except Exception:
            pass


# ── Girlfriends (multi-girl) ──────────────────────────────────────────────────

def get_all_girlfriends(session_id: str) -> list[dict[str, Any]]:
    """Return all girlfriends for a session."""
    return _all_girlfriends.get(session_id, [])


def add_girlfriend(session_id: str, data: dict[str, Any]) -> None:
    """Add a girlfriend to the session's list and set as current."""
    if session_id not in _all_girlfriends:
        _all_girlfriends[session_id] = []
    _all_girlfriends[session_id].append(data)
    # Set as current + update user flags
    user = _sessions.get(session_id)
    if user:
        user["has_girlfriend"] = True
        user["current_girlfriend_id"] = data.get("id")


def get_girlfriend(session_id: str) -> dict[str, Any] | None:
    """Return the CURRENT girlfriend (backward compat)."""
    user = _sessions.get(session_id)
    if not user:
        return None
    current_id = user.get("current_girlfriend_id")
    gfs = _all_girlfriends.get(session_id, [])
    if current_id:
        for gf in gfs:
            if gf.get("id") == current_id:
                return gf
    # Fallback: return first
    return gfs[0] if gfs else None


def get_girlfriend_by_id(session_id: str, girlfriend_id: str) -> dict[str, Any] | None:
    """Return a specific girlfriend by id."""
    gfs = _all_girlfriends.get(session_id, [])
    for gf in gfs:
        if gf.get("id") == girlfriend_id:
            return gf
    return None


def set_girlfriend(session_id: str, data: dict[str, Any]) -> None:
    """Set/replace girlfriend (backward compat — adds if not present, replaces if same id)."""
    gf_id = data.get("id")
    if session_id not in _all_girlfriends:
        _all_girlfriends[session_id] = []

    # Replace if same id exists
    existing = _all_girlfriends[session_id]
    for i, gf in enumerate(existing):
        if gf.get("id") == gf_id:
            existing[i] = data
            break
    else:
        existing.append(data)

    # Update user's has_girlfriend flag
    user = _sessions.get(session_id)
    if user:
        user["has_girlfriend"] = True
        user["current_girlfriend_id"] = gf_id


def set_current_girlfriend_id(session_id: str, girlfriend_id: str) -> bool:
    """Set the current girlfriend id. Returns True if valid."""
    gfs = _all_girlfriends.get(session_id, [])
    for gf in gfs:
        if gf.get("id") == girlfriend_id:
            user = _sessions.get(session_id)
            if user:
                user["current_girlfriend_id"] = girlfriend_id
            return True
    return False


def get_girlfriend_count(session_id: str) -> int:
    """Return the number of girlfriends for a session."""
    return len(_all_girlfriends.get(session_id, []))


# ── Relationship State (per girlfriend) ───────────────────────────────────────

def get_relationship_state(session_id: str, girlfriend_id: str | None = None) -> dict[str, Any] | None:
    """Get relationship state. If girlfriend_id is None, use current girlfriend."""
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return None
    return _relationship_state.get((session_id, girlfriend_id))


def set_relationship_state(session_id: str, data: dict[str, Any], girlfriend_id: str | None = None) -> None:
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return
    _relationship_state[(session_id, girlfriend_id)] = data


# ── Messages (per girlfriend) ─────────────────────────────────────────────────

def get_messages(session_id: str, girlfriend_id: str | None = None) -> list[dict[str, Any]]:
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return []
    return _messages.get((session_id, girlfriend_id)) or []


def append_message(session_id: str, msg: dict[str, Any], girlfriend_id: str | None = None) -> None:
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return
    key = (session_id, girlfriend_id)
    if key not in _messages:
        _messages[key] = []
    _messages[key].append(msg)


# ── Habit Profile (per girlfriend) ─────────────────────────────────────────────

def get_habit_profile(session_id: str, girlfriend_id: str | None = None) -> dict[str, Any]:
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return {}
    return _habit_profile.get((session_id, girlfriend_id)) or {}


def set_habit_profile(session_id: str, data: dict[str, Any], girlfriend_id: str | None = None) -> None:
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return
    _habit_profile[(session_id, girlfriend_id)] = data


# ── Gallery (per girlfriend) ──────────────────────────────────────────────────

def get_gallery(session_id: str, girlfriend_id: str | None = None) -> list[dict[str, Any]]:
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return []
    return _gallery.get((session_id, girlfriend_id)) or []


def add_gallery_item(session_id: str, item: dict[str, Any], girlfriend_id: str | None = None) -> None:
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return
    key = (session_id, girlfriend_id)
    if key not in _gallery:
        _gallery[key] = []
    _gallery[key].append(item)


def set_gallery(session_id: str, items: list[dict[str, Any]], girlfriend_id: str | None = None) -> None:
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return
    _gallery[(session_id, girlfriend_id)] = items


# ── Relationship Progression (per girlfriend) ─────────────────────────────────

def get_relationship_progress(session_id: str, girlfriend_id: str | None = None) -> RelationshipProgressState:
    """Return progress state for the session+girlfriend, creating a default if absent."""
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return RelationshipProgressState()
    return _relationship_progress.get((session_id, girlfriend_id), RelationshipProgressState())


def set_relationship_progress(session_id: str, state: RelationshipProgressState, girlfriend_id: str | None = None) -> None:
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return
    _relationship_progress[(session_id, girlfriend_id)] = state


# ── Intimacy State (per girlfriend) ──────────────────────────────────────────

def get_intimacy_state(session_id: str, girlfriend_id: str | None = None) -> IntimacyState:
    """Return intimacy state for session+girlfriend, creating a default if absent."""
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return IntimacyState()
    return _intimacy_state.get((session_id, girlfriend_id), IntimacyState())


def set_intimacy_state(session_id: str, state: IntimacyState, girlfriend_id: str | None = None) -> None:
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return
    _intimacy_state[(session_id, girlfriend_id)] = state


# ── Trust + Intimacy State (per girlfriend) ──────────────────────────────────

def get_trust_intimacy_state(session_id: str, girlfriend_id: str | None = None) -> TrustIntimacyState:
    """Return trust/intimacy state for session+girlfriend, creating a default if absent."""
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return TrustIntimacyState()
    return _trust_intimacy_state.get((session_id, girlfriend_id), TrustIntimacyState())


def set_trust_intimacy_state(session_id: str, state: TrustIntimacyState, girlfriend_id: str | None = None) -> None:
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return
    _trust_intimacy_state[(session_id, girlfriend_id)] = state


# ── Achievement Progress (per girlfriend) ────────────────────────────────────

def get_achievement_progress(session_id: str, girlfriend_id: str | None = None) -> AchievementProgress:
    """Return achievement progress for session+girlfriend, creating a default if absent."""
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return AchievementProgress()
    return _achievement_progress.get((session_id, girlfriend_id), AchievementProgress())


def set_achievement_progress(session_id: str, progress: AchievementProgress, girlfriend_id: str | None = None) -> None:
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return
    _achievement_progress[(session_id, girlfriend_id)] = progress
