"""Gift routes: catalog, checkout, webhook, history."""
import logging
from datetime import datetime, timezone
from uuid import uuid4

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
from app.services.gifting import (
    get_gift_catalog,
    get_gift_by_id,
    validate_cooldown,
    charge_saved_card,
    apply_relationship_boost,
    produce_gift_reaction_message,
    build_memory_summary,
)

router = APIRouter(prefix="/gifts", tags=["gifts"])
logger = logging.getLogger(__name__)

SESSION_COOKIE = "session"

# ── In-memory fallback for gift purchases (per girlfriend) ────────────────────
# (session_id, girlfriend_id) -> list of purchase dicts
_gift_purchases: dict[tuple[str, str], list[dict]] = {}
# stripe_session_id -> bool (idempotency guard)
_processed_sessions: set[str] = set()


def _session_id(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE)


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
    key = _purchase_key(sid, user)
    return _gift_purchases.get(key, [])


def _add_purchase(sid: str, purchase: dict, user: dict | None = None) -> None:
    key = _purchase_key(sid, user)
    if key not in _gift_purchases:
        _gift_purchases[key] = []
    _gift_purchases[key].append(purchase)


def _update_purchase_status(stripe_session_id: str, status: str) -> dict | None:
    """Find and update purchase by stripe session id. Returns purchase dict or None."""
    for key, purchases in _gift_purchases.items():
        for p in purchases:
            if p.get("stripe_session_id") == stripe_session_id:
                p["status"] = status
                return {**p, "_session_id": key[0]}
    return None


# ── GET /api/gifts/list ──────────────────────────────────────────────────────

@router.get("/list")
def list_gifts():
    """Return full gift catalog."""
    catalog = get_gift_catalog()
    return {"gifts": [g.model_dump() for g in catalog]}


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

    # Cooldown check (per-girlfriend)
    purchases = _get_purchases(sid, user)
    cooldown_err = validate_cooldown(purchases, gift)
    if cooldown_err:
        raise HTTPException(status_code=400, detail=cooldown_err)

    user_id = user.get("id", "")
    girlfriend_id = user.get("current_girlfriend_id", "")

    # Ensure Stripe customer exists
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
            logger.info("Created Stripe customer %s for gift checkout", stripe_customer_id)
        except Exception as e:
            logger.warning("Failed to create Stripe customer for gifts: %s", e)
            raise HTTPException(status_code=400, detail="Failed to create payment customer")

    # Get default payment method
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

    # Charge the saved card
    result = charge_saved_card(
        gift=gift,
        stripe_customer_id=stripe_customer_id,
        default_payment_method_id=default_pm,
        metadata={
            "gift_id": gift.id,
            "user_id": user_id,
            "girlfriend_id": girlfriend_id,
            "session_id": sid,
        },
    )

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
    """Apply all gift side effects: relationship boost, memory, chat message, image triggers, unique effects."""
    from app.services.gifting import apply_relationship_boost, produce_gift_reaction_message, build_memory_summary
    from app.services.relationship_state import calculate_relationship_level, check_for_milestone_event, append_milestone_reached

    # 1. Relationship boost
    state = get_relationship_state(session_id)
    if state:
        prev_state = dict(state)
        state = apply_relationship_boost(state, gift.relationship_boost)
        set_relationship_state(session_id, state)

        # Check for milestone
        milestone = check_for_milestone_event(prev_state, state)
        if milestone:
            level, msg = milestone
            state = append_milestone_reached(state, level)
            set_relationship_state(session_id, state)
            # Add milestone message
            append_message(session_id, {
                "id": f"milestone-{uuid4()}",
                "role": "assistant",
                "content": msg,
                "image_url": None,
                "event_type": "milestone",
                "event_key": level,
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
            "trust_gained": gift.relationship_boost.trust,
            "intimacy_gained": gift.relationship_boost.intimacy,
            "unique_effect_name": gift.unique_effect_name,
            "unique_effect_description": gift.unique_effect_description,
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

    # 5. Image album triggers (if gift has album)
    if gift.image_reward.album_size > 0:
        logger.info(
            "Gift %s triggers %d image(s) for gallery",
            gift.id, gift.image_reward.album_size,
        )
        for i in range(gift.image_reward.album_size):
            append_message(session_id, {
                "id": f"gift-img-{uuid4()}",
                "role": "system",
                "content": f"[Album photo {i + 1}/{gift.image_reward.album_size} from {gift.name} — generating...]",
                "image_url": None,
                "event_type": "gift_album",
                "event_key": gift.id,
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
