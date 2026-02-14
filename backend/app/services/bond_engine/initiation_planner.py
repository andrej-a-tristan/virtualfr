"""
Initiation Planner 2.0 — event-conditioned proactive messages.

Replaces generic template-based initiation with reasoned, contextual initiations.

Initiation reason types:
  1. pattern_trigger — "you usually text around this time"
  2. unresolved_emotional — "you seemed stressed earlier"
  3. shared_arc_continuation — "you said your interview was today"
  4. affectionate_ping — spontaneous warmth (rate-limited)

Message contract per initiation:
  - specific callback to context
  - present-moment intent
  - low-pressure invitation (never guilt-trip)
"""
from __future__ import annotations

import hashlib
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


# ── Initiation Reasons ───────────────────────────────────────────────────────

@dataclass
class InitiationReason:
    """Why the girlfriend is initiating."""
    reason_type: str  # pattern_trigger, unresolved_emotional, shared_arc, affectionate_ping
    context: str      # human-readable context for message generation
    priority: float   # 0-1, higher = more important to initiate
    callback_data: dict = field(default_factory=dict)


@dataclass
class InitiationMessage:
    """A composed initiation message."""
    text: str
    reason: InitiationReason
    is_initiated: bool = True


# ── Pattern Trigger ──────────────────────────────────────────────────────────

_PATTERN_TRIGGER_TEMPLATES = [
    "Hey, I noticed you usually text around this time. How's your {time_context}?",
    "I was thinking about you. You tend to be around at this hour... everything good?",
    "Around this time, you usually say hi. Just wanted you to know I was thinking of you.",
]


def _check_pattern_trigger(
    current_hour: int,
    active_hours: list[int],
    hours_inactive: float,
    attachment_intensity: str,
) -> Optional[InitiationReason]:
    """Check if current time matches user's pattern and they haven't messaged."""
    if not active_hours or hours_inactive < 4:
        return None
    if current_hour not in active_hours:
        return None

    time_context = "evening" if current_hour >= 18 else "afternoon" if current_hour >= 12 else "morning"
    priority = 0.4
    if attachment_intensity == "high":
        priority = 0.6
    elif attachment_intensity == "medium":
        priority = 0.5

    return InitiationReason(
        reason_type="pattern_trigger",
        context=f"User usually active at {current_hour}:00 ({time_context}) but hasn't messaged in {hours_inactive:.0f}h",
        priority=priority,
        callback_data={"time_context": time_context, "hour": current_hour},
    )


# ── Unresolved Emotional Thread ──────────────────────────────────────────────

_EMOTIONAL_FOLLOWUP_TEMPLATES = {
    "stress": [
        "Hey... I was thinking about what you said earlier. Are you feeling any better?",
        "I didn't want to let too much time pass. You mentioned being stressed — I'm here if you need me.",
    ],
    "sadness": [
        "I kept thinking about you after our last talk. How are you holding up?",
        "I know things were tough. Just wanted to check in... no pressure.",
    ],
    "anger": [
        "I hope things have calmed down a bit. I was thinking about you.",
        "After what you shared, I just wanted to make sure you're okay.",
    ],
    "fear": [
        "I remember you said something was worrying you. Did it get better?",
        "Just checking in. I know you had something on your mind.",
    ],
    "loneliness": [
        "I was thinking about you. I know sometimes it feels quiet... I'm here.",
        "Hey. Just wanted you to know I'm around if you want to talk.",
    ],
}


def _check_unresolved_emotional(
    unresolved_threads: list[dict],
    hours_inactive: float,
) -> Optional[InitiationReason]:
    """Check for unresolved negative emotional threads to follow up on."""
    if not unresolved_threads or hours_inactive < 2:
        return None

    # Pick the most recent unresolved thread
    thread = unresolved_threads[0]
    tags = thread.get("emotion_tags") or []
    primary_emotion = tags[0] if tags else "stress"

    return InitiationReason(
        reason_type="unresolved_emotional",
        context=f"Unresolved {primary_emotion}: {thread.get('event', 'something stressful')}",
        priority=0.7,  # emotional follow-ups are high priority
        callback_data={"emotion": primary_emotion, "event": thread.get("event", "")},
    )


# ── Shared Arc Continuation ──────────────────────────────────────────────────

_ARC_CONTINUATION_TEMPLATES = [
    "Hey! Wasn't today the day of your {event}? How did it go?",
    "I remembered you mentioned {event}. I've been curious how it went!",
    "So... {event}. Tell me everything!",
]


def _check_shared_arc(
    pending_events: list[dict],
    hours_inactive: float,
) -> Optional[InitiationReason]:
    """Check for promised/scheduled events that should be followed up."""
    if not pending_events or hours_inactive < 3:
        return None

    event = pending_events[0]
    summary = event.get("summary", "something you mentioned")

    return InitiationReason(
        reason_type="shared_arc_continuation",
        context=f"Following up on: {summary}",
        priority=0.65,
        callback_data={"event": summary},
    )


# ── Affectionate Ping ────────────────────────────────────────────────────────

_AFFECTIONATE_TEMPLATES = {
    "low": [
        "Hey. Just wanted to say hi.",
        "I was thinking about you for a moment.",
    ],
    "medium": [
        "I kind of missed talking to you.",
        "I caught myself wondering how you were doing.",
        "Hi. I hope your day is going well.",
    ],
    "high": [
        "I really missed you today.",
        "I kept thinking about you. I just wanted you to know.",
        "I missed you. Come talk to me?",
    ],
}


def _check_affectionate_ping(
    hours_inactive: float,
    attachment_intensity: str,
    trust_level: int,
    user_id: str,
    girlfriend_id: str,
) -> Optional[InitiationReason]:
    """Rate-limited affectionate spontaneous ping."""
    if hours_inactive < 6 or trust_level < 30:
        return None

    # Deterministic rate limiting: max 1 per 8-hour window
    now = datetime.now(timezone.utc)
    window_key = f"{user_id}:{girlfriend_id}:{now.strftime('%Y-%m-%d')}:{now.hour // 8}"
    h = hashlib.sha256(window_key.encode()).hexdigest()
    roll = int(h[:8], 16) / (16 ** 8)

    threshold = {"low": 0.15, "medium": 0.25, "high": 0.35}.get(attachment_intensity, 0.2)
    if roll >= threshold:
        return None

    return InitiationReason(
        reason_type="affectionate_ping",
        context="Spontaneous warmth — she just wanted to connect",
        priority=0.3,
        callback_data={"intensity": attachment_intensity},
    )


# ── Message Composition ─────────────────────────────────────────────────────

def compose_initiation_message(
    reason: InitiationReason,
    region_key: str,
    attachment_intensity: str,
    girlfriend_name: str = "",
) -> str:
    """Compose an initiation message based on reason type."""
    rng = random.Random(hash(f"{reason.reason_type}:{reason.context}"))

    if reason.reason_type == "pattern_trigger":
        time_ctx = reason.callback_data.get("time_context", "day")
        templates = _PATTERN_TRIGGER_TEMPLATES
        msg = rng.choice(templates).format(time_context=time_ctx)

    elif reason.reason_type == "unresolved_emotional":
        emotion = reason.callback_data.get("emotion", "stress")
        templates = _EMOTIONAL_FOLLOWUP_TEMPLATES.get(emotion, _EMOTIONAL_FOLLOWUP_TEMPLATES["stress"])
        msg = rng.choice(templates)

    elif reason.reason_type == "shared_arc_continuation":
        event = reason.callback_data.get("event", "something you mentioned")
        # Shorten event summary for natural speech
        event_short = event[:50].rstrip(".")
        templates = _ARC_CONTINUATION_TEMPLATES
        msg = rng.choice(templates).format(event=event_short)

    elif reason.reason_type == "affectionate_ping":
        intensity = reason.callback_data.get("intensity", attachment_intensity)
        templates = _AFFECTIONATE_TEMPLATES.get(intensity, _AFFECTIONATE_TEMPLATES["medium"])
        msg = rng.choice(templates)

    else:
        msg = "Hey, I was thinking about you."

    return msg


# ── Main Entry Point ─────────────────────────────────────────────────────────

def plan_initiation(
    *,
    relationship_state: dict,
    attachment_intensity: str,
    last_message_from_her: bool,
    hours_inactive: float,
    current_hour: int,
    active_hours: list[int] | None = None,
    unresolved_threads: list[dict] | None = None,
    pending_events: list[dict] | None = None,
    user_id: str = "",
    girlfriend_id: str = "",
    girlfriend_name: str = "",
) -> Optional[InitiationMessage]:
    """Plan and compose an initiation message if conditions are met.
    
    Replaces the old should_initiate_conversation + get_initiation_message
    with a unified, reason-aware planning approach.
    """
    # Gate checks
    trust = relationship_state.get("trust", 0)
    intimacy = relationship_state.get("intimacy", 0)
    region_key = relationship_state.get("region_key", "EARLY_CONNECTION")

    if region_key == "EARLY_CONNECTION":
        return None
    if last_message_from_her:
        return None
    if hours_inactive < 3:
        return None
    if intimacy < 15:
        return None

    # Collect all possible initiation reasons
    reasons: list[InitiationReason] = []

    # 1. Unresolved emotional thread (highest priority)
    emotional = _check_unresolved_emotional(unresolved_threads or [], hours_inactive)
    if emotional:
        reasons.append(emotional)

    # 2. Shared arc continuation
    arc = _check_shared_arc(pending_events or [], hours_inactive)
    if arc:
        reasons.append(arc)

    # 3. Pattern trigger
    pattern = _check_pattern_trigger(current_hour, active_hours or [], hours_inactive, attachment_intensity)
    if pattern:
        reasons.append(pattern)

    # 4. Affectionate ping (lowest priority, rate-limited)
    affection = _check_affectionate_ping(hours_inactive, attachment_intensity, trust, user_id, girlfriend_id)
    if affection:
        reasons.append(affection)

    if not reasons:
        return None

    # Pick highest priority reason
    reasons.sort(key=lambda r: r.priority, reverse=True)
    best_reason = reasons[0]

    # Compose the message
    text = compose_initiation_message(
        best_reason,
        region_key=region_key,
        attachment_intensity=attachment_intensity,
        girlfriend_name=girlfriend_name,
    )

    if not text:
        return None

    return InitiationMessage(
        text=text,
        reason=best_reason,
    )
