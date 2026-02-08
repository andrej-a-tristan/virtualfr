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
    create_checkout_session,
    apply_relationship_boost,
    produce_gift_reaction_message,
    build_memory_summary,
)

router = APIRouter(prefix="/gifts", tags=["gifts"])
logger = logging.getLogger(__name__)

SESSION_COOKIE = "session"

# ── In-memory fallback for gift purchases ─────────────────────────────────────
# session_id -> list of purchase dicts
_gift_purchases: dict[str, list[dict]] = {}
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


def _get_purchases(sid: str) -> list[dict]:
    return _gift_purchases.get(sid, [])


def _add_purchase(sid: str, purchase: dict) -> None:
    if sid not in _gift_purchases:
        _gift_purchases[sid] = []
    _gift_purchases[sid].append(purchase)


def _update_purchase_status(stripe_session_id: str, status: str) -> dict | None:
    """Find and update purchase by stripe session id. Returns purchase dict or None."""
    for sid, purchases in _gift_purchases.items():
        for p in purchases:
            if p.get("stripe_session_id") == stripe_session_id:
                p["status"] = status
                return {**p, "_session_id": sid}
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
    """Create Stripe Checkout Session for a gift purchase."""
    _init_stripe()
    sid, user = _require_user(request)

    body = await request.json()
    gift_id = body.get("gift_id")
    if not gift_id:
        raise HTTPException(status_code=400, detail="gift_id required")

    gift = get_gift_by_id(gift_id)
    if not gift:
        raise HTTPException(status_code=404, detail=f"Gift '{gift_id}' not found")

    # Cooldown check
    purchases = _get_purchases(sid)
    cooldown_err = validate_cooldown(purchases, gift)
    if cooldown_err:
        raise HTTPException(status_code=400, detail=cooldown_err)

    user_id = user.get("id", "")
    girlfriend_id = user.get("current_girlfriend_id", "")

    # Create Stripe session
    result = create_checkout_session(gift, user_id, girlfriend_id, sid)

    # Record pending purchase
    purchase = {
        "id": str(uuid4()),
        "gift_id": gift.id,
        "gift_name": gift.name,
        "amount_eur": gift.price_eur,
        "currency": "eur",
        "stripe_session_id": result["session_id"],
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "emoji": gift.emoji,
    }
    _add_purchase(sid, purchase)

    return {"checkout_url": result["checkout_url"], "session_id": result["session_id"]}


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
    """Apply all gift side effects: relationship boost, memory, chat message, image triggers."""
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

    # 2. Gift reaction chat message
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

    # 4. Image album triggers (if gift has album)
    if gift.image_reward.album_size > 0:
        logger.info(
            "Gift %s triggers %d image(s) for gallery",
            gift.id, gift.image_reward.album_size,
        )
        # Images go to gallery — we'll add placeholder gallery items
        # In production this would trigger actual image generation jobs
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

    # 5. Patron badge for queen_treatment
    if gift.id == "queen_treatment_patron":
        user = get_session_user(session_id)
        if user:
            set_session_user(session_id, {**user, "patron_badge": True})

    logger.info("Gift %s delivered to session %s", gift.id, session_id)


# ── GET /api/gifts/history ───────────────────────────────────────────────────

@router.get("/history")
def gift_history(request: Request):
    """Return gift purchase history for current user."""
    sid, user = _require_user(request)
    purchases = _get_purchases(sid)
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
