"""Unified payment endpoint.

POST /api/payments/intent — single entry-point for every paid action.
POST /api/payments/confirm — finalise business logic after frontend 3DS confirm.
"""
import logging
from datetime import datetime, timezone
from uuid import uuid4

import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.api.store import (
    get_session_user,
    is_payment_fulfilled,
    mark_payment_fulfilled,
)
from app.services.stripe_payments import (
    init_stripe,
    create_one_time_payment,
    create_or_update_subscription,
    create_setup_intent as svc_create_setup,
    verify_payment_intent,
    get_saved_card_info,
    PaymentResult,
    PLAN_MONTHLY_CENTS,
)

router = APIRouter(prefix="/payments", tags=["payments"])
logger = logging.getLogger(__name__)

SESSION_COOKIE = "session"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def finalize_payment_intent_for_webhook(payment_intent_id: str) -> dict:
    """Idempotently fulfill business logic for a succeeded PaymentIntent.

    This is used by webhook handlers to guarantee eventual consistency.
    """
    if is_payment_fulfilled(payment_intent_id):
        return {"status": "succeeded", "already_fulfilled": True}

    if not init_stripe():
        # In dev mode (no Stripe), webhook fulfillment isn't needed.
        return {"status": "succeeded", "dev_mode": True}

    try:
        pi = stripe.PaymentIntent.retrieve(payment_intent_id)
    except Exception as e:
        logger.warning("Webhook finalization: failed to retrieve PI %s: %s", payment_intent_id, e)
        return {"status": "failed", "error": "payment_intent_not_found"}

    if pi.status != "succeeded":
        return {"status": "failed", "error": f"payment_not_succeeded:{pi.status}"}

    meta = pi.metadata or {}
    payment_type = meta.get("type", "")
    sid = meta.get("session_id", "")
    gf_id = meta.get("girlfriend_id", "")

    # Gift purchase
    if payment_type == "gift":
        from app.services.gifting import get_gift_by_id
        from app.api.routes.gifts import _add_purchase, _deliver_gift, _processed_sessions

        gift_id = meta.get("gift_id", "")
        gift = get_gift_by_id(gift_id)
        if not gift or not sid:
            return {"status": "failed", "error": "gift_or_session_missing"}

        _processed_sessions.add(payment_intent_id)
        purchase = {
            "id": str(uuid4()),
            "gift_id": gift.id,
            "gift_name": gift.name,
            "amount_eur": gift.price_eur,
            "currency": "eur",
            "stripe_session_id": payment_intent_id,
            "status": "paid",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "emoji": gift.emoji,
        }
        user = get_session_user(sid)
        _add_purchase(sid, purchase, user)
        _deliver_gift(sid, gift, purchase)
        mark_payment_fulfilled(payment_intent_id, {"type": "gift", "gift_id": gift.id, "girlfriend_id": gf_id})
        return {"status": "succeeded", "type": "gift"}

    # Leak slot
    if payment_type in ("leaks_spin", "leak_slot"):
        from app.api.routes.leaks import _leaks_unlocked, _persist as leaks_persist
        import hashlib as _hl

        leak_id = meta.get("leak_id", "")
        if not sid or not gf_id or not leak_id:
            return {"status": "failed", "error": "leak_metadata_missing"}

        key = (sid, gf_id)
        if key not in _leaks_unlocked:
            _leaks_unlocked[key] = {}
        if leak_id not in _leaks_unlocked[key]:
            seed = _hl.md5(f"{gf_id}:{leak_id}".encode()).hexdigest()[:10]
            _leaks_unlocked[key][leak_id] = f"https://picsum.photos/seed/{seed}/400/600"
            leaks_persist()
        mark_payment_fulfilled(payment_intent_id, {"type": "leaks_spin", "leak_id": leak_id, "girlfriend_id": gf_id})
        return {"status": "succeeded", "type": "leaks_spin"}

    # Mystery box
    if payment_type == "mystery_box":
        from app.services.gifting import get_gift_by_id
        from app.api.routes.gifts import _add_purchase, _deliver_gift, _processed_sessions, MYSTERY_BOXES

        gift_id = meta.get("gift_id", "")
        box_id = meta.get("box_id", "")
        gift = get_gift_by_id(gift_id)
        if not gift or not sid:
            return {"status": "failed", "error": "gift_or_session_missing"}

        _processed_sessions.add(payment_intent_id)
        box = MYSTERY_BOXES.get(box_id, {})
        purchase = {
            "id": str(uuid4()),
            "gift_id": gift.id,
            "gift_name": gift.name,
            "amount_eur": box.get("price_eur", gift.price_eur),
            "currency": "eur",
            "stripe_session_id": payment_intent_id,
            "status": "paid",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "emoji": gift.emoji,
            "source": "mystery_box",
            "box_id": box_id,
        }
        user = get_session_user(sid)
        _add_purchase(sid, purchase, user)
        _deliver_gift(sid, gift, purchase)
        mark_payment_fulfilled(payment_intent_id, {"type": "mystery_box", "gift_id": gift.id, "girlfriend_id": gf_id})
        return {"status": "succeeded", "type": "mystery_box"}

    # Subscriptions are finalized by Stripe subscription/invoice webhooks in billing.py
    if payment_type in ("subscription", "upgrade"):
        mark_payment_fulfilled(payment_intent_id, {"type": payment_type, "girlfriend_id": gf_id})
        return {"status": "succeeded", "type": payment_type}

    # Unknown metadata type - mark as fulfilled to avoid infinite retries.
    mark_payment_fulfilled(payment_intent_id, {"type": payment_type or "unknown"})
    return {"status": "succeeded", "type": payment_type or "unknown"}


# ---------------------------------------------------------------------------
# POST /api/payments/intent
# ---------------------------------------------------------------------------

class PaymentIntentRequest(BaseModel):
    type: str  # "subscription" | "gift" | "leaks_spin" | "mystery_box" | "upgrade" | "setup"
    plan: str | None = None
    product_id: str | None = None
    tier: str | None = None
    girlfriend_id: str | None = None
    metadata: dict | None = None


class PaymentIntentResponse(BaseModel):
    status: str
    payment_intent_client_secret: str | None = None
    setup_intent_client_secret: str | None = None
    payment_intent_id: str | None = None
    requires_setup: bool = False
    display_amount: dict | None = None
    saved_card_available: bool = False
    saved_card_last4: str | None = None
    saved_card_brand: str | None = None
    error: str | None = None
    # Business-logic payload returned on success
    result_data: dict | None = None


@router.post("/intent", response_model=PaymentIntentResponse)
def create_payment_intent(request: Request, body: PaymentIntentRequest):
    sid, user = _require_user(request)
    gf_id = body.girlfriend_id or user.get("current_girlfriend_id", "")

    # Resolve saved card info for display
    has_stripe = init_stripe()
    card_info = None
    if has_stripe:
        cid = user.get("stripe_customer_id")
        pm = user.get("default_payment_method_id")
        if cid:
            card_info = get_saved_card_info(cid, pm)

    saved_available = card_info is not None

    # ── Setup (save new card) ─────────────────────────────────────────
    if body.type == "setup":
        if not has_stripe:
            return PaymentIntentResponse(status="succeeded", saved_card_available=saved_available)
        setup = svc_create_setup(sid, user)
        return PaymentIntentResponse(
            status="requires_payment_method",
            setup_intent_client_secret=setup.client_secret,
            requires_setup=True,
            saved_card_available=saved_available,
        )

    # ── Subscription / upgrade ────────────────────────────────────────
    if body.type in ("subscription", "upgrade"):
        plan = body.plan
        if not plan:
            raise HTTPException(status_code=400, detail="plan required")

        result = create_or_update_subscription(sid, user, plan)
        if result.status == "no_card" and init_stripe():
            setup = svc_create_setup(sid, user)
            return PaymentIntentResponse(
                status="requires_payment_method",
                setup_intent_client_secret=setup.client_secret,
                requires_setup=True,
                saved_card_available=False,
                display_amount={"currency": "eur", "amount": PLAN_MONTHLY_CENTS.get(plan, 0)},
            )
        return _to_response(result, saved_available, card_info,
                            display_cents=PLAN_MONTHLY_CENTS.get(plan, 0))

    # ── Gift purchase ─────────────────────────────────────────────────
    if body.type == "gift":
        gift_id = body.product_id
        if not gift_id:
            raise HTTPException(status_code=400, detail="product_id (gift_id) required")

        from app.services.gifting import get_gift_by_id, validate_cooldown
        from app.api.routes.gifts import _get_purchases, _add_purchase, _deliver_gift, _processed_sessions

        gift = get_gift_by_id(gift_id)
        if not gift:
            raise HTTPException(status_code=404, detail=f"Gift '{gift_id}' not found")

        purchases = _get_purchases(sid, user)
        already = any(p.get("gift_id") == gift_id and p.get("status") == "paid" for p in purchases)
        if already:
            raise HTTPException(status_code=400, detail="Already gifted. Each gift once per girlfriend.")

        cooldown_err = validate_cooldown(purchases, gift)
        if cooldown_err:
            raise HTTPException(status_code=400, detail=cooldown_err)

        amount_cents = int(round(gift.price_eur * 100))
        meta = {
            "type": "gift", "gift_id": gift.id,
            "user_id": user.get("id", ""), "girlfriend_id": gf_id, "session_id": sid,
        }

        result = create_one_time_payment(
            sid, user, amount_cents, "eur",
            f"Gift: {gift.name}", meta,
            idempotency_extra=f"gift:{gift.id}:{gf_id}",
        )
        if result.status == "no_card" and init_stripe():
            setup = svc_create_setup(sid, user)
            return PaymentIntentResponse(
                status="requires_payment_method",
                setup_intent_client_secret=setup.client_secret,
                requires_setup=True,
                saved_card_available=False,
                display_amount={"currency": "eur", "amount": amount_cents},
            )

        if result.status == "succeeded":
            pi_id = result.payment_intent_id or ""
            if pi_id not in _processed_sessions:
                _processed_sessions.add(pi_id)
                purchase = {
                    "id": str(uuid4()), "gift_id": gift.id, "gift_name": gift.name,
                    "amount_eur": gift.price_eur, "currency": "eur",
                    "stripe_session_id": pi_id, "status": "paid",
                    "created_at": datetime.now(timezone.utc).isoformat(), "emoji": gift.emoji,
                }
                _add_purchase(sid, purchase, user)
                _deliver_gift(sid, gift, purchase)
                mark_payment_fulfilled(pi_id, {"type": "gift", "gift_id": gift.id, "girlfriend_id": gf_id})

        return _to_response(result, saved_available, card_info, display_cents=amount_cents)

    # ── Leaks spin ────────────────────────────────────────────────────
    if body.type == "leaks_spin":
        box_id = body.tier or body.product_id
        if not box_id:
            raise HTTPException(status_code=400, detail="tier (box_id) required")

        from app.api.routes.leaks import (
            LEAK_BOXES, _leaks_unlocked, _pick_random_leak, _persist as leaks_persist,
        )
        import hashlib as _hl

        box = LEAK_BOXES.get(box_id)
        if not box:
            raise HTTPException(status_code=400, detail="Invalid box_id")

        already_map = _leaks_unlocked.get((sid, gf_id), {})
        chosen = _pick_random_leak(box["weights"], already_map)
        if not chosen:
            return PaymentIntentResponse(
                status="failed", error="All leaks already unlocked!",
                saved_card_available=saved_available,
            )

        chosen_rarity, chosen_id = chosen
        amount_cents = int(round(box["price_eur"] * 100))
        meta = {
            "type": "leaks_spin", "box_id": box_id, "leak_id": chosen_id,
            "user_id": user.get("id", ""), "girlfriend_id": gf_id, "session_id": sid,
        }

        result = create_one_time_payment(
            sid, user, amount_cents, "eur",
            f"Leak Slot: {box['name']}", meta,
            idempotency_extra=f"leak:{box_id}:{chosen_id}:{gf_id}",
        )
        if result.status == "no_card" and init_stripe():
            setup = svc_create_setup(sid, user)
            return PaymentIntentResponse(
                status="requires_payment_method",
                setup_intent_client_secret=setup.client_secret,
                requires_setup=True,
                saved_card_available=False,
                display_amount={"currency": "eur", "amount": amount_cents},
                result_data={"leak_id": chosen_id, "rarity": chosen_rarity},
            )

        if result.status == "succeeded":
            pi_id = result.payment_intent_id or ""
            if not is_payment_fulfilled(pi_id):
                seed = _hl.md5(f"{gf_id}:{chosen_id}".encode()).hexdigest()[:10]
                image_url = f"https://picsum.photos/seed/{seed}/400/600"
                key = (sid, gf_id)
                if key not in _leaks_unlocked:
                    _leaks_unlocked[key] = {}
                _leaks_unlocked[key][chosen_id] = image_url
                leaks_persist()
                mark_payment_fulfilled(pi_id, {"type": "leaks_spin", "leak_id": chosen_id, "girlfriend_id": gf_id})

            return _to_response(result, saved_available, card_info, display_cents=amount_cents,
                                extra_data={"leak_id": chosen_id, "rarity": chosen_rarity,
                                            "image_url": _leaks_unlocked.get((sid, gf_id), {}).get(chosen_id)})

        return _to_response(result, saved_available, card_info, display_cents=amount_cents,
                            extra_data={"leak_id": chosen_id, "rarity": chosen_rarity})

    # ── Mystery box ───────────────────────────────────────────────────
    if body.type == "mystery_box":
        box_id = body.tier or body.product_id
        if not box_id:
            raise HTTPException(status_code=400, detail="tier (box_id) required")

        from app.api.routes.gifts import (
            MYSTERY_BOXES, _pick_mystery_gift, _get_purchases,
            _add_purchase, _deliver_gift, _processed_sessions,
        )

        box = MYSTERY_BOXES.get(box_id)
        if not box:
            raise HTTPException(status_code=400, detail="Invalid box_id")

        purchases = _get_purchases(sid, user)
        owned_ids = {p["gift_id"] for p in purchases if p.get("status") == "paid"}
        gift = _pick_mystery_gift(box_id, owned_ids)
        if not gift:
            return PaymentIntentResponse(
                status="failed", error="All gifts collected!",
                saved_card_available=saved_available,
            )

        amount_cents = int(round(box["price_eur"] * 100))
        meta = {
            "type": "mystery_box", "box_id": box_id, "gift_id": gift.id,
            "user_id": user.get("id", ""), "girlfriend_id": gf_id, "session_id": sid,
        }

        gift_data = {
            "id": gift.id, "name": gift.name, "emoji": gift.emoji,
            "tier": gift.tier, "price_eur": gift.price_eur,
            "description": gift.description,
            "normal_photos": gift.image_reward.normal_photos,
            "spicy_photos": gift.image_reward.spicy_photos,
        }
        box_data = {"id": box_id, "name": box["name"], "price_eur": box["price_eur"]}

        result = create_one_time_payment(
            sid, user, amount_cents, "eur",
            f"Mystery Box: {box['name']}", meta,
            idempotency_extra=f"mystery:{box_id}:{gift.id}:{gf_id}",
        )
        if result.status == "no_card" and init_stripe():
            setup = svc_create_setup(sid, user)
            return PaymentIntentResponse(
                status="requires_payment_method",
                setup_intent_client_secret=setup.client_secret,
                requires_setup=True,
                saved_card_available=False,
                display_amount={"currency": "eur", "amount": amount_cents},
                result_data={"gift": gift_data, "box": box_data},
            )

        if result.status == "succeeded":
            pi_id = result.payment_intent_id or ""
            if pi_id not in _processed_sessions:
                _processed_sessions.add(pi_id)
                purchase = {
                    "id": str(uuid4()), "gift_id": gift.id, "gift_name": gift.name,
                    "amount_eur": box["price_eur"], "currency": "eur",
                    "stripe_session_id": pi_id, "status": "paid",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "emoji": gift.emoji, "source": "mystery_box", "box_id": box_id,
                }
                _add_purchase(sid, purchase, user)
                _deliver_gift(sid, gift, purchase)
                mark_payment_fulfilled(pi_id, {"type": "mystery_box", "gift_id": gift.id, "girlfriend_id": gf_id})

            return _to_response(result, saved_available, card_info, display_cents=amount_cents,
                                extra_data={"gift": gift_data, "box": box_data})

        return _to_response(result, saved_available, card_info, display_cents=amount_cents,
                            extra_data={"gift": gift_data, "box": box_data})

    raise HTTPException(status_code=400, detail=f"Unknown payment type: {body.type}")


# ---------------------------------------------------------------------------
# POST /api/payments/confirm
# ---------------------------------------------------------------------------

class PaymentConfirmRequest(BaseModel):
    payment_intent_id: str
    type: str
    product_id: str | None = None
    tier: str | None = None
    girlfriend_id: str | None = None


@router.post("/confirm")
def confirm_payment(request: Request, body: PaymentConfirmRequest):
    """Called by frontend after 3DS completes.  Verifies PI status and
    runs business-logic fulfilment exactly once."""
    _sid, _user = _require_user(request)
    pi_id = body.payment_intent_id

    if is_payment_fulfilled(pi_id):
        return {"status": "succeeded", "already_fulfilled": True}

    if not verify_payment_intent(pi_id):
        return {"status": "failed", "error": "Payment not completed"}

    result = finalize_payment_intent_for_webhook(pi_id)
    if result.get("status") == "succeeded":
        return result
    return {"status": "failed", "error": result.get("error", f"Unknown type: {body.type}")}


# ---------------------------------------------------------------------------
# Response builder
# ---------------------------------------------------------------------------

def _to_response(
    result: PaymentResult,
    saved_available: bool,
    card_info,
    display_cents: int = 0,
    extra_data: dict | None = None,
) -> PaymentIntentResponse:
    return PaymentIntentResponse(
        status=result.status,
        payment_intent_client_secret=result.client_secret,
        payment_intent_id=result.payment_intent_id,
        error=result.error,
        saved_card_available=saved_available,
        saved_card_last4=card_info.last4 if card_info else None,
        saved_card_brand=card_info.brand if card_info else None,
        display_amount={"currency": "eur", "amount": display_cents} if display_cents else None,
        result_data=extra_data,
    )
