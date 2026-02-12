"""TelemetryService — logs progression events and engagement metrics.

Tracks: session quality, progression events, message engagement, retention signals.
Primary metrics: 7-day retained users, meaningful_reply_rate, story_completion_rate.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

# ── In-memory telemetry buffer ────────────────────────────────────────────────
# Flushed to DB periodically or on explicit flush
_event_buffer: list[dict] = []
_BUFFER_MAX = 50  # flush after N events


def log_event(
    event_type: str,
    user_id: str,
    girlfriend_id: str | None = None,
    event_data: dict[str, Any] | None = None,
    quality_score: float | None = None,
) -> None:
    """Log a telemetry event."""
    event = {
        "id": str(uuid4()),
        "event_type": event_type,
        "user_id": user_id,
        "girlfriend_id": girlfriend_id,
        "event_data": event_data or {},
        "session_quality_score": quality_score,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _event_buffer.append(event)

    if len(_event_buffer) >= _BUFFER_MAX:
        flush()


def log_progression_event(
    user_id: str,
    girlfriend_id: str,
    event_type: str,
    payload: dict[str, Any],
    quality_score: float,
) -> None:
    """Log a progression-specific event with full context."""
    log_event(
        event_type=f"progression.{event_type}",
        user_id=user_id,
        girlfriend_id=girlfriend_id,
        event_data=payload,
        quality_score=quality_score,
    )


def log_message_engagement(
    user_id: str,
    girlfriend_id: str,
    message_id: str,
    action: str,  # "read", "clicked", "replied", "dismissed"
    extra: dict[str, Any] | None = None,
) -> None:
    """Log engagement with a milestone message."""
    log_event(
        event_type=f"message.{action}",
        user_id=user_id,
        girlfriend_id=girlfriend_id,
        event_data={"message_id": message_id, **(extra or {})},
    )


def log_session_quality(
    user_id: str,
    girlfriend_id: str,
    quality_score: float,
    signals: dict[str, Any],
) -> None:
    """Log session quality for analytics."""
    log_event(
        event_type="session.quality",
        user_id=user_id,
        girlfriend_id=girlfriend_id,
        event_data={"signals": signals},
        quality_score=quality_score,
    )


def flush() -> int:
    """Flush buffered events to Supabase. Returns count flushed."""
    global _event_buffer
    if not _event_buffer:
        return 0

    events = _event_buffer[:]
    _event_buffer = []

    count = 0
    try:
        from app.core.supabase_client import get_supabase_admin
        from uuid import UUID
        admin = get_supabase_admin()
        if admin:
            # Filter to events with valid UUIDs
            valid_events = []
            for e in events:
                try:
                    UUID(e["user_id"])
                    row = {
                        "event_type": e["event_type"],
                        "user_id": e["user_id"],
                        "event_data": e.get("event_data", {}),
                        "session_quality_score": e.get("session_quality_score"),
                        "created_at": e["created_at"],
                    }
                    if e.get("girlfriend_id"):
                        try:
                            UUID(e["girlfriend_id"])
                            row["girlfriend_id"] = e["girlfriend_id"]
                        except (ValueError, TypeError):
                            pass
                    valid_events.append(row)
                except (ValueError, TypeError):
                    pass

            if valid_events:
                admin.table("telemetry_events").insert(valid_events).execute()
                count = len(valid_events)
                logger.info(f"Flushed {count} telemetry events to DB")
    except Exception as exc:
        logger.warning(f"Failed to flush telemetry: {exc}")
        # Put events back in buffer
        _event_buffer = events + _event_buffer

    return count


# ── In-memory session quality tracker ─────────────────────────────────────────

_session_quality: dict[tuple[str, str, str], dict] = {}  # (user, gf, date) → stats


def update_session_quality(
    user_id: str,
    girlfriend_id: str,
    quality_score: float,
    signals: dict[str, Any],
) -> None:
    """Update session quality aggregates for today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = (user_id, girlfriend_id, today)

    if key not in _session_quality:
        _session_quality[key] = {
            "message_count": 0,
            "meaningful_reply_count": 0,
            "questions_asked": 0,
            "emotional_messages": 0,
            "total_length": 0,
            "quality_scores": [],
            "story_quests_completed": 0,
            "preference_confirmations": 0,
        }

    stats = _session_quality[key]
    stats["message_count"] += 1
    stats["quality_scores"].append(quality_score)

    if quality_score >= 40:
        stats["meaningful_reply_count"] += 1
    if signals.get("has_question"):
        stats["questions_asked"] += 1
    if signals.get("emotional_keywords", 0) > 0:
        stats["emotional_messages"] += 1
    if signals.get("is_story_followup"):
        stats["story_quests_completed"] += 1
    if signals.get("is_preference_confirmation"):
        stats["preference_confirmations"] += 1
    stats["total_length"] += signals.get("message_length", 0)

    # Persist aggregate to DB
    _persist_session_quality(user_id, girlfriend_id, today, stats)


def _persist_session_quality(
    user_id: str, girlfriend_id: str, session_date: str, stats: dict
) -> None:
    try:
        from app.core.supabase_client import get_supabase_admin
        from uuid import UUID
        admin = get_supabase_admin()
        if not admin:
            return
        UUID(user_id)
        UUID(girlfriend_id)

        avg_length = stats["total_length"] / max(stats["message_count"], 1)
        avg_quality = sum(stats["quality_scores"]) / max(len(stats["quality_scores"]), 1)

        admin.table("session_quality").upsert({
            "user_id": user_id,
            "girlfriend_id": girlfriend_id,
            "session_date": session_date,
            "message_count": stats["message_count"],
            "meaningful_reply_count": stats["meaningful_reply_count"],
            "questions_asked": stats["questions_asked"],
            "emotional_messages": stats["emotional_messages"],
            "avg_message_length": round(avg_length, 2),
            "quality_score": round(avg_quality, 2),
            "story_quests_completed": stats["story_quests_completed"],
            "preference_confirmations": stats["preference_confirmations"],
        }).execute()
    except Exception:
        pass
