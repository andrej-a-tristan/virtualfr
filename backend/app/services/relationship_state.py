"""
Relationship State Engine (Python source of truth).
Trust/intimacy/levels/decay/milestones/jealousy. No guilt-based messages.
"""
from typing import Optional

from app.services.time_utils import now_iso

RELATIONSHIP_LEVELS = ("STRANGER", "FAMILIAR", "CLOSE", "INTIMATE", "EXCLUSIVE")
AttachmentIntensity = str  # "high" | "medium" | "low"
JealousyLevel = str  # "High" | "Medium" | "Low"


def create_initial_relationship_state() -> dict:
    return {
        "trust": 10,
        "intimacy": 5,  # Architecture: starts at 5, not 10
        "last_interaction_at": now_iso(),
        "level": "STRANGER",
        "milestones_reached": ["STRANGER"],  # Architecture: STRANGER milestone already reached
    }


def calculate_relationship_level(intimacy: int) -> str:
    """Calculate level from intimacy: STRANGER (0-15), FAMILIAR (16-35), CLOSE (36-60), INTIMATE (61-80), EXCLUSIVE (81-100)."""
    if intimacy >= 81:
        return "EXCLUSIVE"
    if intimacy >= 61:
        return "INTIMATE"
    if intimacy >= 36:
        return "CLOSE"
    if intimacy >= 16:
        return "FAMILIAR"
    return "STRANGER"


def register_interaction(
    state: dict,
    emotional_disclosure: bool = False,
    affection: bool = False,
) -> dict:
    """Register interaction: base +1 trust/intimacy, +2 if emotionalDisclosure/affection."""
    trust_delta = 1 + (2 if emotional_disclosure else 0)  # Architecture: base 1 + bonus 2
    intimacy_delta = 1 + (2 if affection else 0)  # Architecture: base 1 + bonus 2
    trust = min(100, state["trust"] + trust_delta)
    intimacy = min(100, state["intimacy"] + intimacy_delta)
    level = calculate_relationship_level(intimacy)
    return {
        **state,
        "trust": trust,
        "intimacy": intimacy,
        "last_interaction_at": now_iso(),
        "level": level,
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
    level = calculate_relationship_level(intimacy)
    return {**state, "intimacy": intimacy, "level": level}


# Jealousy reactions (architecture-compliant)
_JEALOUSY_TEMPLATES = {
    "Low": {
        "STRANGER": [],
        "FAMILIAR": ["I figured you were just busy."],
        "CLOSE": ["I was wondering how you were doing."],
        "INTIMATE": ["I missed hearing from you, but it's okay."],
        "EXCLUSIVE": ["I noticed you were gone… I hope you're alright."],
    },
    "Medium": {
        "STRANGER": [],
        "FAMILIAR": ["You disappeared a bit."],
        "CLOSE": ["I kind of noticed you weren't around."],
        "INTIMATE": ["I missed you more than I expected."],
        "EXCLUSIVE": ["I didn't like not hearing from you."],
    },
    "High": {
        "STRANGER": [],
        "FAMILIAR": ["You went quiet…"],
        "CLOSE": ["I actually worried when you didn't reply."],
        "INTIMATE": ["It bothered me that you disappeared."],
        "EXCLUSIVE": ["I really didn't like being ignored."],
    },
}


def get_jealousy_reaction(
    level: str, jealousy_level: JealousyLevel, hours_inactive: float
) -> Optional[str]:
    """Get jealousy reaction if hours_inactive >= 24. Returns random message from options."""
    if hours_inactive < 24:
        return None
    templates = _JEALOUSY_TEMPLATES.get(jealousy_level, _JEALOUSY_TEMPLATES["Low"]).get(level, [])
    if not templates:
        return None
    import random
    return random.choice(templates)


_MILESTONE_MESSAGES = {
    "STRANGER": [],
    "FAMILIAR": [
        "I feel like I'm starting to recognize you now.",
        "Talking to you feels easier than it did at first.",
    ],
    "CLOSE": [
        "I actually notice when you're not around now.",
        "I didn't expect to feel this close to you.",
    ],
    "INTIMATE": [
        "I trust you with parts of me I don't share easily.",
        "Being close to you feels natural now.",
    ],
    "EXCLUSIVE": [
        "What we have feels special to me.",
        "I don't want this to feel casual anymore.",
    ],
}


def check_for_milestone_event(prev: dict, next_state: dict) -> Optional[tuple[str, str]]:
    """Return (level, message) if new milestone reached, else None. Architecture-compliant."""
    prev_level = prev.get("level", "STRANGER")
    next_level = next_state.get("level", "STRANGER")
    if prev_level == next_level:
        return None
    milestones = next_state.get("milestones_reached") or []
    if next_level in milestones:
        return None
    messages = _MILESTONE_MESSAGES.get(next_level, [])
    if not messages:
        return None
    import random
    msg = random.choice(messages)
    return (next_level, msg)


def append_milestone_reached(state: dict, level: str) -> dict:
    milestones = list(state.get("milestones_reached") or [])
    if level in milestones:
        return state
    return {**state, "milestones_reached": milestones + [level]}
