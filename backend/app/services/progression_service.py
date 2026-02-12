"""ProgressionService — evaluates session quality and emits domain events.

Computes level transitions and gates progression by quality signals,
not just message frequency.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any

from app.schemas.progression import (
    ProgressionEvent,
    SessionQualityScore,
    SessionQualitySignals,
)

logger = logging.getLogger(__name__)

# ── Emotional keyword sets ────────────────────────────────────────────────────

_EMOTIONAL_KEYWORDS = {
    "love", "miss", "happy", "sad", "angry", "scared", "grateful", "lonely",
    "excited", "nervous", "afraid", "hurt", "sorry", "forgive", "trust",
    "jealous", "proud", "hopeful", "anxious", "embarrassed", "worried",
    "disappointed", "confused", "overwhelmed", "thankful", "appreciate",
    "care", "feel", "emotion", "heart", "soul", "cry", "laugh", "smile",
    "hug", "kiss", "comfort", "safe", "vulnerable", "honest", "open",
}

_PREFERENCE_PATTERNS = [
    r"\b(yes|yeah|yep|sure|okay|ok|definitely|absolutely|of course)\b",
    r"\b(no|nah|nope|not really|i don'?t think so)\b",
    r"\bi (like|love|prefer|enjoy|want|need|hate|dislike)\b",
    r"\b(that'?s (right|correct|true|exactly))\b",
]

_QUESTION_PATTERN = re.compile(r"\?")

_STORY_FOLLOWUP_PATTERNS = [
    r"\btell me more\b",
    r"\bwhat happened\b",
    r"\bwhy did\b",
    r"\bhow did\b",
    r"\bthen what\b",
    r"\bgo on\b",
    r"\bcontinue\b",
    r"\byes.*(tell|show|share)\b",
    r"\bi('m| am) (curious|interested)\b",
    r"\bwhat('s| is) (next|the next)\b",
]

# ── Region boundaries (match existing relationship_progression.py) ────────────

REGIONS = [
    {"key": "EARLY_CONNECTION",       "min": 0,   "max": 14},
    {"key": "COMFORT_FAMILIARITY",    "min": 15,  "max": 34},
    {"key": "GROWING_CLOSENESS",      "min": 35,  "max": 59},
    {"key": "EMOTIONAL_TRUST",        "min": 60,  "max": 89},
    {"key": "DEEP_BOND",              "min": 90,  "max": 119},
    {"key": "MUTUAL_DEVOTION",        "min": 120, "max": 149},
    {"key": "INTIMATE_PARTNERSHIP",   "min": 150, "max": 174},
    {"key": "SHARED_LIFE",            "min": 175, "max": 194},
    {"key": "ENDURING_COMPANIONSHIP", "min": 195, "max": 200},
]

# Trust milestones (triggers at trust_visible thresholds)
TRUST_MILESTONES = [20, 40, 60, 80, 100]

# Streak milestones
STREAK_MILESTONES = [3, 7, 14, 30, 60]

# Message count milestones
MESSAGE_MILESTONES = [50, 100, 250, 500, 1000]


def region_for_level(level: int) -> dict:
    """Return the region dict for a given level."""
    for r in REGIONS:
        if r["min"] <= level <= r["max"]:
            return r
    return REGIONS[-1]


# ── Quality Signal Extraction ─────────────────────────────────────────────────

def extract_quality_signals(
    message: str,
    recent_message_count: int = 0,
    recent_messages: list[dict] | None = None,
) -> SessionQualitySignals:
    """Extract quality signals from a user message and conversation context."""
    msg_lower = message.lower().strip()

    # Emotional keyword count
    words = set(re.findall(r"\b\w+\b", msg_lower))
    emotional_count = len(words & _EMOTIONAL_KEYWORDS)

    # Question detection
    has_question = bool(_QUESTION_PATTERN.search(message))

    # Preference confirmation
    is_pref = any(re.search(p, msg_lower) for p in _PREFERENCE_PATTERNS)

    # Story followup
    is_followup = any(re.search(p, msg_lower) for p in _STORY_FOLLOWUP_PATTERNS)

    # Sustained conversation (5+ messages in recent window)
    sustained = recent_message_count >= 5

    # Reply depth
    reply_depth = min(recent_message_count, 20)

    return SessionQualitySignals(
        message_length=len(message),
        has_question=has_question,
        emotional_keywords=emotional_count,
        is_story_followup=is_followup,
        is_preference_confirmation=is_pref,
        sustained_conversation=sustained,
        reply_depth=reply_depth,
    )


def compute_quality_score(signals: SessionQualitySignals) -> SessionQualityScore:
    """Compute a 0-100 quality score from session signals."""
    breakdown: dict[str, float] = {}

    # Base score for any message
    breakdown["base"] = 15.0

    # Message length bonus (capped at 20)
    if signals.message_length > 100:
        breakdown["length"] = 20.0
    elif signals.message_length > 50:
        breakdown["length"] = 12.0
    elif signals.message_length > 20:
        breakdown["length"] = 5.0

    # Questions = engagement
    if signals.has_question:
        breakdown["question"] = 10.0

    # Emotional content
    em_score = min(signals.emotional_keywords * 5.0, 15.0)
    if em_score > 0:
        breakdown["emotional"] = em_score

    # Story followup = high engagement
    if signals.is_story_followup:
        breakdown["story_followup"] = 15.0

    # Preference confirmation = explicit engagement
    if signals.is_preference_confirmation:
        breakdown["preference_confirm"] = 10.0

    # Sustained conversation bonus
    if signals.sustained_conversation:
        breakdown["sustained"] = 10.0

    # Reply depth bonus (diminishing returns)
    depth_bonus = min(signals.reply_depth * 0.5, 5.0)
    if depth_bonus > 0:
        breakdown["reply_depth"] = depth_bonus

    total = min(sum(breakdown.values()), 100.0)
    return SessionQualityScore(total=round(total, 2), breakdown=breakdown)


# ── Level Transition Detection ────────────────────────────────────────────────

def detect_progression_events(
    *,
    user_id: str,
    girlfriend_id: str,
    quality_score: float,
    # Before/after state
    old_level: int,
    new_level: int,
    old_trust: int,
    new_trust: int,
    old_streak: int,
    new_streak: int,
    old_message_count: int,
    new_message_count: int,
    # Already-reached milestones to avoid duplicates
    reached_milestones: list[str] | None = None,
) -> list[ProgressionEvent]:
    """Detect all progression events from a state transition."""
    events: list[ProgressionEvent] = []
    reached = set(reached_milestones or [])

    # 1) Relationship region transition
    old_region = region_for_level(old_level)
    new_region = region_for_level(new_level)
    if new_region["key"] != old_region["key"]:
        milestone_key = f"region_{new_region['key'].lower()}"
        if milestone_key not in reached:
            events.append(ProgressionEvent(
                event_type="relationship.level_achieved",
                user_id=user_id,
                girlfriend_id=girlfriend_id,
                payload={
                    "level": new_level,
                    "region_key": new_region["key"],
                    "old_region_key": old_region["key"],
                    "milestone_key": milestone_key,
                },
                quality_score=quality_score,
            ))

    # 2) Trust milestones
    for threshold in TRUST_MILESTONES:
        milestone_key = f"trust_{threshold}"
        if old_trust < threshold <= new_trust and milestone_key not in reached:
            events.append(ProgressionEvent(
                event_type="intimacy.level_unlocked",
                user_id=user_id,
                girlfriend_id=girlfriend_id,
                payload={
                    "trust_level": new_trust,
                    "threshold": threshold,
                    "milestone_key": milestone_key,
                },
                quality_score=quality_score,
            ))

    # 3) Streak milestones
    for threshold in STREAK_MILESTONES:
        milestone_key = f"streak_{threshold}"
        if old_streak < threshold <= new_streak and milestone_key not in reached:
            events.append(ProgressionEvent(
                event_type="streak.milestone",
                user_id=user_id,
                girlfriend_id=girlfriend_id,
                payload={
                    "streak_days": new_streak,
                    "threshold": threshold,
                    "milestone_key": milestone_key,
                },
                quality_score=quality_score,
            ))

    # 4) Message count milestones
    for threshold in MESSAGE_MILESTONES:
        milestone_key = f"messages_{threshold}"
        if old_message_count < threshold <= new_message_count and milestone_key not in reached:
            events.append(ProgressionEvent(
                event_type="engagement.milestone",
                user_id=user_id,
                girlfriend_id=girlfriend_id,
                payload={
                    "message_count": new_message_count,
                    "threshold": threshold,
                    "milestone_key": milestone_key,
                },
                quality_score=quality_score,
            ))

    return events


# ── Quality gate: minimum quality for progression ─────────────────────────────

QUALITY_GATE_THRESHOLD = 25.0  # Minimum quality score to award progression

def should_award_progression(quality_score: float) -> bool:
    """Only award progression points if quality meets threshold."""
    return quality_score >= QUALITY_GATE_THRESHOLD
