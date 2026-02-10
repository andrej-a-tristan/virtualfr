"""
Trust & Intimacy Service — unified progression engine with region-capped banking.

Trust (1–100):   increases from conversation (slow, quality-gated, cooldowned) and gifts (tier-based).
Intimacy (1–100): increases ONLY from region milestones and gifts (constant boost). Chatting ≠ intimacy.

Gains go to the BANK first, then RELEASE into VISIBLE up to the current region cap.
This prevents "Trust 95 / Intimacy 80" while still in early regions, and keeps
purchases satisfying because the bank always increases.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from app.schemas.trust_intimacy import GainResult, TrustIntimacyState

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Trust
TRUST_MIN = 1
TRUST_MAX = 100
TRUST_COOLDOWN_SECONDS = 720  # 12 minutes
DAILY_TRUST_CAP_TOTAL = 6
DAILY_TRUST_CAP_GIFTS = 15
TRUST_GIFT_TIERS = {
    "everyday": 2,
    "dates": 4,
    "luxury": 7,
    "legendary": 10,
}
TRUST_DECAY_INACTIVITY_DAYS = 7
TRUST_DECAY_PER_DAY = 1
TRUST_DECAY_FLOOR = 10

# Intimacy
INTIMACY_MIN = 1
INTIMACY_MAX = 100
DAILY_INTIMACY_CAP_TOTAL = 8
DAILY_INTIMACY_CAP_GIFTS = 4
GIFT_INTIMACY_BOOST = 2


# ═══════════════════════════════════════════════════════════════════════════════
# REGION CAP TABLES
# ═══════════════════════════════════════════════════════════════════════════════

# region_key -> max visible intimacy at this region
INTIMACY_CAPS: dict[str, int] = {
    "EARLY_CONNECTION":       20,
    "COMFORT_FAMILIARITY":    28,
    "GROWING_CLOSENESS":      38,
    "EMOTIONAL_TRUST":        50,
    "DEEP_BOND":              62,
    "MUTUAL_DEVOTION":        72,
    "INTIMATE_PARTNERSHIP":   82,
    "SHARED_LIFE":            90,
    "ENDURING_COMPANIONSHIP": 100,
}

# region_key -> max visible trust at this region
TRUST_CAPS: dict[str, int] = {
    "EARLY_CONNECTION":       35,
    "COMFORT_FAMILIARITY":    45,
    "GROWING_CLOSENESS":      55,
    "EMOTIONAL_TRUST":        65,
    "DEEP_BOND":              75,
    "MUTUAL_DEVOTION":        83,
    "INTIMATE_PARTNERSHIP":   90,
    "SHARED_LIFE":            95,
    "ENDURING_COMPANIONSHIP": 100,
}


def get_intimacy_cap_for_region(region_key: str) -> int:
    """Return the max visible intimacy for a given region. Defaults to 100."""
    return INTIMACY_CAPS.get(region_key, 100)


def get_trust_cap_for_region(region_key: str) -> int:
    """Return the max visible trust for a given region. Defaults to 100."""
    return TRUST_CAPS.get(region_key, 100)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, val))


def _today_str(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m-%d")


def _reset_daily_if_needed(state: TrustIntimacyState, now: datetime | None = None) -> TrustIntimacyState:
    today = _today_str(now)
    if state.cap_date != today:
        state.trust_gained_today = 0
        state.intimacy_gained_today = 0
        state.intimacy_gained_today_gifts = 0
        state.trust_gained_today_gifts = 0
        state.cap_date = today
    return state


def region_reward(region_index: int) -> int:
    """Intimacy reward for reaching region at *region_index* (0-based). Range 2–6."""
    return _clamp(2 + region_index // 2, 2, 6)


# ═══════════════════════════════════════════════════════════════════════════════
# RELEASE MECHANISM — move banked → visible up to region cap
# ═══════════════════════════════════════════════════════════════════════════════

def release_banked(
    state: TrustIntimacyState,
    region_key: str,
) -> dict:
    """Move points from bank into visible up to the current region cap.

    Returns ``{"trust_released": int, "intimacy_released": int}``.
    Called after ANY award and after region changes.
    """
    trust_cap = get_trust_cap_for_region(region_key)
    intimacy_cap = get_intimacy_cap_for_region(region_key)

    # ── TRUST ─────────────────────────────────────────────────────────────
    trust_room = max(0, trust_cap - state.trust_visible)
    trust_release = min(trust_room, state.trust_bank)
    state.trust_visible = _clamp(state.trust_visible + trust_release, TRUST_MIN, TRUST_MAX)
    state.trust_bank = max(0, state.trust_bank - trust_release)

    # ── INTIMACY ──────────────────────────────────────────────────────────
    intimacy_room = max(0, intimacy_cap - state.intimacy_visible)
    intimacy_release = min(intimacy_room, state.intimacy_bank)
    state.intimacy_visible = _clamp(state.intimacy_visible + intimacy_release, INTIMACY_MIN, INTIMACY_MAX)
    state.intimacy_bank = max(0, state.intimacy_bank - intimacy_release)

    return {
        "trust_released": trust_release,
        "intimacy_released": intimacy_release,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# QUALITY SCORE (for conversation trust gain)
# ═══════════════════════════════════════════════════════════════════════════════

_SUPPORTIVE = frozenset([
    "love", "care", "proud", "glad", "appreciate", "thank", "miss",
    "support", "believe", "encourage", "hug", "kiss",
    "❤", "💕", "😊", "🥰", "💖",
])
_QUESTION_ABOUT_HER = frozenset([
    "how are you", "how do you feel", "what do you think",
    "tell me about", "what's on your mind", "how was your",
    "are you ok", "what matters to you",
])


def compute_quality_score(text: str) -> float:
    """Return 0.0–1.0 quality score for a user message."""
    if not text:
        return 0.0
    score = 0.0
    lower = text.lower()
    # Novelty — longer messages show effort
    if len(text) > 80:
        score += 0.4
    elif len(text) > 40:
        score += 0.2
    # Sentiment — supportive/affectionate phrases
    if any(tok in lower for tok in _SUPPORTIVE):
        score += 0.3
    # Effort — questions about her feelings/interests
    if any(phrase in lower for phrase in _QUESTION_ABOUT_HER):
        score += 0.3
    return min(1.0, score)


# ═══════════════════════════════════════════════════════════════════════════════
# TRUST GAIN — CONVERSATION  (bank-first)
# ═══════════════════════════════════════════════════════════════════════════════

def apply_conversation_trust_gain(
    state: TrustIntimacyState,
    message_text: str,
    now: datetime | None = None,
    region_key: str = "ENDURING_COMPANIONSHIP",
) -> tuple[TrustIntimacyState, GainResult]:
    """Award trust from a conversation message. Goes to bank first, then releases."""
    now = now or datetime.now(timezone.utc)
    state = _reset_daily_if_needed(state, now)
    trust_cap = get_trust_cap_for_region(region_key)

    # Cooldown check
    if state.trust_last_gain_at:
        elapsed = (now - state.trust_last_gain_at).total_seconds()
        if elapsed < TRUST_COOLDOWN_SECONDS:
            return state, GainResult(
                metric="trust", old_value=state.trust_visible, new_value=state.trust_visible,
                delta=0, reason="cooldown_active",
                message=f"Trust cooldown active ({int(TRUST_COOLDOWN_SECONDS - elapsed)}s remaining).",
                visible_new=state.trust_visible, bank_new=state.trust_bank, cap=trust_cap,
            )

    # Daily cap
    remaining = DAILY_TRUST_CAP_TOTAL - state.trust_gained_today
    if remaining <= 0:
        return state, GainResult(
            metric="trust", old_value=state.trust_visible, new_value=state.trust_visible,
            delta=0, reason="cap_reached",
            message="Daily trust cap reached.",
            visible_new=state.trust_visible, bank_new=state.trust_bank, cap=trust_cap,
        )

    # Compute delta
    quality = compute_quality_score(message_text)
    base_delta = round(2 * quality)  # 0, 1, or 2

    # Diminishing returns at high trust (visible)
    if state.trust_visible >= 85:
        base_delta = min(base_delta, 1)
    elif state.trust_visible >= 70:
        base_delta = math.floor(base_delta * 0.5)

    if base_delta <= 0:
        return state, GainResult(
            metric="trust", old_value=state.trust_visible, new_value=state.trust_visible,
            delta=0, reason="conversation",
            message="Message didn't contribute enough quality for trust.",
            visible_new=state.trust_visible, bank_new=state.trust_bank, cap=trust_cap,
        )

    earned = min(base_delta, remaining)
    old_visible = state.trust_visible

    # ── BANK FIRST ────────────────────────────────────────────────────────
    state.trust_bank += earned
    state.trust_gained_today += earned
    state.trust_last_gain_at = now

    # ── RELEASE ───────────────────────────────────────────────────────────
    released = release_banked(state, region_key)
    trust_released = released["trust_released"]

    return state, GainResult(
        metric="trust",
        old_value=old_visible,
        new_value=state.trust_visible,
        delta=earned,
        reason="conversation",
        message=f"Conversation: +{earned} trust." if earned > 0 else "No trust gained.",
        banked_delta=earned,
        released_delta=trust_released,
        visible_new=state.trust_visible,
        bank_new=state.trust_bank,
        cap=trust_cap,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TRUST GAIN — GIFT  (bank-first)
# ═══════════════════════════════════════════════════════════════════════════════

def award_trust_gift(
    state: TrustIntimacyState,
    gift_purchase_id: str,
    gift_tier: str,
    now: datetime | None = None,
    region_key: str = "ENDURING_COMPANIONSHIP",
) -> tuple[TrustIntimacyState, GainResult]:
    """Award trust for a gift purchase. Goes to bank first, then releases."""
    now = now or datetime.now(timezone.utc)
    state = _reset_daily_if_needed(state, now)
    trust_cap = get_trust_cap_for_region(region_key)

    if gift_purchase_id in state.used_gift_ids_trust:
        return state, GainResult(
            metric="trust", old_value=state.trust_visible, new_value=state.trust_visible,
            delta=0, reason="no_op_already_awarded",
            message=f"Trust already awarded for gift {gift_purchase_id}.",
            visible_new=state.trust_visible, bank_new=state.trust_bank, cap=trust_cap,
        )

    remaining_total = DAILY_TRUST_CAP_TOTAL - state.trust_gained_today
    remaining_gifts = DAILY_TRUST_CAP_GIFTS - state.trust_gained_today_gifts
    if remaining_total <= 0 or remaining_gifts <= 0:
        return state, GainResult(
            metric="trust", old_value=state.trust_visible, new_value=state.trust_visible,
            delta=0, reason="cap_reached",
            message="Daily trust cap reached.",
            visible_new=state.trust_visible, bank_new=state.trust_bank, cap=trust_cap,
        )

    boost = TRUST_GIFT_TIERS.get(gift_tier.lower(), 2)
    boost = min(boost, remaining_total, remaining_gifts)
    old_visible = state.trust_visible

    # ── BANK FIRST ────────────────────────────────────────────────────────
    state.trust_bank += boost
    state.trust_gained_today += boost
    state.trust_gained_today_gifts += boost
    state.used_gift_ids_trust.append(gift_purchase_id)
    state.trust_last_gain_at = now

    # ── RELEASE ───────────────────────────────────────────────────────────
    released = release_banked(state, region_key)
    trust_released = released["trust_released"]

    return state, GainResult(
        metric="trust",
        old_value=old_visible,
        new_value=state.trust_visible,
        delta=boost,
        reason="gift_purchase",
        message=f"Gift ({gift_tier}): +{boost} trust." if boost > 0 else "Trust at maximum.",
        banked_delta=boost,
        released_delta=trust_released,
        visible_new=state.trust_visible,
        bank_new=state.trust_bank,
        cap=trust_cap,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INTIMACY GAIN — REGION MILESTONE  (bank-first)
# ═══════════════════════════════════════════════════════════════════════════════

def award_intimacy_region(
    state: TrustIntimacyState,
    region_key: str,
    region_index: int = 0,
    now: datetime | None = None,
) -> tuple[TrustIntimacyState, GainResult]:
    """Award intimacy for reaching a NEW relationship region. Bank-first."""
    now = now or datetime.now(timezone.utc)
    state = _reset_daily_if_needed(state, now)
    intimacy_cap = get_intimacy_cap_for_region(region_key)

    if region_key in state.used_region_ids:
        return state, GainResult(
            metric="intimacy", old_value=state.intimacy_visible, new_value=state.intimacy_visible,
            delta=0, reason="no_op_already_awarded",
            message=f"Region {region_key} already awarded.",
            visible_new=state.intimacy_visible, bank_new=state.intimacy_bank, cap=intimacy_cap,
        )

    remaining = DAILY_INTIMACY_CAP_TOTAL - state.intimacy_gained_today
    if remaining <= 0:
        return state, GainResult(
            metric="intimacy", old_value=state.intimacy_visible, new_value=state.intimacy_visible,
            delta=0, reason="cap_reached",
            message="Daily intimacy cap reached.",
            visible_new=state.intimacy_visible, bank_new=state.intimacy_bank, cap=intimacy_cap,
        )

    reward = min(region_reward(region_index), remaining)
    old_visible = state.intimacy_visible

    # ── BANK FIRST ────────────────────────────────────────────────────────
    state.intimacy_bank += reward
    state.intimacy_gained_today += reward
    state.used_region_ids.append(region_key)
    state.intimacy_last_gain_at = now

    # ── RELEASE ───────────────────────────────────────────────────────────
    released = release_banked(state, region_key)
    intimacy_released = released["intimacy_released"]

    return state, GainResult(
        metric="intimacy",
        old_value=old_visible,
        new_value=state.intimacy_visible,
        delta=reward,
        reason="region_milestone",
        message=f"Reached {region_key}: +{reward} intimacy." if reward > 0 else "Intimacy at maximum.",
        banked_delta=reward,
        released_delta=intimacy_released,
        visible_new=state.intimacy_visible,
        bank_new=state.intimacy_bank,
        cap=intimacy_cap,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INTIMACY GAIN — GIFT  (bank-first)
# ═══════════════════════════════════════════════════════════════════════════════

def award_intimacy_gift(
    state: TrustIntimacyState,
    gift_purchase_id: str,
    now: datetime | None = None,
    region_key: str = "ENDURING_COMPANIONSHIP",
) -> tuple[TrustIntimacyState, GainResult]:
    """Award intimacy for a gift purchase. Bank-first."""
    now = now or datetime.now(timezone.utc)
    state = _reset_daily_if_needed(state, now)
    intimacy_cap = get_intimacy_cap_for_region(region_key)

    if gift_purchase_id in state.used_gift_ids_intimacy:
        return state, GainResult(
            metric="intimacy", old_value=state.intimacy_visible, new_value=state.intimacy_visible,
            delta=0, reason="no_op_already_awarded",
            message=f"Intimacy already awarded for gift {gift_purchase_id}.",
            visible_new=state.intimacy_visible, bank_new=state.intimacy_bank, cap=intimacy_cap,
        )

    remaining_total = DAILY_INTIMACY_CAP_TOTAL - state.intimacy_gained_today
    remaining_gifts = DAILY_INTIMACY_CAP_GIFTS - state.intimacy_gained_today_gifts
    if remaining_total <= 0 or remaining_gifts <= 0:
        return state, GainResult(
            metric="intimacy", old_value=state.intimacy_visible, new_value=state.intimacy_visible,
            delta=0, reason="cap_reached",
            message="Daily intimacy cap reached.",
            visible_new=state.intimacy_visible, bank_new=state.intimacy_bank, cap=intimacy_cap,
        )

    boost = min(GIFT_INTIMACY_BOOST, remaining_total, remaining_gifts)
    old_visible = state.intimacy_visible

    # ── BANK FIRST ────────────────────────────────────────────────────────
    state.intimacy_bank += boost
    state.intimacy_gained_today += boost
    state.intimacy_gained_today_gifts += boost
    state.used_gift_ids_intimacy.append(gift_purchase_id)
    state.intimacy_last_gain_at = now

    # ── RELEASE ───────────────────────────────────────────────────────────
    released = release_banked(state, region_key)
    intimacy_released = released["intimacy_released"]

    return state, GainResult(
        metric="intimacy",
        old_value=old_visible,
        new_value=state.intimacy_visible,
        delta=boost,
        reason="gift_purchase",
        message=f"Gift: +{boost} intimacy." if boost > 0 else "Intimacy at maximum.",
        banked_delta=boost,
        released_delta=intimacy_released,
        visible_new=state.intimacy_visible,
        bank_new=state.intimacy_bank,
        cap=intimacy_cap,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TRUST DECAY
# ═══════════════════════════════════════════════════════════════════════════════

def apply_trust_decay(
    state: TrustIntimacyState,
    hours_inactive: float,
) -> tuple[TrustIntimacyState, GainResult | None]:
    """Gentle trust decay after prolonged inactivity. Intimacy never decays.

    Decay hits VISIBLE only — bank is preserved.
    """
    threshold_hours = TRUST_DECAY_INACTIVITY_DAYS * 24
    if hours_inactive < threshold_hours:
        return state, None

    # How many full days past the threshold?
    days_past = int((hours_inactive - threshold_hours) / 24) + 1
    loss = min(days_past * TRUST_DECAY_PER_DAY, state.trust_visible - TRUST_DECAY_FLOOR)
    if loss <= 0:
        return state, None

    old = state.trust_visible
    state.trust_visible = _clamp(old - loss, TRUST_DECAY_FLOOR, TRUST_MAX)
    delta = state.trust_visible - old

    return state, GainResult(
        metric="trust", old_value=old, new_value=state.trust_visible,
        delta=delta, reason="decay",
        message=f"Trust decayed by {abs(delta)} after {int(hours_inactive / 24)} days away.",
        visible_new=state.trust_visible, bank_new=state.trust_bank,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PERSONALITY-BASED INTIMACY THRESHOLD (for image gating — unchanged)
# ═══════════════════════════════════════════════════════════════════════════════

def get_required_intimacy(traits: dict) -> int:
    """Required intimacy (1–100) to unlock sensitive content. Personality-driven."""
    base = 40
    pace = (traits.get("relationship_pace") or "").lower()
    if pace == "slow":
        base += 15
    elif pace == "fast":
        base -= 10
    comm = (traits.get("communication_style") or "").lower()
    if comm in ("reserved", "soft"):
        base += 5
    elif comm in ("teasing", "direct"):
        base -= 5
    emo = (traits.get("emotional_style") or "").lower()
    if emo == "reserved":
        base += 10
    elif emo == "playful":
        base -= 5
    return _clamp(base, 15, 85)
