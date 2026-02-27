"""Gift routes: catalog, checkout, webhook, history."""
import logging
from datetime import datetime, timezone
from uuid import uuid4, UUID

import stripe
from fastapi import APIRouter, Request, HTTPException

from app.core.config import get_settings
from app.api.store import (
    get_session_user,
    set_session_user,
    get_relationship_state,
    set_relationship_state,
    append_message,
    get_girlfriend,
)
from app.api import supabase_store as sb_store
from app.core.supabase_client import get_supabase_admin
from app.services.gifting import (
    get_gift_catalog,
    get_gift_by_id,
    validate_cooldown,
    apply_relationship_boost,
    produce_gift_reaction_message,
    build_memory_summary,
)
from app.services.stripe_payments import create_one_time_payment

router = APIRouter(prefix="/gifts", tags=["gifts"])
logger = logging.getLogger(__name__)

SESSION_COOKIE = "session"

# ── In-memory fallback for gift purchases (per girlfriend) ────────────────────
# (session_id, girlfriend_id) -> list of purchase dicts
_gift_purchases: dict[tuple[str, str], list[dict]] = {}
# stripe_session_id -> bool (idempotency guard)
_processed_sessions: set[str] = set()

# ── Persist gift purchases across server reloads ──────────────────────────────
import os as _os
import pickle as _pickle
import threading as _threading

_GIFTS_STORE_FILE = _os.path.join(_os.path.dirname(__file__), "..", "..", "..", "_gifts_cache.pkl")
_gifts_save_lock = _threading.Lock()


def _persist_gifts() -> None:
    """Save gift purchases to pickle file."""
    with _gifts_save_lock:
        try:
            tmp = _GIFTS_STORE_FILE + ".tmp"
            with open(tmp, "wb") as f:
                _pickle.dump({"purchases": _gift_purchases, "processed": _processed_sessions}, f)
            _os.replace(tmp, _GIFTS_STORE_FILE)
        except Exception:
            pass


def _load_gifts() -> None:
    """Load gift purchases from pickle file."""
    if not _os.path.exists(_GIFTS_STORE_FILE):
        return
    try:
        with open(_GIFTS_STORE_FILE, "rb") as f:
            data = _pickle.load(f)
        _gift_purchases.update(data.get("purchases", {}))
        _processed_sessions.update(data.get("processed", set()))
    except Exception:
        pass


_load_gifts()


def _uuid_or_none(v: str | None) -> UUID | None:
    if not v:
        return None
    try:
        return UUID(str(v))
    except (ValueError, TypeError):
        return None


def _db_ctx(user: dict | None) -> tuple[UUID, UUID] | None:
    if not get_supabase_admin() or not user:
        return None
    user_uuid = _uuid_or_none((user or {}).get("user_id") or (user or {}).get("id"))
    gf_uuid = _uuid_or_none((user or {}).get("current_girlfriend_id"))
    if user_uuid and gf_uuid:
        return user_uuid, gf_uuid
    return None


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


def _init_stripe() -> None:
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    stripe.api_key = settings.stripe_secret_key


def _purchase_key(sid: str, user: dict | None = None) -> tuple[str, str]:
    """Return (session_id, girlfriend_id) tuple for purchase storage."""
    gf_id = (user or {}).get("current_girlfriend_id", "")
    return (sid, gf_id)


def _get_purchases(sid: str, user: dict | None = None) -> list[dict]:
    ctx = _db_ctx(user)
    if ctx:
        try:
            return sb_store.list_gift_purchases(ctx[0], ctx[1])
        except Exception:
            pass
    key = _purchase_key(sid, user)
    return _gift_purchases.get(key, [])


def _add_purchase(sid: str, purchase: dict, user: dict | None = None) -> None:
    ctx = _db_ctx(user)
    if ctx:
        try:
            sb_store.create_gift_purchase(ctx[0], ctx[1], purchase)
            return
        except Exception:
            pass
    key = _purchase_key(sid, user)
    if key not in _gift_purchases:
        _gift_purchases[key] = []
    _gift_purchases[key].append(purchase)
    _persist_gifts()


def _update_purchase_status(stripe_session_id: str, status: str) -> dict | None:
    """Find and update purchase by stripe session id. Returns purchase dict or None."""
    if get_supabase_admin():
        try:
            row = sb_store.update_gift_purchase_status_by_payment_intent(stripe_session_id, status)
            if not row:
                row = sb_store.update_gift_purchase_status_by_session(stripe_session_id, status)
            if row:
                return row
        except Exception:
            pass
    for key, purchases in _gift_purchases.items():
        for p in purchases:
            if p.get("stripe_session_id") == stripe_session_id:
                p["status"] = status
                _persist_gifts()
                return {**p, "_session_id": key[0]}
    return None


# ── GET /api/gifts/list ──────────────────────────────────────────────────────

@router.get("/list")
def list_gifts(request: Request):
    """Return full gift catalog with age-gate context.

    Always returns the real spicy_photos count so the UI can show it
    (with a lock icon when locked). The `spicy_unlocked` flag tells the
    frontend whether the user can actually receive those photos.
    """
    catalog = get_gift_catalog()
    gifts_out = []

    # Determine age-gate status (sufficient to show spicy photo counts)
    sid = _session_id(request)
    user = get_session_user(sid) if sid else None
    age_gate_passed = bool((user or {}).get("age_gate_passed"))
    spicy_unlocked = age_gate_passed

    # Determine which gifts have already been purchased for this girlfriend
    purchases = _get_purchases(sid, user) if sid and user else []
    purchased_ids = {
        p["gift_id"] for p in purchases if p.get("status") == "paid"
    }

    for g in catalog:
        d = g.model_dump()
        # Always include the real spicy_photos count — frontend shows locked state
        d["spicy_unlocked"] = spicy_unlocked
        d["already_purchased"] = g.id in purchased_ids
        gifts_out.append(d)
    return {"gifts": gifts_out, "spicy_unlocked": spicy_unlocked}


# ── POST /api/gifts/checkout ─────────────────────────────────────────────────

@router.post("/checkout")
async def gift_checkout(request: Request):
    """Charge the user's saved card for a gift. No redirect — payment is inline.

    Returns:
      - status: "succeeded" | "requires_action" | "failed" | "no_card"
      - client_secret: (only if requires_action, for frontend 3DS handling)
      - error: (only if failed)
    """
    _init_stripe()
    sid, user = _require_user(request)

    body = await request.json()
    gift_id = body.get("gift_id")
    if not gift_id:
        raise HTTPException(status_code=400, detail="gift_id required")

    gift = get_gift_by_id(gift_id)
    if not gift:
        raise HTTPException(status_code=404, detail=f"Gift '{gift_id}' not found")

    # One-per-girl check: each gift can only be bought once per girlfriend
    purchases = _get_purchases(sid, user)
    already_bought = any(
        p.get("gift_id") == gift_id and p.get("status") == "paid"
        for p in purchases
    )
    if already_bought:
        raise HTTPException(
            status_code=400,
            detail=f"You already gave {gift.name} to her. Each gift can only be given once.",
        )

    # Cooldown check (per-girlfriend)
    cooldown_err = validate_cooldown(purchases, gift)
    if cooldown_err:
        raise HTTPException(status_code=400, detail=cooldown_err)

    user_id = user.get("id", "")
    girlfriend_id = user.get("current_girlfriend_id", "")
    amount_cents = int(round(gift.price_eur * 100))

    # Legacy endpoint now delegates to the unified payment helper.
    result = create_one_time_payment(
        sid=sid,
        user=user,
        amount_cents=amount_cents,
        currency="eur",
        description=f"Gift: {gift.name}",
        metadata={
            "type": "gift",
            "gift_id": gift.id,
            "user_id": user_id,
            "girlfriend_id": girlfriend_id,
            "session_id": sid,
        },
        idempotency_extra=f"legacy_gifts_checkout:{gift.id}:{girlfriend_id}",
    ).__dict__

    pi_id = result.get("payment_intent_id", "")

    # Record purchase
    purchase = {
        "id": str(uuid4()),
        "gift_id": gift.id,
        "gift_name": gift.name,
        "amount_eur": gift.price_eur,
        "currency": "eur",
        "stripe_session_id": pi_id,
        "status": "paid" if result["status"] == "succeeded" else "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "emoji": gift.emoji,
    }
    _add_purchase(sid, purchase, user)

    # If payment succeeded immediately, deliver the gift now
    if result["status"] == "succeeded":
        _deliver_gift(sid, gift, purchase)
        return {"status": "succeeded"}

    # If 3DS is required, return client_secret for frontend to handle
    if result["status"] == "requires_action":
        return {
            "status": "requires_action",
            "client_secret": result.get("client_secret", ""),
            "payment_intent_id": pi_id,
        }

    # Failed
    return {"status": "failed", "error": result.get("error", "Payment failed")}


# ── POST /api/gifts/confirm-payment ──────────────────────────────────────────

@router.post("/confirm-payment")
async def confirm_gift_payment(request: Request):
    """Called by frontend after 3DS completes. Checks PaymentIntent status and delivers gift."""
    _init_stripe()
    sid, user = _require_user(request)

    body = await request.json()
    payment_intent_id = body.get("payment_intent_id")
    if not payment_intent_id:
        raise HTTPException(status_code=400, detail="payment_intent_id required")

    pi = stripe.PaymentIntent.retrieve(payment_intent_id)

    if pi.status != "succeeded":
        return {"status": "failed", "error": f"Payment not completed (status: {pi.status})"}

    # Extract gift_id from metadata
    gift_id = pi.metadata.get("gift_id", "")
    gift = get_gift_by_id(gift_id)
    if not gift:
        return {"status": "failed", "error": "Gift not found"}

    # Idempotency: check if already processed
    if payment_intent_id in _processed_sessions:
        return {"status": "succeeded"}
    _processed_sessions.add(payment_intent_id)

    # Update purchase status
    _update_purchase_status(payment_intent_id, "paid")

    # Deliver
    _deliver_gift(sid, gift, None)

    return {"status": "succeeded"}


# ── POST /api/gifts/webhook ──────────────────────────────────────────────────

@router.post("/webhook")
async def gift_webhook(request: Request):
    """Handle Stripe webhook for gift payments."""
    _init_stripe()
    settings = get_settings()

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception as exc:
        if "SignatureVerification" in type(exc).__name__:
            raise HTTPException(status_code=400, detail="Invalid signature")
        raise

    event_type = event["type"]
    logger.info("Gift webhook event: %s", event_type)

    if event_type == "payment_intent.succeeded":
        pi = event["data"]["object"]
        pi_id = pi.get("id", "")
        metadata = pi.get("metadata", {})
        payment_type = metadata.get("type", "")
        if payment_type in ("gift", "mystery_box", "leaks_spin", "leak_slot"):
            try:
                from app.api.routes.payments import finalize_payment_intent_for_webhook
                result = finalize_payment_intent_for_webhook(pi_id)
                logger.info("Gift webhook PI.succeeded finalized: type=%s pi=%s status=%s",
                            payment_type, pi_id, result.get("status"))
            except Exception as e:
                logger.warning("Gift webhook PI finalization failed: %s", e)
        return {"ok": True}

    if event_type == "checkout.session.completed":
        session_obj = event["data"]["object"]
        stripe_session_id = session_obj.get("id", "")
        metadata = session_obj.get("metadata", {})
        gift_id = metadata.get("gift_id", "")
        app_session_id = metadata.get("session_id", "")

        # Idempotency
        if stripe_session_id in _processed_sessions:
            logger.info("Gift session %s already processed, skipping", stripe_session_id)
            return {"ok": True}
        _processed_sessions.add(stripe_session_id)

        # Update purchase status
        purchase = _update_purchase_status(stripe_session_id, "paid")

        gift = get_gift_by_id(gift_id)
        if not gift:
            logger.warning("Gift %s not found in catalog", gift_id)
            return {"ok": True}

        # Apply side effects
        _deliver_gift(app_session_id, gift, purchase)

    return {"ok": True}


def _deliver_gift(session_id: str, gift, purchase: dict | None):
    """Apply all gift side effects: relationship boost, memory, chat message, image triggers, unique effects, trust/intimacy."""
    from app.services.gifting import apply_relationship_boost, produce_gift_reaction_message, build_memory_summary
    from app.services.relationship_state import check_for_milestone_event, append_milestone_reached
    from app.api.store import get_intimacy_state, set_intimacy_state
    from app.api.store import get_trust_intimacy_state, set_trust_intimacy_state
    from app.services.intimacy_service import award_gift_purchase
    from app.services.trust_intimacy_service import (
        award_intimacy_gift,
        award_trust_gift,
        get_trust_cap_for_region,
        get_intimacy_cap_for_region,
    )
    from app.services.relationship_descriptors import get_gain_micro_lines
    from app.services.relationship_regions import get_region_for_level

    purchase_id = (purchase or {}).get("id", gift.id)

    # Gift photos are ALWAYS delivered — no plan/intimacy/age-gate restriction.
    # The user paid for the gift, they get all the photos.
    normal_count = gift.image_reward.normal_photos
    spicy_count = gift.image_reward.spicy_photos

    # Determine current region_key for cap calculations
    _rel_state = get_relationship_state(session_id) or {}
    _level = _rel_state.get("level", 0) if isinstance(_rel_state.get("level"), int) else 0
    _region_key = _rel_state.get("region_key") or get_region_for_level(_level).key

    # 0a. Legacy Intimacy boost
    try:
        int_state = get_intimacy_state(session_id)
        int_state, int_result = award_gift_purchase(int_state, gift.id)
        set_intimacy_state(session_id, int_state)
        logger.info("Intimacy gift award (legacy): %s delta=%d", int_result.reason, int_result.delta)
    except Exception as e:
        logger.warning("Intimacy gift award (legacy) failed: %s", e)

    # 0b. Unified Trust + Intimacy boost (bank-first)
    trust_delta = 0
    intimacy_delta = 0
    try:
        ti_state = get_trust_intimacy_state(session_id)

        # Intimacy from gift (constant boost) — goes to bank first
        ti_state, int_res = award_intimacy_gift(ti_state, purchase_id, region_key=_region_key)
        intimacy_delta = int_res.delta

        # Trust from gift (tier-based boost) — goes to bank first
        ti_state, trust_res = award_trust_gift(ti_state, purchase_id, gift.tier, region_key=_region_key)
        trust_delta = trust_res.delta

        set_trust_intimacy_state(session_id, ti_state)
        logger.info(
            "Gift trust/intimacy award: trust +%d (banked %d, released %d), intimacy +%d (banked %d, released %d)",
            trust_delta, trust_res.banked_delta, trust_res.released_delta,
            intimacy_delta, int_res.banked_delta, int_res.released_delta,
        )

        # Emit relationship_gain message in chat (visible feedback)
        if trust_delta > 0 or intimacy_delta > 0:
            micro = get_gain_micro_lines(trust_delta, ti_state.trust, intimacy_delta, ti_state.intimacy)

            # Build a tease line when bank increased but cap prevented release
            tease_line = ""
            trust_banked_only = trust_res.banked_delta > 0 and trust_res.released_delta == 0
            intimacy_banked_only = int_res.banked_delta > 0 and int_res.released_delta == 0
            if trust_banked_only or intimacy_banked_only:
                tease_line = "You're building something real — it'll unlock as your relationship grows."

            gain_msg = {
                "id": f"gain-{uuid4()}",
                "role": "assistant",
                "content": "",
                "image_url": None,
                "event_type": "relationship_gain",
                "event_key": "gift",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "gain_data": {
                    "trust_delta": trust_delta,
                    "trust_new": ti_state.trust,
                    "intimacy_delta": intimacy_delta,
                    "intimacy_new": ti_state.intimacy,
                    "reason": "gift",
                    # Bank/release breakdown
                    "trust_banked_delta": trust_res.banked_delta,
                    "trust_released_delta": trust_res.released_delta,
                    "trust_visible_new": trust_res.visible_new,
                    "trust_bank_new": trust_res.bank_new,
                    "trust_cap": trust_res.cap,
                    "intimacy_banked_delta": int_res.banked_delta,
                    "intimacy_released_delta": int_res.released_delta,
                    "intimacy_visible_new": int_res.visible_new,
                    "intimacy_bank_new": int_res.bank_new,
                    "intimacy_cap": int_res.cap,
                    "tease_line": tease_line,
                    **micro,
                },
            }
            append_message(session_id, gain_msg)
    except Exception as e:
        logger.warning("Unified trust/intimacy gift award failed: %s", e)

    # 1. Relationship boost
    state = get_relationship_state(session_id)
    if state:
        prev_state = dict(state)
        state = apply_relationship_boost(state, gift.relationship_boost)
        set_relationship_state(session_id, state)

        # Check for milestone
        milestone = check_for_milestone_event(prev_state, state)
        if milestone:
            region_key, msg = milestone
            state = append_milestone_reached(state, region_key)
            set_relationship_state(session_id, state)
            # Add milestone message
            append_message(session_id, {
                "id": f"milestone-{uuid4()}",
                "role": "assistant",
                "content": msg,
                "image_url": None,
                "event_type": "milestone",
                "event_key": region_key,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

    # 2. Gift reaction chat message (includes unique effect flavor)
    reaction = produce_gift_reaction_message(gift)
    gift_msg = {
        "id": f"gift-{uuid4()}",
        "role": "assistant",
        "content": reaction,
        "image_url": None,
        "event_type": "gift_received",
        "event_key": gift.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "gift_data": {
            "gift_id": gift.id,
            "gift_name": gift.name,
            "emoji": gift.emoji,
            "tier": gift.tier,
            "trust_gained": trust_delta if trust_delta else gift.relationship_boost.trust,
            "intimacy_gained": intimacy_delta if intimacy_delta else gift.relationship_boost.intimacy,
            "unique_effect_name": gift.unique_effect_name,
            "unique_effect_description": gift.unique_effect_description,
            "normal_photos": normal_count,
            "spicy_photos": spicy_count,
        },
    }
    append_message(session_id, gift_msg)

    # 3. Memory item
    memory_text = build_memory_summary(gift)
    append_message(session_id, {
        "id": f"memory-gift-{uuid4()}",
        "role": "system",
        "content": memory_text,
        "image_url": None,
        "event_type": "gift_memory",
        "event_key": gift.memory_tag,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # 4. Apply unique effects to relationship state / user session
    _apply_unique_effect(session_id, gift)

    # 4b. Achievement trigger: first_gift_in_region (new engine)
    try:
        from app.services.achievement_engine import (
            get_current_region_index_for_girl,
            mark_gift_confirmed,
            try_unlock_for_triggers,
            TriggerType,
        )
        from app.api.store import get_achievement_progress, set_achievement_progress
        _cur_state = get_relationship_state(session_id) or {}
        _cur_region_idx = get_current_region_index_for_girl(_cur_state.get("level", 0))
        _ach_progress = get_achievement_progress(session_id)
        _gift_triggers = mark_gift_confirmed(_ach_progress)
        _cur_state, _ach_events = try_unlock_for_triggers(
            _cur_state, _ach_progress, _gift_triggers, context=None,
        )
        set_achievement_progress(session_id, _ach_progress)
        if _ach_events:
            set_relationship_state(session_id, _cur_state)
            for _ach_evt in _ach_events:
                append_message(session_id, {
                    "id": f"ach-{uuid4()}",
                    "role": "assistant",
                    "content": f"Achievement unlocked: {_ach_evt['title']}",
                    "image_url": None,
                    "event_type": "relationship_achievement",
                    "event_key": _ach_evt["id"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "achievement": _ach_evt,
                })
                logger.info("Achievement unlocked from gift: %s", _ach_evt["id"])
    except Exception as e:
        logger.warning("Gift achievement trigger failed: %s", e)

    # 5. Image album triggers — always deliver ALL photos the user paid for
    total_photos = normal_count + spicy_count
    photo_prompts = gift.image_reward.photo_prompts or []
    spicy_prompts = gift.image_reward.spicy_photo_prompts or []

    if total_photos > 0:
        logger.info(
            "Gift %s triggers %d normal + %d spicy image(s) for gallery",
            gift.id, normal_count, spicy_count,
        )
        # Normal photos — each with a unique prompt
        for i in range(normal_count):
            prompt = photo_prompts[i] if i < len(photo_prompts) else gift.image_reward.prompt_template
            append_message(session_id, {
                "id": f"gift-img-{uuid4()}",
                "role": "system",
                "content": f"[Photo {i + 1}/{total_photos} from {gift.name} — generating...]",
                "image_url": None,
                "event_type": "gift_album",
                "event_key": gift.id,
                "photo_type": "normal",
                "photo_prompt": prompt,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        # Spicy photos — each with a unique prompt
        for i in range(spicy_count):
            prompt = spicy_prompts[i] if i < len(spicy_prompts) else gift.image_reward.spicy_prompt_template
            append_message(session_id, {
                "id": f"gift-img-spicy-{uuid4()}",
                "role": "system",
                "content": f"[Spicy photo {normal_count + i + 1}/{total_photos} from {gift.name} — generating...]",
                "image_url": None,
                "event_type": "gift_album",
                "event_key": gift.id,
                "photo_type": "spicy",
                "photo_prompt": prompt,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

    logger.info("Gift %s delivered to session %s", gift.id, session_id)


def _apply_unique_effect(session_id: str, gift):
    """Apply gift-specific unique effects to session/relationship state."""
    user = get_session_user(session_id)
    state = get_relationship_state(session_id) or {}

    # Build effects dict on relationship state
    effects = state.get("active_effects", {})

    if gift.id == "queen_treatment_patron":
        # Patron badge
        if user:
            set_session_user(session_id, {**user, "patron_badge": True})
        effects["patron_status"] = True

    elif gift.id == "designer_handbag_moment":
        # Style badge
        effects["style_badge"] = True

    elif gift.id == "wine":
        # Slow-burn: next 10 messages romantic flag
        effects["slow_burn_remaining"] = 10

    elif gift.id == "coffee":
        # Morning ritual: queue good-morning seed
        effects["morning_ritual_pending"] = True

    elif gift.id == "spa_kit":
        # Gentle check-ins for 3 days
        effects["gentle_checkins_remaining"] = 3

    elif gift.id == "dress":
        # Outfit era for ~7 days
        effects["outfit_era_until"] = (
            datetime.now(timezone.utc) + __import__("datetime").timedelta(days=7)
        ).isoformat()

    elif gift.id == "stickers":
        # Inside joke emoji
        effects["inside_joke_emoji"] = True

    elif gift.id == "song_dedication":
        # Theme song in memory
        effects["theme_song"] = True

    elif gift.id == "candy":
        # Sweet tooth reveal
        effects["sweet_tooth_revealed"] = True

    elif gift.id == "love_note":
        # Pinned note
        effects["pinned_note"] = True

    elif gift.id == "plushie":
        # Comfort object
        effects["comfort_object"] = True

    elif gift.id == "movie_tickets":
        # Shared quote
        effects["shared_quote"] = True

    elif gift.id == "perfume":
        # Scent memory
        effects["scent_memory"] = True

    elif gift.id == "dinner":
        # Date milestone counter
        date_count = effects.get("date_milestone_count", 0) + 1
        effects["date_milestone_count"] = date_count

    elif gift.id == "photoshoot_basic":
        # Gallery album tag
        effects["gallery_album_mini"] = True

    elif gift.id == "surprise_date_night":
        # Surprise initiation on next app_open
        effects["surprise_initiation_pending"] = True

    elif gift.id == "luxury_bouquet_note":
        # Keepsake note
        effects["keepsake_note"] = True

    elif gift.id == "cozy_weekend_retreat":
        # Weekend vibe
        effects["weekend_vibe"] = True

    elif gift.id == "professional_photoshoot":
        # Signature pose
        effects["signature_pose"] = True

    elif gift.id == "signature_jewelry":
        # Signature piece milestone
        milestones = state.get("milestones_reached", [])
        if "signature_piece" not in milestones:
            state["milestones_reached"] = milestones + ["signature_piece"]
        effects["signature_piece"] = True

    elif gift.id == "wishlist_mystery_box":
        # Random rare perk
        import random
        rare_perks = [
            "bonus_intimacy_5",
            "bonus_trust_5",
            "double_next_gift_boost",
            "secret_backstory_reveal",
            "exclusive_pet_name",
        ]
        chosen = random.choice(rare_perks)
        effects["mystery_perk"] = chosen

    elif gift.id == "city_getaway":
        # Deferred second message on next app_open
        effects["deferred_message_pending"] = True

    elif gift.id == "private_rooftop_dinner":
        # Anniversary marker
        effects["anniversary_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    elif gift.id == "dream_vacation":
        # Episode arc: 3 postcards over next 3 app_open events
        effects["vacation_postcards_remaining"] = 3

    # Persist effects
    state["active_effects"] = effects
    set_relationship_state(session_id, state)


# ── GET /api/gifts/history ───────────────────────────────────────────────────

@router.get("/history")
def gift_history(request: Request):
    """Return gift purchase history for current user + current girlfriend."""
    sid, user = _require_user(request)
    purchases = _get_purchases(sid, user)
    # Only return paid + pending
    items = [
        {
            "id": p["id"],
            "gift_id": p["gift_id"],
            "gift_name": p["gift_name"],
            "amount_eur": p["amount_eur"],
            "status": p["status"],
            "created_at": p["created_at"],
            "emoji": p.get("emoji", "🎁"),
        }
        for p in purchases
        if p.get("status") in ("paid", "pending")
    ]
    return {"purchases": items}


# ── GET /api/gifts/collection ─────────────────────────────────────────────────

@router.get("/collection")
def gift_collection(request: Request):
    """Return the full gift catalog with purchase status for the current girlfriend.

    Each gift includes:
      - Full catalog data (name, emoji, tier, image_reward, etc.)
      - purchased: bool  (whether this gift has been bought for this girl)
      - purchased_at: str | null  (ISO timestamp of purchase)
    """
    sid, user = _require_user(request)
    catalog = get_gift_catalog()
    purchases = _get_purchases(sid, user)

    # Build a lookup: gift_id -> earliest paid purchase
    paid_map: dict[str, dict] = {}
    for p in purchases:
        if p.get("status") == "paid" and p["gift_id"] not in paid_map:
            paid_map[p["gift_id"]] = p

    collection = []
    for g in catalog:
        d = g.model_dump()
        purchase = paid_map.get(g.id)
        d["purchased"] = purchase is not None
        d["purchased_at"] = purchase["created_at"] if purchase else None
        collection.append(d)

    total = len(catalog)
    owned = len(paid_map)

    return {"collection": collection, "total": total, "owned": owned}


# ═══════════════════════════════════════════════════════════════════════════════
# MYSTERY BOX SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

import random

# Mystery box definitions with tier probabilities (must sum to 1.0)
# Pricing is set so expected value > box price — feels like a deal.
#
# Price Math:
#   Everyday avg ≈ €4.50 | Dates avg ≈ €22.14 | Luxury avg ≈ €103.57 | Legendary avg ≈ €184.75
#
#   Bronze: 0.65×4.50 + 0.25×22.14 + 0.08×103.57 + 0.02×184.75 = €2.93+5.54+8.29+3.70 = €20.45 EV → price €5.99
#   Gold:   0.50×22.14 + 0.35×103.57 + 0.15×184.75 = €11.07+36.25+27.71 = €75.03 EV → price €19.99
#   Diamond: 0.55×103.57 + 0.45×184.75 = €56.96+83.14 = €140.10 EV → price €49.99

MYSTERY_BOXES = {
    "bronze": {
        "id": "bronze",
        "name": "Sweet Whisper",
        "price_eur": 5.99,
        "emoji": "🌸",
        "description": "A gentle surprise — a little something to make her smile.",
        "tier_weights": {"everyday": 0.65, "dates": 0.25, "luxury": 0.08, "legendary": 0.02},
        "color": "#cd7f32",
    },
    "gold": {
        "id": "gold",
        "name": "Passionate Heart",
        "price_eur": 19.99,
        "emoji": "💝",
        "description": "Skip the small talk — sweep her off her feet with something special.",
        "tier_weights": {"everyday": 0.0, "dates": 0.50, "luxury": 0.35, "legendary": 0.15},
        "color": "#ffd700",
    },
    "diamond": {
        "id": "diamond",
        "name": "Eternal Flame",
        "price_eur": 49.99,
        "emoji": "💎",
        "description": "Only the finest. A grand gesture she'll never forget.",
        "tier_weights": {"everyday": 0.0, "dates": 0.0, "luxury": 0.55, "legendary": 0.45},
        "color": "#b9f2ff",
    },
}


def _pick_mystery_gift(box_id: str, owned_ids: set[str]) -> dict | None:
    """Pick a random unowned gift based on mystery box probabilities.
    Returns the gift object or None if all eligible gifts are owned."""
    box = MYSTERY_BOXES.get(box_id)
    if not box:
        return None

    catalog = get_gift_catalog()
    tier_weights = box["tier_weights"]

    # Build pool of unowned gifts grouped by tier
    tier_pools: dict[str, list] = {}
    for g in catalog:
        if g.id not in owned_ids:
            tier_pools.setdefault(g.tier, []).append(g)

    # Build weighted list: (gift, weight)
    weighted = []
    for tier, weight in tier_weights.items():
        pool = tier_pools.get(tier, [])
        if pool and weight > 0:
            per_gift_weight = weight / len(pool)
            for g in pool:
                weighted.append((g, per_gift_weight))

    if not weighted:
        return None

    gifts, weights = zip(*weighted)
    chosen = random.choices(gifts, weights=weights, k=1)[0]
    return chosen


@router.get("/mystery-boxes")
def list_mystery_boxes(request: Request):
    """Return available mystery boxes with their odds and prices."""
    sid = _session_id(request)
    user = get_session_user(sid) if sid else None
    purchases = _get_purchases(sid, user) if sid and user else []
    owned_ids = {p["gift_id"] for p in purchases if p.get("status") == "paid"}

    catalog = get_gift_catalog()
    total_gifts = len(catalog)
    owned_count = len(owned_ids)
    unowned_count = total_gifts - owned_count

    # Count unowned per tier
    unowned_by_tier: dict[str, int] = {}
    for g in catalog:
        if g.id not in owned_ids:
            unowned_by_tier[g.tier] = unowned_by_tier.get(g.tier, 0) + 1

    boxes = []
    for box in MYSTERY_BOXES.values():
        # Calculate effective probabilities (excluding owned gifts)
        effective_weights: dict[str, float] = {}
        total_weight = 0.0
        for tier, w in box["tier_weights"].items():
            if unowned_by_tier.get(tier, 0) > 0 and w > 0:
                effective_weights[tier] = w
                total_weight += w

        # Normalize to 1.0
        if total_weight > 0:
            effective_weights = {t: w / total_weight for t, w in effective_weights.items()}

        # Check if any gifts available for this box
        has_eligible = total_weight > 0

        boxes.append({
            **box,
            "effective_odds": effective_weights,
            "has_eligible_gifts": has_eligible,
            "unowned_by_tier": {t: unowned_by_tier.get(t, 0) for t in box["tier_weights"]},
        })

    return {
        "boxes": boxes,
        "total_gifts": total_gifts,
        "owned_gifts": owned_count,
        "unowned_gifts": unowned_count,
    }


@router.post("/mystery-box/open")
async def open_mystery_box(request: Request):
    """Purchase and open a mystery box using the user's saved card.

    Charges via Stripe PaymentIntent (no redirects). Returns error if no card.
    Body: { "box_id": "bronze" | "gold" | "diamond" }
    """
    _init_stripe()
    sid, user = _require_user(request)

    body = await request.json()
    box_id = body.get("box_id")
    if not box_id or box_id not in MYSTERY_BOXES:
        raise HTTPException(status_code=400, detail="Invalid box_id")

    box = MYSTERY_BOXES[box_id]

    # Get owned gifts
    purchases = _get_purchases(sid, user)
    owned_ids = {p["gift_id"] for p in purchases if p.get("status") == "paid"}

    # Pick random gift
    gift = _pick_mystery_gift(box_id, owned_ids)
    if not gift:
        raise HTTPException(
            status_code=400,
            detail="No eligible gifts remaining for this box. You already own them all!",
        )

    if gift.id in owned_ids:
        raise HTTPException(status_code=400, detail="Selected gift already owned — try again.")

    user_id = user.get("id", "")
    girlfriend_id = user.get("current_girlfriend_id", "")

    # ── Ensure Stripe customer exists ─────────────────────────────────────
    stripe_customer_id = user.get("stripe_customer_id")
    if not stripe_customer_id:
        try:
            customer = stripe.Customer.create(
                email=user.get("email", ""),
                metadata={"user_id": user_id},
            )
            stripe_customer_id = customer.id
            set_session_user(sid, {**user, "stripe_customer_id": stripe_customer_id})
            user = get_session_user(sid) or user
            logger.info("Created Stripe customer %s for mystery box", stripe_customer_id)
        except Exception as e:
            logger.warning("Failed to create Stripe customer for mystery box: %s", e)
            raise HTTPException(status_code=400, detail="Failed to create payment customer")

    # ── Get default payment method ────────────────────────────────────────
    default_pm = user.get("default_payment_method_id")
    if not default_pm:
        try:
            pms = stripe.Customer.list_payment_methods(stripe_customer_id, type="card", limit=1)
            if pms.data:
                default_pm = pms.data[0].id
                set_session_user(sid, {**user, "default_payment_method_id": default_pm})
        except Exception:
            pass

    if not default_pm:
        return {"status": "no_card", "error": "No card on file. Please add a card first."}

    # ── Charge the saved card ─────────────────────────────────────────────
    amount_cents = int(round(box["price_eur"] * 100))
    try:
        pi = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="eur",
            customer=stripe_customer_id,
            payment_method=default_pm,
            off_session=True,
            confirm=True,
            metadata={
                "type": "mystery_box",
                "box_id": box_id,
                "gift_id": gift.id,
                "user_id": user_id,
                "girlfriend_id": girlfriend_id,
                "session_id": sid,
            },
        )
    except stripe.error.CardError as e:
        return {"status": "failed", "error": str(e.user_message or e)}
    except Exception as e:
        logger.error("Stripe PaymentIntent failed for mystery box: %s", e)
        return {"status": "failed", "error": "Payment failed. Please try again."}

    pi_id = pi.id

    if pi.status == "requires_action":
        # 3DS needed — return client_secret for frontend to handle
        return {
            "status": "requires_action",
            "client_secret": pi.client_secret,
            "payment_intent_id": pi.id,
            "gift": {
                "id": gift.id,
                "name": gift.name,
                "emoji": gift.emoji,
                "tier": gift.tier,
                "price_eur": gift.price_eur,
                "description": gift.description,
                "normal_photos": gift.image_reward.normal_photos,
                "spicy_photos": gift.image_reward.spicy_photos,
            },
            "box": {
                "id": box_id,
                "name": box["name"],
                "price_eur": box["price_eur"],
            },
        }

    if pi.status != "succeeded":
        return {"status": "failed", "error": f"Payment not completed: {pi.status}"}

    # ── Payment succeeded — record purchase & deliver ─────────────────────
    purchase = {
        "id": str(uuid4()),
        "gift_id": gift.id,
        "gift_name": gift.name,
        "amount_eur": box["price_eur"],
        "currency": "eur",
        "stripe_session_id": pi_id,
        "status": "paid",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "emoji": gift.emoji,
        "source": "mystery_box",
        "box_id": box_id,
    }
    _add_purchase(sid, purchase, user)
    _deliver_gift(sid, gift, purchase)

    return {
        "status": "succeeded",
        "gift": {
            "id": gift.id,
            "name": gift.name,
            "emoji": gift.emoji,
            "tier": gift.tier,
            "price_eur": gift.price_eur,
            "description": gift.description,
            "normal_photos": gift.image_reward.normal_photos,
            "spicy_photos": gift.image_reward.spicy_photos,
        },
        "box": {
            "id": box_id,
            "name": box["name"],
            "price_eur": box["price_eur"],
        },
    }
