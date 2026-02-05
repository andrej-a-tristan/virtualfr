"""Supabase-backed store: read/write by user_id and girlfriend_id. Use service-role client."""
from uuid import UUID
from typing import Any

from app.core.supabase_client import get_supabase_admin


def _admin():
    return get_supabase_admin()


def get_session(session_id: str) -> dict[str, Any] | None:
    """Load session from DB so login survives backend restart."""
    sb = _admin()
    if not sb:
        return None
    r = sb.table("sessions").select("*").eq("id", session_id).execute()
    if not r.data or len(r.data) == 0:
        return None
    row = r.data[0]
    return {
        "id": str(row["user_id"]),
        "user_id": str(row["user_id"]),
        "email": row.get("email"),
        "display_name": row.get("display_name"),
        "current_girlfriend_id": row.get("current_girlfriend_id"),
    }


def set_session(session_id: str, data: dict[str, Any]) -> None:
    """Persist session to DB."""
    sb = _admin()
    if not sb:
        return
    user_id = data.get("user_id") or data.get("id")
    if not user_id:
        return
    payload = {
        "id": session_id,
        "user_id": str(user_id),
        "email": data.get("email"),
        "display_name": data.get("display_name"),
        "current_girlfriend_id": data.get("current_girlfriend_id"),
    }
    sb.table("sessions").upsert(payload, on_conflict="id").execute()


def delete_session(session_id: str) -> None:
    sb = _admin()
    if not sb:
        return
    sb.table("sessions").delete().eq("id", session_id).execute()


def get_user_profile(user_id: UUID) -> dict[str, Any] | None:
    sb = _admin()
    if not sb:
        return None
    r = sb.table("users_profile").select("*").eq("user_id", str(user_id)).execute()
    if not r.data or len(r.data) == 0:
        return None
    row = r.data[0]
    return {"user_id": row["user_id"], "language_pref": row.get("language_pref", "en")}


def upsert_user_profile(user_id: UUID, language_pref: str = "en") -> None:
    sb = _admin()
    if not sb:
        return
    sb.table("users_profile").upsert(
        {"user_id": str(user_id), "language_pref": language_pref},
        on_conflict="user_id",
    ).execute()


def get_girlfriend_by_id(user_id: UUID, girlfriend_id: UUID) -> dict[str, Any] | None:
    sb = _admin()
    if not sb:
        return None
    r = sb.table("girlfriends").select("*").eq("user_id", str(user_id)).eq("id", str(girlfriend_id)).execute()
    if not r.data or len(r.data) == 0:
        return None
    row = r.data[0]
    return {
        "id": row["id"],
        "display_name": row["display_name"],
        "traits": row.get("traits") or {},
        "created_at": row["created_at"],
    }


def get_current_girlfriend(user_id: UUID) -> dict[str, Any] | None:
    sb = _admin()
    if not sb:
        return None
    r = sb.table("girlfriends").select("*").eq("user_id", str(user_id)).order("created_at").limit(1).execute()
    if not r.data or len(r.data) == 0:
        return None
    row = r.data[0]
    return {
        "id": row["id"],
        "display_name": row["display_name"],
        "traits": row.get("traits") or {},
        "created_at": row["created_at"],
    }


def create_girlfriend(user_id: UUID, display_name: str, traits: dict) -> dict[str, Any]:
    sb = _admin()
    if not sb:
        raise RuntimeError("Supabase not configured")
    r = sb.table("girlfriends").insert(
        {"user_id": str(user_id), "display_name": display_name, "traits": traits}
    ).execute()
    if not r.data or len(r.data) == 0:
        raise RuntimeError("Failed to create girlfriend")
    row = r.data[0]
    return {
        "id": row["id"],
        "display_name": row["display_name"],
        "traits": row.get("traits") or {},
        "created_at": row["created_at"],
    }


def get_messages(user_id: UUID, girlfriend_id: UUID) -> list[dict[str, Any]]:
    sb = _admin()
    if not sb:
        return []
    r = (
        sb.table("messages")
        .select("*")
        .eq("user_id", str(user_id))
        .eq("girlfriend_id", str(girlfriend_id))
        .order("created_at")
        .execute()
    )
    if not r.data:
        return []
    return [
        {
            "id": row["id"],
            "role": row["role"],
            "content": row.get("content"),
            "image_url": row.get("image_url"),
            "event_type": row.get("event_type"),
            "event_key": row.get("event_key"),
            "created_at": row["created_at"],
        }
        for row in r.data
    ]


def append_message(user_id: UUID, girlfriend_id: UUID, msg: dict[str, Any]) -> None:
    sb = _admin()
    if not sb:
        return
    payload = {
        "user_id": str(user_id),
        "girlfriend_id": str(girlfriend_id),
        "role": msg["role"],
        "content": msg.get("content"),
        "image_url": msg.get("image_url"),
        "event_type": msg.get("event_type"),
        "event_key": msg.get("event_key"),
    }
    sb.table("messages").insert(payload).execute()


def get_relationship_state(user_id: UUID, girlfriend_id: UUID) -> dict[str, Any] | None:
    sb = _admin()
    if not sb:
        return None
    r = (
        sb.table("relationship_state")
        .select("*")
        .eq("user_id", str(user_id))
        .eq("girlfriend_id", str(girlfriend_id))
        .execute()
    )
    if not r.data or len(r.data) == 0:
        return None
    row = r.data[0]
    return {
        "trust": row["trust"],
        "intimacy": row["intimacy"],
        "level": row["level"],
        "last_interaction_at": row.get("last_interaction_at"),
        "milestones_reached": list(row.get("milestones_reached") or []),
        "updated_at": row.get("updated_at"),
    }


def upsert_relationship_state(user_id: UUID, girlfriend_id: UUID, state: dict[str, Any]) -> None:
    sb = _admin()
    if not sb:
        return
    payload = {
        "user_id": str(user_id),
        "girlfriend_id": str(girlfriend_id),
        "trust": state["trust"],
        "intimacy": state["intimacy"],
        "level": state["level"],
        "last_interaction_at": state.get("last_interaction_at"),
        "milestones_reached": state.get("milestones_reached") or [],
    }
    sb.table("relationship_state").upsert(payload, on_conflict="user_id,girlfriend_id").execute()


def get_habit_profile(user_id: UUID, girlfriend_id: UUID) -> dict[str, Any]:
    sb = _admin()
    if not sb:
        return {}
    r = (
        sb.table("habit_profile")
        .select("*")
        .eq("user_id", str(user_id))
        .eq("girlfriend_id", str(girlfriend_id))
        .execute()
    )
    if not r.data or len(r.data) == 0:
        return {}
    row = r.data[0]
    return {
        "preferred_hours": list(row.get("preferred_hours") or []) or None,
        "typical_gap_hours": row.get("typical_gap_hours"),
        "big_five": {
            "openness": float(row.get("big_five_openness")) if row.get("big_five_openness") is not None else None,
            "conscientiousness": float(row.get("big_five_conscientiousness")) if row.get("big_five_conscientiousness") is not None else None,
            "extraversion": float(row.get("big_five_extraversion")) if row.get("big_five_extraversion") is not None else None,
            "agreeableness": float(row.get("big_five_agreeableness")) if row.get("big_five_agreeableness") is not None else None,
            "neuroticism": float(row.get("big_five_neuroticism")) if row.get("big_five_neuroticism") is not None else None,
        } if any(row.get(f"big_five_{k}") is not None for k in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]) else None,
    }


def upsert_habit_profile(user_id: UUID, girlfriend_id: UUID, data: dict[str, Any]) -> None:
    sb = _admin()
    if not sb:
        return
    big_five = data.get("big_five") or {}
    payload = {
        "user_id": str(user_id),
        "girlfriend_id": str(girlfriend_id),
        "preferred_hours": data.get("preferred_hours"),
        "typical_gap_hours": data.get("typical_gap_hours"),
        "big_five_openness": big_five.get("openness"),
        "big_five_conscientiousness": big_five.get("conscientiousness"),
        "big_five_extraversion": big_five.get("extraversion"),
        "big_five_agreeableness": big_five.get("agreeableness"),
        "big_five_neuroticism": big_five.get("neuroticism"),
    }
    sb.table("habit_profile").upsert(payload, on_conflict="user_id,girlfriend_id").execute()
