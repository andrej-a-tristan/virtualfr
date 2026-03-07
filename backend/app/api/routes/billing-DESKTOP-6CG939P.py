"""Billing: plan status, Stripe SetupIntent for card saving, subscriptions,
plan changes with proration, proration previews, payment methods, webhook."""
import logging
from datetime import datetime, timezone
from uuid import UUID

import stripe
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import get_settings
from app.api.store import get_session_user, set_session_user, get_girlfriend_count
from app.api import supabase_store as sb_store
from app.core.supabase_client import get_supabase_admin
from app.schemas.payment_method import (
    PaymentMethodCardSummary,
    PaymentMethodResponse,
    PaymentMethodsListResponse,
    SetDefaultCardRequest,
)
from app.schemas.billing import (
    ChangePlanRequest,
    ChangePlanResponse,
    PreviewChangeRequest,
    PreviewChangeResponse,
    BillingStatusResponse,
    InvoiceSummary,
    ProrationLineItem,
)

router = APIRouter(prefix="/billing", tags=["billing"])
logger = logging.getLogger(__name__)

SESSION_COOKIE = "session"

PLAN_PRICE_MAP = {
    "plus": "stripe_price_plus",
    "premium": "stripe_price_premium",
}

PLAN_ORDER = {"free": 0, "plus": 1, "premium": 2}

# Monthly amounts (cents) for display/fallback when no Stripe subscription exists
PLAN_MONTHLY_CENTS = {"free": 0, "plus": 1499, "premium": 2999}


def _uuid_or_none(v: str | None) -> UUID | None:
    if not v:
        return None
    try:
        return UUID(str(v))
    except (ValueError, TypeError):
        return None


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


def _price_id_to_plan(price_id: str) -> str:
    """Reverse-lookup: Stripe Price ID → plan name."""
    s = get_settings()
    if price_id == s.stripe_price_plus:
        return "plus"
    if price_id == s.stripe_price_premium:
        return "premium"
    return "free"


def _ensure_customer_and_pm(sid: str, user: dict) -> tuple[str, str]:
    """Return (customer_id, default_payment_method_id) or raise."""
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=409, detail="NO_PAYMENT_METHOD")

    default_pm = user.get("default_payment_method_id")
    if not default_pm:
        try:
            pms = stripe.Customer.list_payment_methods(customer_id, type="card", limit=1)
            if pms.data:
                default_pm = pms.data[0].id
                set_session_user(sid, {**user, "default_payment_method_id": default_pm})
        except Exception as e:
            logger.warning("Failed to fetch PMs from Stripe: %s", e)

    if not default_pm:
        raise HTTPException(status_code=409, detail="NO_PAYMENT_METHOD")

    return customer_id, default_pm


def _ts_to_iso(ts: int | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


# ── GET /api/billing/status ──────────────────────────────────────────────────

FREE_TRIAL_DAYS = 7  # free plan auto-upgrades to Plus after this many days

@router.get("/status", response_model=BillingStatusResponse)
def billing_status(request: Request):
    sid = _session_id(request)
    if not sid:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    user = get_session_user(sid)
    user_uuid = _uuid_or_none((user or {}).get("user_id") or (user or {}).get("id"))
    if user_uuid and get_supabase_admin():
        try:
            sub = sb_store.get_latest_subscription(user_uuid) or {}
            billing = sb_store.get_billing_customer(user_uuid) or {}
            if user:
                user = {
                    **user,
                    "plan": sub.get("plan", user.get("plan", "free")),
                    "stripe_subscription_id": sub.get("stripe_subscription_id", user.get("stripe_subscription_id")),
                    "has_card_on_file": bool(billing.get("has_card_on_file", user.get("has_card_on_file", False))),
                    "stripe_customer_id": billing.get("stripe_customer_id", user.get("stripe_customer_id")),
                    "default_payment_method_id": billing.get("default_payment_method_id", user.get("default_payment_method_id")),
                }
                set_session_user(sid, user)
        except Exception:
            pass
    plan = (user or {}).get("plan", "free")
    has_card = (user or {}).get("has_card_on_file", False)

    # ── Free trial: stamp start date on first check, auto-upgrade after 7 days ──
    free_trial_ends_at: str | None = None
    if plan == "free" and user:
        from datetime import timedelta
        trial_start_iso = user.get("free_trial_started_at")
        if not trial_start_iso:
            trial_start = datetime.now(timezone.utc)
            trial_start_iso = trial_start.isoformat().replace("+00:00", "Z")
            set_session_user(sid, {**user, "free_trial_started_at": trial_start_iso})
        else:
            trial_start = datetime.fromisoformat(trial_start_iso.replace("Z", "+00:00"))

        trial_end = trial_start + timedelta(days=FREE_TRIAL_DAYS)
        free_trial_ends_at = trial_end.isoformat().replace("+00:00", "Z")

        if datetime.now(timezone.utc) >= trial_end:
            # Auto-upgrade to Plus
            plan = "plus"
            set_session_user(sid, {**user, "plan": "plus"})
            user = get_session_user(sid)  # refresh

    girls_max = 3 if plan in ("premium", "plus") else 1
    girls_count = get_girlfriend_count(sid)

    # Try to fetch subscription period info from Stripe
    current_period_end: str | None = None
    subscription_status: str | None = None
    next_invoice_amount: int | None = None

    sub_id = (user or {}).get("stripe_subscription_id")
    if sub_id:
        try:
            _init_stripe()
            sub = stripe.Subscription.retrieve(sub_id)
            current_period_end = _ts_to_iso(sub.get("current_period_end"))
            subscription_status = sub.get("status")
            # Try to get upcoming invoice amount
            customer_id = (user or {}).get("stripe_customer_id")
            if customer_id:
                try:
                    upcoming = stripe.Invoice.upcoming(customer=customer_id, subscription=sub_id)
                    next_invoice_amount = upcoming.get("amount_due")
                except Exception:
                    next_invoice_amount = PLAN_MONTHLY_CENTS.get(plan)
        except Exception as e:
            logger.warning("Failed to fetch subscription info: %s", e)

    return BillingStatusResponse(
        plan=plan,
        has_card_on_file=has_card,
        message_cap=20 if plan == "free" else 999,
        message_cap_period="day" if plan == "free" else "unlimited",
        image_cap=0 if plan == "free" else 30 if plan == "plus" else 80,
        girls_max=girls_max,
        girls_count=girls_count,
        can_create_more_girls=girls_count < girls_max,
        current_period_end=current_period_end,
        next_renewal_date=current_period_end,
        next_invoice_amount=next_invoice_amount,
        subscription_status=subscription_status,
        free_trial_ends_at=free_trial_ends_at,
    )


# ── GET /api/billing/stripe-key ─────────────────────────────────────────────

@router.get("/stripe-key")
def get_stripe_key():
    """Return the Stripe publishable key for frontend use."""
    settings = get_settings()
    return {"publishable_key": settings.stripe_publishable_key}


# ── GET /api/billing/payment-method ─────────────────────────────────────────

@router.get("/payment-method", response_model=PaymentMethodResponse)
def get_payment_method(request: Request):
    """Return a safe summary of the user's default saved card."""
    _init_stripe()
    sid, user = _require_user(request)

    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        return PaymentMethodResponse(has_card=False)

    try:
        customer = stripe.Customer.retrieve(customer_id)
        default_pm_id = None
        inv_settings = customer.get("invoice_settings")
        if inv_settings:
            default_pm_id = inv_settings.get("default_payment_method")

        if not default_pm_id:
            pms = stripe.Customer.list_payment_methods(customer_id, type="card", limit=1)
            if pms.data:
                default_pm_id = pms.data[0].id

        if not default_pm_id:
            return PaymentMethodResponse(has_card=False)

        pm = stripe.PaymentMethod.retrieve(default_pm_id)
        card_data = pm.get("card", {})
        return PaymentMethodResponse(
            has_card=True,
            card=PaymentMethodCardSummary(
                id=default_pm_id,
                brand=card_data.get("brand", "unknown"),
                last4=card_data.get("last4", "????"),
                exp_month=card_data.get("exp_month", 0),
                exp_year=card_data.get("exp_year", 0),
                is_default=True,
            ),
        )
    except Exception as e:
        logger.warning("Failed to fetch payment method: %s", e)
        return PaymentMethodResponse(has_card=False)


# ── GET /api/billing/payment-methods (list all cards) ────────────────────────

@router.get("/payment-methods", response_model=PaymentMethodsListResponse)
def list_payment_methods(request: Request):
    """Return all saved cards for the user, marking the default."""
    sid, user = _require_user(request)

    # Dev/demo fallback
    settings = get_settings()
    if not settings.stripe_secret_key:
        return PaymentMethodsListResponse(cards=[], default_payment_method_id=None)

    _init_stripe()
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        return PaymentMethodsListResponse(cards=[], default_payment_method_id=None)

    try:
        # Get the default payment method
        customer = stripe.Customer.retrieve(customer_id)
        default_pm_id = None
        inv_settings = customer.get("invoice_settings")
        if inv_settings:
            default_pm_id = inv_settings.get("default_payment_method")

        # List all cards
        pms = stripe.Customer.list_payment_methods(customer_id, type="card", limit=10)
        cards = []
        for pm in pms.data:
            card_data = pm.get("card", {})
            cards.append(PaymentMethodCardSummary(
                id=pm.id,
                brand=card_data.get("brand", "unknown"),
                last4=card_data.get("last4", "????"),
                exp_month=card_data.get("exp_month", 0),
                exp_year=card_data.get("exp_year", 0),
                is_default=pm.id == default_pm_id,
            ))

        # If no default was set but we have cards, mark the first as default
        if cards and not default_pm_id:
            cards[0].is_default = True
            default_pm_id = cards[0].id

        return PaymentMethodsListResponse(
            cards=cards,
            default_payment_method_id=default_pm_id,
        )
    except Exception as e:
        logger.warning("Failed to list payment methods: %s", e)
        return PaymentMethodsListResponse(cards=[], default_payment_method_id=None)


# ── POST /api/billing/set-default-card ───────────────────────────────────────

@router.post("/set-default-card")
def set_default_card(request: Request, body: SetDefaultCardRequest):
    """Set a payment method as the default for this customer."""
    sid, user = _require_user(request)

    # Dev/demo fallback
    settings = get_settings()
    if not settings.stripe_secret_key:
        set_session_user(sid, {**user, "default_payment_method_id": body.payment_method_id})
        return {"ok": True}

    _init_stripe()
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="No customer on file")

    try:
        stripe.Customer.modify(
            customer_id,
            invoice_settings={"default_payment_method": body.payment_method_id},
        )
        set_session_user(sid, {**user, "default_payment_method_id": body.payment_method_id})
        logger.info("Set default card %s for customer %s", body.payment_method_id, customer_id)
        return {"ok": True}
    except Exception as e:
        logger.warning("Failed to set default card: %s", e)
        raise HTTPException(status_code=400, detail=str(e))


# ── DELETE /api/billing/payment-method/{pm_id} ───────────────────────────────

@router.delete("/payment-method/{pm_id}")
def delete_payment_method(request: Request, pm_id: str):
    """Detach (remove) a saved payment method."""
    sid, user = _require_user(request)

    settings = get_settings()
    if not settings.stripe_secret_key:
        return {"ok": True}

    _init_stripe()
    try:
        stripe.PaymentMethod.detach(pm_id)
        logger.info("Detached payment method %s", pm_id)
        # If this was the default, clear it
        if user.get("default_payment_method_id") == pm_id:
            set_session_user(sid, {**user, "default_payment_method_id": None})
        return {"ok": True}
    except Exception as e:
        logger.warning("Failed to detach payment method %s: %s", pm_id, e)
        raise HTTPException(status_code=400, detail=str(e))


# ── POST /api/billing/setup-intent ──────────────────────────────────────────

@router.post("/setup-intent")
def create_setup_intent(request: Request):
    """Create a Stripe SetupIntent so the frontend can collect a card."""
    _init_stripe()
    settings = get_settings()
    sid, user = _require_user(request)

    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.get("email", ""),
            metadata={"user_id": user.get("id", "")},
        )
        customer_id = customer.id
        set_session_user(sid, {**user, "stripe_customer_id": customer_id})
        logger.info("Created Stripe customer %s for user %s", customer_id, user.get("id"))

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


# ── POST /api/billing/preview-change ────────────────────────────────────────

@router.post("/preview-change", response_model=PreviewChangeResponse)
def preview_plan_change(request: Request, body: PreviewChangeRequest):
    """Preview the proration cost of switching to a different plan.
    Uses Stripe Invoice.upcoming to compute the prorated amount.
    Falls back to flat monthly price when Stripe is not configured."""
    sid, user = _require_user(request)

    # ── Dev/demo fallback ─────────────────────────────────────────────────
    settings = get_settings()
    if not settings.stripe_secret_key:
        monthly = PLAN_MONTHLY_CENTS.get(body.plan, 0)
        return PreviewChangeResponse(
            amount_due_now=monthly,
            currency="eur",
            next_recurring_amount=monthly,
            next_renewal_date="",
            proration_line_items=[],
        )

    _init_stripe()

    if body.plan == "free":
        # Downgrading to free — no charge
        return PreviewChangeResponse(
            amount_due_now=0,
            currency="eur",
            next_recurring_amount=0,
            next_renewal_date="",
            proration_line_items=[],
        )

    customer_id = user.get("stripe_customer_id")
    sub_id = user.get("stripe_subscription_id")
    price_id = _get_price_id(body.plan)

    if not customer_id or not sub_id:
        # No existing subscription — full price, no proration
        monthly = PLAN_MONTHLY_CENTS.get(body.plan, 0)
        return PreviewChangeResponse(
            amount_due_now=monthly,
            currency="eur",
            next_recurring_amount=monthly,
            next_renewal_date="",
            proration_line_items=[],
        )

    try:
        # Retrieve current subscription to get the item id
        sub = stripe.Subscription.retrieve(sub_id)
        if sub.status not in ("active", "trialing"):
            monthly = PLAN_MONTHLY_CENTS.get(body.plan, 0)
            return PreviewChangeResponse(
                amount_due_now=monthly,
                currency="eur",
                next_recurring_amount=monthly,
                next_renewal_date="",
                proration_line_items=[],
            )

        sub_item_id = sub["items"]["data"][0]["id"]

        # Use Invoice.upcoming with subscription_items to preview proration
        upcoming = stripe.Invoice.upcoming(
            customer=customer_id,
            subscription=sub_id,
            subscription_items=[{
                "id": sub_item_id,
                "price": price_id,
            }],
            subscription_proration_date=int(datetime.now(timezone.utc).timestamp()),
        )

        # Extract line items that are proration-related
        proration_items: list[ProrationLineItem] = []
        for line in upcoming.get("lines", {}).get("data", []):
            if line.get("proration"):
                proration_items.append(ProrationLineItem(
                    description=line.get("description", ""),
                    amount=line.get("amount", 0),
                    currency=line.get("currency", "eur"),
                ))

        # Next recurring = the plan's monthly price
        next_recurring = PLAN_MONTHLY_CENTS.get(body.plan, 0)
        next_renewal = _ts_to_iso(sub.get("current_period_end")) or ""

        return PreviewChangeResponse(
            amount_due_now=upcoming.get("amount_due", 0),
            currency=upcoming.get("currency", "eur"),
            next_recurring_amount=next_recurring,
            next_renewal_date=next_renewal,
            proration_line_items=proration_items,
        )

    except stripe.InvalidRequestError as e:
        logger.warning("Preview proration failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e.user_message or e))
    except Exception as e:
        logger.warning("Preview proration error: %s", e)
        monthly = PLAN_MONTHLY_CENTS.get(body.plan, 0)
        return PreviewChangeResponse(
            amount_due_now=monthly,
            currency="eur",
            next_recurring_amount=monthly,
            next_renewal_date="",
            proration_line_items=[],
        )


# ── POST /api/billing/change-plan ───────────────────────────────────────────

@router.post("/change-plan", response_model=ChangePlanResponse)
def change_plan(request: Request, body: ChangePlanRequest):
    """Change the user's subscription plan with correct proration.
    - Upgrade: credit unused time on old plan, charge remaining time on new plan.
    - Downgrade to free: cancel subscription immediately.
    - If no subscription exists: create a new one.
    Returns 409 with code NO_PAYMENT_METHOD if no card is on file.
    Falls back to demo mode (in-memory only) when Stripe is not configured."""
    sid, user = _require_user(request)

    # ── Dev/demo fallback: just update session plan when Stripe isn't set up ──
    settings = get_settings()
    if not settings.stripe_secret_key:
        current_plan = user.get("plan", "free")
        set_session_user(sid, {**user, "plan": body.plan})
        logger.info("DEV MODE: Changed plan %s → %s (no Stripe)", current_plan, body.plan)
        return ChangePlanResponse(
            plan=body.plan,
            previous_plan=current_plan,
            subscription_id=None,
        )

    _init_stripe()

    current_plan = user.get("plan", "free")

    # ── Same plan → no-op ────────────────────────────────────────────────
    if body.plan == current_plan:
        return ChangePlanResponse(
            plan=current_plan,
            previous_plan=current_plan,
            subscription_id=user.get("stripe_subscription_id"),
        )

    # ── Downgrade to free → cancel subscription ──────────────────────────
    if body.plan == "free":
        sub_id = user.get("stripe_subscription_id")
        if sub_id:
            try:
                stripe.Subscription.cancel(sub_id)
                logger.info("Cancelled subscription %s (downgrade to free)", sub_id)
            except Exception as e:
                logger.warning("Failed to cancel subscription %s: %s", sub_id, e)
        set_session_user(sid, {**user, "plan": "free", "stripe_subscription_id": None})
        return ChangePlanResponse(
            plan="free",
            previous_plan=current_plan,
            subscription_id=None,
        )

    # ── Paid plan change (upgrade or cross-grade) ────────────────────────
    customer_id, default_pm = _ensure_customer_and_pm(sid, user)
    price_id = _get_price_id(body.plan)
    sub_id = user.get("stripe_subscription_id")

    # Try to modify existing active subscription
    if sub_id:
        try:
            existing_sub = stripe.Subscription.retrieve(sub_id)
            if existing_sub.status in ("active", "trialing"):
                sub_item_id = existing_sub["items"]["data"][0]["id"]
                sub = stripe.Subscription.modify(
                    sub_id,
                    items=[{"id": sub_item_id, "price": price_id}],
                    proration_behavior="create_prorations",
                    default_payment_method=default_pm,
                    cancel_at_period_end=False,
                    metadata={"user_id": user.get("id", ""), "session_id": sid},
                )
                logger.info("Changed plan %s → %s (sub=%s)", current_plan, body.plan, sub.id)

                # Try to pay any proration invoice immediately
                invoice_summary = _try_pay_proration_invoice(sub.get("latest_invoice"), customer_id)

                set_session_user(sid, {
                    **user,
                    "plan": body.plan,
                    "stripe_subscription_id": sub.id,
                })

                return ChangePlanResponse(
                    plan=body.plan,
                    previous_plan=current_plan,
                    subscription_id=sub.id,
                    current_period_end=_ts_to_iso(sub.get("current_period_end")),
                    invoice=invoice_summary,
                )
            else:
                # Subscription not active — cancel it and create new
                try:
                    stripe.Subscription.cancel(sub_id)
                except Exception:
                    pass
        except stripe.InvalidRequestError:
            logger.info("Previous subscription %s no longer exists", sub_id)
        except Exception as e:
            logger.warning("Failed to modify subscription: %s", e)

    # No active subscription — create a new one
    sub = stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": price_id}],
        default_payment_method=default_pm,
        metadata={"user_id": user.get("id", ""), "session_id": sid},
    )

    logger.info("Created subscription %s status=%s for plan=%s", sub.id, sub.status, body.plan)

    invoice_summary = _try_pay_proration_invoice(sub.get("latest_invoice"), customer_id)

    set_session_user(sid, {
        **user,
        "plan": body.plan,
        "stripe_subscription_id": sub.id,
    })

    return ChangePlanResponse(
        plan=body.plan,
        previous_plan=current_plan,
        subscription_id=sub.id,
        current_period_end=_ts_to_iso(sub.get("current_period_end")),
        invoice=invoice_summary,
    )


def _try_pay_proration_invoice(latest_invoice_id: str | None, customer_id: str) -> InvoiceSummary | None:
    """If the subscription has a pending proration invoice, try to pay it."""
    if not latest_invoice_id:
        return None
    try:
        inv = stripe.Invoice.retrieve(latest_invoice_id)
        if inv.status == "open" and inv.amount_due > 0:
            # Pay using the customer's default payment method
            inv = stripe.Invoice.pay(latest_invoice_id)
        return InvoiceSummary(
            amount_due=inv.get("amount_due", 0),
            currency=inv.get("currency", "eur"),
            paid=inv.get("paid", False),
            hosted_invoice_url=inv.get("hosted_invoice_url"),
        )
    except Exception as e:
        logger.warning("Failed to pay proration invoice %s: %s", latest_invoice_id, e)
        return None


# ── POST /api/billing/subscribe (kept for backward compat) ──────────────────

class SubscribeRequest(BaseModel):
    plan: str  # "plus" or "premium"


@router.post("/subscribe")
def subscribe(request: Request, body: SubscribeRequest):
    """Create or upgrade a Stripe Subscription for a paid plan using the saved card.
    Delegates to change-plan internally for consistency."""
    _init_stripe()
    sid, user = _require_user(request)

    if body.plan == "free":
        set_session_user(sid, {**user, "plan": "free"})
        return {"ok": True, "plan": "free", "subscription_id": None}

    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer. Save a card first.")

    default_pm = user.get("default_payment_method_id")
    if not default_pm:
        try:
            pms = stripe.Customer.list_payment_methods(customer_id, type="card", limit=1)
            if pms.data:
                default_pm = pms.data[0].id
                set_session_user(sid, {**user, "default_payment_method_id": default_pm})
        except Exception as e:
            logger.warning("Failed to fetch PMs from Stripe: %s", e)

    if not default_pm:
        raise HTTPException(status_code=400, detail="No default payment method; please add a card.")

    price_id = _get_price_id(body.plan)

    existing_sub_id = user.get("stripe_subscription_id")
    if existing_sub_id:
        try:
            existing_sub = stripe.Subscription.retrieve(existing_sub_id)
            if existing_sub.status in ("active", "trialing"):
                sub_item_id = existing_sub["items"]["data"][0]["id"]
                sub = stripe.Subscription.modify(
                    existing_sub_id,
                    items=[{"id": sub_item_id, "price": price_id}],
                    proration_behavior="create_prorations",
                    default_payment_method=default_pm,
                    metadata={"user_id": user.get("id", ""), "session_id": sid},
                )
                logger.info("Upgraded subscription %s to plan=%s", sub.id, body.plan)
                set_session_user(sid, {
                    **user,
                    "plan": body.plan,
                    "stripe_subscription_id": sub.id,
                })
                return {"ok": True, "plan": body.plan, "subscription_id": sub.id, "status": sub.status}
            else:
                try:
                    stripe.Subscription.cancel(existing_sub_id)
                except Exception:
                    pass
        except stripe.InvalidRequestError:
            pass
        except Exception as e:
            logger.warning("Failed to modify subscription: %s", e)

    sub = stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": price_id}],
        default_payment_method=default_pm,
        metadata={"user_id": user.get("id", ""), "session_id": sid},
    )

    set_session_user(sid, {
        **user,
        "plan": body.plan,
        "stripe_subscription_id": sub.id,
    })

    return {"ok": True, "plan": body.plan, "subscription_id": sub.id, "status": sub.status}


# ── POST /api/billing/cancel ─────────────────────────────────────────────────

@router.post("/cancel")
def cancel_subscription(request: Request):
    """Cancel the current Stripe subscription. User will be logged out by the frontend."""
    sid, user = _require_user(request)

    # Dev/demo fallback
    settings = get_settings()
    if not settings.stripe_secret_key:
        set_session_user(sid, {**user, "plan": "free", "stripe_subscription_id": None})
        logger.info("DEV MODE: Cancelled plan for session %s", sid)
        return {"ok": True, "plan": "free"}

    _init_stripe()

    sub_id = user.get("stripe_subscription_id")
    if not sub_id:
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
        user_id_meta = _uuid_or_none(metadata.get("user_id"))
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
        if user_id_meta and get_supabase_admin():
            try:
                sb_store.upsert_billing_customer(
                    user_id_meta,
                    stripe_customer_id=customer_id,
                    default_payment_method_id=payment_method,
                    has_card_on_file=True,
                )
            except Exception:
                pass

    # ── PaymentIntent succeeded (unified: gift, leak, mystery_box) ──────
    elif event_type == "payment_intent.succeeded":
        pi = event["data"]["object"]
        pi_id = pi.get("id", "")
        metadata = pi.get("metadata", {})
        payment_type = metadata.get("type", "")
        if payment_type:
            try:
                from app.api.routes.payments import finalize_payment_intent_for_webhook
                result = finalize_payment_intent_for_webhook(pi_id)
                logger.info(
                    "Webhook PI.succeeded: type=%s pi=%s result=%s",
                    payment_type, pi_id, result.get("status"),
                )
            except Exception as e:
                logger.warning("Webhook PI.succeeded fulfilment error: %s", e)
        else:
            logger.info("PaymentIntent succeeded (non-unified): pi=%s", pi_id)

    # ── Invoice paid (subscription payment succeeded) ────────────────────
    elif event_type == "invoice.paid":
        invoice = event["data"]["object"]
        customer_id = invoice.get("customer")
        sub_id = invoice.get("subscription")
        logger.info("Invoice paid: customer=%s subscription=%s amount=%s",
                     customer_id, sub_id, invoice.get("amount_paid"))

    # ── Invoice payment failed ───────────────────────────────────────────
    elif event_type == "invoice.payment_failed":
        invoice = event["data"]["object"]
        sub_id = invoice.get("subscription")
        logger.warning("Invoice payment failed: subscription=%s", sub_id)
        # Could notify user or mark subscription as past_due

    # ── Subscription created/updated ─────────────────────────────────────
    elif event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
    ):
        sub = event["data"]["object"]
        metadata = sub.get("metadata", {})
        session_id = metadata.get("session_id", "")
        user_id_meta = _uuid_or_none(metadata.get("user_id"))
        status = sub.get("status")
        logger.info("Subscription %s status=%s", sub.get("id"), status)

        if session_id and status in ("active", "trialing"):
            user = get_session_user(session_id)
            if user:
                items = sub.get("items", {}).get("data", [])
                plan = user.get("plan", "free")
                if items:
                    price_id = items[0].get("price", {}).get("id", "")
                    plan = _price_id_to_plan(price_id)
                set_session_user(session_id, {
                    **user,
                    "plan": plan,
                    "stripe_subscription_id": sub.get("id"),
                })
        if user_id_meta:
            try:
                items = sub.get("items", {}).get("data", [])
                plan = "free"
                if items:
                    price_id = items[0].get("price", {}).get("id", "")
                    plan = _price_id_to_plan(price_id)
                sb_store.upsert_subscription(
                    user_id=user_id_meta,
                    plan=plan if status in ("active", "trialing") else "free",
                    stripe_subscription_id=sub.get("id"),
                    status=status,
                    current_period_end=_ts_to_iso(sub.get("current_period_end")),
                )
            except Exception:
                pass

    # ── Subscription deleted ─────────────────────────────────────────────
    elif event_type == "customer.subscription.deleted":
        sub = event["data"]["object"]
        metadata = sub.get("metadata", {})
        session_id = metadata.get("session_id", "")
        user_id_meta = _uuid_or_none(metadata.get("user_id"))
        if session_id:
            user = get_session_user(session_id)
            if user:
                set_session_user(session_id, {
                    **user,
                    "plan": "free",
                    "stripe_subscription_id": None,
                })
                logger.info("Subscription cancelled, reverted to free")
        if user_id_meta:
            try:
                sb_store.upsert_subscription(
                    user_id=user_id_meta,
                    plan="free",
                    stripe_subscription_id=None,
                    status="canceled",
                    current_period_end=None,
                )
            except Exception:
                pass

    # ── Checkout session completed (gift purchases) ──────────────────────
    elif event_type == "checkout.session.completed":
        session_obj = event["data"]["object"]
        metadata = session_obj.get("metadata", {})
        gift_id = metadata.get("gift_id")
        if gift_id:
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
