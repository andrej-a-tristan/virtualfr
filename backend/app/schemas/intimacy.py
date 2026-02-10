"""Intimacy Index schemas."""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class IntimacyState(BaseModel):
    """Persistent intimacy state per (session, girlfriend)."""
    intimacy_index: int = Field(default=1, ge=1, le=100)
    last_increase_at: Optional[datetime] = None
    used_region_ids: List[str] = Field(default_factory=list)
    used_gift_ids: List[str] = Field(default_factory=list)
    # Daily cap tracking
    gained_today_total: int = 0
    gained_today_gifts: int = 0
    gained_today_date: Optional[str] = None  # "YYYY-MM-DD"


class IntimacyAwardResult(BaseModel):
    """Result of an intimacy award attempt."""
    new_intimacy_index: int
    delta: int
    reason: Literal[
        "region_milestone",
        "gift_purchase",
        "no_op_already_awarded",
        "cap_reached",
    ]
    message: str
