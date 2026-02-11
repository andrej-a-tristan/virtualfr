"""Tests for the profile stats endpoint and streak calculation."""
from datetime import datetime, timezone, timedelta
import pytest

from app.services.streaks import compute_streaks, StreakResult


# ═══════════════════════════════════════════════════════════════════════════════
# STREAK CALCULATION UNIT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputeStreaks:
    """Pure unit tests for compute_streaks()."""

    def test_empty_messages(self):
        result = compute_streaks([])
        assert result == StreakResult(current_days=0, best_days=0, active_today=False)

    def test_single_message_today(self):
        now = datetime.now(timezone.utc)
        result = compute_streaks([now])
        assert result.current_days == 1
        assert result.best_days == 1
        assert result.active_today is True

    def test_consecutive_days_ending_today(self):
        now = datetime.now(timezone.utc)
        times = [
            now - timedelta(days=2, hours=3),
            now - timedelta(days=1, hours=5),
            now - timedelta(hours=1),
        ]
        result = compute_streaks(times)
        assert result.current_days == 3
        assert result.best_days == 3
        assert result.active_today is True

    def test_consecutive_days_ending_yesterday(self):
        now = datetime.now(timezone.utc)
        times = [
            now - timedelta(days=3, hours=3),
            now - timedelta(days=2, hours=5),
            now - timedelta(days=1, hours=1),
        ]
        result = compute_streaks(times)
        assert result.current_days == 3
        assert result.best_days == 3
        assert result.active_today is False

    def test_gap_breaks_streak(self):
        now = datetime.now(timezone.utc)
        times = [
            now - timedelta(days=5),
            now - timedelta(days=4),
            # gap on day -3
            now - timedelta(days=1),
            now,
        ]
        result = compute_streaks(times)
        assert result.current_days == 2  # yesterday + today
        assert result.best_days == 2  # both runs are length 2
        assert result.active_today is True

    def test_best_streak_from_past(self):
        now = datetime.now(timezone.utc)
        times = [
            now - timedelta(days=10),
            now - timedelta(days=9),
            now - timedelta(days=8),
            now - timedelta(days=7),
            now - timedelta(days=6),
            # gap
            now,
        ]
        result = compute_streaks(times)
        assert result.current_days == 1  # only today
        assert result.best_days == 5     # the 5-day run in the past
        assert result.active_today is True

    def test_multiple_messages_same_day(self):
        now = datetime.now(timezone.utc)
        times = [
            now - timedelta(hours=5),
            now - timedelta(hours=3),
            now - timedelta(hours=1),
        ]
        result = compute_streaks(times)
        assert result.current_days == 1
        assert result.best_days == 1
        assert result.active_today is True

    def test_no_messages_today_or_yesterday(self):
        now = datetime.now(timezone.utc)
        times = [
            now - timedelta(days=5),
            now - timedelta(days=4),
        ]
        result = compute_streaks(times)
        assert result.current_days == 0
        assert result.best_days == 2
        assert result.active_today is False

    def test_naive_datetimes_treated_as_utc(self):
        """Naive datetimes should be treated as UTC and still produce valid results."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        times = [now - timedelta(days=1), now]
        result = compute_streaks(times)
        assert result.current_days >= 1
        assert result.best_days >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# PROFILE ENDPOINT INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestProfileEndpoint:
    """Integration tests using the in-memory store directly."""

    def _setup_session(self):
        """Create a session with one girlfriend and some messages."""
        from app.api.store import (
            set_session_user,
            add_girlfriend,
            append_message,
            add_gallery_item,
        )
        from app.api.routes.gifts import _gift_purchases

        sid = "test-profile-session"
        gf_id = "gf-001"

        set_session_user(sid, {
            "id": "user-1",
            "email": "test@test.com",
            "display_name": "Tester",
            "age_gate_passed": True,
            "has_girlfriend": True,
            "current_girlfriend_id": gf_id,
            "plan": "plus",
        })

        add_girlfriend(sid, {
            "id": gf_id,
            "display_name": "Luna",
            "avatar_url": None,
            "traits": {
                "emotional_style": "Playful",
                "attachment_style": "Very attached",
                "reaction_to_absence": "High",
                "communication_style": "Teasing",
                "relationship_pace": "Fast",
                "cultural_personality": "Warm Slavic",
            },
            "identity": {
                "job_vibe": "Artist",
                "origin_vibe": "Prague",
                "hobbies": ["painting", "music"],
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        # Add messages across multiple days
        now = datetime.now(timezone.utc)
        for i in range(5):
            append_message(sid, {
                "id": f"msg-{i}",
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}",
                "created_at": (now - timedelta(days=4 - i)).isoformat(),
            }, gf_id)

        # Add gallery items
        add_gallery_item(sid, {"id": "img-1", "url": "http://example.com/1.jpg", "created_at": now.isoformat()}, gf_id)
        add_gallery_item(sid, {"id": "img-2", "url": "http://example.com/2.jpg", "created_at": now.isoformat()}, gf_id)

        # Add gift purchase
        _gift_purchases[(sid, gf_id)] = [
            {"gift_id": "stickers", "status": "paid", "created_at": now.isoformat()},
        ]

        return sid, gf_id

    def _cleanup(self, sid: str):
        from app.api.store import clear_session
        from app.api.routes.gifts import _gift_purchases
        clear_session(sid)
        # Clean up gift purchases for this session
        keys_to_remove = [k for k in _gift_purchases if k[0] == sid]
        for k in keys_to_remove:
            del _gift_purchases[k]

    def test_returns_one_entry_per_girlfriend(self):
        sid, gf_id = self._setup_session()
        try:
            from app.api.routes.profile import get_profile_girls, _require_user, _build_vibe_line
            from app.api.store import get_all_girlfriends, get_messages

            girlfriends = get_all_girlfriends(sid)
            assert len(girlfriends) == 1
            assert girlfriends[0]["id"] == gf_id
        finally:
            self._cleanup(sid)

    def test_message_count_matches(self):
        sid, gf_id = self._setup_session()
        try:
            from app.api.store import get_messages
            messages = get_messages(sid, gf_id)
            assert len(messages) == 5
        finally:
            self._cleanup(sid)

    def test_vibe_line_from_identity(self):
        sid, gf_id = self._setup_session()
        try:
            from app.api.store import get_girlfriend_by_id
            from app.api.routes.profile import _build_vibe_line
            gf = get_girlfriend_by_id(sid, gf_id)
            vibe = _build_vibe_line(gf)
            assert "Artist" in vibe
            assert "Prague" in vibe
            assert "painting" in vibe
        finally:
            self._cleanup(sid)

    def test_gallery_count_matches(self):
        sid, gf_id = self._setup_session()
        try:
            from app.api.store import get_gallery
            gallery = get_gallery(sid, gf_id)
            assert len(gallery) == 2
        finally:
            self._cleanup(sid)

    def test_gift_count_matches(self):
        sid, gf_id = self._setup_session()
        try:
            from app.api.routes.gifts import _gift_purchases
            purchases = _gift_purchases.get((sid, gf_id), [])
            paid = [p for p in purchases if p.get("status") == "paid"]
            assert len(paid) == 1
        finally:
            self._cleanup(sid)

    def test_streak_with_consecutive_days(self):
        """Streak should detect consecutive days from synthetic timestamps."""
        now = datetime.now(timezone.utc)
        times = [
            now - timedelta(days=4),
            now - timedelta(days=3),
            now - timedelta(days=2),
            now - timedelta(days=1),
            now,
        ]
        result = compute_streaks(times)
        assert result.current_days == 5
        assert result.best_days == 5
        assert result.active_today is True

    def test_streak_with_gap(self):
        """Gap in days should break the current streak."""
        now = datetime.now(timezone.utc)
        times = [
            now - timedelta(days=5),
            now - timedelta(days=4),
            # gap on day -3
            now - timedelta(days=1),
            now,
        ]
        result = compute_streaks(times)
        assert result.current_days == 2
        assert result.best_days == 2
