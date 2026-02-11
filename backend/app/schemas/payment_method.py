"""Payment method schemas for billing."""
from typing import Optional
from pydantic import BaseModel


class PaymentMethodCardSummary(BaseModel):
    id: str  # Stripe payment method ID
    brand: str
    last4: str
    exp_month: int
    exp_year: int
    is_default: bool = False


class PaymentMethodResponse(BaseModel):
    has_card: bool
    card: Optional[PaymentMethodCardSummary] = None


class PaymentMethodsListResponse(BaseModel):
    cards: list[PaymentMethodCardSummary] = []
    default_payment_method_id: Optional[str] = None


class SetDefaultCardRequest(BaseModel):
    payment_method_id: str
