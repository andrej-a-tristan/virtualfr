"""Billing Pydantic schemas for plan changes, proration previews, and status."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


Plan = Literal["free", "plus", "premium"]


# ── Requests ─────────────────────────────────────────────────────────────────

class ChangePlanRequest(BaseModel):
    plan: Plan


class PreviewChangeRequest(BaseModel):
    plan: Plan


# ── Responses ────────────────────────────────────────────────────────────────

class ProrationLineItem(BaseModel):
    description: str
    amount: int  # cents
    currency: str


class InvoiceSummary(BaseModel):
    amount_due: int  # cents
    currency: str
    paid: bool
    hosted_invoice_url: str | None = None


class ChangePlanResponse(BaseModel):
    ok: bool = True
    plan: Plan
    previous_plan: Plan
    subscription_id: str | None = None
    current_period_end: str | None = None  # ISO timestamp
    invoice: InvoiceSummary | None = None


class PreviewChangeResponse(BaseModel):
    amount_due_now: int  # cents — what will be charged immediately (proration)
    currency: str
    next_recurring_amount: int  # cents — regular monthly charge on the new plan
    next_renewal_date: str  # ISO timestamp
    proration_line_items: list[ProrationLineItem] = []


class BillingStatusResponse(BaseModel):
    plan: Plan
    has_card_on_file: bool
    message_cap: int
    image_cap: int
    girls_max: int
    girls_count: int
    can_create_more_girls: bool
    current_period_end: str | None = None  # ISO timestamp of current billing period end
    next_renewal_date: str | None = None  # same as current_period_end
    next_invoice_amount: int | None = None  # cents, if available
    subscription_status: str | None = None  # "active", "canceled", etc.
