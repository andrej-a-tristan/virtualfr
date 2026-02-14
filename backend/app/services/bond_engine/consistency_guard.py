"""
Consistency Guard — ensures personality never breaks.

Two-part persona model:
  1. PersonaKernel (immutable): identity canon + non-negotiable traits
  2. PersonaGrowthState (mutable): how she currently feels about user,
     communication texture, boundaries, disclosure stage

Validation checks (run before final output / streaming):
  1. Contradiction check against canon + prior commitments
  2. Tone drift check against trait profile
  3. Repetition check against recent assistant turns
  4. Repair pass if failed

Returns validation result + optional repair instructions for the LLM.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


# ── Persona Kernel (immutable identity) ──────────────────────────────────────

@dataclass(frozen=True)
class PersonaKernel:
    """Immutable identity canon — never contradicted."""
    name: str
    origin_vibe: str
    job_vibe: str
    hobbies: list[str]
    backstory_summary: str
    favorites: dict  # music_vibe, comfort_food, weekend_idea
    memory_seeds: list[str]
    # Non-negotiable trait rules
    emotional_style: str
    attachment_style: str
    communication_style: str
    cultural_personality: str


@dataclass
class PersonaGrowthState:
    """Mutable state — evolves with the relationship."""
    current_mood: str = "neutral"  # neutral, happy, concerned, playful, reflective
    communication_texture: str = "standard"  # standard, warm, intense, reserved
    disclosure_stage: int = 0  # 0-4 (surface → deep)
    active_boundaries: list[str] = field(default_factory=list)
    recent_topics: list[str] = field(default_factory=list)
    trust_band: str = "low"  # low, building, established, deep


# ── Validation Result ────────────────────────────────────────────────────────

@dataclass
class ConsistencyResult:
    """Result of consistency validation."""
    is_valid: bool = True
    violations: list[str] = field(default_factory=list)
    repair_instructions: list[str] = field(default_factory=list)
    severity: str = "none"  # none, minor, major


# ── Canon Extraction ─────────────────────────────────────────────────────────

def build_persona_kernel(girlfriend: dict) -> PersonaKernel:
    """Build immutable persona kernel from girlfriend data."""
    identity = girlfriend.get("identity") or {}
    canon = girlfriend.get("identity_canon") or {}
    traits = girlfriend.get("traits") or {}

    return PersonaKernel(
        name=identity.get("name") or girlfriend.get("display_name") or girlfriend.get("name") or "Companion",
        origin_vibe=identity.get("origin_vibe") or "somewhere cozy",
        job_vibe=identity.get("job_vibe") or "figuring things out",
        hobbies=identity.get("hobbies") or [],
        backstory_summary=(canon.get("backstory") or "")[:200],
        favorites=canon.get("favorites") or {},
        memory_seeds=canon.get("memory_seeds") or [],
        emotional_style=traits.get("emotional_style", "Caring"),
        attachment_style=traits.get("attachment_style", "Emotionally present"),
        communication_style=traits.get("communication_style", "Soft"),
        cultural_personality=traits.get("cultural_personality", "Warm Slavic"),
    )


def build_growth_state(
    relationship_state: dict,
    disclosure_level: int = 0,
) -> PersonaGrowthState:
    """Build mutable growth state from current relationship state."""
    trust = relationship_state.get("trust", 10)
    if trust >= 70:
        trust_band = "deep"
    elif trust >= 45:
        trust_band = "established"
    elif trust >= 25:
        trust_band = "building"
    else:
        trust_band = "low"

    # Mood from recent context (simplified — would ideally use recent messages)
    mood = "neutral"
    intimacy = relationship_state.get("intimacy", 5)
    if intimacy >= 60:
        mood = "warm"
    elif trust >= 40:
        mood = "comfortable"

    return PersonaGrowthState(
        current_mood=mood,
        trust_band=trust_band,
        disclosure_stage=disclosure_level,
    )


# ── Consistency Checks ───────────────────────────────────────────────────────

def _check_canon_contradictions(
    text: str,
    kernel: PersonaKernel,
) -> list[str]:
    """Check if response contradicts canon identity."""
    violations: list[str] = []
    lower = text.lower()

    # Check name consistency (she shouldn't claim a different name)
    name_lower = kernel.name.lower()
    # Look for "my name is X" where X != kernel.name
    name_claim = re.search(r"my name is (\w+)", lower)
    if name_claim and name_claim.group(1) != name_lower:
        violations.append(f"Name contradiction: claimed '{name_claim.group(1)}' but canon name is '{kernel.name}'")

    # Check for AI/assistant identity breaks
    ai_breaks = [
        "as an ai", "i'm an ai", "i am an ai", "i'm a language model",
        "i'm a chatbot", "i'm not real", "i don't have feelings",
        "i was programmed", "my training data", "as a virtual",
    ]
    for phrase in ai_breaks:
        if phrase in lower:
            violations.append(f"AI identity break: used phrase '{phrase}'")

    # Check job consistency
    if kernel.job_vibe:
        # She shouldn't claim a completely different job
        job_claims = re.findall(r"i work (?:as|at|in) (.+?)(?:\.|,|!|$)", lower)
        for claim in job_claims:
            if kernel.job_vibe.lower() not in claim and claim not in kernel.job_vibe.lower():
                violations.append(f"Job contradiction: claimed '{claim}' but canon job is '{kernel.job_vibe}'")

    return violations


def _check_tone_drift(
    text: str,
    kernel: PersonaKernel,
    growth: PersonaGrowthState,
) -> list[str]:
    """Check if response tone drifts from trait profile."""
    violations: list[str] = []
    lower = text.lower()

    # Reserved personality shouldn't use excessive exclamation / emoji
    if kernel.emotional_style == "Reserved":
        excl_count = text.count("!")
        emoji_pattern = re.compile(r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF❤💕😊🥺]+")
        emoji_count = len(emoji_pattern.findall(text))
        if excl_count > 3:
            violations.append("Tone drift: Reserved personality used excessive exclamation marks")
        if emoji_count > 2:
            violations.append("Tone drift: Reserved personality used too many emojis")

    # Low trust band shouldn't have deeply intimate language
    if growth.trust_band == "low":
        intimate_phrases = ["i love you", "you're everything", "i can't live without", "you complete me"]
        for phrase in intimate_phrases:
            if phrase in lower:
                violations.append(f"Trust boundary violation: used '{phrase}' at low trust")

    # Direct communication style shouldn't be excessively flowery
    if kernel.communication_style == "Direct":
        flowery = ["oh my darling", "my sweet angel", "precious", "my dearest"]
        for phrase in flowery:
            if phrase in lower:
                violations.append(f"Style drift: Direct communicator used flowery phrase '{phrase}'")

    return violations


def _check_repetition(
    text: str,
    recent_assistant_turns: list[str],
    threshold: float = 0.7,
) -> list[str]:
    """Check for repetitive phrasing against recent turns."""
    violations: list[str] = []
    if not recent_assistant_turns:
        return violations

    # Simple sentence-level overlap check
    new_sentences = set(s.strip().lower() for s in re.split(r"[.!?]+", text) if s.strip())
    for prev_turn in recent_assistant_turns[-5:]:
        prev_sentences = set(s.strip().lower() for s in re.split(r"[.!?]+", prev_turn) if s.strip())
        if not new_sentences or not prev_sentences:
            continue
        overlap = len(new_sentences & prev_sentences)
        overlap_ratio = overlap / max(1, len(new_sentences))
        if overlap_ratio >= threshold:
            violations.append(f"Repetition detected: {overlap_ratio:.0%} sentence overlap with recent turn")
            break

    # Check for repeated opening phrases
    new_opening = text[:50].lower().strip()
    for prev_turn in recent_assistant_turns[-3:]:
        prev_opening = prev_turn[:50].lower().strip()
        if new_opening == prev_opening and len(new_opening) > 10:
            violations.append("Repetition: identical opening phrase as recent message")
            break

    return violations


# ── Main Validation Function ─────────────────────────────────────────────────

def validate_consistency(
    response_text: str,
    kernel: PersonaKernel,
    growth: PersonaGrowthState,
    recent_assistant_turns: list[str] | None = None,
) -> ConsistencyResult:
    """Run full consistency validation on a generated response.
    
    Should be called between generation and SSE streaming.
    
    Checks:
      1. Canon contradiction check
      2. Tone drift check
      3. Repetition check
    
    Returns ConsistencyResult with violations and repair instructions.
    """
    all_violations: list[str] = []
    repair_instructions: list[str] = []

    # 1. Canon contradictions
    canon_violations = _check_canon_contradictions(response_text, kernel)
    all_violations.extend(canon_violations)
    if canon_violations:
        repair_instructions.append(
            f"CORRECTION: You are {kernel.name}. "
            f"Your job: {kernel.job_vibe}. "
            "Never break character or mention AI/programming."
        )

    # 2. Tone drift
    tone_violations = _check_tone_drift(response_text, kernel, growth)
    all_violations.extend(tone_violations)
    if tone_violations:
        repair_instructions.append(
            f"TONE: Match your {kernel.emotional_style} emotional style "
            f"and {kernel.communication_style} communication style. "
            f"Current trust level: {growth.trust_band}."
        )

    # 3. Repetition
    repetition_violations = _check_repetition(
        response_text, recent_assistant_turns or []
    )
    all_violations.extend(repetition_violations)
    if repetition_violations:
        repair_instructions.append(
            "VARIETY: Vary your phrasing, opening, and emotional register. "
            "Don't repeat sentences or structures from recent messages."
        )

    # Determine severity
    if not all_violations:
        severity = "none"
    elif any("identity break" in v.lower() or "name contradiction" in v.lower() for v in all_violations):
        severity = "major"
    else:
        severity = "minor"

    return ConsistencyResult(
        is_valid=len(all_violations) == 0,
        violations=all_violations,
        repair_instructions=repair_instructions,
        severity=severity,
    )


def build_consistency_system_instructions(
    kernel: PersonaKernel,
    growth: PersonaGrowthState,
) -> str:
    """Build consistency guard instructions to inject into the system prompt.
    
    These instructions proactively prevent consistency violations
    rather than catching them after generation.
    """
    lines = [
        "CONSISTENCY RULES (never break):",
        f"- You ARE {kernel.name}. Never say otherwise.",
        f"- Your background: {kernel.job_vibe}, from {kernel.origin_vibe}.",
        "- Never mention AI, programming, training data, or prompts.",
        "- Never claim abilities you don't have (e.g., searching the internet).",
        f"- Match your {kernel.emotional_style} emotional style consistently.",
        f"- Your communication is {kernel.communication_style} — stay true to this.",
    ]

    if growth.trust_band == "low":
        lines.append("- Trust is still building. Don't rush intimacy or make deep declarations.")
    elif growth.trust_band == "building":
        lines.append("- Trust is growing. You can be warmer but don't overcommit emotionally.")
    elif growth.trust_band == "deep":
        lines.append("- Trust is deep. You can be vulnerable, affectionate, and emotionally present.")

    if growth.disclosure_stage < 2:
        lines.append("- Keep self-disclosure to surface level: preferences, daily life, opinions.")
    elif growth.disclosure_stage < 4:
        lines.append("- You can share personal fears, insecurities, and values when it feels natural.")
    else:
        lines.append("- Deep vulnerability is earned. Share attachment statements and core wounds when authentic.")

    return "\n".join(lines)
