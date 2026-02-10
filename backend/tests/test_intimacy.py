"""Tests for Intimacy Index system."""
from datetime import datetime, timezone, timedelta

import pytest

from app.schemas.intimacy import IntimacyState
from app.services.intimacy_service import (
    DAILY_INTIMACY_CAP_GIFTS,
    DAILY_INTIMACY_CAP_TOTAL,
    GIFT_INTIMACY_BOOST,
    INTIMACY_MAX,
    INTIMACY_MIN,
    award_gift_purchase,
    award_region_milestone,
    get_required_intimacy,
    region_reward,
)
from app.services.image_decision_engine import (
    FREE_PLAN_BLURRED_INTIMACY,
    ImageDecision,
    decide_image_action,
    request_is_sensitive,
    should_send_blurred_surprise,
)


NOW = datetime(2026, 2, 3, 12, 0, 0, tzinfo=timezone.utc)


# ── Region reward formula ────────────────────────────────────────────────────

class TestRegionReward:
    def test_early_region_gives_2(self):
        assert region_reward(0) == 2
        assert region_reward(1) == 2

    def test_mid_region_gives_3_or_4(self):
        assert region_reward(4) == 4
        assert region_reward(5) == 4

    def test_late_region_gives_5_or_6(self):
        assert region_reward(8) == 6

    def test_clamped_at_6(self):
        assert region_reward(100) == 6


# ── Region milestone awards ──────────────────────────────────────────────────

class TestRegionMilestone:
    def test_first_award_succeeds(self):
        state = IntimacyState()
        state, result = award_region_milestone(state, "EARLY_CONNECTION", 0, NOW)
        assert result.reason == "region_milestone"
        assert result.delta == 2
        assert state.intimacy_index == 3  # 1 + 2
        assert "EARLY_CONNECTION" in state.used_region_ids

    def test_duplicate_region_no_op(self):
        state = IntimacyState(used_region_ids=["EARLY_CONNECTION"])
        state, result = award_region_milestone(state, "EARLY_CONNECTION", 0, NOW)
        assert result.reason == "no_op_already_awarded"
        assert result.delta == 0

    def test_daily_cap_enforced(self):
        state = IntimacyState(
            gained_today_total=DAILY_INTIMACY_CAP_TOTAL,
            gained_today_date=NOW.strftime("%Y-%m-%d"),
        )
        state, result = award_region_milestone(state, "DEEP_BOND", 4, NOW)
        assert result.reason == "cap_reached"
        assert result.delta == 0

    def test_daily_counter_resets_on_new_day(self):
        yesterday = (NOW - timedelta(days=1)).strftime("%Y-%m-%d")
        state = IntimacyState(
            gained_today_total=DAILY_INTIMACY_CAP_TOTAL,
            gained_today_date=yesterday,
        )
        state, result = award_region_milestone(state, "COMFORT_FAMILIARITY", 1, NOW)
        assert result.reason == "region_milestone"
        assert result.delta == 2

    def test_max_cap_100(self):
        state = IntimacyState(intimacy_index=99)
        state, result = award_region_milestone(state, "ENDURING_COMPANIONSHIP", 8, NOW)
        assert state.intimacy_index == INTIMACY_MAX
        assert result.delta == 1  # only 1 to reach 100


# ── Gift purchase awards ─────────────────────────────────────────────────────

class TestGiftPurchase:
    def test_first_gift_succeeds(self):
        state = IntimacyState()
        state, result = award_gift_purchase(state, "rose_bouquet", NOW)
        assert result.reason == "gift_purchase"
        assert result.delta == GIFT_INTIMACY_BOOST
        assert "rose_bouquet" in state.used_gift_ids

    def test_duplicate_gift_no_op(self):
        state = IntimacyState(used_gift_ids=["rose_bouquet"])
        state, result = award_gift_purchase(state, "rose_bouquet", NOW)
        assert result.reason == "no_op_already_awarded"
        assert result.delta == 0

    def test_different_gifts_both_award(self):
        state = IntimacyState()
        state, _ = award_gift_purchase(state, "gift_a", NOW)
        state, result = award_gift_purchase(state, "gift_b", NOW)
        assert result.reason == "gift_purchase"
        assert state.intimacy_index == 1 + GIFT_INTIMACY_BOOST * 2

    def test_gift_daily_cap_enforced(self):
        state = IntimacyState(
            gained_today_gifts=DAILY_INTIMACY_CAP_GIFTS,
            gained_today_date=NOW.strftime("%Y-%m-%d"),
        )
        state, result = award_gift_purchase(state, "new_gift", NOW)
        assert result.reason == "cap_reached"
        assert result.delta == 0

    def test_total_daily_cap_enforced_for_gifts(self):
        state = IntimacyState(
            gained_today_total=DAILY_INTIMACY_CAP_TOTAL,
            gained_today_date=NOW.strftime("%Y-%m-%d"),
        )
        state, result = award_gift_purchase(state, "new_gift", NOW)
        assert result.reason == "cap_reached"


# ── Personality-based threshold ──────────────────────────────────────────────

class TestRequiredIntimacy:
    def test_default_traits(self):
        threshold = get_required_intimacy({})
        assert 15 <= threshold <= 85

    def test_slow_reserved_higher(self):
        threshold = get_required_intimacy({
            "relationship_pace": "Slow",
            "emotional_style": "Reserved",
            "communication_style": "Soft",
        })
        assert threshold > 50

    def test_fast_playful_lower(self):
        threshold = get_required_intimacy({
            "relationship_pace": "Fast",
            "emotional_style": "Playful",
            "communication_style": "Teasing",
        })
        assert threshold < 35


# ── Sensitive intent detection ───────────────────────────────────────────────

class TestSensitiveDetection:
    def test_normal_message_not_sensitive(self):
        assert not request_is_sensitive("How are you today?")

    def test_nude_keyword_sensitive(self):
        assert request_is_sensitive("Show me a nude photo")

    def test_lingerie_sensitive(self):
        assert request_is_sensitive("Wear some lingerie for me")

    def test_case_insensitive(self):
        assert request_is_sensitive("Take It Off")


# ── Image decision engine ────────────────────────────────────────────────────

class TestImageDecision:
    def _make_state(self, index: int = 1) -> IntimacyState:
        return IntimacyState(intimacy_index=index)

    def test_safe_request_generates(self):
        d = decide_image_action(
            "Take a cute selfie", True, True,
            self._make_state(1), {}, True,
        )
        assert d.action == "generate"

    def test_sensitive_below_threshold_tease(self):
        d = decide_image_action(
            "Show me a nude photo", True, True,
            self._make_state(5), {"relationship_pace": "Slow"},
            True,
        )
        assert d.action == "tease"
        assert d.reason == "intimacy_locked"
        assert len(d.suggested_prompts) > 0

    def test_sensitive_above_threshold_paid_generates(self):
        """Paid user with sufficient intimacy can generate sensitive images."""
        d = decide_image_action(
            "Show me a nude photo", True, True,
            self._make_state(90), {},
            True, user_plan="plus",
        )
        assert d.action == "generate"
        assert d.reason == "intimacy_unlocked"

    def test_sensitive_above_threshold_free_gets_blurred_paywall(self):
        """Free user with sufficient intimacy gets blurred paywall instead of generate."""
        d = decide_image_action(
            "Show me a nude photo", True, True,
            self._make_state(90), {},
            True, user_plan="free", girlfriend_id="gf_1",
        )
        assert d.action == "blurred_paywall"
        assert d.reason == "free_plan_upgrade"
        assert d.blurred_image_url  # should have a URL
        assert "Upgrade" in d.ui_copy or "upgrade" in d.ui_copy.lower()

    def test_sensitive_premium_user_generates(self):
        """Premium user with sufficient intimacy generates normally."""
        d = decide_image_action(
            "nude photo", True, True,
            self._make_state(90), {},
            True, user_plan="premium",
        )
        assert d.action == "generate"

    def test_sensitive_no_age_gate_deny(self):
        d = decide_image_action(
            "nude", False, True,
            self._make_state(99), {},
            True,
        )
        assert d.action == "deny"
        assert d.reason == "age_gate_required"

    def test_sensitive_no_opt_in_deny(self):
        d = decide_image_action(
            "nude", True, False,
            self._make_state(99), {},
            True,
        )
        assert d.action == "deny"
        assert d.reason == "content_pref_off"

    def test_no_quota_paywall(self):
        d = decide_image_action(
            "Take a photo", True, True,
            self._make_state(1), {},
            has_quota=False,
        )
        assert d.action == "paywall"

    def test_paid_no_quota_paywall(self):
        """Paid user with intimacy but no quota gets paywall."""
        d = decide_image_action(
            "nude", True, True,
            self._make_state(90), {},
            has_quota=False, user_plan="plus",
        )
        assert d.action == "paywall"
        assert d.reason == "quota_exceeded"


class TestBlurredSurprise:
    def test_free_user_above_threshold_gets_surprise(self):
        assert should_send_blurred_surprise(
            intimacy_index=FREE_PLAN_BLURRED_INTIMACY,
            user_plan="free",
            age_gate_passed=True,
            wants_spicy=True,
        )

    def test_free_user_below_threshold_no_surprise(self):
        assert not should_send_blurred_surprise(
            intimacy_index=FREE_PLAN_BLURRED_INTIMACY - 1,
            user_plan="free",
            age_gate_passed=True,
            wants_spicy=True,
        )

    def test_paid_user_no_surprise(self):
        """Paid users don't get blurred surprises (they get the real thing)."""
        assert not should_send_blurred_surprise(
            intimacy_index=FREE_PLAN_BLURRED_INTIMACY + 10,
            user_plan="plus",
            age_gate_passed=True,
            wants_spicy=True,
        )

    def test_no_age_gate_no_surprise(self):
        assert not should_send_blurred_surprise(
            intimacy_index=FREE_PLAN_BLURRED_INTIMACY + 10,
            user_plan="free",
            age_gate_passed=False,
            wants_spicy=True,
        )

    def test_no_spicy_opt_in_no_surprise(self):
        assert not should_send_blurred_surprise(
            intimacy_index=FREE_PLAN_BLURRED_INTIMACY + 10,
            user_plan="free",
            age_gate_passed=True,
            wants_spicy=False,
        )
