"""
Pattern Memory — time habits, topic cycles, response latency, style preferences.

Observes user behavior over time and builds up pattern profiles:
  - Active hours / weekday distribution
  - Average response gap
  - Favorite topics / recurring themes
  - Message style (length, emoji usage, question frequency)
  - Conversation cadence (bursty vs steady)
"""
from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


# ── Pattern Extraction ───────────────────────────────────────────────────────

def extract_time_patterns(timestamps: list[str]) -> dict:
    """Extract time-based patterns from message timestamps.
    
    Returns: {"active_hours": [21,22,23], "weekday_dist": {"Mon": 5, ...},
              "avg_gap_minutes": 45, "peak_day": "Mon"}
    """
    if not timestamps:
        return {}
    
    parsed: list[datetime] = []
    for ts in timestamps:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            parsed.append(dt)
        except Exception:
            continue
    
    if len(parsed) < 3:
        return {}
    
    parsed.sort()
    
    # Active hours
    hour_counts = Counter(dt.hour for dt in parsed)
    total = sum(hour_counts.values())
    # Top hours (>= 10% of messages or top 4)
    threshold = max(1, total * 0.10)
    active_hours = sorted(h for h, c in hour_counts.items() if c >= threshold)
    if not active_hours:
        active_hours = [h for h, _ in hour_counts.most_common(4)]
    
    # Weekday distribution
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekday_counts = Counter(day_names[dt.weekday()] for dt in parsed)
    
    # Average gap between consecutive messages (minutes)
    gaps: list[float] = []
    for i in range(1, len(parsed)):
        gap = (parsed[i] - parsed[i - 1]).total_seconds() / 60.0
        if gap < 1440:  # exclude gaps > 1 day
            gaps.append(gap)
    avg_gap = round(sum(gaps) / len(gaps), 1) if gaps else None
    
    # Peak day
    peak_day = weekday_counts.most_common(1)[0][0] if weekday_counts else None
    
    return {
        "active_hours": active_hours,
        "weekday_dist": dict(weekday_counts),
        "avg_gap_minutes": avg_gap,
        "peak_day": peak_day,
        "total_messages": len(parsed),
    }


def extract_style_patterns(messages: list[str]) -> dict:
    """Extract message style patterns.
    
    Returns: {"avg_length": 42, "emoji_rate": 0.3, "question_rate": 0.2,
              "uppercase_rate": 0.05, "typical_sentences": 2}
    """
    if not messages:
        return {}
    
    lengths = [len(m) for m in messages]
    emoji_pattern = re.compile(
        r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        r"\U0001F1E0-\U0001F1FF\U00002700-\U000027BF\U0000FE00-\U0000FE0F"
        r"\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF"
        r"\U00002702-\U000027B0\U0000231A-\U0000231B\U00002328\U000023CF"
        r"\U000023E9-\U000023F3\U000023F8-\U000023FA❤️💕😊😢🥺]+",
        re.UNICODE,
    )
    
    emoji_count = sum(1 for m in messages if emoji_pattern.search(m))
    question_count = sum(1 for m in messages if "?" in m)
    sentence_counts = [len(re.split(r"[.!?]+", m)) for m in messages if m.strip()]
    
    return {
        "avg_length": round(sum(lengths) / len(lengths)) if lengths else 0,
        "emoji_rate": round(emoji_count / len(messages), 2),
        "question_rate": round(question_count / len(messages), 2),
        "typical_sentences": round(sum(sentence_counts) / len(sentence_counts)) if sentence_counts else 1,
    }


# ── Topic Tracking ───────────────────────────────────────────────────────────

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "work": ["work", "job", "boss", "office", "meeting", "project", "deadline", "client", "coworker"],
    "school": ["school", "class", "exam", "study", "professor", "homework", "grade", "university"],
    "family": ["mom", "dad", "brother", "sister", "family", "parent", "cousin", "uncle", "aunt"],
    "friends": ["friend", "friends", "buddy", "crew", "hang out", "hangout", "party"],
    "health": ["sick", "doctor", "hospital", "health", "workout", "gym", "exercise", "sleep"],
    "emotions": ["feel", "felt", "sad", "happy", "angry", "scared", "worried", "anxious", "excited"],
    "hobbies": ["game", "gaming", "read", "reading", "music", "movie", "show", "cook", "travel"],
    "relationship": ["love", "miss", "together", "us", "relationship", "date", "future"],
    "daily_life": ["today", "morning", "evening", "lunch", "dinner", "weather", "weekend"],
}


def extract_topic_distribution(messages: list[str]) -> dict[str, int]:
    """Count topic mentions across messages."""
    topic_counts: dict[str, int] = defaultdict(int)
    for msg in messages:
        lower = msg.lower()
        for topic, keywords in _TOPIC_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                topic_counts[topic] += 1
    return dict(topic_counts)


# ── Persistence ──────────────────────────────────────────────────────────────

def upsert_pattern(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    pattern_type: str,
    pattern_key: str,
    pattern_value: dict,
) -> None:
    """Upsert a pattern memory entry."""
    if not sb:
        return
    now = datetime.now(timezone.utc).isoformat()
    try:
        sb.table("memory_patterns").upsert(
            {
                "user_id": str(user_id),
                "girlfriend_id": str(girlfriend_id),
                "pattern_type": pattern_type,
                "pattern_key": pattern_key,
                "pattern_value": pattern_value,
                "last_reinforced_at": now,
                "observation_count": 1,  # will be incremented via SQL COALESCE on conflict
            },
            on_conflict="user_id,girlfriend_id,pattern_key"
        ).execute()
    except Exception as e:
        logger.warning("Failed to upsert pattern memory: %s", e)


def get_patterns(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    pattern_type: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Retrieve pattern memories, optionally filtered by type."""
    if not sb:
        return []
    try:
        q = (
            sb.table("memory_patterns")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("girlfriend_id", str(girlfriend_id))
        )
        if pattern_type:
            q = q.eq("pattern_type", pattern_type)
        r = q.order("salience", desc=True).limit(limit).execute()
        return r.data or []
    except Exception as e:
        logger.warning("Failed to get pattern memory: %s", e)
        return []


def update_all_patterns(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    user_timestamps: list[str],
    user_messages: list[str],
) -> None:
    """Update all pattern types from recent user data."""
    # Time patterns
    time_pats = extract_time_patterns(user_timestamps)
    if time_pats:
        upsert_pattern(sb, user_id, girlfriend_id, "time_habit", "active_hours",
                       {"hours": time_pats.get("active_hours", [])})
        if time_pats.get("avg_gap_minutes") is not None:
            upsert_pattern(sb, user_id, girlfriend_id, "response_latency", "avg_response_gap",
                           {"avg_gap_minutes": time_pats["avg_gap_minutes"]})
        if time_pats.get("weekday_dist"):
            upsert_pattern(sb, user_id, girlfriend_id, "time_habit", "weekday_distribution",
                           time_pats["weekday_dist"])
    
    # Style patterns
    style_pats = extract_style_patterns(user_messages)
    if style_pats:
        upsert_pattern(sb, user_id, girlfriend_id, "style_preference", "message_style", style_pats)
    
    # Topic distribution
    topic_dist = extract_topic_distribution(user_messages)
    if topic_dist:
        upsert_pattern(sb, user_id, girlfriend_id, "topic_cycle", "topic_distribution", topic_dist)
