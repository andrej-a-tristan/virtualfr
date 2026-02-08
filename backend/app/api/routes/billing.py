"""Billing: plan status, Stripe SetupIntent for card saving, subscriptions, webhook."""
import logging

import stripe
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import get_settings
from app.api.store import get_session_user, set_session_user

router = APIRouter(prefix="/billing", tags=["billing"])
logger = logging.getLogger(__name__)

SESSION_COOKIE = "session"

PLAN_PRICE_MAP = {
    "plus": "stripe_price_plus",
    "premium": "stripe_price_premium",
}


def _session_id(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE)


def _require_user(request: Request) -> tuple[str, dict]:
    """Return (session_id, user_dict) or raise 401."""
    sid = _session_id(request)
    if not sid:
        raise HTTPException(status_code=401, detail="unauthorized")
    user = get_session_user(sid)
    if not user:
        raise HTTPException(status_code=401, detail="unauthorized")
    return sid, user


def _init_stripe() -> None:
    """Set stripe.api_key from settings. Call before any stripe.* call."""
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    stripe.api_key = settings.stripe_secret_key


def _get_price_id(plan: str) -> str:
    """Resolve a plan name to a Stripe Price ID from settings."""
    settings = get_settings()
    attr = PLAN_PRICE_MAP.get(plan)
    if not attr:
        raise HTTPException(status_code=400, detail=f"No price configured for plan: {plan}")
    price_id = getattr(settings, attr, "")
    if not price_id:
        raise HTTPException(status_code=503, detail=f"Price ID not configured for plan: {plan}")
    return price_id


# ── GET /api/billing/status ──────────────────────────────────────────────────

@router.get("/status")
def billing_status(request: Request):
    sid = _session_id(request)
    if not sid:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    user = get_session_user(sid)
    plan = (user or {}).get("plan", "free")
    has_card = (user or {}).get("has_card_on_file", False)
    return {
        "plan": plan,
        "has_card_on_file": has_card,
        "message_cap": 50 if plan == "free" else 999,
        "image_cap": 0 if plan == "free" else 30 if plan == "plus" else 80,
    }


# ── POST /api/billing/setup-intent ──────────────────────────────────────────

@router.post("/setup-intent")
def create_setup_intent(request: Request):
    """Create a Stripe SetupIntent so the frontend can collect a card."""
    _init_stripe()
    settings = get_settings()
    sid, user = _require_user(request)

    # Create or reuse Stripe Customer
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.get("email", ""),
            metadata={"user_id": user.get("id", "")},
        )
        customer_id = customer.id
        set_session_user(sid, {**user, "stripe_customer_id": customer_id})
        logger.info("Created Stripe customer %s for user %s", customer_id, user.get("id"))

    # Create SetupIntent
    si = stripe.SetupIntent.create(
        customer=customer_id,
        payment_method_types=["card"],
        usage="off_session",
        metadata={"user_id": user.get("id", ""), "session_id": sid},
    )

    return {
        "client_secret": si.client_secret,
        "publishable_key": settings.stripe_publishable_key,
    }


# ── POST /api/billing/subscribe ──────────────────────────────────────────────

class SubscribeRequest(BaseModel):
    plan: str  # "plus" or "premium"


@router.post("/subscribe")
def subscribe(request: Request, body: SubscribeRequest):
    """Create a Stripe Subscription for a paid plan using the saved card."""
    _init_stripe()
    sid, user = _require_user(request)

    if body.plan == "free":
        # Free plan: no subscription needed, just set the plan
        set_session_user(sid, {**user, "plan": "free"})
        return {"ok": True, "plan": "free", "subscription_id": None}

    # Ensure customer + payment method exist
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer. Save a card first.")

    default_pm = user.get("default_payment_method_id")

    # If we don't have the PM ID locally, fetch it from Stripe
    if not default_pm:
        try:
            pms = stripe.Customer.list_payment_methods(customer_id, type="card", limit=1)
            if pms.data:
                default_pm = pms.data[0].id
                set_session_user(sid, {**user, "default_payment_method_id": default_pm})
                logger.info("Fetched PM from Stripe: %s", default_pm)
        except Exception as e:
            logger.warning("Failed to fetch PMs from Stripe: %s", e)

    if not default_pm:
        raise HTTPException(status_code=400, detail="No card on file. Save a card first.")

    price_id = _get_price_id(body.plan)

    # Cancel existing subscription if upgrading/changing
    existing_sub_id = user.get("stripe_subscription_id")
    if existing_sub_id:
        try:
            stripe.Subscription.cancel(existing_sub_id)
            logger.info("Cancelled old subscription %s", existing_sub_id)
        except Exception as e:
            logger.warning("Failed to cancel old subscription: %s", e)

    # Create subscription — card is already saved as default, Stripe charges it immediately
    sub = stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": price_id}],
        default_payment_method=default_pm,
        metadata={"user_id": user.get("id", ""), "session_id": sid},
    )

    status = sub.status
    logger.info("Created subscription %s status=%s for plan=%s", sub.id, status, body.plan)

    # Update user record
    set_session_user(sid, {
        **user,
        "plan": body.plan,
        "stripe_subscription_id": sub.id,
    })

    return {"ok": True, "plan": body.plan, "subscription_id": sub.id, "status": status}


# ── POST /api/billing/cancel ─────────────────────────────────────────────────

@router.post("/cancel")
def cancel_subscription(request: Request):
    """Cancel the current Stripe subscription and revert to free plan."""
    _init_stripe()
    sid, user = _require_user(request)

    sub_id = user.get("stripe_subscription_id")
    if not sub_id:
        # No active subscription — just ensure plan is free
        set_session_user(sid, {**user, "plan": "free", "stripe_subscription_id": None})
        return {"ok": True, "plan": "free"}

    try:
        stripe.Subscription.cancel(sub_id)
        logger.info("Cancelled subscription %s", sub_id)
    except Exception as e:
        logger.warning("Failed to cancel subscription %s: %s", sub_id, e)

    set_session_user(sid, {**user, "plan": "free", "stripe_subscription_id": None})
    return {"ok": True, "plan": "free"}


# ── POST /api/billing/webhook ────────────────────────────────────────────────

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Stripe webhook handler. Verifies signature, processes events."""
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
    logger.info("Stripe event: %s", event_type)

    # ── SetupIntent succeeded (card saved) ───────────────────────────────
    if event_type == "setup_intent.succeeded":
        si = event["data"]["object"]
        metadata = si.get("metadata", {})
        session_id = metadata.get("session_id", "")
        payment_method = si.get("payment_method")
        customer_id = si.get("customer")

        logger.info("SetupIntent succeeded: pm=%s customer=%s", payment_method, customer_id)

        if customer_id and payment_method:
            try:
                stripe.Customer.modify(
                    customer_id,
                    invoice_settings={"default_payment_method": payment_method},
                )
            except Exception as e:
                logger.warning("Failed to set default PM on customer: %s", e)

        if session_id:
            user = get_session_user(session_id)
            if user:
                set_session_user(session_id, {
                    **user,
                    "has_card_on_file": True,
                    "default_payment_method_id": payment_method,
                })

    # ── Invoice paid (subscription payment succeeded) ────────────────────
    elif event_type == "invoice.paid":
        invoice = event["data"]["object"]
        customer_id = invoice.get("customer")
        sub_id = invoice.get("subscription")
        logger.info("Invoice paid: customer=%s subscription=%s", customer_id, sub_id)

    # ── Subscription updated (plan change, cancellation, etc.) ───────────
    elif event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
    ):
        sub = event["data"]["object"]
        metadata = sub.get("metadata", {})
        session_id = metadata.get("session_id", "")
        status = sub.get("status")
        logger.info("Subscription %s status=%s", sub.get("id"), status)

        if session_id and status == "active":
            user = get_session_user(session_id)
            if user:
                # Determine plan from price
                items = sub.get("items", {}).get("data", [])
                plan = user.get("plan", "free")
                if items:
                    price_id = items[0].get("price", {}).get("id", "")
                    s = get_settings()
                    if price_id == s.stripe_price_plus:
                        plan = "plus"
                    elif price_id == s.stripe_price_premium:
                        plan = "premium"
                set_session_user(session_id, {
                    **user,
                    "plan": plan,
                    "stripe_subscription_id": sub.get("id"),
                })

    # ── Checkout session completed (gift purchases) ────────────────────
    elif event_type == "checkout.session.completed":
        session_obj = event["data"]["object"]
        metadata = session_obj.get("metadata", {})
        gift_id = metadata.get("gift_id")
        if gift_id:
            # Delegate to the gift delivery handler
            try:
                from app.api.routes.gifts import _deliver_gift, _processed_sessions, _update_purchase_status
                stripe_session_id = session_obj.get("id", "")
                app_session_id = metadata.get("session_id", "")

                if stripe_session_id not in _processed_sessions:
                    _processed_sessions.add(stripe_session_id)
                    _update_purchase_status(stripe_session_id, "paid")
                    from app.services.gifting import get_gift_by_id
                    gift = get_gift_by_id(gift_id)
                    if gift:
                        _deliver_gift(app_session_id, gift, None)
                        logger.info("Gift %s delivered via billing webhook", gift_id)
                else:
                    logger.info("Gift session %s already processed", stripe_session_id)
            except Exception as e:
                logger.warning("Failed to process gift checkout: %s", e)

    # ── Subscription deleted ─────────────────────────────────────────────
    elif event_type == "customer.subscription.deleted":
        sub = event["data"]["object"]
        metadata = sub.get("metadata", {})
        session_id = metadata.get("session_id", "")
        if session_id:
            user = get_session_user(session_id)
            if user:
                set_session_user(session_id, {
                    **user,
                    "plan": "free",
                    "stripe_subscription_id": None,
                })
                logger.info("Subscription cancelled, reverted to free")

    return {"ok": True}


# ── POST /api/billing/confirm-card (frontend fallback if webhook is slow) ────

class ConfirmCardRequest(BaseModel):
    payment_method_id: str | None = None


@router.post("/confirm-card")
def confirm_card(request: Request, body: ConfirmCardRequest):
    """Optimistic card confirmation — frontend calls this after stripe.confirmSetup
    succeeds, so the user doesn't have to wait for the webhook."""
    sid, user = _require_user(request)
    updates: dict = {"has_card_on_file": True}
    if body.payment_method_id:
        updates["default_payment_method_id"] = body.payment_method_id
        # Also set it as default on the Stripe Customer
        customer_id = user.get("stripe_customer_id")
        if customer_id:
            try:
                _init_stripe()
                stripe.Customer.modify(
                    customer_id,
                    invoice_settings={"default_payment_method": body.payment_method_id},
                )
            except Exception as e:
                logger.warning("Failed to set default PM on customer: %s", e)
    set_session_user(sid, {**user, **updates})
    return {"ok": True, "has_card_on_file": True}
