"""Intimacy achievement catalog + per-girlfriend unlocked status."""
import logging

from fastapi import APIRouter, Request

from app.services.intimacy_milestones import (
    INTIMACY_ACHIEVEMENTS,
    INTIMACY_ACHIEVEMENTS_BY_TIER,
    TIER_GATES,
    TIER_RARITY,
)
from app.api.store import (
    get_session_user,
    get_intimacy_achievements_unlocked,
    get_photo_for_intimacy_achievement,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intimacy", tags=["intimacy-achievements"])


def _session_id(request: Request) -> str | None:
    """Extract session_id from cookie or header."""
    return (
        request.cookies.get("session")
        or request.cookies.get("session_id")
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
