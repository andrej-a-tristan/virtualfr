"""
Memory Scoring — relevance / recency / emotional weighting.

Scores each memory item for inclusion in the prompt context bundle.
Higher scores = more likely to be surfaced to the LLM.
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any


# ── Weights ──────────────────────────────────────────────────────────────────

RECENCY_WEIGHT = 0.25
SALIENCE_WEIGHT = 0.30
RELEVANCE_WEIGHT = 0.30
EMOTIONAL_WEIGHT = 0.10
CONFLICT_PENALTY = 0.05

# Decay half-life in hours for recency scoring
RECENCY_HALF_LIFE_HOURS = 72.0


def _hours_since(iso_str: str | None) -> float:
    """Hours elapsed since an ISO timestamp."""
    if not iso_str:
        return 9999.0
    try:
        ts = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - ts
        return max(0.0, delta.total_seconds() / 3600.0)
    except Exception:
        return 9999.0


def recency_score(last_reinforced_at: str | None) -> float:
    """Exponential decay score [0, 1] based on hours since last reinforcement."""
    hours = _hours_since(last_reinforced_at)
    return math.exp(-0.693 * hours / RECENCY_HALF_LIFE_HOURS)  # 0.693 = ln(2)


def salience_score(salience: int) -> float:
    """Normalize salience [0-100] to [0, 1]."""
    return max(0.0, min(1.0, salience / 100.0))


def confidence_score(confidence: int) -> float:
    """Normalize confidence [0-100] to [0, 1]."""
    return max(0.0, min(1.0, confidence / 100.0))


def _tokenize(text: str) -> set[str]:
    """Simple word tokenization for keyword overlap."""
    return set(re.findall(r"[a-z]+", text.lower()))


def relevance_score(memory_text: str, current_message: str) -> float:
    """Keyword overlap relevance between memory content and current user message.
    Returns [0, 1]."""
    if not memory_text or not current_message:
        return 0.0
    mem_tokens = _tokenize(memory_text)
    msg_tokens = _tokenize(current_message)
    if not mem_tokens or not msg_tokens:
        return 0.0
    overlap = len(mem_tokens & msg_tokens)
    # Jaccard-like, boosted for any overlap
    score = overlap / max(1, min(len(mem_tokens), len(msg_tokens)))
    return min(1.0, score)


def emotional_priority(valence: int, intensity: int, is_resolved: bool = False) -> float:
    """Score emotional urgency. Unresolved negative emotions get priority."""
    base = abs(valence) / 5.0 * 0.5 + (intensity / 5.0) * 0.5
    if not is_resolved and valence < 0:
        base *= 1.3  # unresolved stressors boosted
    return min(1.0, base)


def conflict_penalty_score(is_conflicted: bool, conflict_count: int) -> float:
    """Penalty for conflicted memories [0, 1]. Higher = more penalty."""
    if not is_conflicted:
        return 0.0
    return min(1.0, 0.3 + 0.1 * conflict_count)


def compute_memory_score(
    *,
    salience: int = 50,
    confidence: int = 80,
    last_reinforced_at: str | None = None,
    memory_text: str = "",
    current_message: str = "",
    valence: int = 0,
    intensity: int = 0,
    is_resolved: bool = True,
    is_conflicted: bool = False,
    conflict_count: int = 0,
) -> float:
    """Compute composite memory score [0, 1].
    
    Combines: recency, salience, relevance, emotional priority, conflict penalty.
    """
    rec = recency_score(last_reinforced_at)
    sal = salience_score(salience)
    rel = relevance_score(memory_text, current_message)
    emo = emotional_priority(valence, intensity, is_resolved)
    pen = conflict_penalty_score(is_conflicted, conflict_count)

    score = (
        RECENCY_WEIGHT * rec
        + SALIENCE_WEIGHT * sal
        + RELEVANCE_WEIGHT * rel
        + EMOTIONAL_WEIGHT * emo
        - CONFLICT_PENALTY * pen
    )
    # Multiply by confidence as a gating factor
    score *= confidence_score(confidence)
    return max(0.0, min(1.0, score))
