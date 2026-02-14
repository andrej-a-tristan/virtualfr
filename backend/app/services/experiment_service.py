"""ExperimentService — personality-driven tone selection.

Instead of random A/B testing, uses the girlfriend's onboarding traits
to determine the tone and style of milestone messages. Each girlfriend
personality produces a consistent, matching communication style.

Tone mapping:
  emotional_style + communication_style + attachment_style + cultural_personality
  → one of: playful, warm, direct, passionate, gentle
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Tone categories ───────────────────────────────────────────────────────────
# These map to template variants in message_composer / message_templates

TONES = ["playful", "warm", "direct", "passionate", "gentle"]

# ── Trait → Tone scoring matrix ───────────────────────────────────────────────
# Each trait value adds weight to one or more tones.

_EMOTIONAL_STYLE_SCORES: dict[str, dict[str, float]] = {
    "Playful":    {"playful": 3.0, "passionate": 1.0},
    "Reserved":   {"gentle": 2.5, "direct": 1.5},
    "Protective": {"warm": 3.0, "gentle": 1.0},
}

_COMMUNICATION_STYLE_SCORES: dict[str, dict[str, float]] = {
    "Direct":  {"direct": 3.0, "passionate": 0.5},
    "Teasing": {"playful": 3.0, "passionate": 1.0},
    "Soft":    {"warm": 2.0, "gentle": 2.0},
}

_ATTACHMENT_STYLE_SCORES: dict[str, dict[str, float]] = {
    "Very attached":       {"passionate": 2.0, "warm": 1.5},
    "Emotionally present": {"warm": 2.0, "gentle": 1.0},
    "Calm but caring":     {"gentle": 2.5, "direct": 0.5},
}

_CULTURAL_PERSONALITY_SCORES: dict[str, dict[str, float]] = {
    "Warm Slavic":           {"warm": 2.0, "gentle": 1.0},
    "Calm Central European": {"direct": 2.0, "gentle": 1.0},
    "Passionate Balkan":     {"passionate": 3.0, "playful": 1.0},
}

_REACTION_TO_ABSENCE_SCORES: dict[str, dict[str, float]] = {
    "High":   {"passionate": 1.5, "warm": 1.0},
    "Medium": {"warm": 1.0, "gentle": 0.5},
    "Low":    {"gentle": 1.0, "direct": 0.5},
}


def resolve_tone_from_traits(traits: dict[str, Any]) -> str:
    """Compute the best matching tone from a girlfriend's trait dict.

    Args:
        traits: Girlfriend's traits dict from onboarding, e.g.:
            {
                "emotional_style": "Playful",
                "communication_style": "Teasing",
                "attachment_style": "Very attached",
                "cultural_personality": "Passionate Balkan",
                "reaction_to_absence": "High",
            }

    Returns:
        One of: "playful", "warm", "direct", "passionate", "gentle"
    """
    scores: dict[str, float] = {t: 0.0 for t in TONES}

    # Score each trait dimension
    _add_scores(scores, _EMOTIONAL_STYLE_SCORES, traits.get("emotional_style", ""))
    _add_scores(scores, _COMMUNICATION_STYLE_SCORES, traits.get("communication_style", ""))
    _add_scores(scores, _ATTACHMENT_STYLE_SCORES, traits.get("attachment_style", ""))
    _add_scores(scores, _CULTURAL_PERSONALITY_SCORES, traits.get("cultural_personality", ""))
    _add_scores(scores, _REACTION_TO_ABSENCE_SCORES, traits.get("reaction_to_absence", ""))

    # Pick highest scoring tone
    best_tone = max(scores, key=lambda t: scores[t])

    # If all zero (no traits matched), default to warm
    if scores[best_tone] == 0:
        best_tone = "warm"

    logger.debug(f"Tone resolved: {best_tone} (scores: {scores}) from traits: {traits}")
    return best_tone


def _add_scores(
    scores: dict[str, float],
    mapping: dict[str, dict[str, float]],
    trait_value: str,
) -> None:
    """Add scores from a trait value to the running totals."""
    additions = mapping.get(trait_value, {})
    for tone, weight in additions.items():
        if tone in scores:
            scores[tone] += weight


# ── Convenience: get variant for a user (kept for backward compat) ────────────

def get_variant(user_id: str, experiment_key: str, traits: dict[str, Any] | None = None) -> str:
    """Get the tone variant based on girlfriend traits.

    If traits are provided, resolves tone from personality.
    Falls back to 'warm' if no traits available.
    """
    if traits:
        return resolve_tone_from_traits(traits)
    return "warm"


def assign_variant(user_id: str, experiment_key: str, traits: dict[str, Any] | None = None) -> str:
    """Alias for get_variant (backward compat)."""
    return get_variant(user_id, experiment_key, traits)


def get_all_assignments(user_id: str, traits: dict[str, Any] | None = None) -> dict[str, str]:
    """Get tone assignment for all 'experiments' (now trait-driven)."""
    tone = resolve_tone_from_traits(traits or {})
    return {
        "milestone_tone": tone,
    }
