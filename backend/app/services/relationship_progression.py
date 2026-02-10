"""
Relationship Progression Engine — points, streaks, cooldowns, difficulty curve.

Drives the relationship level (0–200) automatically as the user chats.
No XP UI, no progress bars — purely backend state.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.services.relationship_regions import (
    MAX_RELATIONSHIP_LEVEL,
    clamp_level,
    get_region_for_level,
)

# ── Constants ─────────────────────────────────────────────────────────────────

AWARD_COOLDOWN_MINUTES = 12
BASE_POINTS_MIN = 8
BASE_POINTS_MAX = 14
RETURN_GAP_DAYS = 7
RETURN_BONUS = 20
ANTI_FARM_WINDOW_SECONDS = 300  # 5 minutes
ANTI_FARM_THRESHOLD = 10
RECENT_TS_LIMIT = 20

# ── Points-per-level curve (keyed by region max_level) ────────────────────────

_REGION_POINTS: list[tuple[int, int]] = [
    (10, 30),    # EARLY_CONNECTION        1–10
    (25, 60),    # COMFORT_FAMILIARITY     11–25
    (45, 90),    # GROWING_CLOSENESS       26–45
    (70, 130),   # EMOTIONAL_TRUST         46–70
    (105, 170),  # DEEP_BOND               71–105
    (135, 220),  # MUTUAL_DEVOTION         106–135
    (165, 280),  # INTIMATE_PARTNERSHIP    136–165
    (185, 360),  # SHARED_LIFE             166–185
    (200, 480),  # ENDURING_COMPANIONSHIP  186–200
]


def points_needed_for_level(level: int) -> int:
    """Points needed to go from *level* to *level+1*.

    Level 0 uses the same cost as levels 1–10 (30).
    """
    if level <= 0:
        return 30
    for max_lvl, pts in _REGION_POINTS:
        if level <= max_lvl:
            return pts
    return _REGION_POINTS[-1][1]  # 480 for anything above 200


# ── Multipliers / helpers ─────────────────────────────────────────────────────

_EMOTION_TOKENS = frozenset([
    "love", "miss", "happy", "sad", "feel", "felt", "heart", "care",
    "excited", "nervous", "worried", "grateful", "hug", "kiss",
    "❤", "💕", "😊", "😢", "🥺",
])


def streak_multiplier(streak_days: int) -> float:
    if streak_days >= 22:
        return 1.25
    if streak_days >= 8:
        return 1.2
    if streak_days >= 3:
        return 1.1
    return 1.0


def quality_multiplier(user_text: str) -> float:
    """Simple heuristic quality bonus. Capped at 1.20."""
    m = 1.0
    if len(user_text) >= 80:
        m += 0.05
    if "?" in user_text:
        m += 0.05
    lower = user_text.lower()
    if any(tok in lower for tok in _EMOTION_TOKENS):
        m += 0.10
    return min(m, 1.20)


def anti_farm_multiplier(recent_ts: List[datetime], now: datetime) -> float:
    """If >= 10 messages in last 5 minutes → 0.3, else 1.0."""
    cutoff = now - timedelta(seconds=ANTI_FARM_WINDOW_SECONDS)
    count = sum(1 for ts in recent_ts if ts >= cutoff)
    return 0.3 if count >= ANTI_FARM_THRESHOLD else 1.0


def return_after_gap_bonus(
    prev_last_interaction_at: Optional[datetime], now: datetime
) -> int:
    if prev_last_interaction_at is None:
        return 0
    gap = now - prev_last_interaction_at
    return RETURN_BONUS if gap >= timedelta(days=RETURN_GAP_DAYS) else 0


def can_award(now: datetime, last_award_at: Optional[datetime]) -> bool:
    if last_award_at is None:
        return True
    return (now - last_award_at) >= timedelta(minutes=AWARD_COOLDOWN_MINUTES)


def _deterministic_base_points(date_str: str, user_text: str) -> int:
    """Pseudo-random base points in [BASE_POINTS_MIN, BASE_POINTS_MAX].

    Deterministic for the same (date, text) pair so tests are stable.
    """
    h = hashlib.sha256(f"{date_str}:{user_text}".encode()).hexdigest()
    val = int(h[:8], 16)
    span = BASE_POINTS_MAX - BASE_POINTS_MIN + 1  # 7
    return BASE_POINTS_MIN + (val % span)


# ── State dataclass ───────────────────────────────────────────────────────────

@dataclass
class RelationshipProgressState:
    level: int = 0
    banked_points: int = 0
    streak_days: int = 0
    last_interaction_at: Optional[datetime] = None
    last_award_at: Optional[datetime] = None
    recent_message_timestamps: List[datetime] = field(default_factory=list)


# ── Core award function ──────────────────────────────────────────────────────

@dataclass
class AwardResult:
    """Returned alongside the updated state for callers that want diagnostics."""
    points_awarded: int = 0
    level_before: int = 0
    level_after: int = 0
    levels_gained: int = 0
    cooldown_blocked: bool = False


def award_progress(
    state: RelationshipProgressState,
    user_text: str,
    now: datetime,
) -> tuple[RelationshipProgressState, AwardResult]:
    """Process one user message and return (updated_state, result).

    Always records the message timestamp & updates streak.
    Points are only awarded if the cooldown has elapsed.
    """
    result = AwardResult(level_before=state.level)

    # ── 1) Record timestamp ──────────────────────────────────────────────
    recent = list(state.recent_message_timestamps)
    recent.append(now)
    if len(recent) > RECENT_TS_LIMIT:
        recent = recent[-RECENT_TS_LIMIT:]

    # ── 2) Update streak ─────────────────────────────────────────────────
    today = now.date()
    if state.last_interaction_at is None:
        streak = 1
    else:
        prev_date = state.last_interaction_at.date()
        if prev_date == today:
            streak = state.streak_days  # same day → keep
        elif prev_date == today - timedelta(days=1):
            streak = state.streak_days + 1
        else:
            streak = 1

    # ── 3) Cooldown gate ─────────────────────────────────────────────────
    if not can_award(now, state.last_award_at):
        result.cooldown_blocked = True
        result.level_after = state.level
        return (
            RelationshipProgressState(
                level=state.level,
                banked_points=state.banked_points,
                streak_days=streak,
                last_interaction_at=now,
                last_award_at=state.last_award_at,
                recent_message_timestamps=recent,
            ),
            result,
        )

    # ── 4) Compute points ────────────────────────────────────────────────
    date_str = now.strftime("%Y-%m-%d")
    base = _deterministic_base_points(date_str, user_text)
    sm = streak_multiplier(streak)
    qm = quality_multiplier(user_text)
    af = anti_farm_multiplier(recent, now)
    gap_bonus = return_after_gap_bonus(state.last_interaction_at, now)

    raw = base * sm * qm * af
    points = int(round(raw)) + gap_bonus
    if points < 0:
        points = 0

    result.points_awarded = points

    # ── 5) Bank points & level up ────────────────────────────────────────
    banked = state.banked_points + points
    level = state.level
    while level < MAX_RELATIONSHIP_LEVEL:
        needed = points_needed_for_level(level)
        if banked >= needed:
            banked -= needed
            level += 1
        else:
            break

    level = clamp_level(level)
    result.level_after = level
    result.levels_gained = level - result.level_before

    return (
        RelationshipProgressState(
            level=level,
            banked_points=banked,
            streak_days=streak,
            last_interaction_at=now,
            last_award_at=now,
            recent_message_timestamps=recent,
        ),
        result,
    )


# ── Helpers to derive trust/intimacy from level ──────────────────────────────

def derive_trust(level: int) -> int:
    return max(0, min(100, int(level * 0.9)))


def derive_intimacy(level: int) -> int:
    return max(0, min(100, int(max(0, level - 10) * 0.8)))
