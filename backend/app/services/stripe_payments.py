"""Unified Stripe payment service.

Centralises customer management, default-PM resolution, PaymentIntent
creation (off_session where possible), SetupIntent creation, and
subscription lifecycle.  Every paid action in the app flows through here.
"""
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any

import stripe

from app.core.config import get_settings
from app.api.store import get_session_user, set_session_user

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result DTOs
# ---------------------------------------------------------------------------

@dataclass
class PaymentResult:
    status: str  # "succeeded" | "requires_action" | "requires_payment_method" | "no_card" | "failed"
    payment_intent_id: str | None = None
    client_secret: str | None = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class SetupResult:
    client_secret: str
    publishable_key: str
    customer_id: str


@dataclass
class CardInfo:
    pm_id: str
    brand: str
    last4: str
    exp_month: int
    exp_year: int


# ---------------------------------------------------------------------------
# Stripe initialisation
# ---------------------------------------------------------------------------

def init_stripe() -> bool:
    """Set stripe.api_key. Returns True if Stripe is configured."""
    settings = get_settings()
    if not settings.stripe_secret_key:
        return False
    stripe.api_key = settings.stripe_secret_key
    return True


# ---------------------------------------------------------------------------
# Customer + payment-method helpers
# ---------------------------------------------------------------------------

def ensure_customer(sid: str, user: dict) -> tuple[str, dict]:
    """Ensure a Stripe customer exists for this user.  Returns (customer_id, updated_user)."""
    cid = user.get("stripe_customer_id")
    if cid:
        return cid, user

    cust = stripe.Customer.create(
        email=user.get("email", ""),
        metadata={"user_id": user.get("id", ""), "session_id": sid},
    )
    cid = cust.id
    user = {**user, "stripe_customer_id": cid}
    set_session_user(sid, user)
    logger.info("Created Stripe customer %s for session %s", cid, sid[:8])
    return cid, user


def resolve_default_pm(sid: str, user: dict, customer_id: str) -> tuple[str | None, dict]:
    """Return the default payment-method id (or None) and an updated user dict."""
    pm = user.get("default_payment_method_id")
    if pm:
        return pm, user

    try:
        pms = stripe.Customer.list_payment_methods(customer_id, type="card", limit=1)
        if pms.data:
            pm = pms.data[0].id
            user = {**user, "default_payment_method_id": pm}
            set_session_user(sid, user)
    except Exception as e:
        logger.warning("Failed to list PMs for customer %s: %s", customer_id, e)

    return pm, user


def get_saved_card_info(customer_id: str, pm_id: str | None = None) -> CardInfo | None:
    """Return summary of a saved card."""
    try:
        if not pm_id:
            cust = stripe.Customer.retrieve(customer_id)
            inv_settings = cust.get("invoice_settings") or {}
            pm_id = inv_settings.get("default_payment_method")
            if not pm_id:
                pms = stripe.Customer.list_payment_methods(customer_id, type="card", limit=1)
                if pms.data:
                    pm_id = pms.data[0].id
        if not pm_id:
            return None
        pm = stripe.PaymentMethod.retrieve(pm_id)
        card = pm.get("card", {})
        return CardInfo(
            pm_id=pm_id,
            brand=card.get("brand", "unknown"),
            last4=card.get("last4", "????"),
            exp_month=card.get("exp_month", 0),
            exp_year=card.get("exp_year", 0),
        )
    except Exception as e:
        logger.warning("get_saved_card_info failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Idempotency helpers
# ---------------------------------------------------------------------------

def _idempotency_key(sid: str, action: str, extra: str = "") -> str:
    """Deterministic idempotency key based on user+action."""
    raw = f"{sid}:{action}:{extra}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# One-time payment (gifts, leaks, mystery boxes)
# ---------------------------------------------------------------------------

def create_one_time_payment(
    sid: str,
    user: dict,
    amount_cents: int,
    currency: str,
    description: str,
    metadata: dict[str, str],
    idempotency_extra: str = "",
) -> PaymentResult:
    """Create a PaymentIntent using the saved card (off_session).

    - If the card works → status=succeeded
    - If 3DS needed → status=requires_action + client_secret
    - If no card → status=no_card
    - If payment fails → status=failed
    """
    if not init_stripe():
        logger.info("DEV MODE: payment %s skipped (no Stripe key)", description)
        return PaymentResult(status="succeeded", metadata=metadata)

    customer_id, user = ensure_customer(sid, user)
    pm_id, user = resolve_default_pm(sid, user, customer_id)

    if not pm_id:
        return PaymentResult(status="no_card", error="No card on file. Please add a card first.")

    idem_key = _idempotency_key(sid, description, idempotency_extra) if idempotency_extra else None

    try:
        pi_kwargs: dict[str, Any] = dict(
            amount=amount_cents,
            currency=currency,
            customer=customer_id,
            payment_method=pm_id,
            off_session=True,
            confirm=True,
            description=description,
            metadata=metadata,
        )
        if idem_key:
            pi_kwargs["idempotency_key"] = idem_key

        pi = stripe.PaymentIntent.create(**pi_kwargs)
    except stripe.error.CardError as e:
        return PaymentResult(status="failed", error=str(e.user_message or e))
    except Exception as e:
        logger.error("PaymentIntent create failed: %s", e)
        return PaymentResult(status="failed", error="Payment failed. Please try again.")

    if pi.status == "requires_action":
        return PaymentResult(
            status="requires_action",
            payment_intent_id=pi.id,
            client_secret=pi.client_secret,
            metadata=metadata,
        )

    if pi.status == "succeeded":
        return PaymentResult(status="succeeded", payment_intent_id=pi.id, metadata=metadata)

    return PaymentResult(
        status="failed",
        payment_intent_id=pi.id,
        error=f"Payment not completed (status: {pi.status})",
    )


def verify_payment_intent(payment_intent_id: str) -> bool:
    """Check if a PaymentIntent has succeeded (for confirm flows)."""
    if not init_stripe():
        return True
    try:
        pi = stripe.PaymentIntent.retrieve(payment_intent_id)
        return pi.status == "succeeded"
    except Exception as e:
        logger.warning("PI verification failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# SetupIntent (save card)
# ---------------------------------------------------------------------------

def create_setup_intent(sid: str, user: dict) -> SetupResult:
    """Create a SetupIntent to collect a new card."""
    init_stripe()
    settings = get_settings()
    customer_id, user = ensure_customer(sid, user)

    si = stripe.SetupIntent.create(
        customer=customer_id,
        payment_method_types=["card"],
        usage="off_session",
        metadata={"user_id": user.get("id", ""), "session_id": sid},
    )
    return SetupResult(
        client_secret=si.client_secret,
        publishable_key=settings.stripe_publishable_key,
        customer_id=customer_id,
    )


def confirm_setup_intent(sid: str, user: dict, payment_method_id: str | None) -> None:
    """Optimistic card confirmation after frontend confirmSetup succeeds."""
    updates: dict = {"has_card_on_file": True}
    if payment_method_id:
        updates["default_payment_method_id"] = payment_method_id
        customer_id = user.get("stripe_customer_id")
        if customer_id:
            try:
                init_stripe()
                stripe.Customer.modify(
                    customer_id,
                    invoice_settings={"default_payment_method": payment_method_id},
                )
            except Exception as e:
                logger.warning("Failed to set default PM: %s", e)
    set_session_user(sid, {**user, **updates})


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------

PLAN_PRICE_MAP = {"plus": "stripe_price_plus", "premium": "stripe_price_premium"}
PLAN_MONTHLY_CENTS = {"free": 0, "plus": 1499, "premium": 2999}


def _get_price_id(plan: str) -> str:
    settings = get_settings()
    attr = PLAN_PRICE_MAP.get(plan)
    if not attr:
        raise ValueError(f"No price for plan: {plan}")
    return getattr(settings, attr, "")


def create_or_update_subscription(
    sid: str,
    user: dict,
    plan: str,
) -> PaymentResult:
    """Create or upgrade a Stripe Subscription and return the result.

    For free plan: cancels existing subscription.
    For paid plans: creates/updates subscription using saved card.
    """
    if not init_stripe():
        current = user.get("plan", "free")
        set_session_user(sid, {**user, "plan": plan})
        logger.info("DEV MODE: plan %s→%s", current, plan)
        return PaymentResult(status="succeeded")

    current = user.get("plan", "free")

    if plan == "free":
        sub_id = user.get("stripe_subscription_id")
        if sub_id:
            try:
                stripe.Subscription.cancel(sub_id)
            except Exception as e:
                logger.warning("Cancel sub failed: %s", e)
        set_session_user(sid, {**user, "plan": "free", "stripe_subscription_id": None})
        return PaymentResult(status="succeeded")

    customer_id, user = ensure_customer(sid, user)
    pm_id, user = resolve_default_pm(sid, user, customer_id)
    if not pm_id:
        return PaymentResult(status="no_card", error="No card on file.")

    price_id = _get_price_id(plan)
    if not price_id:
        return PaymentResult(status="failed", error="Price not configured.")

    sub_id = user.get("stripe_subscription_id")

    # Try modifying existing active sub
    if sub_id:
        try:
            existing = stripe.Subscription.retrieve(sub_id)
            if existing.status in ("active", "trialing"):
                item_id = existing["items"]["data"][0]["id"]
                sub = stripe.Subscription.modify(
                    sub_id,
                    items=[{"id": item_id, "price": price_id}],
                    proration_behavior="create_prorations",
                    default_payment_method=pm_id,
                    cancel_at_period_end=False,
                    metadata={"user_id": user.get("id", ""), "session_id": sid},
                )
                # Pay any proration invoice
                inv_id = sub.get("latest_invoice")
                if inv_id:
                    try:
                        inv = stripe.Invoice.retrieve(inv_id)
                        if inv.status == "open" and inv.amount_due > 0:
                            stripe.Invoice.pay(inv_id)
                    except Exception:
                        pass

                set_session_user(sid, {**user, "plan": plan, "stripe_subscription_id": sub.id})
                return PaymentResult(status="succeeded", metadata={"subscription_id": sub.id})
            else:
                try:
                    stripe.Subscription.cancel(sub_id)
                except Exception:
                    pass
        except stripe.InvalidRequestError:
            pass
        except Exception as e:
            logger.warning("Sub modify failed: %s", e)

    # Create new subscription
    sub = stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": price_id}],
        default_payment_method=pm_id,
        metadata={"user_id": user.get("id", ""), "session_id": sid},
        expand=["latest_invoice.payment_intent"],
    )

    # Check if the initial payment needs 3DS
    latest_invoice = sub.get("latest_invoice")
    if isinstance(latest_invoice, dict):
        pi = latest_invoice.get("payment_intent")
        if isinstance(pi, dict):
            if pi.get("status") == "requires_action":
                set_session_user(sid, {**user, "plan": plan, "stripe_subscription_id": sub.id})
                return PaymentResult(
                    status="requires_action",
                    client_secret=pi.get("client_secret"),
                    payment_intent_id=pi.get("id"),
                )

    set_session_user(sid, {**user, "plan": plan, "stripe_subscription_id": sub.id})
    return PaymentResult(status="succeeded", metadata={"subscription_id": sub.id})
