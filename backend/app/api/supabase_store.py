"""Supabase-backed store: read/write by user_id and girlfriend_id. Use service-role client."""
from uuid import UUID
from typing import Any
from datetime import datetime, timezone

from app.core.supabase_client import get_supabase_admin
from app.services.relationship_progression import RelationshipProgressState
from app.schemas.trust_intimacy import TrustIntimacyState
from app.services.achievement_engine import AchievementProgress


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
    out = {
        "id": str(row["user_id"]),
        "user_id": str(row["user_id"]),
        "email": row.get("email"),
        "display_name": row.get("display_name"),
        "current_girlfriend_id": row.get("current_girlfriend_id"),
    }
    try:
        user_uuid = UUID(str(row["user_id"]))
        profile = get_user_profile(user_uuid) or {}
        billing = get_billing_customer(user_uuid) or {}
        sub = get_latest_subscription(user_uuid) or {}
        out["display_name"] = profile.get("display_name") or out.get("display_name")
        out["language_pref"] = profile.get("language_pref", "en")
        out["age_gate_passed"] = bool(profile.get("age_gate_passed", False))
        out["plan"] = sub.get("plan", "free")
        out["stripe_subscription_id"] = sub.get("stripe_subscription_id")
        out["subscription_status"] = sub.get("status")
        out["current_period_end"] = sub.get("current_period_end")
        out["stripe_customer_id"] = billing.get("stripe_customer_id")
        out["default_payment_method_id"] = billing.get("default_payment_method_id")
        out["has_card_on_file"] = bool(billing.get("has_card_on_file", False))
    except Exception:
        pass
    return out


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
    try:
        uid = UUID(str(user_id))
        upsert_user_profile(
            uid,
            language_pref=data.get("language_pref", "en"),
            display_name=data.get("display_name"),
            age_gate_passed=data.get("age_gate_passed"),
        )
        if any(k in data for k in ("stripe_customer_id", "default_payment_method_id", "has_card_on_file")):
            upsert_billing_customer(
                uid,
                stripe_customer_id=data.get("stripe_customer_id"),
                default_payment_method_id=data.get("default_payment_method_id"),
                has_card_on_file=data.get("has_card_on_file"),
            )
        if any(k in data for k in ("plan", "stripe_subscription_id", "subscription_status", "current_period_end")):
            upsert_subscription(
                uid,
                plan=data.get("plan", "free"),
                stripe_subscription_id=data.get("stripe_subscription_id"),
                status=data.get("subscription_status"),
                current_period_end=data.get("current_period_end"),
            )
    except Exception:
        pass


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
    return {
        "user_id": row["user_id"],
        "language_pref": row.get("language_pref", "en"),
        "display_name": row.get("display_name"),
        "age_gate_passed": bool(row.get("age_gate_passed", False)),
    }


def upsert_user_profile(
    user_id: UUID,
    language_pref: str = "en",
    display_name: str | None = None,
    age_gate_passed: bool | None = None,
) -> None:
    sb = _admin()
    if not sb:
        return
    payload: dict[str, Any] = {"user_id": str(user_id), "language_pref": language_pref}
    if display_name is not None:
        payload["display_name"] = display_name
    if age_gate_passed is not None:
        payload["age_gate_passed"] = age_gate_passed
    sb.table("users_profile").upsert(payload, on_conflict="user_id").execute()


def get_billing_customer(user_id: UUID) -> dict[str, Any] | None:
    sb = _admin()
    if not sb:
        return None
    r = sb.table("billing_customers").select("*").eq("user_id", str(user_id)).limit(1).execute()
    if not r.data:
        return None
    return r.data[0]


def upsert_billing_customer(
    user_id: UUID,
    stripe_customer_id: str | None = None,
    default_payment_method_id: str | None = None,
    has_card_on_file: bool | None = None,
) -> None:
    sb = _admin()
    if not sb:
        return
    payload: dict[str, Any] = {"user_id": str(user_id)}
    if stripe_customer_id is not None:
        payload["stripe_customer_id"] = stripe_customer_id
    if default_payment_method_id is not None:
        payload["default_payment_method_id"] = default_payment_method_id
    if has_card_on_file is not None:
        payload["has_card_on_file"] = has_card_on_file
    sb.table("billing_customers").upsert(payload, on_conflict="user_id").execute()


def get_latest_subscription(user_id: UUID) -> dict[str, Any] | None:
    sb = _admin()
    if not sb:
        return None
    r = sb.table("subscriptions").select("*").eq("user_id", str(user_id)).order("created_at", desc=True).limit(1).execute()
    if not r.data:
        return None
    return r.data[0]


def upsert_subscription(
    user_id: UUID,
    plan: str,
    stripe_subscription_id: str | None = None,
    status: str | None = None,
    current_period_end: str | None = None,
) -> None:
    sb = _admin()
    if not sb:
        return
    existing = get_latest_subscription(user_id)
    payload: dict[str, Any] = {
        "user_id": str(user_id),
        "plan": plan,
        "stripe_subscription_id": stripe_subscription_id,
        "status": status,
        "current_period_end": current_period_end,
    }
    if existing and existing.get("id"):
        sb.table("subscriptions").update(payload).eq("id", existing["id"]).execute()
    else:
        sb.table("subscriptions").insert(payload).execute()


def _row_to_girlfriend(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a DB girlfriend row to a full dict with all fields."""
    return {
        "id": row["id"],
        "display_name": row.get("display_name"),
        "name": row.get("name"),
        "avatar_url": row.get("avatar_url"),
        "traits": row.get("traits") or {},
        "appearance_prefs": row.get("appearance_prefs") or {},
        "content_prefs": row.get("content_prefs") or {},
        "identity": row.get("identity") or {},
        "identity_canon": row.get("identity_canon") or {},
        "created_at": row["created_at"],
    }


def get_girlfriend_by_id(user_id: UUID, girlfriend_id: UUID) -> dict[str, Any] | None:
    sb = _admin()
    if not sb:
        return None
    r = sb.table("girlfriends").select("*").eq("user_id", str(user_id)).eq("id", str(girlfriend_id)).execute()
    if not r.data or len(r.data) == 0:
        return None
    return _row_to_girlfriend(r.data[0])


def get_current_girlfriend(user_id: UUID, current_girlfriend_id: str | None = None) -> dict[str, Any] | None:
    """Get the current girlfriend. If current_girlfriend_id is provided, look up by ID.
    Otherwise fall back to the first girlfriend (ordered by created_at)."""
    sb = _admin()
    if not sb:
        return None
    # If we know which girlfriend is current, fetch that specific one
    if current_girlfriend_id:
        r = sb.table("girlfriends").select("*").eq("user_id", str(user_id)).eq("id", current_girlfriend_id).execute()
        if r.data and len(r.data) > 0:
            return _row_to_girlfriend(r.data[0])
    # Fallback: first girlfriend
    r = sb.table("girlfriends").select("*").eq("user_id", str(user_id)).order("created_at").limit(1).execute()
    if not r.data or len(r.data) == 0:
        return None
    return _row_to_girlfriend(r.data[0])


def create_girlfriend(user_id: UUID, display_name: str, traits: dict, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    sb = _admin()
    if not sb:
        raise RuntimeError("Supabase not configured")
    payload = {
        "user_id": str(user_id),
        "display_name": display_name,
        "traits": traits,
    }
    if extra:
        for key in ("avatar_url", "appearance_prefs", "content_prefs", "identity", "identity_canon"):
            if key in extra:
                payload[key] = extra.get(key)
    r = sb.table("girlfriends").insert(payload).execute()
    if not r.data or len(r.data) == 0:
        raise RuntimeError("Failed to create girlfriend")
    row = r.data[0]
    return {
        "id": row["id"],
        "display_name": row["display_name"],
        "traits": row.get("traits") or {},
        "created_at": row["created_at"],
    }


def list_girlfriends(user_id: UUID) -> list[dict[str, Any]]:
    sb = _admin()
    if not sb:
        return []
    r = sb.table("girlfriends").select("*").eq("user_id", str(user_id)).order("created_at").execute()
    if not r.data:
        return []
    return [_row_to_girlfriend(row) for row in r.data]


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
    messages: list[dict[str, Any]] = []
    for row in r.data:
        base: dict[str, Any] = {
            "id": row["id"],
            "role": row["role"],
            "content": row.get("content"),
            "image_url": row.get("image_url"),
            "event_type": row.get("event_type"),
            "event_key": row.get("event_key"),
            "created_at": row["created_at"],
        }
        # Merge any structured payload back into the message so the frontend
        # can render rich cards (gain_data, achievement, gift_data, etc.)
        raw_payload = row.get("payload")
        if isinstance(raw_payload, dict):
            for k, v in raw_payload.items():
                if k in base:
                    continue
                base[k] = v
        messages.append(base)
    return messages


def append_message(user_id: UUID, girlfriend_id: UUID, msg: dict[str, Any]) -> None:
    sb = _admin()
    if not sb:
        return
    payload: dict[str, Any] = {
        "user_id": str(user_id),
        "girlfriend_id": str(girlfriend_id),
        "role": msg["role"],
        "content": msg.get("content"),
        "image_url": msg.get("image_url"),
        "event_type": msg.get("event_type"),
        "event_key": msg.get("event_key"),
    }
    # Persist additional structured data for rich events into the payload column.
    # This lets chat history reconstruct cards like relationship_gain, achievements, gifts, etc.
    extra: dict[str, Any] = {}
    for k, v in msg.items():
        if k in ("id", "role", "content", "image_url", "event_type", "event_key", "created_at"):
            continue
        extra[k] = v
    if extra:
        payload["payload"] = extra
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


def get_gallery_items(user_id: UUID, girlfriend_id: UUID) -> list[dict[str, Any]]:
    sb = _admin()
    if not sb:
        return []
    r = (
        sb.table("gallery_items")
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
            "url": row.get("image_url"),
            "created_at": row["created_at"],
            "caption": row.get("caption"),
        }
        for row in r.data
    ]


def add_gallery_item(user_id: UUID, girlfriend_id: UUID, item: dict[str, Any]) -> None:
    sb = _admin()
    if not sb:
        return
    payload = {
        "user_id": str(user_id),
        "girlfriend_id": str(girlfriend_id),
        "source": item.get("source", "generated"),
        "image_url": item.get("url"),
        "caption": item.get("caption"),
        "metadata": item.get("metadata") or {},
    }
    sb.table("gallery_items").insert(payload).execute()


def replace_gallery_items(user_id: UUID, girlfriend_id: UUID, items: list[dict[str, Any]]) -> None:
    sb = _admin()
    if not sb:
        return
    sb.table("gallery_items").delete().eq("user_id", str(user_id)).eq("girlfriend_id", str(girlfriend_id)).execute()
    for item in items:
        add_gallery_item(user_id, girlfriend_id, item)


def _parse_iso_dt(v: Any) -> datetime | None:
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except Exception:
        return None


def get_relationship_progress(user_id: UUID, girlfriend_id: UUID) -> RelationshipProgressState:
    sb = _admin()
    if not sb:
        return RelationshipProgressState()
    r = (
        sb.table("relationship_progress")
        .select("*")
        .eq("user_id", str(user_id))
        .eq("girlfriend_id", str(girlfriend_id))
        .execute()
    )
    if not r.data:
        return RelationshipProgressState()
    row = r.data[0]
    recent = []
    for ts in (row.get("recent_message_timestamps") or []):
        dt = _parse_iso_dt(ts)
        if dt:
            recent.append(dt)
    return RelationshipProgressState(
        level=row.get("level", 0),
        banked_points=row.get("banked_points", 0),
        streak_days=row.get("streak_days", 0),
        last_interaction_at=_parse_iso_dt(row.get("last_interaction_at")),
        last_award_at=_parse_iso_dt(row.get("last_award_at")),
        recent_message_timestamps=recent,
    )


def upsert_relationship_progress(user_id: UUID, girlfriend_id: UUID, state: RelationshipProgressState) -> None:
    sb = _admin()
    if not sb:
        return
    payload = {
        "user_id": str(user_id),
        "girlfriend_id": str(girlfriend_id),
        "level": state.level,
        "banked_points": state.banked_points,
        "streak_days": state.streak_days,
        "last_interaction_at": state.last_interaction_at.isoformat() if state.last_interaction_at else None,
        "last_award_at": state.last_award_at.isoformat() if state.last_award_at else None,
        "recent_message_timestamps": [dt.isoformat() for dt in state.recent_message_timestamps],
    }
    sb.table("relationship_progress").upsert(payload, on_conflict="user_id,girlfriend_id").execute()


def get_trust_intimacy_state(user_id: UUID, girlfriend_id: UUID) -> TrustIntimacyState:
    sb = _admin()
    if not sb:
        return TrustIntimacyState()
    r = (
        sb.table("trust_intimacy_state")
        .select("*")
        .eq("user_id", str(user_id))
        .eq("girlfriend_id", str(girlfriend_id))
        .execute()
    )
    if not r.data:
        return TrustIntimacyState()
    row = r.data[0]
    return TrustIntimacyState(
        trust_visible=row.get("trust_visible", 20),
        trust_bank=row.get("trust_bank", 0),
        intimacy_visible=row.get("intimacy_visible", 1),
        intimacy_bank=row.get("intimacy_bank", 0),
        trust_last_gain_at=_parse_iso_dt(row.get("trust_last_gain_at")),
        intimacy_last_gain_at=_parse_iso_dt(row.get("intimacy_last_gain_at")),
        trust_gained_today=row.get("trust_gained_today", 0),
        intimacy_gained_today=row.get("intimacy_gained_today", 0),
        intimacy_gained_today_gifts=row.get("intimacy_gained_today_gifts", 0),
        trust_gained_today_gifts=row.get("trust_gained_today_gifts", 0),
        cap_date=row.get("cap_date"),
        used_region_ids=list(row.get("used_region_ids") or []),
        used_gift_ids_intimacy=list(row.get("used_gift_ids_intimacy") or []),
        used_gift_ids_trust=list(row.get("used_gift_ids_trust") or []),
    )


def upsert_trust_intimacy_state(user_id: UUID, girlfriend_id: UUID, state: TrustIntimacyState) -> None:
    sb = _admin()
    if not sb:
        return
    payload = {
        "user_id": str(user_id),
        "girlfriend_id": str(girlfriend_id),
        "trust_visible": state.trust_visible,
        "trust_bank": state.trust_bank,
        "intimacy_visible": state.intimacy_visible,
        "intimacy_bank": state.intimacy_bank,
        "trust_last_gain_at": state.trust_last_gain_at.isoformat() if state.trust_last_gain_at else None,
        "intimacy_last_gain_at": state.intimacy_last_gain_at.isoformat() if state.intimacy_last_gain_at else None,
        "trust_gained_today": state.trust_gained_today,
        "intimacy_gained_today": state.intimacy_gained_today,
        "intimacy_gained_today_gifts": state.intimacy_gained_today_gifts,
        "trust_gained_today_gifts": state.trust_gained_today_gifts,
        "cap_date": state.cap_date,
        "used_region_ids": state.used_region_ids,
        "used_gift_ids_intimacy": state.used_gift_ids_intimacy,
        "used_gift_ids_trust": state.used_gift_ids_trust,
    }
    sb.table("trust_intimacy_state").upsert(payload, on_conflict="user_id,girlfriend_id").execute()


def get_achievement_progress(user_id: UUID, girlfriend_id: UUID) -> AchievementProgress:
    sb = _admin()
    if not sb:
        return AchievementProgress()
    r = (
        sb.table("achievement_progress")
        .select("*")
        .eq("user_id", str(user_id))
        .eq("girlfriend_id", str(girlfriend_id))
        .execute()
    )
    if not r.data:
        return AchievementProgress()
    return AchievementProgress.from_dict(r.data[0])


def upsert_achievement_progress(user_id: UUID, girlfriend_id: UUID, progress: AchievementProgress) -> None:
    sb = _admin()
    if not sb:
        return
    payload = {"user_id": str(user_id), "girlfriend_id": str(girlfriend_id), **progress.to_dict()}
    sb.table("achievement_progress").upsert(payload, on_conflict="user_id,girlfriend_id").execute()


def list_gift_purchases(user_id: UUID, girlfriend_id: UUID) -> list[dict[str, Any]]:
    sb = _admin()
    if not sb:
        return []
    r = (
        sb.table("gift_purchases")
        .select("*")
        .eq("user_id", str(user_id))
        .eq("girlfriend_id", str(girlfriend_id))
        .order("created_at")
        .execute()
    )
    return list(r.data or [])


def create_gift_purchase(user_id: UUID, girlfriend_id: UUID, purchase: dict[str, Any]) -> dict[str, Any] | None:
    sb = _admin()
    if not sb:
        return None
    payload = {
        "user_id": str(user_id),
        "girlfriend_id": str(girlfriend_id),
        "gift_id": purchase.get("gift_id"),
        "gift_name": purchase.get("gift_name"),
        "amount_eur": purchase.get("amount_eur"),
        "currency": purchase.get("currency", "eur"),
        "stripe_session_id": purchase.get("stripe_session_id"),
        "stripe_payment_intent": purchase.get("stripe_payment_intent") or purchase.get("stripe_session_id"),
        "status": purchase.get("status", "pending"),
        "metadata": purchase.get("metadata") or {},
    }
    r = sb.table("gift_purchases").insert(payload).execute()
    if not r.data:
        return None
    return r.data[0]


def update_gift_purchase_status_by_payment_intent(payment_intent: str, status: str) -> dict[str, Any] | None:
    sb = _admin()
    if not sb:
        return None
    r = (
        sb.table("gift_purchases")
        .update({"status": status})
        .eq("stripe_payment_intent", payment_intent)
        .execute()
    )
    if not r.data:
        return None
    return r.data[0]


def update_gift_purchase_status_by_session(session_id: str, status: str) -> dict[str, Any] | None:
    sb = _admin()
    if not sb:
        return None
    r = (
        sb.table("gift_purchases")
        .update({"status": status})
        .eq("stripe_session_id", session_id)
        .execute()
    )
    if not r.data:
        return None
    return r.data[0]


def create_image_job(
    user_id: UUID,
    girlfriend_id: UUID,
    status: str,
    image_url: str | None = None,
    request_prompt: str | None = None,
    error: str | None = None,
) -> dict[str, Any] | None:
    sb = _admin()
    if not sb:
        return None
    payload = {
        "user_id": str(user_id),
        "girlfriend_id": str(girlfriend_id),
        "status": status,
        "image_url": image_url,
        "request_prompt": request_prompt,
        "error": error,
        "completed_at": datetime.now(timezone.utc).isoformat() if status in ("done", "failed") else None,
    }
    r = sb.table("image_jobs").insert(payload).execute()
    if not r.data:
        return None
    return r.data[0]


def get_image_job(user_id: UUID, girlfriend_id: UUID, job_id: str) -> dict[str, Any] | None:
    sb = _admin()
    if not sb:
        return None
    r = (
        sb.table("image_jobs")
        .select("*")
        .eq("id", str(job_id))
        .eq("user_id", str(user_id))
        .eq("girlfriend_id", str(girlfriend_id))
        .limit(1)
        .execute()
    )
    if not r.data:
        return None
    return r.data[0]
