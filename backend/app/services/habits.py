"""Habit inference from message history: preferred hours, typical gap."""
from typing import Optional

DEFAULT_LAST_N = 50
MIN_OCCURRENCES = 2
TOP_HOURS = 3
GAP_CAP_MIN = 4
GAP_CAP_MAX = 72


def infer_preferred_hours(
    message_timestamps: list[str], last_n: int = DEFAULT_LAST_N
) -> list[int]:
    """Top 3 hours (0-23) with at least 2 occurrences in last N messages."""
    recent = message_timestamps[-last_n:] if len(message_timestamps) > last_n else message_timestamps
    hour_counts: dict[int, int] = {}
    for ts in recent:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            h = dt.hour
            hour_counts[h] = hour_counts.get(h, 0) + 1
        except (ValueError, TypeError):
            continue
    candidates = [(h, c) for h, c in hour_counts.items() if c >= MIN_OCCURRENCES]
    candidates.sort(key=lambda x: -x[1])
    return [h for h, _ in candidates[:TOP_HOURS]]


def infer_typical_gap_hours(message_timestamps: list[str]) -> Optional[int]:
    """Median gap in hours between consecutive user messages, capped [4, 72]."""
    if len(message_timestamps) < 2:
        return None
    sorted_ts = sorted(message_timestamps)
    gaps = []
    for i in range(1, len(sorted_ts)):
        try:
            from datetime import datetime
            a = datetime.fromisoformat(sorted_ts[i - 1].replace("Z", "+00:00"))
            b = datetime.fromisoformat(sorted_ts[i].replace("Z", "+00:00"))
            hours = (b - a).total_seconds() / 3600
            gaps.append(max(GAP_CAP_MIN, min(GAP_CAP_MAX, round(hours))))
        except (ValueError, TypeError):
            continue
    if not gaps:
        return None
    gaps.sort()
    mid = len(gaps) // 2
    median = gaps[mid] if len(gaps) % 2 else (gaps[mid - 1] + gaps[mid]) // 2
    return median


def build_habit_profile(user_message_timestamps: list[str]) -> dict:
    return {
        "preferred_hours": infer_preferred_hours(user_message_timestamps) or None,
        "typical_gap_hours": infer_typical_gap_hours(user_message_timestamps),
    }
