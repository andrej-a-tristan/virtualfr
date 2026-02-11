"""Intimacy achievement catalog + per-girlfriend unlocked status + mystery-box unlock."""
import hashlib
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.intimacy_milestones import (
    INTIMACY_ACHIEVEMENTS,
    INTIMACY_ACHIEVEMENTS_BY_TIER,
    ALL_INTIMACY_ACHIEVEMENTS,
    TIER_GATES,
    TIER_RARITY,
)
from app.api.request_context import get_current_user
from app.api.store import (
    get_session_user,
    get_intimacy_achievements_unlocked,
    mark_intimacy_achievement_unlocked,
    get_photo_for_intimacy_achievement,
    set_photo_for_intimacy_achievement,
    get_intimacy_last_award_time,
    set_intimacy_last_award_time,
    add_gallery_item,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intimacy", tags=["intimacy-achievements"])


def _session_id(request: Request) -> str | None:
    """Extract session_id from cookie or header."""
    return (
        request.cookies.get("session_id")
        or request.headers.get("x-session-id")
        or None
    )


@router.get("/achievements")
def get_intimacy_achievements(
    request: Request,
    girlfriend_id: str | None = None,
    include_secrets: bool = False,
):
    """Return full intimacy achievement catalog grouped by tier.

    Per-girlfriend: includes unlocked status and image_url if earned.
    Secret achievements show as '???' unless unlocked or include_secrets=true.
    """
    sid = _session_id(request)
    user = get_session_user(sid) if sid else None

    # Per-girlfriend unlocked state
    unlocked_map: dict[str, str] = {}
    if sid and user:
        if not girlfriend_id:
            girlfriend_id = (user or {}).get("current_girlfriend_id")
        if girlfriend_id:
            unlocked_map = get_intimacy_achievements_unlocked(sid, girlfriend_id=girlfriend_id)

    result: dict[int, dict] = {}
    for tier, achievements in sorted(INTIMACY_ACHIEVEMENTS_BY_TIER.items()):
        gate = TIER_GATES.get(tier, {})
        tier_info = {
            "tier": tier,
            "rarity": TIER_RARITY.get(tier, "COMMON").value if hasattr(TIER_RARITY.get(tier, "COMMON"), "value") else str(TIER_RARITY.get(tier, "COMMON")),
            "required_region_index": gate.get("required_region_index", 0),
            "required_intimacy_visible": gate.get("required_intimacy_visible"),
            "achievements": [],
        }

        for a in achievements:
            is_unlocked = a.id in unlocked_map
            is_revealed = include_secrets or not a.is_secret or is_unlocked

            if a.is_secret and not is_revealed:
                tier_info["achievements"].append({
                    "id": a.id,
                    "tier": a.tier,
                    "title": "???",
                    "subtitle": "A hidden intimate achievement awaits...",
                    "rarity": a.rarity.value,
                    "sort_order": a.sort_order,
                    "is_secret": True,
                    "unlocked": False,
                    "unlocked_at": None,
                    "image_url": None,
                    "icon": "❓",
                })
            else:
                # Get photo if unlocked
                image_url = None
                if is_unlocked and sid and girlfriend_id:
                    image_url = get_photo_for_intimacy_achievement(sid, a.id, girlfriend_id=girlfriend_id)

                tier_info["achievements"].append({
                    "id": a.id,
                    "tier": a.tier,
                    "title": a.title,
                    "subtitle": a.subtitle,
                    "rarity": a.rarity.value,
                    "sort_order": a.sort_order,
                    "is_secret": a.is_secret,
                    "unlocked": is_unlocked,
                    "unlocked_at": unlocked_map.get(a.id),
                    "image_url": image_url,
                    "icon": a.icon,
                })

        result[tier] = tier_info

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# MYSTERY BOX UNLOCK  — bypasses tier/region/intimacy gates
# ═══════════════════════════════════════════════════════════════════════════════

class MysteryUnlockRequest(BaseModel):
    achievement_id: str
    girlfriend_id: str | None = None


@router.post("/mystery-unlock")
def mystery_unlock(request: Request, body: MysteryUnlockRequest):
    """Unlock an intimacy achievement via mystery box ("Seduce Her Now").

    This is the ONLY path that bypasses the normal tier/region/intimacy gates.
    - Achievement must exist in the catalog.
    - Achievement must not already be unlocked for this girlfriend.
    - Generates a photo immediately (no throttle for mystery box unlocks).
    - Does NOT award any trust/intimacy points.
    """
    sid = _session_id(request)
    user = get_session_user(sid) if sid else None
    if not sid or not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    girlfriend_id = body.girlfriend_id or (user or {}).get("current_girlfriend_id")
    if not girlfriend_id:
        return JSONResponse(status_code=400, content={"error": "no_girlfriend"})

    # Validate achievement exists
    ach = INTIMACY_ACHIEVEMENTS.get(body.achievement_id)
    if not ach:
        return JSONResponse(status_code=404, content={"error": "achievement_not_found"})

    # Check not already unlocked
    unlocked = get_intimacy_achievements_unlocked(sid, girlfriend_id=girlfriend_id)
    if body.achievement_id in unlocked:
        # Already unlocked — return existing data (idempotent)
        image_url = get_photo_for_intimacy_achievement(sid, body.achievement_id, girlfriend_id=girlfriend_id)
        return {
            "ok": True,
            "already_unlocked": True,
            "achievement_id": ach.id,
            "title": ach.title,
            "subtitle": ach.subtitle,
            "rarity": ach.rarity.value,
            "tier": ach.tier,
            "icon": ach.icon,
            "image_url": image_url,
        }

    # Unlock — NO tier/region/intimacy gate check (mystery box bypass)
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    mark_intimacy_achievement_unlocked(sid, ach.id, now_iso, girlfriend_id=girlfriend_id)

    # Generate photo immediately (mystery boxes skip the 6h throttle)
    seed = hashlib.md5(f"{girlfriend_id}:{ach.id}".encode()).hexdigest()[:10]
    image_url = f"https://picsum.photos/seed/{seed}/400/400"

    set_photo_for_intimacy_achievement(sid, ach.id, image_url, girlfriend_id=girlfriend_id)
    add_gallery_item(sid, {
        "id": f"intach-{ach.id}-{uuid.uuid4().hex[:6]}",
        "url": image_url,
        "created_at": now_iso,
        "caption": f"{ach.icon} {ach.title}",
        "source": "intimacy_achievement_mystery",
        "achievement_id": ach.id,
    }, girlfriend_id=girlfriend_id)

    # Update last award time (so normal chat-based unlocks respect throttle)
    set_intimacy_last_award_time(sid, now_iso, girlfriend_id=girlfriend_id)

    logger.info("Mystery box unlocked intimacy achievement: %s (tier=%d, rarity=%s)",
                ach.id, ach.tier, ach.rarity.value)

    return {
        "ok": True,
        "already_unlocked": False,
        "achievement_id": ach.id,
        "title": ach.title,
        "subtitle": ach.subtitle,
        "rarity": ach.rarity.value,
        "tier": ach.tier,
        "icon": ach.icon,
        "image_url": image_url,
        "unlocked_at": now_iso,
    }
