"""Talking-streak calculation — display-only, no rewards.

Computes current streak, best streak, and whether today is a "talk day"
based on a list of message timestamps.  All date logic uses Europe/Amsterdam.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from typing import List, Sequence
from zoneinfo import ZoneInfo

TZ_AMSTERDAM = ZoneInfo("Europe/Amsterdam")


@dataclass(frozen=True)
class StreakResult:
    current_days: int
    best_days: int
    active_today: bool


def compute_streaks(message_times: Sequence[datetime]) -> StreakResult:
    """Return streak stats from a list of message datetimes (any timezone).

    A "talk day" is any calendar day (Europe/Amsterdam) with >= 1 message.
    Current streak: consecutive days ending today (if today has messages) or
    ending yesterday (if yesterday has messages); otherwise 0.
    Best streak: maximum consecutive run across all history.
    """
    if not message_times:
        return StreakResult(current_days=0, best_days=0, active_today=False)

    # Convert to Amsterdam calendar dates and de-duplicate
    talk_days: set[date] = set()
    for dt in message_times:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        talk_days.add(dt.astimezone(TZ_AMSTERDAM).date())

    sorted_days = sorted(talk_days)
    today = datetime.now(TZ_AMSTERDAM).date()
    active_today = today in talk_days

    # Build runs of consecutive days
    runs: list[list[date]] = []
    current_run: list[date] = [sorted_days[0]]
    for day in sorted_days[1:]:
        if day == current_run[-1] + timedelta(days=1):
            current_run.append(day)
        else:
            runs.append(current_run)
            current_run = [day]
    runs.append(current_run)

    best_days = max(len(r) for r in runs)

    # Current streak: find the run that touches today or yesterday
    yesterday = today - timedelta(days=1)
    current_days = 0
    for run in runs:
        if run[-1] == today:
            current_days = len(run)
            break
        if run[-1] == yesterday:
            current_days = len(run)
            break

    return StreakResult(
        current_days=current_days,
        best_days=best_days,
        active_today=active_today,
    )
