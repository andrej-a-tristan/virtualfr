"""In-memory session store keyed by cookie value.
Supports multiple girlfriends per session with per-girlfriend messages and relationship state.
When Supabase is configured, sessions are also persisted so login survives backend restart.

DATA PERSISTENCE: All in-memory dicts are automatically saved to a pickle file
after every write, and loaded on startup. This ensures data survives uvicorn
--reload without requiring a database."""
import logging
import os
import pickle
import threading
from typing import Any
from uuid import UUID

from app.core.supabase_client import get_supabase_admin
from app.api import supabase_store as sb
from app.services.relationship_progression import RelationshipProgressState
from app.schemas.intimacy import IntimacyState
from app.schemas.trust_intimacy import TrustIntimacyState
from app.services.achievement_engine import AchievementProgress

_logger = logging.getLogger(__name__)

# ── Persistence layer ─────────────────────────────────────────────────────────

_STORE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "_store_cache.pkl")
_save_lock = threading.Lock()

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

# ── Intimacy Achievements (per girlfriend) ────────────────────────────────────
# (session_id, girlfriend_id) -> { achievement_id: unlocked_at_iso }
_intimacy_ach_unlocked: dict[tuple[str, str], dict[str, str]] = {}
# (session_id, girlfriend_id) -> last award datetime iso
_intimacy_ach_last_award: dict[tuple[str, str], str] = {}
# (session_id, girlfriend_id) -> { achievement_id: image_url }
_intimacy_ach_photos: dict[tuple[str, str], dict[str, str]] = {}
# (session_id, girlfriend_id) -> list of achievement_ids awaiting photo generation
_intimacy_ach_pending_photos: dict[tuple[str, str], list[str]] = {}
# (session_id, girlfriend_id) -> { phrase_hash: timestamp } for anti-spam
_intimacy_ach_phrase_log: dict[tuple[str, str], dict[str, float]] = {}


def _persist() -> None:
    """Save all in-memory dicts to a pickle file (thread-safe)."""
    data = {
        "sessions": _sessions,
        "all_girlfriends": _all_girlfriends,
        "relationship_state": _relationship_state,
        "messages": _messages,
        "habit_profile": _habit_profile,
        "gallery": _gallery,
        "relationship_progress": _relationship_progress,
        "intimacy_state": _intimacy_state,
        "trust_intimacy_state": _trust_intimacy_state,
        "achievement_progress": _achievement_progress,
        "intimacy_ach_unlocked": _intimacy_ach_unlocked,
        "intimacy_ach_last_award": _intimacy_ach_last_award,
        "intimacy_ach_photos": _intimacy_ach_photos,
        "intimacy_ach_pending_photos": _intimacy_ach_pending_photos,
        "intimacy_ach_phrase_log": _intimacy_ach_phrase_log,
    }
    with _save_lock:
        try:
            tmp = _STORE_FILE + ".tmp"
            with open(tmp, "wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp, _STORE_FILE)
        except Exception as e:
            _logger.warning("Failed to persist store: %s", e)


def _load_store() -> None:
    """Load persisted data from pickle file into the in-memory dicts."""
    global _sessions, _all_girlfriends, _relationship_state, _messages
    global _habit_profile, _gallery, _relationship_progress, _intimacy_state
    global _trust_intimacy_state, _achievement_progress
    global _intimacy_ach_unlocked, _intimacy_ach_last_award, _intimacy_ach_photos
    global _intimacy_ach_pending_photos, _intimacy_ach_phrase_log

    if not os.path.exists(_STORE_FILE):
        return
    try:
        with open(_STORE_FILE, "rb") as f:
            data = pickle.load(f)
        _sessions.update(data.get("sessions", {}))
        _all_girlfriends.update(data.get("all_girlfriends", {}))
        _relationship_state.update(data.get("relationship_state", {}))
        _messages.update(data.get("messages", {}))
        _habit_profile.update(data.get("habit_profile", {}))
        _gallery.update(data.get("gallery", {}))
        _relationship_progress.update(data.get("relationship_progress", {}))
        _intimacy_state.update(data.get("intimacy_state", {}))
        _trust_intimacy_state.update(data.get("trust_intimacy_state", {}))
        _achievement_progress.update(data.get("achievement_progress", {}))
        _intimacy_ach_unlocked.update(data.get("intimacy_ach_unlocked", {}))
        _intimacy_ach_last_award.update(data.get("intimacy_ach_last_award", {}))
        _intimacy_ach_photos.update(data.get("intimacy_ach_photos", {}))
        _intimacy_ach_pending_photos.update(data.get("intimacy_ach_pending_photos", {}))
        _intimacy_ach_phrase_log.update(data.get("intimacy_ach_phrase_log", {}))
        _logger.info("Loaded store from %s (%d sessions, %d girlfriends)",
                     _STORE_FILE, len(_sessions), sum(len(v) for v in _all_girlfriends.values()))
    except Exception as e:
        _logger.warning("Failed to load store cache (starting fresh): %s", e)


# Load persisted data on module import (i.e., on server start/reload)
_load_store()


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
    _persist()
    if get_supabase_admin() and (out.get("user_id") or out.get("id")):
        try:
            sb.set_session(session_id, out)
        except Exception:
            pass


def set_session_girlfriend_id(session_id: str, girlfriend_id: str) -> None:
    existing = _sessions.get(session_id) or {}
    existing["current_girlfriend_id"] = girlfriend_id
    _sessions[session_id] = existing
    _persist()
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
    _persist()
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
    _persist()


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
    _persist()


def set_current_girlfriend_id(session_id: str, girlfriend_id: str) -> bool:
    """Set the current girlfriend id. Returns True if valid."""
    gfs = _all_girlfriends.get(session_id, [])
    for gf in gfs:
        if gf.get("id") == girlfriend_id:
            user = _sessions.get(session_id)
            if user:
                user["current_girlfriend_id"] = girlfriend_id
            _persist()
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
    _persist()


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
    _persist()


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
    _persist()


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
    _persist()


def set_gallery(session_id: str, items: list[dict[str, Any]], girlfriend_id: str | None = None) -> None:
    if not girlfriend_id:
        user = _sessions.get(session_id)
        girlfriend_id = (user or {}).get("current_girlfriend_id", "")
    if not girlfriend_id:
        return
    _gallery[(session_id, girlfriend_id)] = items
    _persist()


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
    _persist()


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
    _persist()


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
    _persist()


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
    _persist()


# ── Intimacy Achievement Storage (per girlfriend) ─────────────────────────────

def _resolve_gf(session_id: str, girlfriend_id: str | None) -> str:
    if girlfriend_id:
        return girlfriend_id
    user = _sessions.get(session_id)
    return (user or {}).get("current_girlfriend_id", "")


def get_intimacy_achievements_unlocked(session_id: str, girlfriend_id: str | None = None) -> dict[str, str]:
    """Return {achievement_id: unlocked_at_iso} for this girlfriend."""
    gf = _resolve_gf(session_id, girlfriend_id)
    if not gf:
        return {}
    return dict(_intimacy_ach_unlocked.get((session_id, gf), {}))


def mark_intimacy_achievement_unlocked(session_id: str, achievement_id: str, unlocked_at: str, girlfriend_id: str | None = None) -> None:
    gf = _resolve_gf(session_id, girlfriend_id)
    if not gf:
        return
    key = (session_id, gf)
    if key not in _intimacy_ach_unlocked:
        _intimacy_ach_unlocked[key] = {}
    _intimacy_ach_unlocked[key][achievement_id] = unlocked_at
    _persist()


def get_intimacy_last_award_time(session_id: str, girlfriend_id: str | None = None) -> str | None:
    gf = _resolve_gf(session_id, girlfriend_id)
    if not gf:
        return None
    return _intimacy_ach_last_award.get((session_id, gf))


def set_intimacy_last_award_time(session_id: str, award_time: str, girlfriend_id: str | None = None) -> None:
    gf = _resolve_gf(session_id, girlfriend_id)
    if not gf:
        return
    _intimacy_ach_last_award[(session_id, gf)] = award_time
    _persist()


def get_photo_for_intimacy_achievement(session_id: str, achievement_id: str, girlfriend_id: str | None = None) -> str | None:
    gf = _resolve_gf(session_id, girlfriend_id)
    if not gf:
        return None
    return _intimacy_ach_photos.get((session_id, gf), {}).get(achievement_id)


def set_photo_for_intimacy_achievement(session_id: str, achievement_id: str, image_url: str, girlfriend_id: str | None = None) -> None:
    gf = _resolve_gf(session_id, girlfriend_id)
    if not gf:
        return
    key = (session_id, gf)
    if key not in _intimacy_ach_photos:
        _intimacy_ach_photos[key] = {}
    _intimacy_ach_photos[key][achievement_id] = image_url
    _persist()


def get_pending_intimacy_photos(session_id: str, girlfriend_id: str | None = None) -> list[str]:
    gf = _resolve_gf(session_id, girlfriend_id)
    if not gf:
        return []
    return list(_intimacy_ach_pending_photos.get((session_id, gf), []))


def add_pending_intimacy_photo(session_id: str, achievement_id: str, girlfriend_id: str | None = None) -> None:
    gf = _resolve_gf(session_id, girlfriend_id)
    if not gf:
        return
    key = (session_id, gf)
    if key not in _intimacy_ach_pending_photos:
        _intimacy_ach_pending_photos[key] = []
    if achievement_id not in _intimacy_ach_pending_photos[key]:
        _intimacy_ach_pending_photos[key].append(achievement_id)
    _persist()


def pop_pending_intimacy_photo(session_id: str, achievement_id: str, girlfriend_id: str | None = None) -> bool:
    gf = _resolve_gf(session_id, girlfriend_id)
    if not gf:
        return False
    key = (session_id, gf)
    pending = _intimacy_ach_pending_photos.get(key, [])
    if achievement_id in pending:
        pending.remove(achievement_id)
        _persist()
        return True
    return False


def get_intimacy_phrase_log(session_id: str, girlfriend_id: str | None = None) -> dict[str, float]:
    gf = _resolve_gf(session_id, girlfriend_id)
    if not gf:
        return {}
    return dict(_intimacy_ach_phrase_log.get((session_id, gf), {}))


def set_intimacy_phrase_log(session_id: str, phrase_log: dict[str, float], girlfriend_id: str | None = None) -> None:
    gf = _resolve_gf(session_id, girlfriend_id)
    if not gf:
        return
    _intimacy_ach_phrase_log[(session_id, gf)] = phrase_log
    _persist()
