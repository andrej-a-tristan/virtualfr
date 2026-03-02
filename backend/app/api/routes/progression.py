"""Progression API — evaluate, messages, summary, choice actions.

POST /api/progression/evaluate  — evaluate after key interactions
GET  /api/progression/messages   — list milestone messages (unread by default)
POST /api/progression/messages/read — mark messages as read
POST /api/progression/messages/{id}/action — record a choice click
POST /api/progression/messages/{id}/dismiss — dismiss a message
GET  /api/progression/summary    — current progression state summary
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response

from app.api.store import (
    get_girlfriend,
    get_messages as get_chat_messages,
    get_relationship_progress,
    get_trust_intimacy_state,
    get_achievement_progress,
)
from app.api.request_context import get_current_user
from app.schemas.progression import (
    ChoiceActionRequest,
    EvaluateRequest,
    EvaluateResponse,
    MarkReadRequest,
    MilestoneMessageList,
    ProgressionEvent,
    ProgressionSummary,
)
from app.services import (
    progression_service,
    message_composer,
    delivery_service,
    experiment_service,
    telemetry_service,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/progression", tags=["progression"])

def _require_user(request: Request):
    # Use the shared request_context resolver so Supabase-auth sessions work too.
    sid, user, user_id, gf_id = get_current_user(request)
    if not sid or not user:
        raise HTTPException(401, "Not authenticated")
    return sid, user, user_id, gf_id


# ── POST /evaluate ────────────────────────────────────────────────────────────

@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate_progression(body: EvaluateRequest, request: Request):
    """Evaluate progression after a key interaction.

    Called by the chat endpoint after each user message, or can be
    called independently for explicit event triggers.
    """
    sid, user, user_id_uuid, gf_id_session = _require_user(request)
    user_id = str(user_id_uuid) if user_id_uuid else (user.get("user_id") or user.get("id", ""))
    gf_id = body.girlfriend_id or gf_id_session

    # Extract quality signals from the message
    if body.message:
        # Count recent messages for sustained conversation detection
        recent_msgs = get_chat_messages(sid, gf_id)
        recent_count = _count_recent_messages(recent_msgs)

        signals = progression_service.extract_quality_signals(
            body.message,
            recent_message_count=recent_count,
        )
        quality = progression_service.compute_quality_score(signals)
    else:
        signals = progression_service.SessionQualitySignals()
        quality = progression_service.SessionQualityScore(total=0)

    # Log session quality
    telemetry_service.log_session_quality(
        user_id, gf_id, quality.total, signals.model_dump()
    )
    telemetry_service.update_session_quality(
        user_id, gf_id, quality.total, signals.model_dump()
    )

    # Get current progression state
    progress = get_relationship_progress(sid, gf_id)
    trust_state = get_trust_intimacy_state(sid, gf_id)
    achievement = get_achievement_progress(sid, gf_id)

    old_level = progress.get("level", 0) if isinstance(progress, dict) else getattr(progress, "level", 0)
    old_trust = trust_state.get("trust_visible", 20) if isinstance(trust_state, dict) else getattr(trust_state, "trust_visible", 20)
    old_streak = progress.get("streak_days", 0) if isinstance(progress, dict) else getattr(progress, "streak_days", 0)
    old_msg_count = achievement.get("message_counter", 0) if isinstance(achievement, dict) else getattr(achievement, "message_counter", 0)

    # Detect progression events (comparing before/after state)
    # Note: The actual level/trust changes are done by the existing chat.py flow.
    # Here we check for milestone crossings based on current state.
    milestones_reached = _get_reached_milestones(sid, gf_id)

    events = progression_service.detect_progression_events(
        user_id=user_id,
        girlfriend_id=gf_id,
        quality_score=quality.total,
        old_level=old_level,
        new_level=old_level,  # Will be updated by chat flow
        old_trust=old_trust,
        new_trust=old_trust,
        old_streak=old_streak,
        new_streak=old_streak,
        old_message_count=old_msg_count,
        new_message_count=old_msg_count,
        reached_milestones=milestones_reached,
    )

    # If explicit event key, also generate that event
    if body.event_key:
        events.append(ProgressionEvent(
            event_type=body.event_key,
            user_id=user_id,
            girlfriend_id=gf_id,
            payload={"explicit": True},
            quality_score=quality.total,
        ))

    # Compose and queue messages for each event
    messages_queued = 0
    gf = get_girlfriend(sid) or {}
    gf_name = gf.get("display_name") or gf.get("name") or "her"
    gf_traits = gf.get("traits") or {}
    memory_snippet = _get_memory_snippet(sid, gf_id)
    tone = experiment_service.resolve_tone_from_traits(gf_traits)

    for event in events:
        msg = message_composer.compose_milestone_message(
            event,
            girlfriend_name=gf_name,
            memory_snippet=memory_snippet,
            tone=tone,
        )
        if msg:
            delivery_service.queue_message(user_id, gf_id, msg)
            messages_queued += 1

        # Log to telemetry
        telemetry_service.log_progression_event(
            user_id, gf_id, event.event_type, event.payload, quality.total
        )

    return EvaluateResponse(
        quality_score=quality,
        events=events,
        messages_queued=messages_queued,
    )


# ── GET /messages ─────────────────────────────────────────────────────────────

@router.get("/messages", response_model=MilestoneMessageList)
def list_messages(
    request: Request,
    girlfriend_id: str | None = None,
    unread_only: bool = True,
    limit: int = 20,
):
    """List milestone messages (default: unread only)."""
    sid, user, user_id_uuid, gf_id_session = _require_user(request)
    user_id = str(user_id_uuid) if user_id_uuid else (user.get("user_id") or user.get("id", ""))
    gf_id = girlfriend_id or gf_id_session or user.get("current_girlfriend_id", "")
    if not gf_id:
        return MilestoneMessageList()

    return delivery_service.get_messages(user_id, gf_id, unread_only=unread_only, limit=limit)


# ── POST /messages/read ───────────────────────────────────────────────────────

@router.post("/messages/read")
def mark_messages_read(body: MarkReadRequest, request: Request):
    """Mark milestone messages as read."""
    sid, user, user_id_uuid, gf_id_session = _require_user(request)
    user_id = str(user_id_uuid) if user_id_uuid else (user.get("user_id") or user.get("id", ""))
    gf_id = gf_id_session or user.get("current_girlfriend_id", "")

    count = delivery_service.mark_read(user_id, gf_id, body.message_ids)

    # Log engagement
    for mid in body.message_ids:
        telemetry_service.log_message_engagement(user_id, gf_id, mid, "read")

    return {"ok": True, "count": count}


# ── POST /messages/{id}/action ────────────────────────────────────────────────

@router.post("/messages/{message_id}/action")
def record_choice_action(message_id: str, body: ChoiceActionRequest, request: Request):
    """Record a user's choice on a milestone message."""
    sid, user, user_id_uuid, gf_id_session = _require_user(request)
    user_id = str(user_id_uuid) if user_id_uuid else (user.get("user_id") or user.get("id", ""))
    gf_id = gf_id_session or user.get("current_girlfriend_id", "")

    ok = delivery_service.mark_clicked(user_id, gf_id, message_id, body.action)

    # Log engagement
    telemetry_service.log_message_engagement(
        user_id, gf_id, message_id, "clicked", {"action": body.action}
    )

    return {"ok": ok, "action": body.action}


# ── POST /messages/{id}/dismiss ───────────────────────────────────────────────

@router.post("/messages/{message_id}/dismiss")
def dismiss_message(message_id: str, request: Request):
    """Dismiss a milestone message."""
    sid, user, user_id_uuid, gf_id_session = _require_user(request)
    user_id = str(user_id_uuid) if user_id_uuid else (user.get("user_id") or user.get("id", ""))
    gf_id = gf_id_session or user.get("current_girlfriend_id", "")

    ok = delivery_service.dismiss_message(user_id, gf_id, message_id)

    telemetry_service.log_message_engagement(user_id, gf_id, message_id, "dismissed")

    return {"ok": ok}


# ── GET /summary ──────────────────────────────────────────────────────────────

@router.get("/summary", response_model=ProgressionSummary)
def get_summary(request: Request, girlfriend_id: str | None = None):
    """Get current progression state summary."""
    sid, user, user_id_uuid, gf_id_session = _require_user(request)
    user_id = str(user_id_uuid) if user_id_uuid else (user.get("user_id") or user.get("id", ""))
    gf_id = girlfriend_id or gf_id_session or user.get("current_girlfriend_id", "")
    if not gf_id:
        return ProgressionSummary()

    progress = get_relationship_progress(sid, gf_id)
    trust_state = get_trust_intimacy_state(sid, gf_id)
    achievement = get_achievement_progress(sid, gf_id)

    level = progress.get("level", 0) if isinstance(progress, dict) else getattr(progress, "level", 0)
    streak = progress.get("streak_days", 0) if isinstance(progress, dict) else getattr(progress, "streak_days", 0)
    trust_vis = trust_state.get("trust_visible", 20) if isinstance(trust_state, dict) else getattr(trust_state, "trust_visible", 20)
    intimacy_vis = trust_state.get("intimacy_visible", 1) if isinstance(trust_state, dict) else getattr(trust_state, "intimacy_visible", 1)
    msg_count = achievement.get("message_counter", 0) if isinstance(achievement, dict) else getattr(achievement, "message_counter", 0)

    region = progression_service.region_for_level(level)
    milestones_reached = _get_reached_milestones(sid, gf_id)
    unread = delivery_service.get_unread_count(user_id, gf_id)

    # Compute next milestone
    next_ms = _compute_next_milestone(level, trust_vis, streak, msg_count, milestones_reached)

    return ProgressionSummary(
        level=level,
        region_key=region["key"],
        trust_visible=trust_vis,
        intimacy_visible=intimacy_vis,
        streak_days=streak,
        message_count=msg_count,
        milestones_reached=milestones_reached,
        unread_messages=unread,
        next_milestone=next_ms,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _count_recent_messages(messages: list[dict], window_minutes: int = 30) -> int:
    """Count messages within the recent time window."""
    if not messages:
        return 0
    now = datetime.now(timezone.utc)
    count = 0
    for m in reversed(messages):
        try:
            ts = datetime.fromisoformat(m.get("created_at", "").replace("Z", "+00:00"))
            if (now - ts).total_seconds() < window_minutes * 60:
                count += 1
            else:
                break
        except (ValueError, TypeError):
            count += 1
    return count


def _get_reached_milestones(sid: str, gf_id: str) -> list[str]:
    """Get list of already-reached milestone keys."""
    try:
        from app.api.store import get_relationship_state
        state = get_relationship_state(sid, gf_id)
        if isinstance(state, dict):
            return state.get("milestones_reached", [])
        return getattr(state, "milestones_reached", [])
    except Exception:
        return []


def _get_memory_snippet(sid: str, gf_id: str) -> str:
    """Get a short memory snippet for personalization."""
    try:
        from app.services.memory import get_memory_context
        ctx = get_memory_context(sid, gf_id)
        facts = ctx.get("factual", []) if isinstance(ctx, dict) else []
        if facts:
            return facts[0].get("value", "showed up consistently")[:80]
    except Exception:
        pass
    return "showed up consistently"


def _compute_next_milestone(
    level: int, trust: int, streak: int, msg_count: int, reached: list[str]
) -> dict | None:
    """Find the next closest milestone and compute progress %."""
    candidates = []

    # Next region milestone
    for r in progression_service.REGIONS:
        key = f"region_{r['key'].lower()}"
        if key not in reached and r["min"] > level:
            pct = round((level / max(r["min"], 1)) * 100, 1)
            candidates.append({"key": key, "title": r["key"].replace("_", " ").title(), "progress_pct": min(pct, 99)})
            break

    # Next trust milestone
    for t in progression_service.TRUST_MILESTONES:
        key = f"trust_{t}"
        if key not in reached and t > trust:
            pct = round((trust / t) * 100, 1)
            candidates.append({"key": key, "title": f"Trust Level {t}", "progress_pct": min(pct, 99)})
            break

    # Next streak milestone
    for s in progression_service.STREAK_MILESTONES:
        key = f"streak_{s}"
        if key not in reached and s > streak:
            pct = round((streak / s) * 100, 1)
            candidates.append({"key": key, "title": f"{s}-Day Streak", "progress_pct": min(pct, 99)})
            break

    # Return the closest one (highest progress %)
    if candidates:
        candidates.sort(key=lambda c: c["progress_pct"], reverse=True)
        return candidates[0]
    return None
