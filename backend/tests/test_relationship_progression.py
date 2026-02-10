"""Tests for the relationship progression engine."""
import pytest
from datetime import datetime, timedelta, timezone

from app.services.relationship_progression import (
    AWARD_COOLDOWN_MINUTES,
    BASE_POINTS_MIN,
    BASE_POINTS_MAX,
    MAX_RELATIONSHIP_LEVEL,
    RelationshipProgressState,
    AwardResult,
    award_progress,
    points_needed_for_level,
    streak_multiplier,
    quality_multiplier,
    anti_farm_multiplier,
    return_after_gap_bonus,
    can_award,
    derive_trust,
    derive_intimacy,
    clamp_level,
)


# ── Helper ────────────────────────────────────────────────────────────────────

def _utc(year=2026, month=1, day=15, hour=12, minute=0, second=0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


# ── points_needed_for_level curve ─────────────────────────────────────────────

class TestPointsNeededCurve:
    def test_level_zero(self):
        assert points_needed_for_level(0) == 30

    def test_boundary_10(self):
        assert points_needed_for_level(10) == 30

    def test_boundary_11(self):
        assert points_needed_for_level(11) == 60

    def test_boundary_25(self):
        assert points_needed_for_level(25) == 60

    def test_boundary_26(self):
        assert points_needed_for_level(26) == 90

    def test_boundary_45(self):
        assert points_needed_for_level(45) == 90

    def test_boundary_46(self):
        assert points_needed_for_level(46) == 130

    def test_boundary_70(self):
        assert points_needed_for_level(70) == 130

    def test_boundary_71(self):
        assert points_needed_for_level(71) == 170

    def test_boundary_105(self):
        assert points_needed_for_level(105) == 170

    def test_boundary_106(self):
        assert points_needed_for_level(106) == 220

    def test_boundary_135(self):
        assert points_needed_for_level(135) == 220

    def test_boundary_136(self):
        assert points_needed_for_level(136) == 280

    def test_boundary_165(self):
        assert points_needed_for_level(165) == 280

    def test_boundary_166(self):
        assert points_needed_for_level(166) == 360

    def test_boundary_185(self):
        assert points_needed_for_level(185) == 360

    def test_boundary_186(self):
        assert points_needed_for_level(186) == 480

    def test_boundary_200(self):
        assert points_needed_for_level(200) == 480


# ── Cooldown ──────────────────────────────────────────────────────────────────

class TestCooldown:
    def test_first_message_always_awards(self):
        """First message ever: no last_award_at → should always award."""
        state = RelationshipProgressState()
        now = _utc()
        new_state, result = award_progress(state, "hello!", now)
        assert result.points_awarded > 0
        assert not result.cooldown_blocked

    def test_cooldown_blocks_rapid_second_message(self):
        """A second message within the cooldown window should NOT award points."""
        now1 = _utc(minute=0)
        state = RelationshipProgressState()
        state, _ = award_progress(state, "first message", now1)
        level_after_first = state.level
        banked_after_first = state.banked_points

        now2 = now1 + timedelta(minutes=5)  # < 12 min cooldown
        state, result2 = award_progress(state, "second message", now2)
        assert result2.cooldown_blocked is True
        assert result2.points_awarded == 0
        assert state.level == level_after_first
        assert state.banked_points == banked_after_first

    def test_cooldown_allows_after_elapsed(self):
        """After cooldown elapses, points are awarded again."""
        now1 = _utc(minute=0)
        state = RelationshipProgressState()
        state, _ = award_progress(state, "first message", now1)

        now2 = now1 + timedelta(minutes=AWARD_COOLDOWN_MINUTES)
        state, result2 = award_progress(state, "later message", now2)
        assert result2.cooldown_blocked is False
        assert result2.points_awarded > 0


# ── Streak multiplier ────────────────────────────────────────────────────────

class TestStreakMultiplier:
    def test_day_one(self):
        assert streak_multiplier(1) == 1.0

    def test_day_three(self):
        assert streak_multiplier(3) == 1.1

    def test_day_eight(self):
        assert streak_multiplier(8) == 1.2

    def test_day_22(self):
        assert streak_multiplier(22) == 1.25

    def test_streak_increases_points(self):
        """A 10-day streak should yield more points than streak=1 for the same message."""
        now = _utc()
        text = "Hey, how are you feeling today?"

        # streak = 1 (fresh)
        state1 = RelationshipProgressState(streak_days=0)
        _, res1 = award_progress(state1, text, now)

        # streak = 10 (continuing)
        state10 = RelationshipProgressState(
            streak_days=9,  # will become 10 since last_interaction is None → resets to 1
            last_interaction_at=now - timedelta(days=1),  # yesterday → streak continues
        )
        _, res10 = award_progress(state10, text, now)

        assert res10.points_awarded > res1.points_awarded


# ── Clamp prevents level > 200 ───────────────────────────────────────────────

class TestLevelClamp:
    def test_cannot_exceed_max(self):
        """Even with huge banked points, level never exceeds 200."""
        state = RelationshipProgressState(
            level=199,
            banked_points=100_000,  # massive surplus
        )
        now = _utc()
        new_state, result = award_progress(state, "hello", now)
        assert new_state.level <= MAX_RELATIONSHIP_LEVEL


# ── Quality multiplier ───────────────────────────────────────────────────────

class TestQualityMultiplier:
    def test_short_plain(self):
        assert quality_multiplier("hi") == 1.0

    def test_long_text_bonus(self):
        text = "a" * 80
        assert quality_multiplier(text) == pytest.approx(1.05)

    def test_question_bonus(self):
        assert quality_multiplier("How are you?") == pytest.approx(1.05)

    def test_emotion_bonus(self):
        assert quality_multiplier("I love you") == pytest.approx(1.10)

    def test_cap_at_120(self):
        text = "I love you and I miss you so much? " + "a" * 80
        assert quality_multiplier(text) <= 1.20


# ── Anti-farm multiplier ─────────────────────────────────────────────────────

class TestAntiFarm:
    def test_normal_pace(self):
        now = _utc()
        timestamps = [now - timedelta(minutes=i * 3) for i in range(5)]
        assert anti_farm_multiplier(timestamps, now) == 1.0

    def test_rapid_spam(self):
        now = _utc()
        timestamps = [now - timedelta(seconds=i * 10) for i in range(12)]
        assert anti_farm_multiplier(timestamps, now) == 0.3


# ── Return-after-gap bonus ───────────────────────────────────────────────────

class TestReturnBonus:
    def test_no_previous(self):
        assert return_after_gap_bonus(None, _utc()) == 0

    def test_recent(self):
        now = _utc()
        assert return_after_gap_bonus(now - timedelta(days=2), now) == 0

    def test_seven_days(self):
        now = _utc()
        assert return_after_gap_bonus(now - timedelta(days=7), now) == 20


# ── Derive trust/intimacy ────────────────────────────────────────────────────

class TestDerive:
    def test_derive_trust_level_0(self):
        assert derive_trust(0) == 0

    def test_derive_trust_level_100(self):
        assert derive_trust(100) == 90

    def test_derive_trust_capped(self):
        assert derive_trust(200) <= 100

    def test_derive_intimacy_level_0(self):
        assert derive_intimacy(0) == 0

    def test_derive_intimacy_level_50(self):
        assert derive_intimacy(50) == 32  # int(max(0, 40) * 0.8)

    def test_derive_intimacy_capped(self):
        assert derive_intimacy(200) <= 100


# ── Integration: multiple awards accumulate ───────────────────────────────────

class TestIntegration:
    def test_multiple_awards_level_up(self):
        """Repeated awards should eventually level up from 0."""
        state = RelationshipProgressState()
        now = _utc()
        for i in range(20):
            msg_time = now + timedelta(minutes=AWARD_COOLDOWN_MINUTES * i)
            state, _ = award_progress(state, f"message {i}", msg_time)
        assert state.level > 0

    def test_streak_builds_across_days(self):
        """Messaging on consecutive days increases streak_days."""
        state = RelationshipProgressState()
        day1 = _utc(day=10, hour=12)
        state, _ = award_progress(state, "day one", day1)
        assert state.streak_days == 1

        day2 = _utc(day=11, hour=12)
        state, _ = award_progress(state, "day two", day2)
        assert state.streak_days == 2

        day3 = _utc(day=12, hour=12)
        state, _ = award_progress(state, "day three", day3)
        assert state.streak_days == 3
