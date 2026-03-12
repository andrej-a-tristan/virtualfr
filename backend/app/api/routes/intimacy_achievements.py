"""Intimacy achievement catalog + per-girlfriend unlocked status + mystery-box unlock."""
import hashlib
import logging
import uuid
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import get_settings
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
    set_session_user,
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

    # Also emit a persistent chat message so the unlock shows up in history.
    try:
        from app.api.store import append_message as store_append_message

        msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": f"{ach.icon or '🔥'} **{ach.title}** unlocked — {ach.subtitle}",
            "image_url": image_url,
            "event_type": "intimacy_achievement",
            "event_key": ach.id,
            "created_at": now_iso,
            "achievement": {
                "id": ach.id,
                "title": ach.title,
                "subtitle": ach.subtitle,
                "rarity": ach.rarity.value,
                "tier": ach.tier,
                "icon": ach.icon,
            },
        }
        store_append_message(sid, msg, girlfriend_id=girlfriend_id)
    except Exception as exc:
        logger.warning("Failed to append intimacy_achievement message (mystery_unlock): %s", exc)

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


# ═══════════════════════════════════════════════════════════════════════════════
# INTIMATE BOX PURCHASE — charge saved card, then unlock achievement
# ═══════════════════════════════════════════════════════════════════════════════

# Box definitions matching the frontend INTIMATE_BOXES
INTIMATE_BOXES: dict[str, dict] = {
    "tease": {
        "id": "tease",
        "name": "Gentle Tease",
        "price_eur": 4.99,
        "free_on_plan": "plus",
    },
    "desire": {
        "id": "desire",
        "name": "Burning Desire",
        "price_eur": 8.49,
        "free_on_plan": "premium",
    },
    "obsession": {
        "id": "obsession",
        "name": "Dark Obsession",
        "price_eur": 13.99,
        "free_on_plan": "premium",
    },
}

SESSION_COOKIE = "session"


def _require_user_for_purchase(request: Request) -> tuple[str, dict]:
    """Return (session_id, user_dict) or raise 401."""
    sid = (
        request.cookies.get(SESSION_COOKIE)
        or request.cookies.get("session_id")
        or request.headers.get("x-session-id")
        or None
    )
    if not sid:
        raise HTTPException(status_code=401, detail="unauthorized")
    user = get_session_user(sid)
    if not user:
        raise HTTPException(status_code=401, detail="unauthorized")
    return sid, user


def _get_default_pm(user: dict, sid: str) -> tuple[str, str]:
    """Return (stripe_customer_id, default_pm_id) or raise."""
    settings = get_settings()
    if not settings.stripe_secret_key:
        return "", ""  # dev mode — no Stripe

    stripe.api_key = settings.stripe_secret_key

    stripe_customer_id = user.get("stripe_customer_id")
    if not stripe_customer_id:
        # Create customer on-the-fly
        customer = stripe.Customer.create(
            email=user.get("email", ""),
            metadata={"user_id": user.get("id", "")},
        )
        stripe_customer_id = customer.id
        set_session_user(sid, {**user, "stripe_customer_id": stripe_customer_id})

    default_pm = user.get("default_payment_method_id")
    if not default_pm:
        pms = stripe.Customer.list_payment_methods(stripe_customer_id, type="card", limit=1)
        if pms.data:
            default_pm = pms.data[0].id
            set_session_user(sid, {**user, "default_payment_method_id": default_pm})

    return stripe_customer_id, default_pm or ""


class IntimateBoxPurchaseRequest(BaseModel):
    box_id: str
    achievement_id: str
    girlfriend_id: str | None = None


@router.post("/purchase-box")
def purchase_intimate_box(request: Request, body: IntimateBoxPurchaseRequest):
    """Charge the user's saved card for an intimate box, then unlock the achievement.

    Returns:
      - status: "succeeded" | "requires_action" | "no_card" | "free"
      - Plus all the unlock data (achievement_id, title, image_url, etc.)
    """
    sid, user = _require_user_for_purchase(request)

    box = INTIMATE_BOXES.get(body.box_id)
    if not box:
        raise HTTPException(status_code=400, detail="Invalid box_id")

    girlfriend_id = body.girlfriend_id or user.get("current_girlfriend_id")
    if not girlfriend_id:
        raise HTTPException(status_code=400, detail="no_girlfriend")

    # Validate achievement exists
    ach = INTIMACY_ACHIEVEMENTS.get(body.achievement_id)
    if not ach:
        raise HTTPException(status_code=404, detail="achievement_not_found")

    # Check not already unlocked
    unlocked = get_intimacy_achievements_unlocked(sid, girlfriend_id=girlfriend_id)
    if body.achievement_id in unlocked:
        image_url = get_photo_for_intimacy_achievement(sid, body.achievement_id, girlfriend_id=girlfriend_id)
        return {
            "status": "free",
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

    # ── Check if box is free on user's plan ───────────────────────────────
    plan = user.get("plan", "free")
    plan_order = {"free": 0, "plus": 1, "premium": 2}
    free_on = box.get("free_on_plan", "")
    is_free = plan_order.get(plan, 0) >= plan_order.get(free_on, 99)

    # ── Charge if not free ────────────────────────────────────────────────
    payment_status = "free" if is_free else "pending"
    client_secret = None

    if not is_free:
        stripe_customer_id, default_pm = _get_default_pm(user, sid)

        if not stripe_customer_id or not default_pm:
            # Dev mode fallback — deliver for free
            settings = get_settings()
            if not settings.stripe_secret_key:
                logger.info("DEV MODE: Intimate box delivered free (no Stripe)")
                payment_status = "free"
            else:
                return {
                    "status": "no_card",
                    "error": "No card on file. Please add a card first.",
                }
        else:
            # Charge the saved card
            amount_cents = int(round(box["price_eur"] * 100))
            try:
                pi = stripe.PaymentIntent.create(
                    amount=amount_cents,
                    currency="eur",
                    customer=stripe_customer_id,
                    payment_method=default_pm,
                    off_session=True,
                    confirm=True,
                    description=f"Intimate Box: {box['name']}",
                    metadata={
                        "type": "intimate_box",
                        "box_id": body.box_id,
                        "achievement_id": body.achievement_id,
                        "user_id": user.get("id", ""),
                        "girlfriend_id": girlfriend_id,
                        "session_id": sid,
                    },
                )

                if pi.status == "succeeded":
                    payment_status = "succeeded"
                elif pi.status == "requires_action":
                    return {
                        "status": "requires_action",
                        "client_secret": pi.client_secret,
                        "payment_intent_id": pi.id,
                    }
                else:
                    raise HTTPException(status_code=402, detail=f"Payment failed: {pi.status}")
            except stripe.error.CardError as e:
                raise HTTPException(status_code=402, detail=str(e.user_message or e))

    # ── Unlock the achievement ────────────────────────────────────────────
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    mark_intimacy_achievement_unlocked(sid, ach.id, now_iso, girlfriend_id=girlfriend_id)

    seed = hashlib.md5(f"{girlfriend_id}:{ach.id}".encode()).hexdigest()[:10]
    image_url = f"https://picsum.photos/seed/{seed}/400/400"

    set_photo_for_intimacy_achievement(sid, ach.id, image_url, girlfriend_id=girlfriend_id)
    add_gallery_item(sid, {
        "id": f"intach-{ach.id}-{uuid.uuid4().hex[:6]}",
        "url": image_url,
        "created_at": now_iso,
        "caption": f"{ach.icon} {ach.title}",
        "source": "intimate_box_purchase",
        "achievement_id": ach.id,
    }, girlfriend_id=girlfriend_id)

    set_intimacy_last_award_time(sid, now_iso, girlfriend_id=girlfriend_id)

    logger.info("Intimate box purchase: %s -> %s (tier=%d, paid=%s)",
                body.box_id, ach.id, ach.tier, payment_status)

    # ── Apply an intimacy boost + chat cards so behavior adjusts ──────────
    try:
        from app.api.store import (
            get_trust_intimacy_state,
            set_trust_intimacy_state,
            get_relationship_state,
            set_relationship_state,
            append_message as store_append_message,
        )
        from app.services.trust_intimacy_service import (
            award_intimacy_gift,
            get_intimacy_cap_for_region,
        )
        from app.services.relationship_regions import get_region_for_level
        from app.services.relationship_descriptors import get_gain_micro_lines

        # Derive current region for caps
        rel_state = get_relationship_state(sid, girlfriend_id=girlfriend_id) or {}
        level = rel_state.get("level", 0) if isinstance(rel_state.get("level"), int) else 0
        region = rel_state.get("region_key") or get_region_for_level(level).key

        ti_state = get_trust_intimacy_state(sid, girlfriend_id=girlfriend_id)

        # Treat intimate box like a special gift contributing to intimacy bank
        purchase_key = f"intimate_box:{body.box_id}:{ach.id}"
        ti_state, int_res = award_intimacy_gift(ti_state, purchase_key, region_key=region)

        # Cap by region and persist
        cap = get_intimacy_cap_for_region(region)
        if int_res.visible_new > cap:
            int_res.visible_new = cap
        set_trust_intimacy_state(sid, ti_state, girlfriend_id=girlfriend_id)

        # Mirror updated trust/intimacy into relationship_state so other services see it
        rel_state["intimacy"] = ti_state.intimacy
        rel_state["trust"] = ti_state.trust
        set_relationship_state(sid, rel_state, girlfriend_id=girlfriend_id)

        # Relationship gain card so the user sees the effect
        if int_res.delta > 0 or int_res.released_delta > 0 or int_res.banked_delta > 0:
            micro = get_gain_micro_lines(0, ti_state.trust, int_res.delta, ti_state.intimacy)
            gain_msg = {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": "",
                "image_url": None,
                "event_type": "relationship_gain",
                "event_key": "intimate_box",
                "created_at": now_iso,
                "gain_data": {
                    "trust_delta": 0,
                    "trust_new": ti_state.trust,
                    "intimacy_delta": int_res.delta,
                    "intimacy_new": ti_state.intimacy,
                    "reason": "intimate_box",
                    "trust_banked_delta": 0,
                    "trust_released_delta": 0,
                    "trust_visible_new": ti_state.trust_visible,
                    "trust_bank_new": ti_state.trust_bank,
                    "trust_cap": 100,
                    "intimacy_banked_delta": int_res.banked_delta,
                    "intimacy_released_delta": int_res.released_delta,
                    "intimacy_visible_new": int_res.visible_new,
                    "intimacy_bank_new": int_res.bank_new,
                    "intimacy_cap": cap,
                    **micro,
                },
            }
            store_append_message(sid, gain_msg, girlfriend_id=girlfriend_id)

        # Intimacy achievement card in chat history
        ach_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": f"{ach.icon or '🔥'} **{ach.title}** unlocked — {ach.subtitle}",
            "image_url": image_url,
            "event_type": "intimacy_achievement",
            "event_key": ach.id,
            "created_at": now_iso,
            "achievement": {
                "id": ach.id,
                "title": ach.title,
                "subtitle": ach.subtitle,
                "rarity": ach.rarity.value,
                "tier": ach.tier,
                "icon": ach.icon,
            },
        }
        store_append_message(sid, ach_msg, girlfriend_id=girlfriend_id)
    except Exception as exc:
        logger.warning("Intimate box side-effects failed (non-blocking): %s", exc)

    return {
        "status": payment_status,
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
