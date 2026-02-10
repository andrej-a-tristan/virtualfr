"""Trust & Intimacy unified state schemas (1–100 each).

The visible/bank split keeps trust/intimacy capped per relationship region:
  - Gains go to the BANK first.
  - The RELEASE step moves banked points into VISIBLE up to the region cap.
  - ``trust`` and ``intimacy`` are kept as aliases for the *visible* values
    for backward compatibility with all existing code.
"""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class TrustIntimacyState(BaseModel):
    """Persistent per (session, girlfriend) trust + intimacy state."""

    # ── Visible values (shown on meters, used for gating) ────────────────
    trust_visible: int = Field(default=20, ge=1, le=100)
    intimacy_visible: int = Field(default=1, ge=1, le=100)

    # ── Banked overflow (earned but locked until region cap allows) ──────
    trust_bank: int = Field(default=0, ge=0)
    intimacy_bank: int = Field(default=0, ge=0)

    # ── Backward-compat: accept ``trust`` / ``intimacy`` in constructor ──
    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Map legacy ``trust`` → ``trust_visible``, ``intimacy`` → ``intimacy_visible``."""
        if isinstance(values, dict):
            if "trust" in values and "trust_visible" not in values:
                values["trust_visible"] = values.pop("trust")
            elif "trust" in values:
                values.pop("trust")  # remove duplicate
            if "intimacy" in values and "intimacy_visible" not in values:
                values["intimacy_visible"] = values.pop("intimacy")
            elif "intimacy" in values:
                values.pop("intimacy")  # remove duplicate
        return values

    # ── Backward-compat aliases (attribute access) ───────────────────────
    #    Many callers still read/write state.trust and state.intimacy.
    @property
    def trust(self) -> int:  # noqa: D401
        return self.trust_visible

    @trust.setter
    def trust(self, value: int) -> None:
        self.trust_visible = max(1, min(100, value))

    @property
    def intimacy(self) -> int:  # noqa: D401
        return self.intimacy_visible

    @intimacy.setter
    def intimacy(self, value: int) -> None:
        self.intimacy_visible = max(1, min(100, value))

    # ── Timestamps ───────────────────────────────────────────────────────
    trust_last_gain_at: Optional[datetime] = None
    intimacy_last_gain_at: Optional[datetime] = None

    # ── Daily cap tracking ───────────────────────────────────────────────
    trust_gained_today: int = 0
    intimacy_gained_today: int = 0
    intimacy_gained_today_gifts: int = 0
    trust_gained_today_gifts: int = 0
    cap_date: Optional[str] = None  # "YYYY-MM-DD"

    # ── Dedup lists ──────────────────────────────────────────────────────
    used_region_ids: List[str] = Field(default_factory=list)
    used_gift_ids_intimacy: List[str] = Field(default_factory=list)
    used_gift_ids_trust: List[str] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


class GainResult(BaseModel):
    """Result of any trust/intimacy award attempt."""
    metric: Literal["trust", "intimacy"]
    old_value: int
    new_value: int
    delta: int  # total earned (banked)
    reason: Literal[
        "conversation",
        "gift_purchase",
        "region_milestone",
        "no_op_already_awarded",
        "cooldown_active",
        "cap_reached",
        "decay",
        "release",
    ]
    message: str

    # ── Bank / release breakdown ─────────────────────────────────────────
    banked_delta: int = 0        # how much was added to the bank
    released_delta: int = 0      # how much was moved from bank → visible
    visible_new: int = 0         # visible after release
    bank_new: int = 0            # bank after release
    cap: int = 100               # current region cap for this metric
