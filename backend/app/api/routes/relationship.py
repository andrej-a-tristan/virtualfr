"""Relationship achievement catalog endpoint."""
from fastapi import APIRouter, Request

from app.services.relationship_milestones import ACHIEVEMENTS_BY_REGION
from app.api.request_context import get_current_user
from app.api.store import get_relationship_state

router = APIRouter(prefix="/relationship", tags=["relationship"])


@router.get("/achievements")
def get_achievements_catalog(
    request: Request,
    include_secrets: bool = False,
):
    """Return the achievement catalog grouped by region index (0..8).

    Secret achievements are excluded by default unless:
    - include_secrets=true query param is passed, OR
    - the user has already unlocked the secret achievement

    Each entry contains: id, region_index, title, subtitle, rarity, sort_order,
    trigger, is_secret, narrative_hook.
    """
    # Try to get the user's unlocked milestones for secret reveal check
    unlocked_ids: set[str] = set()
    try:
        sid, user, _, _ = get_current_user(request)
        if sid and user:
            rs = get_relationship_state(sid) or {}
            unlocked_ids = set(rs.get("milestones_reached", []))
    except Exception:
        pass

    result: dict[int, list[dict]] = {}
    for region_idx, achievements in sorted(ACHIEVEMENTS_BY_REGION.items()):
        region_list = []
        for a in achievements:
            # Determine if we should include this achievement
            is_revealed = include_secrets or not a.is_secret or a.id in unlocked_ids

            if a.is_secret and not is_revealed:
                # Include a placeholder for secret achievements
                region_list.append({
                    "id": a.id,
                    "region_index": a.region_index,
                    "title": "???",
                    "subtitle": "A hidden achievement awaits...",
                    "rarity": a.rarity.value,
                    "sort_order": a.sort_order,
                    "trigger": a.trigger.value,
                    "is_secret": True,
                    "narrative_hook": "",
                })
            else:
                region_list.append({
                    "id": a.id,
                    "region_index": a.region_index,
                    "title": a.title,
                    "subtitle": a.subtitle,
                    "rarity": a.rarity.value,
                    "sort_order": a.sort_order,
                    "trigger": a.trigger.value,
                    "is_secret": a.is_secret,
                    "narrative_hook": a.narrative_hook,
                })
        result[region_idx] = region_list
    return {"achievements_by_region": result}
