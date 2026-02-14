"""
Response Director — anti-repetition, novelty budgets, cadence alternation.

Ensures the girlfriend's responses never feel boring or repetitive:
  - Phrase blacklist from last N turns
  - Rhetorical pattern rotation (statement, question, reflection, callback)
  - Emotional cadence alternation (supportive/playful/reflective/teasing)
  - Topic continuity planner (continue, deepen, pivot ratios)
  - Assistant style fingerprint + near-duplicate penalty
"""
from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


# ── Response Contract ────────────────────────────────────────────────────────

@dataclass
class ResponseContract:
    """Directives for how the next response should be structured."""
    # Tone/cadence
    suggested_cadence: str = "neutral"  # supportive, playful, reflective, teasing, neutral
    # Topic direction
    topic_action: str = "continue"  # continue, deepen, pivot
    # Memory usage
    max_callbacks: int = 2  # max memory references per message
    # Novelty constraints
    blacklisted_phrases: list[str] = field(default_factory=list)
    blacklisted_openings: list[str] = field(default_factory=list)
    # Pattern to use
    suggested_pattern: str = "statement"  # statement, question, reflection, callback, tease

    def to_prompt_section(self) -> str:
        """Build prompt instructions from this contract."""
        lines = ["RESPONSE DIRECTION (follow these for this message):"]
        lines.append(f"  Emotional tone: {self.suggested_cadence}")
        lines.append(f"  Topic: {self.topic_action} the current thread")
        lines.append(f"  Structure: lead with a {self.suggested_pattern}")
        lines.append(f"  Memory callbacks: max {self.max_callbacks}")

        if self.blacklisted_phrases:
            phrases_str = ", ".join(f'"{p}"' for p in self.blacklisted_phrases[:5])
            lines.append(f"  AVOID these phrases (used recently): {phrases_str}")

        if self.blacklisted_openings:
            openings_str = ", ".join(f'"{o}"' for o in self.blacklisted_openings[:3])
            lines.append(f"  DON'T open with: {openings_str}")

        return "\n".join(lines)


# ── Cadence Planning ─────────────────────────────────────────────────────────

CADENCE_CYCLE = ["supportive", "playful", "reflective", "neutral", "teasing"]

# Map trait-based constraints on cadence
_TRAIT_CADENCE_LIMITS: dict[str, list[str]] = {
    "Caring": ["supportive", "reflective", "neutral", "playful"],
    "Playful": ["playful", "teasing", "supportive", "neutral"],
    "Reserved": ["neutral", "reflective", "supportive"],
    "Protective": ["supportive", "neutral", "reflective"],
}


def _suggest_cadence(
    recent_cadences: list[str],
    emotional_style: str,
    user_emotion: str | None = None,
) -> str:
    """Suggest next cadence based on recent history and personality."""
    allowed = _TRAIT_CADENCE_LIMITS.get(emotional_style, CADENCE_CYCLE)

    # If user just shared an emotion, be supportive
    if user_emotion and user_emotion in ("stress", "sadness", "fear", "anger", "loneliness"):
        return "supportive"
    if user_emotion in ("excitement", "happiness"):
        return "playful"

    # Otherwise, alternate to avoid monotony
    if recent_cadences:
        last = recent_cadences[-1] if recent_cadences[-1] in allowed else "neutral"
        # Pick next in cycle that's different from last 2
        recent_set = set(recent_cadences[-2:])
        for c in allowed:
            if c not in recent_set:
                return c
        return allowed[0]  # fallback

    return allowed[0]


# ── Pattern Rotation ─────────────────────────────────────────────────────────

PATTERN_CYCLE = ["statement", "question", "reflection", "callback", "tease"]


def _suggest_pattern(
    recent_patterns: list[str],
    has_memory_to_callback: bool,
    cadence: str,
) -> str:
    """Suggest rhetorical pattern for the response."""
    # Callbacks require available memories
    available = list(PATTERN_CYCLE)
    if not has_memory_to_callback:
        available = [p for p in available if p != "callback"]
    if cadence != "teasing":
        available = [p for p in available if p != "tease"]

    if recent_patterns:
        recent_set = set(recent_patterns[-2:])
        for p in available:
            if p not in recent_set:
                return p

    return available[0] if available else "statement"


# ── Topic Direction ──────────────────────────────────────────────────────────

def _suggest_topic_action(
    recent_topic_actions: list[str],
    message_count_in_topic: int,
) -> str:
    """Suggest whether to continue, deepen, or pivot the current topic."""
    # After 4+ messages on same topic, suggest pivot
    if message_count_in_topic >= 4:
        return "pivot"
    # After 2-3 messages, suggest deepening
    if message_count_in_topic >= 2:
        return "deepen"
    # Default: continue
    return "continue"


# ── Phrase Blacklisting ──────────────────────────────────────────────────────

def _extract_signature_phrases(text: str) -> list[str]:
    """Extract notable phrases from a response for blacklisting."""
    # Extract opening phrase (first ~40 chars)
    opening = text.strip()[:40].lower().rstrip(".,!?")

    # Extract sentences
    sentences = [s.strip().lower() for s in re.split(r"[.!?]+", text) if s.strip()]

    # Collect phrases to avoid repeating
    phrases: list[str] = []
    if opening and len(opening) > 10:
        phrases.append(opening)
    for s in sentences:
        if len(s) > 15:
            phrases.append(s[:50])

    return phrases[:5]  # limit


def _extract_opening(text: str) -> str:
    """Extract the opening phrase of a message."""
    stripped = text.strip()
    # First sentence or first 50 chars
    first_sentence = re.split(r"[.!?]", stripped)[0].strip()
    return first_sentence[:50].lower()


# ── Style Fingerprint ────────────────────────────────────────────────────────

def compute_style_fingerprint(text: str) -> dict:
    """Compute a style fingerprint for near-duplicate detection."""
    lower = text.lower()
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]

    return {
        "length": len(text),
        "sentence_count": len(sentences),
        "has_question": "?" in text,
        "has_emoji": bool(re.search(r"[\U0001F600-\U0001F64F❤💕😊]", text)),
        "opening_hash": hashlib.md5(lower[:50].encode()).hexdigest()[:8],
        "phrases": _extract_signature_phrases(text),
    }


# ── Main Planning Function ──────────────────────────────────────────────────

def plan_response_contract(
    recent_assistant_turns: list[str],
    emotional_style: str = "Caring",
    user_emotion: str | None = None,
    has_memory_to_callback: bool = False,
    message_count_in_topic: int = 0,
    recent_fingerprints: list[dict] | None = None,
) -> ResponseContract:
    """Plan the response contract for the next assistant turn.
    
    Analyzes recent turns to ensure variety, then produces directives
    for the LLM system prompt.
    """
    # Extract recent cadences and patterns from fingerprints
    recent_cadences: list[str] = []
    recent_patterns: list[str] = []
    recent_topic_actions: list[str] = []

    for fp in (recent_fingerprints or []):
        recent_cadences.append(fp.get("cadence", "neutral"))
        recent_patterns.append(fp.get("pattern", "statement"))
        recent_topic_actions.append(fp.get("topic_action", "continue"))

    # Plan cadence
    cadence = _suggest_cadence(recent_cadences, emotional_style, user_emotion)

    # Plan pattern
    pattern = _suggest_pattern(recent_patterns, has_memory_to_callback, cadence)

    # Plan topic action
    topic_action = _suggest_topic_action(recent_topic_actions, message_count_in_topic)

    # Build phrase blacklist from recent turns
    blacklisted_phrases: list[str] = []
    blacklisted_openings: list[str] = []
    for turn in (recent_assistant_turns or [])[-5:]:
        blacklisted_phrases.extend(_extract_signature_phrases(turn))
        opening = _extract_opening(turn)
        if opening and len(opening) > 5:
            blacklisted_openings.append(opening)

    # Deduplicate
    blacklisted_phrases = list(dict.fromkeys(blacklisted_phrases))[:10]
    blacklisted_openings = list(dict.fromkeys(blacklisted_openings))[:5]

    # Max callbacks based on cadence
    max_callbacks = 2 if cadence in ("reflective", "supportive") else 1

    return ResponseContract(
        suggested_cadence=cadence,
        topic_action=topic_action,
        max_callbacks=max_callbacks,
        blacklisted_phrases=blacklisted_phrases,
        blacklisted_openings=blacklisted_openings,
        suggested_pattern=pattern,
    )
