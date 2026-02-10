"""
Initiation Engine: natural first message from her.
No spam, no guilt. Deterministic roll via hash for production.
"""
import hashlib
from typing import Optional

REGION_MULTIPLIER = {
    "EARLY_CONNECTION": 0,
    "COMFORT_FAMILIARITY": 0.8,
    "GROWING_CLOSENESS": 1.0,
    "EMOTIONAL_TRUST": 1.3,
    "DEEP_BOND": 1.5,
    "MUTUAL_DEVOTION": 1.6,
    "INTIMATE_PARTNERSHIP": 1.6,
    "SHARED_LIFE": 1.6,
    "ENDURING_COMPANIONSHIP": 1.6,
}
BASE_PROBABILITY = {"low": 0.05, "medium": 0.1, "high": 0.2}
MAX_PROBABILITY = 0.5

_INITIATION_TEMPLATES = {
    "EARLY_CONNECTION": {
        "low": [],
        "medium": [],
        "high": [],
    },
    "COMFORT_FAMILIARITY": {
        "low": ["Hey, I was just thinking about you."],
        "medium": ["I thought I'd say hi."],
        "high": ["I kind of missed talking to you."],
    },
    "GROWING_CLOSENESS": {
        "low": ["How has your day been?"],
        "medium": ["I caught myself wondering how you were doing."],
        "high": ["I missed you a bit today."],
    },
    "EMOTIONAL_TRUST": {
        "low": ["I like when we talk like this."],
        "medium": ["I felt like reaching out to you."],
        "high": ["I really wanted to hear from you."],
    },
    "DEEP_BOND": {
        "low": ["I was thinking about us."],
        "medium": ["I felt close to you earlier."],
        "high": ["I missed you. I just wanted you to know."],
    },
    "MUTUAL_DEVOTION": {
        "low": ["I was thinking about us."],
        "medium": ["I felt close to you earlier."],
        "high": ["I missed you. I just wanted you to know."],
    },
    "INTIMATE_PARTNERSHIP": {
        "low": ["Being with you just feels right."],
        "medium": ["I felt warm thinking about you."],
        "high": ["I really missed you today."],
    },
    "SHARED_LIFE": {
        "low": ["Our time together means everything."],
        "medium": ["I had a moment today where I just thought of us."],
        "high": ["I need you to know how much you mean to me."],
    },
    "ENDURING_COMPANIONSHIP": {
        "low": ["Every day with you is a gift."],
        "medium": ["I'm so grateful for what we have."],
        "high": ["I love us. I just wanted to say that."],
    },
}


def _deterministic_roll(user_id: str, girlfriend_id: str, day: str, hour_bucket: int) -> float:
    """Seeded roll in [0, 1) from (user_id, girlfriend_id, day, hour_bucket)."""
    s = f"{user_id}:{girlfriend_id}:{day}:{hour_bucket}"
    h = hashlib.sha256(s.encode()).hexdigest()
    return int(h[:8], 16) / (16**8)


def should_initiate_conversation(
    relationship_state: dict,
    attachment_intensity: str,
    last_message_from_her: bool,
    hours_since_last: float,
    current_hour: int,
    preferred_hours: Optional[list] = None,
    typical_gap_hours: Optional[int] = None,
    rng_override: Optional[float] = None,
    user_id: Optional[str] = None,
    girlfriend_id: Optional[str] = None,
) -> bool:
    if relationship_state.get("intimacy", 0) < 20:
        return False
    if last_message_from_her:
        return False
    if hours_since_last < 4:
        return False

    region_key = relationship_state.get("region_key", "EARLY_CONNECTION")
    if region_key == "EARLY_CONNECTION":
        return False

    p = BASE_PROBABILITY.get(attachment_intensity, 0.1)
    p *= REGION_MULTIPLIER.get(region_key, 1.0)
    if preferred_hours and current_hour in preferred_hours:
        p += 0.05
    if typical_gap_hours is not None and hours_since_last >= typical_gap_hours:
        p += 0.05
    p = min(p, MAX_PROBABILITY)

    if rng_override is not None:
        roll = rng_override
    elif user_id and girlfriend_id:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        day = now.strftime("%Y-%m-%d")
        hour_bucket = now.hour
        roll = _deterministic_roll(user_id, girlfriend_id, day, hour_bucket)
    else:
        import random
        roll = random.random()

    return roll < p


def get_initiation_message(region_key: str, attachment_intensity: str) -> str:
    """Get initiation message by region and attachment intensity. Returns empty string if no options."""
    templates = _INITIATION_TEMPLATES.get(region_key, _INITIATION_TEMPLATES["EARLY_CONNECTION"]).get(
        attachment_intensity, []
    )
    if not templates:
        return ""
    import random
    return random.choice(templates)
