"""Profile route: aggregated per-girlfriend stats for the Profile page."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request, HTTPException

from app.api.store import (
    get_session_user,
    get_all_girlfriends,
    get_messages,
    get_gallery,
    get_trust_intimacy_state,
    get_achievement_progress,
    get_intimacy_achievements_unlocked,
)
from app.schemas.profile import (
    GirlProfileStats,
    RelationshipSnapshot,
    ActivitySnapshot,
    CollectionsSnapshot,
    ProfileTotals,
    ProfileGirlsResponse,
)
from app.services.streaks import compute_streaks
from app.services.relationship_regions import REGIONS, get_region_for_level

# Gift purchases are stored in the gifts route module
from app.api.routes.gifts import _gift_purchases
from app.services.gifting import GIFT_CATALOG
from app.services.relationship_milestones import ACHIEVEMENTS
from app.services.intimacy_milestones import ALL_INTIMACY_ACHIEVEMENTS

router = APIRouter(prefix="/profile", tags=["profile"])
logger = logging.getLogger(__name__)

SESSION_COOKIE = "session"

GIFTS_TOTAL = len(GIFT_CATALOG)
RELATIONSHIP_ACHIEVEMENTS_TOTAL = len(ACHIEVEMENTS)
INTIMACY_ACHIEVEMENTS_TOTAL = len(ALL_INTIMACY_ACHIEVEMENTS)

# Region-index → high-level label mapping (1-based index)
_LEVEL_LABELS = {
    1: "STRANGER",
    2: "STRANGER",
    3: "FAMILIAR",
    4: "FAMILIAR",
    5: "CLOSE",
    6: "CLOSE",
    7: "INTIMATE",
    8: "INTIMATE",
    9: "EXCLUSIVE",
}


def _session_id(request: Request) -> str | None:
    return (
        request.cookies.get(SESSION_COOKIE)
        or request.cookies.get("session_id")
        or request.headers.get("x-session-id")
        or None
    )


def _require_user(request: Request) -> tuple[str, dict]:
    sid = _session_id(request)
    if not sid:
        raise HTTPException(status_code=401, detail="unauthorized")
    user = get_session_user(sid)
    if not user:
        raise HTTPException(status_code=401, detail="unauthorized")
    return sid, user


def _build_vibe_line(gf: dict[str, Any]) -> str:
    """Build a short subtitle from identity or traits."""
    identity = gf.get("identity") or {}
    parts: list[str] = []

    job = identity.get("job_vibe")
    if job:
        parts.append(job)
    origin = identity.get("origin_vibe")
    if origin:
        parts.append(origin)
    hobbies = identity.get("hobbies") or []
    if hobbies:
        parts.append(hobbies[0])

    if parts:
        return " \u2022 ".join(parts)

    # Fallback to trait values
    traits = gf.get("traits") or {}
    trait_vals = [
        str(v) for v in [
            traits.get("emotional_style"),
            traits.get("communication_style"),
            traits.get("cultural_personality"),
        ] if v
    ]
    return " \u2022 ".join(trait_vals[:3]) if trait_vals else "Your companion"


def _get_region_index_from_level(level: int) -> int:
    """Return 1-based region index for a level value."""
    region = get_region_for_level(level)
    for i, r in enumerate(REGIONS, start=1):
        if r.key == region.key:
            return i
    return 1


def _parse_message_times(messages: list[dict[str, Any]]) -> list[datetime]:
    """Extract datetime objects from message created_at fields."""
    times: list[datetime] = []
    for msg in messages:
        ca = msg.get("created_at")
        if not ca:
            continue
        try:
            dt = datetime.fromisoformat(ca)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            times.append(dt)
        except (ValueError, TypeError):
            continue
    return times


@router.get("/girls", response_model=ProfileGirlsResponse)
def get_profile_girls(request: Request):
    """Return aggregated stats for every girlfriend in the session."""
    sid, user = _require_user(request)
    girlfriends = get_all_girlfriends(sid)

    girls: list[GirlProfileStats] = []
    total_messages = 0
    total_photos = 0
    total_gifts = 0

    for gf in girlfriends:
        gf_id = gf.get("id", "")
        name = gf.get("display_name") or gf.get("name") or "Companion"
        avatar_url = gf.get("avatar_url")

        # ── Vibe line ─────────────────────────────────────────────────
        vibe_line = _build_vibe_line(gf)

        # ── Relationship snapshot ─────────────────────────────────────
        ti_state = get_trust_intimacy_state(sid, gf_id)
        # Determine region index from relationship state or trust+intimacy
        # The relationship state dict may carry level/current_region_index
        level = 0
        region_index: int | None = None
        region_title: str | None = None

        # Try to get level from chat state (relationship_state stored in store)
        from app.api.store import get_relationship_state as _get_rel_state
        rel_state = _get_rel_state(sid, gf_id)
        if rel_state:
            level = rel_state.get("level", 0)
            region_index = rel_state.get("current_region_index")
            region_title = rel_state.get("region_title")

        if region_index is None:
            region_index = _get_region_index_from_level(level)

        if region_title is None:
            region = get_region_for_level(level)
            region_title = region.title

        # Trust / intimacy caps come from region system
        trust_cap = 100
        intimacy_cap = 100
        if rel_state:
            trust_cap = rel_state.get("trust_cap", 100) or 100
            intimacy_cap = rel_state.get("intimacy_cap", 100) or 100

        level_label = _LEVEL_LABELS.get(region_index, "STRANGER")

        relationship = RelationshipSnapshot(
            level_label=level_label,
            trust_visible=ti_state.trust_visible,
            trust_cap=trust_cap,
            intimacy_visible=ti_state.intimacy_visible,
            intimacy_cap=intimacy_cap,
            current_region_index=region_index,
            region_title=region_title,
        )

        # ── Activity ──────────────────────────────────────────────────
        messages = get_messages(sid, gf_id)
        message_count = len(messages)
        total_messages += message_count

        msg_times = _parse_message_times(messages)
        streaks = compute_streaks(msg_times)

        last_interaction_at: str | None = None
        if msg_times:
            last_interaction_at = max(msg_times).isoformat()

        activity = ActivitySnapshot(
            message_count=message_count,
            last_interaction_at=last_interaction_at,
            streak_current_days=streaks.current_days,
            streak_best_days=streaks.best_days,
            streak_active_today=streaks.active_today,
        )

        # ── Collections ───────────────────────────────────────────────
        gallery = get_gallery(sid, gf_id)
        photos_count = len(gallery)
        total_photos += photos_count

        # Gift purchases stored in gifts module
        gift_key = (sid, gf_id)
        purchases = _gift_purchases.get(gift_key, [])
        paid_purchases = [p for p in purchases if p.get("status") == "paid"]
        gifts_owned = len(set(p.get("gift_id") for p in paid_purchases))
        total_gifts += gifts_owned

        # Relationship achievements: milestones_reached on relationship state
        rel_achievements_unlocked = 0
        if rel_state:
            milestones = rel_state.get("milestones_reached", [])
            rel_achievements_unlocked = len(milestones)

        # Intimacy achievements
        intimacy_unlocked_dict = get_intimacy_achievements_unlocked(sid, gf_id)
        intimacy_achievements_unlocked = len(intimacy_unlocked_dict)

        collections = CollectionsSnapshot(
            photos=photos_count,
            gifts_owned=gifts_owned,
            gifts_total=GIFTS_TOTAL,
            relationship_achievements_unlocked=rel_achievements_unlocked,
            relationship_achievements_total=RELATIONSHIP_ACHIEVEMENTS_TOTAL,
            intimacy_achievements_unlocked=intimacy_achievements_unlocked,
            intimacy_achievements_total=INTIMACY_ACHIEVEMENTS_TOTAL,
        )

        girls.append(GirlProfileStats(
            girlfriend_id=gf_id,
            name=name,
            avatar_url=avatar_url,
            vibe_line=vibe_line,
            relationship=relationship,
            activity=activity,
            collections=collections,
        ))

    return ProfileGirlsResponse(
        girls=girls,
        totals=ProfileTotals(
            girls=len(girls),
            messages=total_messages,
            photos=total_photos,
            gifts_owned=total_gifts,
        ),
    )
