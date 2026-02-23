"""Persistence helpers for Persona Vectors."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.services.persona_vector import build_persona_vector, persona_vector_hash


def upsert_active_persona_vector(
    sb: Any,
    user_id: UUID | str,
    girlfriend_id: UUID | str,
    traits: dict[str, Any] | None,
    version_tag: str = "pv1",
) -> dict[str, Any] | None:
    if not sb:
        return None
    uid = str(user_id)
    gid = str(girlfriend_id)
    vector = build_persona_vector(traits or {})
    now = datetime.now(timezone.utc).isoformat()
    v_hash = persona_vector_hash(vector)

    payload = {
        "user_id": uid,
        "girlfriend_id": gid,
        "version_tag": version_tag,
        "vector_json": vector,
        "vector_hash": v_hash,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    try:
        sb.table("persona_vectors").upsert(
            payload, on_conflict="user_id,girlfriend_id,version_tag"
        ).execute()
        # Keep a pointer on girlfriends for fast lookup.
        sb.table("girlfriends").update(
            {"persona_vector_version": version_tag}
        ).eq("id", gid).execute()
    except Exception:
        return None
    return payload


def get_active_persona_vector(
    sb: Any,
    user_id: UUID | str,
    girlfriend_id: UUID | str,
    version_hint: str | None = None,
) -> dict[str, Any] | None:
    if not sb:
        return None
    uid = str(user_id)
    gid = str(girlfriend_id)
    try:
        q = sb.table("persona_vectors").select("vector_json,version_tag,vector_hash").eq(
            "user_id", uid
        ).eq("girlfriend_id", gid)
        if version_hint:
            q = q.eq("version_tag", version_hint)
        else:
            q = q.eq("is_active", True)
        r = q.order("updated_at", desc=True).limit(1).execute()
        if r.data:
            return r.data[0]
    except Exception:
        return None
    return None
