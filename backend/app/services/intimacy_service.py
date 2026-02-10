"""
Intimacy Index Service.

Intimacy (1–100) increases ONLY via:
  A) Reaching a NEW relationship region  (region milestone)
  B) Successful gift purchases           (constant boost per gift)

Chatting alone does NOT increase intimacy.
Gifts give a CONSTANT boost (not personality-dependent).
Personality determines REQUIRED intimacy thresholds for sensitive image unlocks.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from app.schemas.intimacy import IntimacyAwardResult, IntimacyState

# ── Constants ─────────────────────────────────────────────────────────────────

INTIMACY_MIN = 1
INTIMACY_MAX = 100
DAILY_INTIMACY_CAP_TOTAL = 8   # max total intimacy increase per day
DAILY_INTIMACY_CAP_GIFTS = 4   # max intimacy from gifts per day
GIFT_INTIMACY_BOOST = 2        # constant per gift


def region_reward(region_index: int) -> int:
    """Compute intimacy reward for reaching region at *region_index* (0-based).

    early regions → +2, mid → +3/+4, late → +5/+6.
    Formula: clamp(2 + floor(index / 2), 2, 6)
    """
    return max(2, min(6, 2 + region_index // 2))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clamp_intimacy(val: int) -> int:
    return max(INTIMACY_MIN, min(INTIMACY_MAX, val))


def _today_str(now: datetime | None = None) -> str:
    dt = now or datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%d")


def _reset_daily_if_needed(state: IntimacyState, now: datetime | None = None) -> IntimacyState:
    """Reset daily counters if the date has changed."""
    today = _today_str(now)
    if state.gained_today_date != today:
        state.gained_today_total = 0
        state.gained_today_gifts = 0
        state.gained_today_date = today
    return state


# ── Core award functions ──────────────────────────────────────────────────────

def award_region_milestone(
    state: IntimacyState,
    region_key: str,
    region_index: int = 0,
    now: datetime | None = None,
) -> tuple[IntimacyState, IntimacyAwardResult]:
    """Award intimacy for reaching a NEW relationship region.

    Returns (updated_state, result).  No-ops if region already awarded.
    """
    now = now or datetime.now(timezone.utc)
    state = _reset_daily_if_needed(state, now)

    # Already awarded this region?
    if region_key in state.used_region_ids:
        return state, IntimacyAwardResult(
            new_intimacy_index=state.intimacy_index,
            delta=0,
            reason="no_op_already_awarded",
            message=f"Region {region_key} already awarded.",
        )

    # Daily cap check
    reward = region_reward(region_index)
    remaining_today = DAILY_INTIMACY_CAP_TOTAL - state.gained_today_total
    if remaining_today <= 0:
        return state, IntimacyAwardResult(
            new_intimacy_index=state.intimacy_index,
            delta=0,
            reason="cap_reached",
            message="Daily intimacy cap reached.",
        )
    reward = min(reward, remaining_today)

    # Clamp to max
    old = state.intimacy_index
    new_val = _clamp_intimacy(old + reward)
    delta = new_val - old

    if delta == 0:
        return state, IntimacyAwardResult(
            new_intimacy_index=new_val,
            delta=0,
            reason="cap_reached",
            message="Intimacy already at maximum.",
        )

    # Apply
    state.intimacy_index = new_val
    state.gained_today_total += delta
    state.used_region_ids.append(region_key)
    state.last_increase_at = now

    return state, IntimacyAwardResult(
        new_intimacy_index=new_val,
        delta=delta,
        reason="region_milestone",
        message=f"Reached {region_key}: +{delta} intimacy.",
    )


def award_gift_purchase(
    state: IntimacyState,
    gift_id: str,
    now: datetime | None = None,
) -> tuple[IntimacyState, IntimacyAwardResult]:
    """Award intimacy for a successful gift purchase.

    Returns (updated_state, result).  No-ops if same gift_id already awarded.
    """
    now = now or datetime.now(timezone.utc)
    state = _reset_daily_if_needed(state, now)

    # Same gift already awarded?
    if gift_id in state.used_gift_ids:
        return state, IntimacyAwardResult(
            new_intimacy_index=state.intimacy_index,
            delta=0,
            reason="no_op_already_awarded",
            message=f"Gift {gift_id} already awarded.",
        )

    # Daily caps
    remaining_total = DAILY_INTIMACY_CAP_TOTAL - state.gained_today_total
    remaining_gifts = DAILY_INTIMACY_CAP_GIFTS - state.gained_today_gifts
    if remaining_total <= 0 or remaining_gifts <= 0:
        return state, IntimacyAwardResult(
            new_intimacy_index=state.intimacy_index,
            delta=0,
            reason="cap_reached",
            message="Daily intimacy cap reached.",
        )

    boost = min(GIFT_INTIMACY_BOOST, remaining_total, remaining_gifts)

    old = state.intimacy_index
    new_val = _clamp_intimacy(old + boost)
    delta = new_val - old

    if delta == 0:
        return state, IntimacyAwardResult(
            new_intimacy_index=new_val,
            delta=0,
            reason="cap_reached",
            message="Intimacy already at maximum.",
        )

    state.intimacy_index = new_val
    state.gained_today_total += delta
    state.gained_today_gifts += delta
    state.used_gift_ids.append(gift_id)
    state.last_increase_at = now

    return state, IntimacyAwardResult(
        new_intimacy_index=new_val,
        delta=delta,
        reason="gift_purchase",
        message=f"Gift received: +{delta} intimacy.",
    )


# ── Personality-based intimacy threshold for sensitive images ─────────────────

def get_required_intimacy(traits: dict) -> int:
    """Return required intimacy_index (1–100) to unlock sensitive/nude content.

    Based on personality traits — more reserved / slower pace → higher threshold.
    """
    base = 40  # default threshold

    # Relationship pace
    pace = (traits.get("relationship_pace") or "").lower()
    if pace == "slow":
        base += 15
    elif pace == "fast":
        base -= 10

    # Communication style
    comm = (traits.get("communication_style") or "").lower()
    if comm == "reserved" or comm == "soft":
        base += 5
    elif comm == "teasing" or comm == "direct":
        base -= 5

    # Emotional style
    emo = (traits.get("emotional_style") or "").lower()
    if emo == "reserved":
        base += 10
    elif emo == "playful":
        base -= 5

    return max(15, min(85, base))
