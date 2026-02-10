"""Tests for the emotional relationship achievement system (v3 — emotional-only, non-missable)."""
import time
import pytest

from app.services.relationship_milestones import (
    ACHIEVEMENTS,
    ACHIEVEMENTS_BY_REGION,
    Achievement,
    Rarity,
    TriggerType,
    get_achievements_for_region,
    get_eligible_achievements,
    get_achievements_by_trigger,
    get_region_index,
)
from app.services.achievement_engine import (
    AchievementProgress,
    DetectedEvent,
    reset_progress_for_region,
    detect_signals,
    evaluate_requirement,
    try_unlock,
    try_unlock_for_triggers,
    get_current_region_index_for_girl,
    can_attempt_unlock,
    _is_on_cooldown,
    _detect_conflict_arc,
    update_streak,
    mark_gift_confirmed,
    SIGNAL_COOLDOWN_HOURS,
)
from app.services.relationship_state import create_initial_relationship_state
from app.services.relationship_regions import REGIONS
from app.services.relationship_descriptors import build_narrative_hooks, get_descriptors


# ═══════════════════════════════════════════════════════════════════════════════
# CATALOG INTEGRITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestCatalog:
    def test_all_9_regions_have_achievements(self):
        for i in range(9):
            assert i in ACHIEVEMENTS_BY_REGION, f"Region {i} missing from catalog"
            assert len(ACHIEVEMENTS_BY_REGION[i]) == 6, (
                f"Region {i} should have exactly 6 achievements, got {len(ACHIEVEMENTS_BY_REGION[i])}"
            )

    def test_total_achievement_count(self):
        assert len(ACHIEVEMENTS) == 54, f"Expected 54 achievements (6x9), got {len(ACHIEVEMENTS)}"

    def test_unique_ids(self):
        all_ids = [a.id for a in ACHIEVEMENTS.values()]
        assert len(all_ids) == len(set(all_ids)), "Duplicate achievement IDs found"

    def test_achievements_sorted_by_sort_order(self):
        for region_idx, achs in ACHIEVEMENTS_BY_REGION.items():
            for i in range(1, len(achs)):
                assert achs[i].sort_order >= achs[i - 1].sort_order, (
                    f"Region {region_idx}: {achs[i].id} not sorted after {achs[i - 1].id}"
                )

    def test_all_achievements_have_rarity(self):
        for a in ACHIEVEMENTS.values():
            assert isinstance(a.rarity, Rarity), f"{a.id} has invalid rarity: {a.rarity}"

    def test_all_achievements_have_trigger(self):
        for a in ACHIEVEMENTS.values():
            assert isinstance(a.trigger, TriggerType), f"{a.id} has invalid trigger: {a.trigger}"

    def test_all_achievements_have_requirement_dict(self):
        for a in ACHIEVEMENTS.values():
            assert isinstance(a.requirement, dict), f"{a.id} has invalid requirement"
            assert "type" in a.requirement, f"{a.id} requirement missing 'type'"
            assert "params" in a.requirement, f"{a.id} requirement missing 'params'"

    def test_rarity_distribution_has_all_levels(self):
        rarities = {a.rarity for a in ACHIEVEMENTS.values()}
        assert Rarity.COMMON in rarities
        assert Rarity.UNCOMMON in rarities
        assert Rarity.RARE in rarities
        assert Rarity.EPIC in rarities
        assert Rarity.LEGENDARY in rarities

    def test_all_achievements_have_narrative_hook(self):
        for a in ACHIEVEMENTS.values():
            assert a.narrative_hook, f"{a.id} missing narrative_hook"

    def test_no_gift_or_streak_triggers(self):
        """Verify no achievements use behavioral triggers like gifts or streaks."""
        for a in ACHIEVEMENTS.values():
            req_type = a.requirement["type"]
            assert req_type not in ("first_gift_in_region", "streak_days_in_region",
                                     "return_after_days", "region_enter"), (
                f"{a.id} uses non-emotional requirement type: {req_type}"
            )

    def test_secret_achievements_exist(self):
        secrets = [a for a in ACHIEVEMENTS.values() if a.is_secret]
        assert len(secrets) >= 6, f"Expected at least 6 secret achievements, got {len(secrets)}"

    def test_secret_achievements_spread_across_regions(self):
        secret_regions = {a.region_index for a in ACHIEVEMENTS.values() if a.is_secret}
        assert len(secret_regions) >= 3, "Secrets should be spread across multiple regions"

    def test_region_index_mapping(self):
        for i, region in enumerate(REGIONS):
            assert get_region_index(region.key) == i


# ═══════════════════════════════════════════════════════════════════════════════
# NON-MISSABLE REGION RULE
# ═══════════════════════════════════════════════════════════════════════════════

class TestNonMissableRule:
    def test_past_region_achievement_can_unlock(self):
        """Past region achievements should be unlockable (non-missable)."""
        ach = ACHIEVEMENTS_BY_REGION[0][0]  # Region 0 achievement
        assert can_attempt_unlock(ach, current_region_index=3), (
            "Past region achievements should be unlockable"
        )

    def test_current_region_achievement_can_unlock(self):
        ach = ACHIEVEMENTS_BY_REGION[3][0]
        assert can_attempt_unlock(ach, current_region_index=3)

    def test_future_region_achievement_blocked(self):
        ach = ACHIEVEMENTS_BY_REGION[5][0]
        assert not can_attempt_unlock(ach, current_region_index=3), (
            "Future region achievements should be blocked"
        )

    def test_get_eligible_achievements_includes_past(self):
        eligible = get_eligible_achievements(3)
        region_indices = {a.region_index for a in eligible}
        assert 0 in region_indices, "Region 0 should be eligible when current=3"
        assert 1 in region_indices
        assert 2 in region_indices
        assert 3 in region_indices
        assert 4 not in region_indices, "Region 4 should NOT be eligible when current=3"

    def test_unlock_past_region_succeeds(self):
        """Unlocking a past-region achievement should work."""
        state = create_initial_relationship_state()
        state["level"] = 50  # region 3
        progress = AchievementProgress()
        # Set the first_flag for region 0's first achievement
        ach = ACHIEVEMENTS_BY_REGION[0][0]
        flag = ach.requirement.get("params", {}).get("flag", "")
        if flag:
            progress.first_time_flags[flag] = True
        state, evt = try_unlock(state, ach.id, progress)
        assert evt is not None, "Past region achievement should unlock"
        assert ach.id in state["milestones_reached"]

    def test_unlock_future_region_fails(self):
        state = create_initial_relationship_state()
        state["level"] = 5  # region 0
        progress = AchievementProgress()
        ach = ACHIEVEMENTS_BY_REGION[5][0]  # Region 5
        # Even with flag set, should fail
        flag = ach.requirement.get("params", {}).get("flag", "")
        if flag:
            progress.first_time_flags[flag] = True
        _, evt = try_unlock(state, ach.id, progress)
        assert evt is None, "Future region achievement should NOT unlock"

    def test_duplicate_unlock_no_op(self):
        state = create_initial_relationship_state()
        state["level"] = 5
        progress = AchievementProgress()
        ach = ACHIEVEMENTS_BY_REGION[0][0]
        flag = ach.requirement.get("params", {}).get("flag", "")
        if flag:
            progress.first_time_flags[flag] = True
        state, evt1 = try_unlock(state, ach.id, progress)
        assert evt1 is not None
        state, evt2 = try_unlock(state, ach.id, progress)
        assert evt2 is None
        assert state["milestones_reached"].count(ach.id) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# REGION INDEX HELPER
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegionIndex:
    def test_level_0_is_region_0(self):
        assert get_current_region_index_for_girl(0) == 0

    def test_level_11_is_region_1(self):
        assert get_current_region_index_for_girl(11) == 1

    def test_level_200_is_region_8(self):
        assert get_current_region_index_for_girl(200) == 8

    def test_level_70_is_region_3(self):
        assert get_current_region_index_for_girl(70) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestSignalDetection:
    def test_affection_detected(self):
        progress = AchievementProgress()
        now = time.time()
        triggers = detect_signals("I miss you so much", "", progress, now=now)
        assert TriggerType.AFFECTION_SIGNAL in triggers
        assert len(progress.event_history) >= 1
        assert progress.event_history[-1]["signal"] == "affection"

    def test_vulnerability_detected(self):
        progress = AchievementProgress()
        now = time.time()
        triggers = detect_signals("", "I'm scared about what might happen", progress, now=now)
        assert TriggerType.VULNERABILITY_SIGNAL in triggers

    def test_we_language_detected(self):
        progress = AchievementProgress()
        now = time.time()
        triggers = detect_signals("We should do this together", "", progress, now=now)
        assert TriggerType.WE_LANGUAGE in triggers

    def test_gratitude_detected(self):
        progress = AchievementProgress()
        now = time.time()
        triggers = detect_signals("Thank you for being there", "", progress, now=now)
        assert TriggerType.GRATITUDE in triggers

    def test_commitment_detected(self):
        progress = AchievementProgress()
        now = time.time()
        triggers = detect_signals("I'm yours, only you", "", progress, now=now)
        assert TriggerType.COMMITMENT in triggers

    def test_future_talk_detected(self):
        progress = AchievementProgress()
        now = time.time()
        triggers = detect_signals("", "Our future together is going to be amazing", progress, now=now)
        assert TriggerType.FUTURE_TALK in triggers

    def test_home_language_detected(self):
        progress = AchievementProgress()
        now = time.time()
        triggers = detect_signals("", "You're my home", progress, now=now)
        assert TriggerType.HOME_LANGUAGE in triggers

    def test_apology_detected(self):
        progress = AchievementProgress()
        now = time.time()
        triggers = detect_signals("I'm sorry about that", "", progress, now=now)
        assert TriggerType.APOLOGY in triggers

    def test_reassurance_detected(self):
        progress = AchievementProgress()
        now = time.time()
        triggers = detect_signals("", "It's okay, don't worry about it", progress, now=now)
        assert TriggerType.REASSURANCE in triggers

    def test_boundary_respect_detected(self):
        progress = AchievementProgress()
        now = time.time()
        triggers = detect_signals("I respect that, take your time", "", progress, now=now)
        assert TriggerType.BOUNDARY_RESPECT in triggers

    def test_message_evaluated_always_present(self):
        progress = AchievementProgress()
        triggers = detect_signals("hello", "hi there", progress, now=time.time())
        assert TriggerType.MESSAGE_EVALUATED in triggers


# ═══════════════════════════════════════════════════════════════════════════════
# FIRST-TIME FLAGS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFirstTimeFlags:
    def test_first_affection_flag_set(self):
        progress = AchievementProgress()
        now = time.time()
        detect_signals("I miss you", "", progress, now=now)
        assert progress.first_time_flags.get("first_affection") is True

    def test_first_curiosity_flag_set(self):
        progress = AchievementProgress()
        now = time.time()
        detect_signals("Tell me about your day", "", progress, now=now)
        assert progress.first_time_flags.get("first_curiosity") is True

    def test_first_compliment_flag_from_assistant(self):
        progress = AchievementProgress()
        now = time.time()
        detect_signals("", "I like how you always know what to say", progress, now=now)
        assert progress.first_time_flags.get("first_compliment") is True

    def test_first_vulnerability_flag_set(self):
        progress = AchievementProgress()
        now = time.time()
        detect_signals("", "I feel scared about this", progress, now=now)
        assert progress.first_time_flags.get("first_vulnerability") is True

    def test_first_miss_you_flag(self):
        progress = AchievementProgress()
        now = time.time()
        detect_signals("I miss you", "", progress, now=now)
        assert progress.first_time_flags.get("first_miss_you") is True

    def test_first_trust_declaration(self):
        progress = AchievementProgress()
        now = time.time()
        detect_signals("", "I trust you completely", progress, now=now)
        assert progress.first_time_flags.get("first_trust_declaration") is True

    def test_flags_not_duplicated(self):
        progress = AchievementProgress()
        now = time.time()
        detect_signals("I miss you", "", progress, now=now)
        # Second detection after cooldown
        detect_signals("I miss you so much", "", progress, now=now + 7200)
        assert progress.first_time_flags.get("first_miss_you") is True
        assert progress.first_time_flags.get("first_affection") is True


# ═══════════════════════════════════════════════════════════════════════════════
# ANTI-FARM: COOLDOWN & DEDUP
# ═══════════════════════════════════════════════════════════════════════════════

class TestAntiFarm:
    def test_cooldown_blocks_rapid_repeat(self):
        progress = AchievementProgress()
        now = time.time()
        # First detection succeeds
        detect_signals("I love you", "", progress, now=now)
        initial_count = len([e for e in progress.event_history if e["signal"] == "affection"])
        # Immediate repeat blocked by cooldown
        detect_signals("I love you baby", "", progress, now=now + 60)
        after_count = len([e for e in progress.event_history if e["signal"] == "affection"])
        assert after_count == initial_count, "Should be blocked by cooldown"

    def test_cooldown_allows_after_expiry(self):
        progress = AchievementProgress()
        now = time.time()
        detect_signals("I love you", "", progress, now=now)
        initial_count = len([e for e in progress.event_history if e["signal"] == "affection"])
        # After cooldown expires (1 hour for affection)
        detect_signals("I adore you", "", progress, now=now + 4000)
        after_count = len([e for e in progress.event_history if e["signal"] == "affection"])
        assert after_count > initial_count, "Should be allowed after cooldown"

    def test_phrase_dedup_blocks_same_phrase(self):
        progress = AchievementProgress()
        now = time.time()
        detect_signals("I love you", "", progress, now=now)
        count1 = len(progress.event_history)
        # Same exact phrase after cooldown — blocked by phrase dedup
        detect_signals("I love you", "", progress, now=now + 7200)
        count2 = len(progress.event_history)
        # The affection signal should be deduped (same phrase hash)
        # But other signals in the message may still fire
        affection_events = [e for e in progress.event_history if e["signal"] == "affection"]
        assert len(affection_events) == 1, "Same phrase should be deduped"

    def test_different_phrase_not_deduped(self):
        progress = AchievementProgress()
        now = time.time()
        detect_signals("I love you", "", progress, now=now)
        detect_signals("I adore you completely", "", progress, now=now + 7200)
        affection_events = [e for e in progress.event_history if e["signal"] == "affection"]
        assert len(affection_events) == 2, "Different phrases should both count"


# ═══════════════════════════════════════════════════════════════════════════════
# CONFLICT REPAIR ARC
# ═══════════════════════════════════════════════════════════════════════════════

class TestConflictRepairArc:
    def test_complete_arc_triggers_repair(self):
        progress = AchievementProgress()
        now = time.time()
        triggered = set()

        # Step 1: Tension
        _detect_conflict_arc(
            "You never listen to me!", None, progress, now, triggered
        )
        assert progress.conflict_tension_at > 0

        # Step 2: Apology
        _detect_conflict_arc(
            "I'm sorry about that", None, progress, now + 60, triggered
        )
        assert progress.conflict_apology_at > 0

        # Step 3: Reassurance completes the arc
        _detect_conflict_arc(
            "It's okay, we'll be fine", None, progress, now + 120, triggered
        )
        assert TriggerType.CONFLICT_REPAIR in triggered
        assert progress.conflict_last_repair_at > 0

    def test_arc_requires_order(self):
        """Reassurance before apology should NOT complete the arc."""
        progress = AchievementProgress()
        now = time.time()
        triggered = set()

        # Tension
        _detect_conflict_arc("You never care!", None, progress, now, triggered)
        # Reassurance (before apology) — shouldn't complete arc
        _detect_conflict_arc("We're okay", None, progress, now + 60, triggered)
        assert TriggerType.CONFLICT_REPAIR not in triggered

    def test_arc_7_day_cooldown(self):
        progress = AchievementProgress()
        now = time.time()
        triggered = set()

        # Complete first repair
        _detect_conflict_arc("You never listen!", None, progress, now, triggered)
        _detect_conflict_arc("I'm sorry", None, progress, now + 60, triggered)
        _detect_conflict_arc("It's okay", None, progress, now + 120, triggered)
        assert TriggerType.CONFLICT_REPAIR in triggered

        # Try another repair within 7 days — should be blocked
        triggered2 = set()
        _detect_conflict_arc("You always forget!", None, progress, now + 86400, triggered2)
        _detect_conflict_arc("I apologize", None, progress, now + 86460, triggered2)
        _detect_conflict_arc("Don't worry about it", None, progress, now + 86520, triggered2)
        assert TriggerType.CONFLICT_REPAIR not in triggered2, "Should be on 7-day cooldown"


# ═══════════════════════════════════════════════════════════════════════════════
# REQUIREMENT EVALUATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestRequirementEvaluation:
    def test_first_flag_not_set(self):
        progress = AchievementProgress()
        assert evaluate_requirement(
            {"type": "first_flag", "params": {"flag": "first_affection"}}, progress
        ) is False

    def test_first_flag_set(self):
        progress = AchievementProgress(first_time_flags={"first_affection": True})
        assert evaluate_requirement(
            {"type": "first_flag", "params": {"flag": "first_affection"}}, progress
        ) is True

    def test_distinct_signals_not_enough(self):
        progress = AchievementProgress(event_history=[
            {"signal": "affection", "strength": 2, "timestamp": 1000.0,
             "message_index": 1, "phrase_hash": hash("love")},
        ])
        assert evaluate_requirement(
            {"type": "distinct_signals", "params": {
                "signal": "affection", "min_distinct": 2, "min_gap_messages": 2,
            }}, progress
        ) is False

    def test_distinct_signals_enough_with_gap(self):
        progress = AchievementProgress(event_history=[
            {"signal": "affection", "strength": 2, "timestamp": 1000.0,
             "message_index": 1, "phrase_hash": hash("love")},
            {"signal": "affection", "strength": 1, "timestamp": 2000.0,
             "message_index": 5, "phrase_hash": hash("darling")},
        ])
        assert evaluate_requirement(
            {"type": "distinct_signals", "params": {
                "signal": "affection", "min_distinct": 2, "min_gap_messages": 2,
            }}, progress
        ) is True

    def test_distinct_signals_dedupes_same_hash(self):
        h = hash("same phrase")
        progress = AchievementProgress(event_history=[
            {"signal": "affection", "strength": 2, "timestamp": 1000.0,
             "message_index": 1, "phrase_hash": h},
            {"signal": "affection", "strength": 2, "timestamp": 2000.0,
             "message_index": 5, "phrase_hash": h},
        ])
        assert evaluate_requirement(
            {"type": "distinct_signals", "params": {
                "signal": "affection", "min_distinct": 2, "min_gap_messages": 2,
            }}, progress
        ) is False, "Same phrase hash should not count as distinct"

    def test_multi_signal_requires_all(self):
        progress = AchievementProgress(event_history=[
            {"signal": "vulnerability", "strength": 2, "timestamp": 1000.0,
             "message_index": 1, "phrase_hash": hash("scared")},
            {"signal": "vulnerability", "strength": 2, "timestamp": 2000.0,
             "message_index": 5, "phrase_hash": hash("worried")},
            {"signal": "reassurance", "strength": 2, "timestamp": 3000.0,
             "message_index": 8, "phrase_hash": hash("okay")},
            {"signal": "reassurance", "strength": 2, "timestamp": 4000.0,
             "message_index": 12, "phrase_hash": hash("fine")},
        ])
        assert evaluate_requirement(
            {"type": "multi_signal", "params": {
                "signals": ["vulnerability", "reassurance"],
                "min_each": 2, "min_gap_messages": 3,
            }}, progress
        ) is True

    def test_multi_signal_fails_if_one_short(self):
        progress = AchievementProgress(event_history=[
            {"signal": "vulnerability", "strength": 2, "timestamp": 1000.0,
             "message_index": 1, "phrase_hash": hash("scared")},
            {"signal": "vulnerability", "strength": 2, "timestamp": 2000.0,
             "message_index": 5, "phrase_hash": hash("worried")},
            # Only 1 reassurance, need 2
            {"signal": "reassurance", "strength": 2, "timestamp": 3000.0,
             "message_index": 8, "phrase_hash": hash("okay")},
        ])
        assert evaluate_requirement(
            {"type": "multi_signal", "params": {
                "signals": ["vulnerability", "reassurance"],
                "min_each": 2, "min_gap_messages": 3,
            }}, progress
        ) is False

    def test_conflict_repair_arc_requirement(self):
        progress = AchievementProgress(
            conflict_last_repair_at=time.time(),
            event_history=[
                {"signal": "conflict_repair", "strength": 3,
                 "timestamp": time.time(), "message_index": 10,
                 "phrase_hash": hash("repair")},
            ],
        )
        assert evaluate_requirement(
            {"type": "conflict_repair_arc", "params": {}}, progress
        ) is True

    def test_conflict_repair_not_happened(self):
        progress = AchievementProgress()
        assert evaluate_requirement(
            {"type": "conflict_repair_arc", "params": {}}, progress
        ) is False

    def test_time_separated_multi_signal(self):
        now = time.time()
        progress = AchievementProgress(event_history=[
            {"signal": "vulnerability", "strength": 2, "timestamp": now - 100000,
             "message_index": 1, "phrase_hash": hash("v1")},
            {"signal": "vulnerability", "strength": 2, "timestamp": now - 10000,
             "message_index": 20, "phrase_hash": hash("v2")},
            {"signal": "affection", "strength": 2, "timestamp": now - 100000,
             "message_index": 2, "phrase_hash": hash("a1")},
            {"signal": "affection", "strength": 2, "timestamp": now - 10000,
             "message_index": 21, "phrase_hash": hash("a2")},
        ])
        assert evaluate_requirement(
            {"type": "multi_signal_time_separated", "params": {
                "signals": ["vulnerability", "affection"],
                "min_each": 2, "min_gap_hours": 24,
            }}, progress
        ) is True


# ═══════════════════════════════════════════════════════════════════════════════
# TRY UNLOCK — FULL INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestTryUnlock:
    def _make_state(self, level: int) -> dict:
        state = create_initial_relationship_state()
        state["level"] = level
        return state

    def test_first_flag_achievement_unlocks(self):
        state = self._make_state(5)  # region 0
        progress = AchievementProgress(first_time_flags={"first_affection": True})
        ach = ACHIEVEMENTS["r1_warm_hello"]
        state, evt = try_unlock(state, ach.id, progress)
        assert evt is not None
        assert evt["id"] == "r1_warm_hello"
        assert evt["rarity"] == "COMMON"
        assert evt["narrative_hook"] != ""
        assert evt["is_secret"] is False

    def test_secret_achievement_includes_is_secret(self):
        state = self._make_state(5)
        progress = AchievementProgress(first_time_flags={"first_thinking_of_you": True})
        ach = ACHIEVEMENTS["r1_lingering_thought"]
        state, evt = try_unlock(state, ach.id, progress)
        assert evt is not None
        assert evt["is_secret"] is True

    def test_nonexistent_achievement(self):
        state = self._make_state(5)
        progress = AchievementProgress()
        _, evt = try_unlock(state, "nonexistent_id", progress)
        assert evt is None


# ═══════════════════════════════════════════════════════════════════════════════
# TRY UNLOCK FOR TRIGGERS (batch)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTryUnlockForTriggers:
    def _make_state(self, level: int) -> dict:
        state = create_initial_relationship_state()
        state["level"] = level
        return state

    def test_message_evaluated_checks_all_eligible(self):
        """MESSAGE_EVALUATED should check all eligible achievements."""
        state = self._make_state(5)
        progress = AchievementProgress(first_time_flags={
            "first_affection": True,
            "first_curiosity": True,
        })
        state, events = try_unlock_for_triggers(
            state, progress, {TriggerType.MESSAGE_EVALUATED}
        )
        ids = {e["id"] for e in events}
        assert "r1_warm_hello" in ids
        assert "r1_genuine_curiosity" in ids

    def test_no_triggers_no_events(self):
        state = self._make_state(5)
        progress = AchievementProgress()
        state, events = try_unlock_for_triggers(state, progress, set())
        assert events == []


# ═══════════════════════════════════════════════════════════════════════════════
# EVENT PAYLOAD
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventPayload:
    def test_event_has_required_fields(self):
        state = create_initial_relationship_state()
        state["level"] = 5
        progress = AchievementProgress(first_time_flags={"first_affection": True})
        ach = ACHIEVEMENTS["r1_warm_hello"]
        _, evt = try_unlock(state, ach.id, progress)
        assert evt is not None
        required_fields = ["id", "title", "subtitle", "rarity", "region_index",
                          "trigger_type", "is_secret", "narrative_hook", "unlocked_at"]
        for field in required_fields:
            assert field in evt, f"Missing field: {field}"


# ═══════════════════════════════════════════════════════════════════════════════
# PROGRESS SERIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestProgressSerialization:
    def test_round_trip(self):
        progress = AchievementProgress(
            region_index=3,
            first_time_flags={"first_affection": True, "first_vulnerability": True},
            event_history=[
                {"signal": "affection", "strength": 2, "timestamp": 1000.0,
                 "message_index": 1, "phrase_hash": 12345},
            ],
            last_signal_timestamps={"affection": 1000.0},
            conflict_tension_at=500.0,
            message_counter=42,
        )
        d = progress.to_dict()
        restored = AchievementProgress.from_dict(d)
        assert restored.region_index == 3
        assert restored.first_time_flags == {"first_affection": True, "first_vulnerability": True}
        assert len(restored.event_history) == 1
        assert restored.last_signal_timestamps == {"affection": 1000.0}
        assert restored.conflict_tension_at == 500.0
        assert restored.message_counter == 42


# ═══════════════════════════════════════════════════════════════════════════════
# PROGRESS RESET (NON-MISSABLE — no counter reset)
# ═══════════════════════════════════════════════════════════════════════════════

class TestProgressReset:
    def test_region_index_updated(self):
        progress = AchievementProgress(region_index=0)
        reset_progress_for_region(progress, 3)
        assert progress.region_index == 3

    def test_flags_preserved_on_region_change(self):
        progress = AchievementProgress(
            region_index=0,
            first_time_flags={"first_affection": True},
        )
        reset_progress_for_region(progress, 1)
        assert progress.first_time_flags.get("first_affection") is True

    def test_event_history_preserved(self):
        progress = AchievementProgress(
            region_index=0,
            event_history=[{"signal": "test", "strength": 1, "timestamp": 1.0,
                           "message_index": 1, "phrase_hash": 0}],
        )
        reset_progress_for_region(progress, 1)
        assert len(progress.event_history) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# NARRATIVE HOOKS
# ═══════════════════════════════════════════════════════════════════════════════

class TestNarrativeHooks:
    def test_build_hooks_from_milestones(self):
        milestones = ["r1_warm_hello", "r1_genuine_curiosity"]
        hooks = build_narrative_hooks(milestones)
        assert len(hooks) == 2
        # Most recent first
        assert "interest" in hooks[0].lower() or "warm" in hooks[0].lower()

    def test_hooks_deduped(self):
        milestones = ["r1_warm_hello", "r1_warm_hello"]
        hooks = build_narrative_hooks(milestones)
        assert len(hooks) == 1

    def test_hooks_limited_to_20(self):
        # Use all 54 achievements
        milestones = list(ACHIEVEMENTS.keys())
        hooks = build_narrative_hooks(milestones)
        assert len(hooks) <= 20

    def test_descriptors_accept_hooks(self):
        hooks = ["She remembers the first time you made her feel warm."]
        desc = get_descriptors(50, 30, narrative_hooks=hooks)
        assert "warm" in desc.prompt_context.lower()
        assert "Relationship memories" in desc.prompt_context


# ═══════════════════════════════════════════════════════════════════════════════
# LEGACY COMPAT
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegacyCompat:
    def test_update_streak_is_noop(self):
        progress = AchievementProgress()
        triggers = update_streak(progress, "2025-01-01")
        assert triggers == set()

    def test_mark_gift_confirmed_is_noop(self):
        progress = AchievementProgress()
        triggers = mark_gift_confirmed(progress)
        assert triggers == set()
