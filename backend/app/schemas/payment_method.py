"""Payment method schemas for billing."""
from typing import Optional
from pydantic import BaseModel


class PaymentMethodCardSummary(BaseModel):
    brand: str
    last4: str
    exp_month: int
    exp_year: int


class PaymentMethodResponse(BaseModel):
    has_card: bool
    card: Optional[PaymentMethodCardSummary] = None
