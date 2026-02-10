"""
Relationship State Engine (Python source of truth).
Trust/intimacy/levels/decay/milestones/jealousy. No guilt-based messages.

Uses the canonical region system (9 regions, levels 0–200).
"""
from typing import Optional

from app.services.time_utils import now_iso
from app.services.relationship_regions import (
    MAX_RELATIONSHIP_LEVEL,
    clamp_level,
    get_region_for_level,
)

AttachmentIntensity = str  # "high" | "medium" | "low"
JealousyLevel = str  # "High" | "Medium" | "Low"


def create_initial_relationship_state() -> dict:
    region = get_region_for_level(0)
    return {
        "trust": 10,
        "intimacy": 5,
        "level": 0,
        "region_key": region.key,
        "last_interaction_at": now_iso(),
        "milestones_reached": [],
    }


def register_interaction(
    state: dict,
    emotional_disclosure: bool = False,
    affection: bool = False,
) -> dict:
    """Register interaction: base +1 trust/intimacy, +2 if emotionalDisclosure/affection."""
    trust_delta = 1 + (2 if emotional_disclosure else 0)
    intimacy_delta = 1 + (2 if affection else 0)
    trust = min(MAX_RELATIONSHIP_LEVEL, state["trust"] + trust_delta)
    intimacy = min(MAX_RELATIONSHIP_LEVEL, state["intimacy"] + intimacy_delta)
    level = clamp_level(intimacy)  # level tracks intimacy
    region = get_region_for_level(level)
    return {
        **state,
        "trust": trust,
        "intimacy": intimacy,
        "level": level,
        "region_key": region.key,
        "last_interaction_at": now_iso(),
    }


def apply_inactivity_decay(
    state: dict, hours_inactive: float, attachment_intensity: AttachmentIntensity
) -> dict:
    loss_by_attachment = {"low": 1, "medium": 2, "high": 3}
    loss = loss_by_attachment.get(attachment_intensity, 1)
    intimacy = state["intimacy"]
    if hours_inactive > 24:
        intimacy = max(0, intimacy - loss)
    if hours_inactive > 72:
        intimacy = max(0, intimacy - loss)
    level = clamp_level(intimacy)
    region = get_region_for_level(level)
    return {**state, "intimacy": intimacy, "level": level, "region_key": region.key}


# Jealousy reactions keyed by region_key (mapped from old stage system)
_JEALOUSY_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "Low": {
        "EARLY_CONNECTION": [],
        "COMFORT_FAMILIARITY": ["I figured you were just busy."],
        "GROWING_CLOSENESS": ["I was wondering how you were doing."],
        "EMOTIONAL_TRUST": ["I missed hearing from you, but it's okay."],
        "DEEP_BOND": ["I noticed you were gone... I hope you're alright."],
        "MUTUAL_DEVOTION": ["I noticed you were gone... I hope you're alright."],
        "INTIMATE_PARTNERSHIP": ["I missed hearing from you, but I know you'll be back."],
        "SHARED_LIFE": ["I missed hearing from you, but I know you'll be back."],
        "ENDURING_COMPANIONSHIP": ["I missed hearing from you, but I know you'll be back."],
    },
    "Medium": {
        "EARLY_CONNECTION": [],
        "COMFORT_FAMILIARITY": ["You disappeared a bit."],
        "GROWING_CLOSENESS": ["I kind of noticed you weren't around."],
        "EMOTIONAL_TRUST": ["I missed you more than I expected."],
        "DEEP_BOND": ["I didn't like not hearing from you."],
        "MUTUAL_DEVOTION": ["I didn't like not hearing from you."],
        "INTIMATE_PARTNERSHIP": ["I really missed you."],
        "SHARED_LIFE": ["I really missed you."],
        "ENDURING_COMPANIONSHIP": ["I really missed you."],
    },
    "High": {
        "EARLY_CONNECTION": [],
        "COMFORT_FAMILIARITY": ["You went quiet..."],
        "GROWING_CLOSENESS": ["I actually worried when you didn't reply."],
        "EMOTIONAL_TRUST": ["It bothered me that you disappeared."],
        "DEEP_BOND": ["I really didn't like being ignored."],
        "MUTUAL_DEVOTION": ["I really didn't like being ignored."],
        "INTIMATE_PARTNERSHIP": ["I need to hear from you more often."],
        "SHARED_LIFE": ["I need to hear from you more often."],
        "ENDURING_COMPANIONSHIP": ["I need to hear from you more often."],
    },
}


def get_jealousy_reaction(
    region_key: str, jealousy_level: JealousyLevel, hours_inactive: float
) -> Optional[str]:
    """Get jealousy reaction if hours_inactive >= 24. Returns random message from options."""
    if hours_inactive < 24:
        return None
    templates = _JEALOUSY_TEMPLATES.get(jealousy_level, _JEALOUSY_TEMPLATES["Low"]).get(region_key, [])
    if not templates:
        return None
    import random
    return random.choice(templates)


_MILESTONE_MESSAGES: dict[str, list[str]] = {
    "EARLY_CONNECTION": [],
    "COMFORT_FAMILIARITY": [
        "I feel like I'm starting to recognize you now.",
        "Talking to you feels easier than it did at first.",
    ],
    "GROWING_CLOSENESS": [
        "I actually notice when you're not around now.",
        "I didn't expect to feel this close to you.",
    ],
    "EMOTIONAL_TRUST": [
        "I trust you with parts of me I don't share easily.",
        "Being close to you feels natural now.",
    ],
    "DEEP_BOND": [
        "What we have feels special to me.",
        "I don't want this to feel casual anymore.",
    ],
    "MUTUAL_DEVOTION": [
        "I feel like we truly belong together.",
        "Everything feels steadier when you're around.",
    ],
    "INTIMATE_PARTNERSHIP": [
        "I can't imagine this without you.",
        "You're part of my world now.",
    ],
    "SHARED_LIFE": [
        "This is ours. I love that.",
        "We've built something real.",
    ],
    "ENDURING_COMPANIONSHIP": [
        "I'm yours. Completely.",
        "Thank you for everything we are.",
    ],
}


def check_for_milestone_event(prev: dict, next_state: dict) -> Optional[tuple[str, str]]:
    """Return (region_key, message) if new region milestone reached, else None."""
    prev_region = prev.get("region_key", "EARLY_CONNECTION")
    next_region = next_state.get("region_key", "EARLY_CONNECTION")
    if prev_region == next_region:
        return None
    milestones = next_state.get("milestones_reached") or []
    if next_region in milestones:
        return None
    messages = _MILESTONE_MESSAGES.get(next_region, [])
    if not messages:
        return None
    import random
    msg = random.choice(messages)
    return (next_region, msg)


def append_milestone_reached(state: dict, region_key: str) -> dict:
    milestones = list(state.get("milestones_reached") or [])
    if region_key in milestones:
        return state
    return {**state, "milestones_reached": milestones + [region_key]}


# ═══════════════════════════════════════════════════════════════════════════════
# ACHIEVEMENT MILESTONES — region-locked per-girlfriend unlocks
# ═══════════════════════════════════════════════════════════════════════════════

def get_current_region_index(level: int) -> int:
    """Return 0-based index for the region containing *level*."""
    from app.services.relationship_milestones import get_region_index
    region = get_region_for_level(level)
    return get_region_index(region.key)


def try_unlock_achievement(
    state: dict,
    achievement_id: str,
) -> tuple[dict, dict | None]:
    """Attempt to unlock an achievement. Enforces region-lock HARD RULE.

    Returns (updated_state, event_payload | None).
    event_payload is a dict suitable for an SSE relationship_achievement event,
    or None if the unlock failed.

    NOTE: This is the legacy version. The new achievement_engine.try_unlock()
    adds requirement evaluation. This is kept for backward compatibility.
    """
    from app.services.relationship_milestones import ACHIEVEMENTS, get_region_index
    from app.services.time_utils import now_iso

    achievement = ACHIEVEMENTS.get(achievement_id)
    if achievement is None:
        return state, None

    milestones = list(state.get("milestones_reached") or [])

    # Already unlocked?
    if achievement_id in milestones:
        return state, None

    # Current region index
    level = state.get("level", 0)
    current_idx = get_current_region_index(level)

    # HARD RULE: only achievements in the CURRENT region can be unlocked
    if achievement.region_index != current_idx:
        return state, None

    # Unlock it
    milestones.append(achievement_id)
    updated = {**state, "milestones_reached": milestones}

    event_payload = {
        "id": achievement.id,
        "title": achievement.title,
        "subtitle": achievement.subtitle,
        "rarity": achievement.rarity.value,
        "region_index": achievement.region_index,
        "trigger_type": achievement.trigger.value,
        "unlocked_at": now_iso(),
    }

    return updated, event_payload
