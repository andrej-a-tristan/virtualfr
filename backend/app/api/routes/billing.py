"""Billing: plan status, Stripe SetupIntent for card saving, webhook."""
import logging

import stripe
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.api.store import get_session_user, set_session_user

router = APIRouter(prefix="/billing", tags=["billing"])
logger = logging.getLogger(__name__)

SESSION_COOKIE = "session"


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
        # Catch SignatureVerificationError (location varies across stripe versions)
        if "SignatureVerification" in type(exc).__name__:
            raise HTTPException(status_code=400, detail="Invalid signature")
        raise

    logger.info("Stripe event: %s", event["type"])

    # Handle setup_intent.succeeded
    if event["type"] == "setup_intent.succeeded":
        si = event["data"]["object"]
        metadata = si.get("metadata", {})
        user_id = metadata.get("user_id", "")
        session_id = metadata.get("session_id", "")
        payment_method = si.get("payment_method")
        customer_id = si.get("customer")

        logger.info(
            "SetupIntent succeeded: user=%s pm=%s customer=%s",
            user_id, payment_method, customer_id,
        )

        # Set default payment method on Stripe Customer
        if customer_id and payment_method:
            try:
                stripe.Customer.modify(
                    customer_id,
                    invoice_settings={"default_payment_method": payment_method},
                )
            except Exception as e:
                logger.warning("Failed to set default PM on customer: %s", e)

        # Persist to in-memory store
        if session_id:
            user = get_session_user(session_id)
            if user:
                set_session_user(session_id, {
                    **user,
                    "has_card_on_file": True,
                    "default_payment_method_id": payment_method,
                })
                logger.info("Marked user %s has_card_on_file=True", user_id)

    return {"ok": True}


# ── POST /api/billing/checkout (placeholder for future subscription creation) ─

@router.post("/checkout")
def checkout(request: Request):
    sid = _session_id(request)
    if not sid:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    return {"checkout_url": "https://example.com/checkout"}


# ── POST /api/billing/confirm-card (frontend fallback if webhook is slow) ────

@router.post("/confirm-card")
def confirm_card(request: Request):
    """Optimistic card confirmation — frontend calls this after stripe.confirmSetup
    succeeds, so the user doesn't have to wait for the webhook."""
    sid, user = _require_user(request)
    set_session_user(sid, {**user, "has_card_on_file": True})
    return {"ok": True, "has_card_on_file": True}
