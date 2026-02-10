"""Tests for the unified Trust & Intimacy service + descriptors."""
from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.trust_intimacy import TrustIntimacyState, GainResult
from app.services.trust_intimacy_service import (
    DAILY_INTIMACY_CAP_GIFTS,
    DAILY_INTIMACY_CAP_TOTAL,
    DAILY_TRUST_CAP_GIFTS,
    DAILY_TRUST_CAP_TOTAL,
    GIFT_INTIMACY_BOOST,
    INTIMACY_MAX,
    INTIMACY_MIN,
    TRUST_COOLDOWN_SECONDS,
    TRUST_DECAY_FLOOR,
    TRUST_DECAY_INACTIVITY_DAYS,
    TRUST_GIFT_TIERS,
    TRUST_MAX,
    TRUST_MIN,
    apply_conversation_trust_gain,
    apply_trust_decay,
    award_intimacy_gift,
    award_intimacy_region,
    award_trust_gift,
    compute_quality_score,
    region_reward,
    release_banked,
    get_trust_cap_for_region,
    get_intimacy_cap_for_region,
    TRUST_CAPS,
    INTIMACY_CAPS,
)
from app.services.relationship_descriptors import (
    get_descriptors,
    get_gain_micro_lines,
)


NOW = datetime(2026, 2, 3, 12, 0, 0, tzinfo=timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# TRUST — CLAMP & BASIC
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrustClamp:
    def test_trust_starts_at_20(self):
        s = TrustIntimacyState()
        assert s.trust == 20

    def test_intimacy_starts_at_1(self):
        s = TrustIntimacyState()
        assert s.intimacy == 1

    def test_trust_min_max(self):
        s = TrustIntimacyState(trust=1)
        assert s.trust >= TRUST_MIN
        s2 = TrustIntimacyState(trust=100)
        assert s2.trust <= TRUST_MAX

    def test_intimacy_min_max(self):
        s = TrustIntimacyState(intimacy=1)
        assert s.intimacy >= INTIMACY_MIN
        s2 = TrustIntimacyState(intimacy=100)
        assert s2.intimacy <= INTIMACY_MAX


# ═══════════════════════════════════════════════════════════════════════════════
# QUALITY SCORE
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityScore:
    def test_empty_message(self):
        assert compute_quality_score("") == 0.0

    def test_short_message(self):
        score = compute_quality_score("hi")
        assert score < 0.5

    def test_long_affectionate_message(self):
        msg = "I really love talking to you about how you feel. You make me so happy and I appreciate everything you do."
        score = compute_quality_score(msg)
        assert score >= 0.7

    def test_capped_at_1(self):
        msg = "I love you so much, how are you feeling today? Tell me about your thoughts and how do you feel about everything?"
        score = compute_quality_score(msg)
        assert score <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# CONVERSATION TRUST GAIN
# ═══════════════════════════════════════════════════════════════════════════════

class TestConversationTrust:
    def test_high_quality_message_gains_trust(self):
        s = TrustIntimacyState()
        msg = "I love how you feel about things. Tell me about your day, it really matters to me."
        s, result = apply_conversation_trust_gain(s, msg, NOW)
        assert result.reason == "conversation"
        assert result.delta > 0
        assert s.trust > 20

    def test_low_quality_no_gain(self):
        s = TrustIntimacyState()
        s, result = apply_conversation_trust_gain(s, "k", NOW)
        assert result.delta == 0

    def test_cooldown_blocks_second_gain(self):
        s = TrustIntimacyState()
        msg = "I love how you feel about things. Tell me about your day, it really matters to me."
        s, r1 = apply_conversation_trust_gain(s, msg, NOW)
        assert r1.delta > 0
        # Second gain within cooldown
        later = NOW + timedelta(seconds=60)
        s, r2 = apply_conversation_trust_gain(s, msg, later)
        assert r2.delta == 0
        assert r2.reason == "cooldown_active"

    def test_cooldown_expires(self):
        s = TrustIntimacyState()
        msg = "I love how you feel about things. Tell me about your day, it really matters to me."
        s, r1 = apply_conversation_trust_gain(s, msg, NOW)
        assert r1.delta > 0
        # After cooldown
        later = NOW + timedelta(seconds=TRUST_COOLDOWN_SECONDS + 1)
        s, r2 = apply_conversation_trust_gain(s, msg, later)
        assert r2.delta > 0

    def test_daily_cap_enforced(self):
        s = TrustIntimacyState(
            trust_gained_today=DAILY_TRUST_CAP_TOTAL,
            cap_date=NOW.strftime("%Y-%m-%d"),
        )
        msg = "I love how you feel about things."
        s, result = apply_conversation_trust_gain(s, msg, NOW)
        assert result.delta == 0
        assert result.reason == "cap_reached"

    def test_diminishing_returns_at_high_trust(self):
        s = TrustIntimacyState(trust=86)
        msg = "I love how you feel about things. Tell me about your day, it really matters to me."
        s, r = apply_conversation_trust_gain(s, msg, NOW)
        # At trust >= 85, delta capped at 1
        assert r.delta <= 1


# ═══════════════════════════════════════════════════════════════════════════════
# TRUST GIFT AWARDS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrustGift:
    def test_everyday_gift(self):
        s = TrustIntimacyState()
        s, r = award_trust_gift(s, "purchase_1", "everyday", NOW)
        assert r.delta == TRUST_GIFT_TIERS["everyday"]
        assert "purchase_1" in s.used_gift_ids_trust

    def test_legendary_gift(self):
        s = TrustIntimacyState()
        s, r = award_trust_gift(s, "purchase_2", "legendary", NOW)
        assert r.delta == min(TRUST_GIFT_TIERS["legendary"], DAILY_TRUST_CAP_TOTAL)

    def test_duplicate_gift_no_op(self):
        s = TrustIntimacyState(used_gift_ids_trust=["purchase_1"])
        s, r = award_trust_gift(s, "purchase_1", "everyday", NOW)
        assert r.delta == 0
        assert r.reason == "no_op_already_awarded"

    def test_daily_cap(self):
        s = TrustIntimacyState(
            trust_gained_today=DAILY_TRUST_CAP_TOTAL,
            cap_date=NOW.strftime("%Y-%m-%d"),
        )
        s, r = award_trust_gift(s, "new_gift", "luxury", NOW)
        assert r.delta == 0
        assert r.reason == "cap_reached"


# ═══════════════════════════════════════════════════════════════════════════════
# INTIMACY REGION AWARDS
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntimacyRegion:
    def test_first_region_succeeds(self):
        s = TrustIntimacyState()
        s, r = award_intimacy_region(s, "EARLY_CONNECTION", 0, NOW)
        assert r.delta == 2
        assert r.reason == "region_milestone"
        assert "EARLY_CONNECTION" in s.used_region_ids

    def test_duplicate_region_no_op(self):
        s = TrustIntimacyState(used_region_ids=["EARLY_CONNECTION"])
        s, r = award_intimacy_region(s, "EARLY_CONNECTION", 0, NOW)
        assert r.delta == 0
        assert r.reason == "no_op_already_awarded"

    def test_late_region_higher_reward(self):
        s = TrustIntimacyState()
        s, r = award_intimacy_region(s, "ENDURING_COMPANIONSHIP", 8, NOW)
        assert r.delta == 6  # region_reward(8) = 6


# ═══════════════════════════════════════════════════════════════════════════════
# INTIMACY GIFT AWARDS
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntimacyGift:
    def test_gift_gives_constant_boost(self):
        s = TrustIntimacyState()
        s, r = award_intimacy_gift(s, "gift_a", NOW)
        assert r.delta == GIFT_INTIMACY_BOOST

    def test_duplicate_no_op(self):
        s = TrustIntimacyState(used_gift_ids_intimacy=["gift_a"])
        s, r = award_intimacy_gift(s, "gift_a", NOW)
        assert r.delta == 0

    def test_daily_gift_cap(self):
        s = TrustIntimacyState(
            intimacy_gained_today_gifts=DAILY_INTIMACY_CAP_GIFTS,
            cap_date=NOW.strftime("%Y-%m-%d"),
        )
        s, r = award_intimacy_gift(s, "new_gift", NOW)
        assert r.delta == 0
        assert r.reason == "cap_reached"


# ═══════════════════════════════════════════════════════════════════════════════
# TRUST DECAY
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrustDecay:
    def test_no_decay_within_threshold(self):
        s = TrustIntimacyState(trust=50)
        s, result = apply_trust_decay(s, hours_inactive=48)
        assert result is None

    def test_decay_after_threshold(self):
        s = TrustIntimacyState(trust=50)
        hours = TRUST_DECAY_INACTIVITY_DAYS * 24 + 24
        s, result = apply_trust_decay(s, hours_inactive=hours)
        assert result is not None
        assert result.delta < 0
        assert s.trust < 50

    def test_decay_floor(self):
        s = TrustIntimacyState(trust=TRUST_DECAY_FLOOR)
        hours = TRUST_DECAY_INACTIVITY_DAYS * 24 + 240
        s, result = apply_trust_decay(s, hours_inactive=hours)
        assert result is None  # already at floor


# ═══════════════════════════════════════════════════════════════════════════════
# DESCRIPTORS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDescriptors:
    def test_low_trust_label(self):
        d = get_descriptors(5, 1)
        assert d.trust.label == "Guarded"

    def test_high_trust_label(self):
        d = get_descriptors(96, 80)
        assert d.trust.label == "Absolute"

    def test_near_max_trust_label(self):
        d = get_descriptors(93, 80)
        assert d.trust.label == "Unconditional"

    def test_every_trust_value_has_label(self):
        """Every integer 1–100 produces a non-empty label."""
        for t in range(1, 101):
            d = get_descriptors(t, 1)
            assert d.trust.label
            assert d.trust.micro_line
            assert "(Trust" in d.trust.micro_line

    def test_every_intimacy_value_has_label(self):
        for i in range(1, 101):
            d = get_descriptors(20, i)
            assert d.intimacy.label
            assert d.intimacy.micro_line
            assert "(Intimacy" in d.intimacy.micro_line

    def test_prompt_context_not_empty(self):
        d = get_descriptors(50, 50)
        assert d.prompt_context
        assert "Trust=" in d.prompt_context
        assert "Intimacy=" in d.prompt_context

    def test_tone_rules_scale_with_trust(self):
        d_low = get_descriptors(10, 10)
        d_high = get_descriptors(90, 80)
        assert d_high.trust.tone_rules.warmth > d_low.trust.tone_rules.warmth
        assert d_high.trust.tone_rules.vulnerability > d_low.trust.tone_rules.vulnerability

    def test_emoji_rate_increases(self):
        d_low = get_descriptors(10, 1)
        d_high = get_descriptors(80, 50)
        assert d_high.trust.tone_rules.emoji_rate > d_low.trust.tone_rules.emoji_rate

    def test_gain_micro_lines(self):
        lines = get_gain_micro_lines(2, 30, 3, 15)
        assert "trust_micro_line" in lines
        assert "intimacy_micro_line" in lines
        assert "trust_label" in lines

    def test_gain_micro_lines_zero_delta(self):
        lines = get_gain_micro_lines(0, 30, 0, 15)
        assert "trust_micro_line" not in lines
        assert "intimacy_micro_line" not in lines

    def test_deterministic(self):
        """Same inputs always give same outputs."""
        d1 = get_descriptors(42, 37)
        d2 = get_descriptors(42, 37)
        assert d1.trust.label == d2.trust.label
        assert d1.trust.micro_line == d2.trust.micro_line
        assert d1.intimacy.micro_line == d2.intimacy.micro_line
        assert d1.prompt_context == d2.prompt_context


# ═══════════════════════════════════════════════════════════════════════════════
# REGION REWARD
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegionReward:
    def test_early(self):
        assert region_reward(0) == 2

    def test_mid(self):
        assert region_reward(4) == 4

    def test_late(self):
        assert region_reward(8) == 6

    def test_clamped(self):
        assert region_reward(100) == 6


# ═══════════════════════════════════════════════════════════════════════════════
# RELATIONSHIP GAIN EVENT EMITTED WHEN DELTA > 0
# ═══════════════════════════════════════════════════════════════════════════════

class TestGainEventEmission:
    """Integration-level: verify that gain results have delta > 0 when they should."""

    def test_trust_gain_has_positive_delta(self):
        s = TrustIntimacyState()
        msg = "I love how you feel about things. Tell me about your day, it really matters to me."
        s, r = apply_conversation_trust_gain(s, msg, NOW)
        assert r.delta > 0

    def test_region_gain_has_positive_delta(self):
        s = TrustIntimacyState()
        s, r = award_intimacy_region(s, "DEEP_BOND", 4, NOW)
        assert r.delta > 0

    def test_gift_gains_both(self):
        s = TrustIntimacyState()
        s, r1 = award_trust_gift(s, "p1", "dates", NOW)
        s, r2 = award_intimacy_gift(s, "p1", NOW)
        assert r1.delta > 0
        assert r2.delta > 0


# ═══════════════════════════════════════════════════════════════════════════════
# REGION CAP TABLES
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegionCaps:
    def test_intimacy_caps_defined_for_all_regions(self):
        expected = [
            "EARLY_CONNECTION", "COMFORT_FAMILIARITY", "GROWING_CLOSENESS",
            "EMOTIONAL_TRUST", "DEEP_BOND", "MUTUAL_DEVOTION",
            "INTIMATE_PARTNERSHIP", "SHARED_LIFE", "ENDURING_COMPANIONSHIP",
        ]
        for key in expected:
            assert get_intimacy_cap_for_region(key) <= 100
            assert get_intimacy_cap_for_region(key) >= 1

    def test_trust_caps_defined_for_all_regions(self):
        expected = [
            "EARLY_CONNECTION", "COMFORT_FAMILIARITY", "GROWING_CLOSENESS",
            "EMOTIONAL_TRUST", "DEEP_BOND", "MUTUAL_DEVOTION",
            "INTIMATE_PARTNERSHIP", "SHARED_LIFE", "ENDURING_COMPANIONSHIP",
        ]
        for key in expected:
            assert get_trust_cap_for_region(key) <= 100
            assert get_trust_cap_for_region(key) >= 1

    def test_caps_monotonically_increase(self):
        regions = [
            "EARLY_CONNECTION", "COMFORT_FAMILIARITY", "GROWING_CLOSENESS",
            "EMOTIONAL_TRUST", "DEEP_BOND", "MUTUAL_DEVOTION",
            "INTIMATE_PARTNERSHIP", "SHARED_LIFE", "ENDURING_COMPANIONSHIP",
        ]
        for i in range(1, len(regions)):
            assert get_intimacy_cap_for_region(regions[i]) >= get_intimacy_cap_for_region(regions[i - 1])
            assert get_trust_cap_for_region(regions[i]) >= get_trust_cap_for_region(regions[i - 1])

    def test_last_region_caps_at_100(self):
        assert get_intimacy_cap_for_region("ENDURING_COMPANIONSHIP") == 100
        assert get_trust_cap_for_region("ENDURING_COMPANIONSHIP") == 100

    def test_unknown_region_defaults_to_100(self):
        assert get_intimacy_cap_for_region("NONEXISTENT") == 100
        assert get_trust_cap_for_region("NONEXISTENT") == 100

    def test_exact_intimacy_cap_values(self):
        assert get_intimacy_cap_for_region("EARLY_CONNECTION") == 20
        assert get_intimacy_cap_for_region("COMFORT_FAMILIARITY") == 28
        assert get_intimacy_cap_for_region("GROWING_CLOSENESS") == 38
        assert get_intimacy_cap_for_region("EMOTIONAL_TRUST") == 50
        assert get_intimacy_cap_for_region("DEEP_BOND") == 62
        assert get_intimacy_cap_for_region("MUTUAL_DEVOTION") == 72
        assert get_intimacy_cap_for_region("INTIMATE_PARTNERSHIP") == 82
        assert get_intimacy_cap_for_region("SHARED_LIFE") == 90
        assert get_intimacy_cap_for_region("ENDURING_COMPANIONSHIP") == 100

    def test_exact_trust_cap_values(self):
        assert get_trust_cap_for_region("EARLY_CONNECTION") == 35
        assert get_trust_cap_for_region("COMFORT_FAMILIARITY") == 45
        assert get_trust_cap_for_region("GROWING_CLOSENESS") == 55
        assert get_trust_cap_for_region("EMOTIONAL_TRUST") == 65
        assert get_trust_cap_for_region("DEEP_BOND") == 75
        assert get_trust_cap_for_region("MUTUAL_DEVOTION") == 83
        assert get_trust_cap_for_region("INTIMATE_PARTNERSHIP") == 90
        assert get_trust_cap_for_region("SHARED_LIFE") == 95
        assert get_trust_cap_for_region("ENDURING_COMPANIONSHIP") == 100


# ═══════════════════════════════════════════════════════════════════════════════
# RELEASE MECHANISM
# ═══════════════════════════════════════════════════════════════════════════════

class TestReleaseBanked:
    def test_release_when_room_available(self):
        s = TrustIntimacyState(trust_visible=10, trust_bank=5, intimacy_visible=5, intimacy_bank=3)
        released = release_banked(s, "EARLY_CONNECTION")  # caps: trust=35, intimacy=20
        assert released["trust_released"] == 5
        assert s.trust_visible == 15
        assert s.trust_bank == 0
        assert released["intimacy_released"] == 3
        assert s.intimacy_visible == 8
        assert s.intimacy_bank == 0

    def test_release_capped_at_region(self):
        s = TrustIntimacyState(trust_visible=30, trust_bank=20, intimacy_visible=15, intimacy_bank=30)
        released = release_banked(s, "EARLY_CONNECTION")  # caps: trust=35, intimacy=20
        assert released["trust_released"] == 5  # only room for 5 (35 - 30)
        assert s.trust_visible == 35
        assert s.trust_bank == 15  # 20 - 5 = 15 remaining
        assert released["intimacy_released"] == 5  # only room for 5 (20 - 15)
        assert s.intimacy_visible == 20
        assert s.intimacy_bank == 25  # 30 - 5 = 25 remaining

    def test_release_nothing_when_at_cap(self):
        s = TrustIntimacyState(trust_visible=35, trust_bank=10, intimacy_visible=20, intimacy_bank=10)
        released = release_banked(s, "EARLY_CONNECTION")  # already at cap
        assert released["trust_released"] == 0
        assert released["intimacy_released"] == 0
        assert s.trust_bank == 10  # unchanged
        assert s.intimacy_bank == 10

    def test_release_nothing_when_bank_empty(self):
        s = TrustIntimacyState(trust_visible=10, trust_bank=0, intimacy_visible=5, intimacy_bank=0)
        released = release_banked(s, "EARLY_CONNECTION")
        assert released["trust_released"] == 0
        assert released["intimacy_released"] == 0

    def test_higher_region_releases_more(self):
        """Simulates a region transition: bank accumulated at low cap, then released at higher cap."""
        s = TrustIntimacyState(trust_visible=35, trust_bank=20, intimacy_visible=20, intimacy_bank=15)
        # At EARLY_CONNECTION cap, nothing releases
        r1 = release_banked(s, "EARLY_CONNECTION")
        assert r1["trust_released"] == 0
        assert r1["intimacy_released"] == 0
        # Region transition to COMFORT_FAMILIARITY (trust=45, intimacy=28)
        r2 = release_banked(s, "COMFORT_FAMILIARITY")
        assert r2["trust_released"] == 10  # 45 - 35
        assert s.trust_visible == 45
        assert s.trust_bank == 10  # 20 - 10
        assert r2["intimacy_released"] == 8  # 28 - 20
        assert s.intimacy_visible == 28
        assert s.intimacy_bank == 7  # 15 - 8


# ═══════════════════════════════════════════════════════════════════════════════
# BANK-FIRST AWARDS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBankFirstAwards:
    def test_gift_early_region_cap_low_bank_increases(self):
        """Gift in early region: visible stays at cap, bank increases."""
        # Start at the trust cap for EARLY_CONNECTION
        s = TrustIntimacyState(trust_visible=35, trust_bank=0, intimacy_visible=20, intimacy_bank=0)
        # Award a dates gift (+4 trust) — should go to bank, not visible (already at cap)
        s, r = award_trust_gift(s, "gift_1", "dates", NOW, region_key="EARLY_CONNECTION")
        assert r.delta == 4  # full earned delta
        assert r.banked_delta == 4
        assert r.released_delta == 0  # no room
        assert s.trust_visible == 35  # unchanged (at cap)
        assert s.trust_bank == 4  # all in bank

    def test_gift_intimacy_early_region_banks(self):
        """Intimacy gift in early region goes to bank when at cap."""
        s = TrustIntimacyState(intimacy_visible=20, intimacy_bank=0)
        s, r = award_intimacy_gift(s, "gift_i1", NOW, region_key="EARLY_CONNECTION")
        assert r.delta == GIFT_INTIMACY_BOOST
        assert r.banked_delta == GIFT_INTIMACY_BOOST
        assert r.released_delta == 0  # at cap 20
        assert s.intimacy_visible == 20
        assert s.intimacy_bank == GIFT_INTIMACY_BOOST

    def test_conversation_trust_banks_when_capped(self):
        """Conversation trust goes to bank when visible is at region cap."""
        s = TrustIntimacyState(trust_visible=35, trust_bank=0)
        msg = "I love how you feel about things. Tell me about your day, it really matters to me."
        s, r = apply_conversation_trust_gain(s, msg, NOW, region_key="EARLY_CONNECTION")
        assert r.delta > 0
        assert r.banked_delta == r.delta
        assert r.released_delta == 0
        assert s.trust_visible == 35  # unchanged
        assert s.trust_bank == r.delta

    def test_region_milestone_banks_when_capped(self):
        """Region milestone intimacy goes to bank, limited release."""
        # intimacy_visible=18, cap for EARLY_CONNECTION=20, region milestone gives +2
        s = TrustIntimacyState(intimacy_visible=18, intimacy_bank=0)
        s, r = award_intimacy_region(s, "EARLY_CONNECTION", 0, NOW)
        assert r.delta == 2
        assert r.banked_delta == 2
        assert r.released_delta == 2  # room for 2 (20 - 18)
        assert s.intimacy_visible == 20
        assert s.intimacy_bank == 0

    def test_region_milestone_partially_banks(self):
        """Region milestone partially banks when visible is near cap."""
        # intimacy_visible=19, cap for EARLY_CONNECTION=20, milestone gives +2
        s = TrustIntimacyState(intimacy_visible=19, intimacy_bank=0)
        s, r = award_intimacy_region(s, "EARLY_CONNECTION", 0, NOW)
        assert r.delta == 2
        assert r.banked_delta == 2
        assert r.released_delta == 1  # only room for 1
        assert s.intimacy_visible == 20
        assert s.intimacy_bank == 1  # 1 remains banked

    def test_region_transition_releases_bank(self):
        """Transitioning to a higher region releases previously banked points."""
        s = TrustIntimacyState(
            trust_visible=35, trust_bank=12,
            intimacy_visible=20, intimacy_bank=8,
        )
        # Region change to COMFORT_FAMILIARITY (trust=45, intimacy=28)
        released = release_banked(s, "COMFORT_FAMILIARITY")
        assert released["trust_released"] == 10  # 45 - 35
        assert s.trust_visible == 45
        assert s.trust_bank == 2  # 12 - 10
        assert released["intimacy_released"] == 8  # 28 - 20
        assert s.intimacy_visible == 28
        assert s.intimacy_bank == 0  # fully released

    def test_sensitive_gating_uses_visible_only(self):
        """Verify that banked intimacy does not count toward required intimacy threshold."""
        s = TrustIntimacyState(intimacy_visible=15, intimacy_bank=50)
        # Even though total earned = 65, only visible (15) matters for gating
        assert s.intimacy == 15  # property alias
        assert s.intimacy_visible == 15
        assert s.intimacy_bank == 50

    def test_conversation_trust_partial_release(self):
        """Conversation trust with room below cap: some is released, rest banked."""
        # trust_visible=33, cap=35, earning 2 → 2 goes to bank, 2 released from bank
        s = TrustIntimacyState(trust_visible=33, trust_bank=0)
        msg = "I love how you feel about things. Tell me about your day, it really matters to me."
        s, r = apply_conversation_trust_gain(s, msg, NOW, region_key="EARLY_CONNECTION")
        assert r.delta > 0
        assert r.released_delta == min(r.delta, 2)  # at most 2 room
        assert s.trust_visible <= 35

    def test_gain_result_includes_cap(self):
        """GainResult includes the current region cap."""
        s = TrustIntimacyState()
        s, r = award_trust_gift(s, "p_cap_test", "everyday", NOW, region_key="GROWING_CLOSENESS")
        assert r.cap == 55  # trust cap for GROWING_CLOSENESS

    def test_gift_always_counts_even_when_capped(self):
        """Even if visible is capped, bank MUST still increase so purchase always 'counts'."""
        s = TrustIntimacyState(trust_visible=35, trust_bank=100)
        s, r = award_trust_gift(s, "gift_always_counts", "luxury", NOW, region_key="EARLY_CONNECTION")
        assert r.delta > 0  # earned something
        assert s.trust_bank == 100 + r.delta  # bank increased
        assert s.trust_visible == 35  # visible unchanged (at cap)

    def test_descriptor_engine_uses_visible(self):
        """Descriptor engine receives visible values (not bank)."""
        from app.services.relationship_descriptors import get_descriptors
        s = TrustIntimacyState(trust_visible=20, trust_bank=50, intimacy_visible=5, intimacy_bank=30)
        d = get_descriptors(s.trust, s.intimacy)
        # trust=20 is in the "Cautious" range, not in a higher range
        assert d.trust.label != "Absolute"  # would be if bank counted

    def test_decay_only_affects_visible(self):
        """Trust decay only reduces visible, bank is preserved."""
        s = TrustIntimacyState(trust_visible=50, trust_bank=20)
        hours = TRUST_DECAY_INACTIVITY_DAYS * 24 + 24
        s, result = apply_trust_decay(s, hours_inactive=hours)
        assert result is not None
        assert result.delta < 0
        assert s.trust_visible < 50
        assert s.trust_bank == 20  # preserved

    def test_backward_compat_constructor(self):
        """Legacy constructor TrustIntimacyState(trust=X) still works."""
        s = TrustIntimacyState(trust=50, intimacy=30)
        assert s.trust_visible == 50
        assert s.intimacy_visible == 30
        assert s.trust == 50
        assert s.intimacy == 30

    def test_backward_compat_setter(self):
        """Legacy setter state.trust = X forwards to trust_visible."""
        s = TrustIntimacyState()
        s.trust = 60
        assert s.trust_visible == 60
        s.intimacy = 40
        assert s.intimacy_visible == 40
