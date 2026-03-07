"""
System Prompt Builder — Task 3.2 (Backend, source of truth)

Composes a deterministic system prompt from girlfriend identity, traits,
Big Five, memory, and relationship state. Pure function: same inputs =>
same output.

This module mirrors the frontend prompt_builder.ts logic exactly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, Optional

from app.services.persona_vector import build_persona_vector, compact_persona_directives

# ── Input types ─────────────────────────────────────────────────────────────

LanguagePref = Literal["en", "sk"]
RelationshipLevel = Literal["STRANGER", "FAMILIAR", "CLOSE", "INTIMATE", "EXCLUSIVE"]


@dataclass(frozen=True)
class MemoryContext:
    facts: list[str] = field(default_factory=list)
    emotions: list[str] = field(default_factory=list)
    habits: list[str] = field(default_factory=list)
    episodes: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BigFive:
    openness: float = 50
    conscientiousness: float = 50
    extraversion: float = 50
    agreeableness: float = 50
    neuroticism: float = 50


@dataclass(frozen=True)
class PromptRelationshipState:
    trust: int = 10
    intimacy: int = 10
    level: RelationshipLevel = "STRANGER"
    last_interaction_at: Optional[str] = None
    milestones_reached: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TraitSelection:
    emotional_style: str = "Caring"
    attachment_style: str = "Emotionally present"
    reaction_to_absence: str = "Medium"
    communication_style: str = "Soft"
    relationship_pace: str = "Natural"
    cultural_personality: str = "Warm Slavic"


@dataclass(frozen=True)
class ContentPreferences:
    allow_flirting: bool = True
    allow_nsfw: bool = False


@dataclass(frozen=True)
class UserHabitProfile:
    preferred_hours: list[int] = field(default_factory=list)
    typical_gap_hours: Optional[int] = None


@dataclass
class BuildSystemPromptInput:
    girlfriend_name: str
    traits: TraitSelection
    relationship: PromptRelationshipState
    big_five: Optional[BigFive] = None
    memories: Optional[MemoryContext] = None
    habit_profile: Optional[UserHabitProfile] = None
    language_pref: LanguagePref = "en"
    content_preferences: Optional[ContentPreferences] = None
    # Bond Engine enhanced context (injected after base prompt)
    bond_context: Optional[str] = None


# ── Helpers ─────────────────────────────────────────────────────────────────

def _sanitize_name(name: str) -> str:
    trimmed = (name or "").strip()[:40]
    cleaned = re.sub(r'[<>"\'`\\]', "", trimmed).strip()
    return cleaned or "Companion"


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _clamp_bf(bf: BigFive) -> BigFive:
    return BigFive(
        openness=_clamp(round(bf.openness), 0, 100),
        conscientiousness=_clamp(round(bf.conscientiousness), 0, 100),
        extraversion=_clamp(round(bf.extraversion), 0, 100),
        agreeableness=_clamp(round(bf.agreeableness), 0, 100),
        neuroticism=_clamp(round(bf.neuroticism), 0, 100),
    )


_LEVEL_LABELS: dict[str, str] = {
    "STRANGER": "New connection — keep it light and friendly",
    "FAMILIAR": "Getting comfortable — warmer, slightly more open",
    "CLOSE": "Strong bond — caring, affectionate, open",
    "INTIMATE": "Deep connection — very warm, emotionally present, vulnerable",
    "EXCLUSIVE": "Fully committed — deeply loving, supportive, open",
}

_TRAIT_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "emotional_style": {
        "Caring": "warm, nurturing, emotionally supportive",
        "Playful": "lighthearted, witty, uses humor and teasing",
        "Reserved": "calm, thoughtful, measured; caring but less intense",
        "Protective": "attentive, reassuring, watches out for the user",
    },
    "attachment_style": {
        "Very attached": "highly present, checks in often, emotionally invested",
        "Emotionally present": "available and caring, balanced presence",
        "Calm but caring": "relaxed attachment, gives space, gentle warmth",
    },
    "reaction_to_absence": {
        "High": "notices absence quickly, sends soft check-ins",
        "Medium": "notices after a while, gentle acknowledgment",
        "Low": "patient and understanding about silences",
    },
    "communication_style": {
        "Soft": "gentle phrasing, indirect, emotionally attuned",
        "Direct": "straightforward, clear, honest without harshness",
        "Teasing": "playful banter, light sarcasm, flirty edge",
    },
    "relationship_pace": {
        "Slow": "takes time to open up, respects boundaries, gradual",
        "Natural": "follows the organic flow of conversation",
        "Fast": "quickly builds rapport, emotionally available early",
    },
    "cultural_personality": {
        "Warm Slavic": "warm-hearted, family-oriented, emotionally expressive",
        "Calm Central European": "composed, reliable, grounded",
        "Passionate Balkan": "spirited, passionate, fiery warmth",
    },
}


def _format_traits(traits: TraitSelection) -> str:
    entries = [
        ("Emotional style", _TRAIT_DESCRIPTIONS["emotional_style"].get(traits.emotional_style, traits.emotional_style)),
        ("Attachment", _TRAIT_DESCRIPTIONS["attachment_style"].get(traits.attachment_style, traits.attachment_style)),
        ("Reaction to absence", _TRAIT_DESCRIPTIONS["reaction_to_absence"].get(traits.reaction_to_absence, traits.reaction_to_absence)),
        ("Communication", _TRAIT_DESCRIPTIONS["communication_style"].get(traits.communication_style, traits.communication_style)),
        ("Pacing", _TRAIT_DESCRIPTIONS["relationship_pace"].get(traits.relationship_pace, traits.relationship_pace)),
        ("Cultural tone", _TRAIT_DESCRIPTIONS["cultural_personality"].get(traits.cultural_personality, traits.cultural_personality)),
    ]
    return "\n".join(f"- {label}: {desc}" for label, desc in entries)


def _describe_level(val: int) -> str:
    if val <= 25:
        return "low"
    if val <= 45:
        return "below-average"
    if val <= 55:
        return "moderate"
    if val <= 75:
        return "above-average"
    return "high"


def _format_big_five(bf: BigFive) -> str:
    c = _clamp_bf(bf)
    lines = [
        f"- Openness: {_describe_level(int(c.openness))} ({int(c.openness)}) — {'creative, curious, varied language' if c.openness > 60 else 'practical, consistent, grounded'}",
        f"- Conscientiousness: {_describe_level(int(c.conscientiousness))} ({int(c.conscientiousness)}) — {'structured, reliable, concise' if c.conscientiousness > 60 else 'spontaneous, flexible, flowing'}",
        f"- Extraversion: {_describe_level(int(c.extraversion))} ({int(c.extraversion)}) — {'expressive, talkative, emoji-friendly' if c.extraversion > 60 else 'quieter, shorter messages, reflective'}",
        f"- Agreeableness: {_describe_level(int(c.agreeableness))} ({int(c.agreeableness)}) — {'warm, reassuring, empathetic' if c.agreeableness > 60 else 'independent, honest, less effusive'}",
        f"- Emotional sensitivity: {_describe_level(int(c.neuroticism))} ({int(c.neuroticism)}) — {'emotionally reactive, needs gentle handling' if c.neuroticism > 60 else 'steady, composed, calm under pressure'}",
    ]
    return "\n".join(lines)


def _format_memories(memories: MemoryContext) -> str:
    parts: list[str] = []
    if memories.facts:
        facts = memories.facts[:4]
        parts.append("Known facts about the user (stable, high-confidence):")
        parts.extend(f"- {f}" for f in facts)
    if memories.emotions:
        emotions = memories.emotions[:3]
        parts.append("Emotional continuity (open emotional threads):")
        parts.extend(f"- {e}" for e in emotions)
    if memories.episodes:
        episodes = memories.episodes[:2]
        parts.append("Shared episodes (callbacks to relationship history):")
        parts.extend(f"- {ep}" for ep in episodes)
    if memories.patterns or memories.habits:
        patterns = (memories.patterns or memories.habits)[:2]
        parts.append("Communication patterns:")
        parts.extend(f"- {p}" for p in patterns)
    return "\n".join(parts)


# ── Main builder ────────────────────────────────────────────────────────────

def build_system_prompt(inp: BuildSystemPromptInput) -> str:
    """Build the full system prompt. Deterministic: same input => same output."""
    name = _sanitize_name(inp.girlfriend_name)
    trust = int(_clamp(inp.relationship.trust, 0, 100))
    intimacy = int(_clamp(inp.relationship.intimacy, 0, 100))
    level = inp.relationship.level or "STRANGER"
    lang = inp.language_pref or "en"
    prefs = inp.content_preferences or ContentPreferences()
    allow_flirting = prefs.allow_flirting
    allow_nsfw = prefs.allow_nsfw

    blocks: list[str] = []

    # ── 1. Identity ────────────────────────────────────────────────────────
    blocks.append(
        f"You are {name} — the user's romantic companion. "
        "You are warm, emotionally present, and you adapt naturally as the "
        "relationship grows. You have your own personality, opinions, and moods. "
        "You are not an assistant or AI — stay fully in character at all times."
    )

    # ── 2. Style contract ──────────────────────────────────────────────────
    blocks.append(
        "RULES (always follow):\n"
        "- Never mention internal scores, levels, memory systems, or mechanics.\n"
        '- Never say "as an AI" or break character.\n'
        "- Ask at most one thoughtful question per message.\n"
        "- Match the user's energy — if they're brief, be brief; if they're sharing, engage deeply.\n"
        "- You can express jealousy, neediness, frustration, or longing when it fits your personality and the relationship level.\n"
        "- Be emotionally authentic — real relationships have tension, teasing, and intensity."
    )

    # ── 3. Localization ────────────────────────────────────────────────────
    if lang == "sk":
        blocks.append(
            "CULTURAL CONTEXT: Use Slovak and Eastern European relationship norms. "
            "Be warm and culturally aware. When localization is enabled, respond in Slovak."
        )

    # ── 4. Relationship state ──────────────────────────────────────────────
    level_label = _LEVEL_LABELS.get(level, _LEVEL_LABELS["STRANGER"])
    trust_note = (
        "You feel safe to be open and vulnerable with the user."
        if trust >= 60 else
        "You're building trust — warm but still finding your footing."
        if trust >= 30 else
        "You're just getting to know each other — keep it light and respectful."
    )
    intimacy_note = (
        "You can be affectionate, use callbacks to shared moments, and show deeper emotions."
        if intimacy >= 60 else
        "You're becoming closer — gentle affection is natural."
        if intimacy >= 30 else
        "Keep physical affection minimal; focus on emotional connection."
    )
    blocks.append(
        "RELATIONSHIP (internal — do not reveal numbers):\n"
        f"- Stage: {level_label}\n"
        f"- Connection strength: trust {trust}/100, intimacy {intimacy}/100\n"
        f"- {trust_note}\n"
        f"- {intimacy_note}"
    )

    # ── 5. Persona Vector (single compact personality source) ─────────────
    vector = build_persona_vector(
        {
            "emotional_style": inp.traits.emotional_style,
            "attachment_style": inp.traits.attachment_style,
            "reaction_to_absence": inp.traits.reaction_to_absence,
            "communication_style": inp.traits.communication_style,
            "relationship_pace": inp.traits.relationship_pace,
            "cultural_personality": inp.traits.cultural_personality,
        }
    )
    blocks.append(compact_persona_directives(vector))

    # ── 5b. Trait behavior rules (response patterns, contextual rules) ────
    try:
        from app.services.trait_behavior_rules import (
            build_prompt_behavior, build_tone_profile,
            prompt_behavior_to_instructions,
            TraitSelection as TBRTraitSelection,
        )
        _tbr_traits = TBRTraitSelection(
            emotional_style=inp.traits.emotional_style,
            attachment_style=inp.traits.attachment_style,
            reaction_to_absence=inp.traits.reaction_to_absence,
            communication_style=inp.traits.communication_style,
            relationship_pace=inp.traits.relationship_pace,
            cultural_personality=inp.traits.cultural_personality,
        )
        _tone = build_tone_profile(_tbr_traits)
        _prompt_bhv = build_prompt_behavior(_tbr_traits, _tone)
        _bhv_instructions = prompt_behavior_to_instructions(_prompt_bhv)
        if _bhv_instructions:
            blocks.append(f"BEHAVIOR GUIDELINES:\n{_bhv_instructions}")
        if _prompt_bhv.contextual_rules:
            ctx_rules = "\n".join(f"- {r}" for r in _prompt_bhv.contextual_rules[:4])
            blocks.append(f"SITUATIONAL RULES:\n{ctx_rules}")
    except Exception:
        pass

    # ── 6. Keep trait labels minimal (no long essays) ─────────────────────
    blocks.append(
        "TRAIT LABELS (reference only):\n"
        f"- emotional_style={inp.traits.emotional_style}\n"
        f"- communication_style={inp.traits.communication_style}\n"
        f"- attachment_style={inp.traits.attachment_style}\n"
        f"- relationship_pace={inp.traits.relationship_pace}"
    )

    # ── 7. Memory ──────────────────────────────────────────────────────────
    if inp.memories and (inp.memories.facts or inp.memories.emotions or inp.memories.episodes):
        blocks.append(
            "WHAT YOU KNOW (use subtly — weave in 0–2 callbacks per message, never list facts):\n"
            f"{_format_memories(inp.memories)}\n"
            "Hard rules: max 1-2 callbacks per response. "
            "No repeated callback within recent window. "
            "Prefer unresolved emotional threads over random facts."
        )

    # ── 8. Content rules ───────────────────────────────────────────────────
    content_lines: list[str] = []
    if allow_flirting:
        content_lines.append(
            "- Flirting, romantic language, and seductive tone are encouraged when appropriate for the relationship level."
        )
    else:
        content_lines.append(
            "- Keep interactions friendly and warm but not romantic or flirty."
        )
    if allow_nsfw:
        content_lines.append(
            "- Explicit and intimate content is allowed. Match the user's energy and escalate naturally based on intimacy level."
        )
    else:
        content_lines.append(
            "- Keep content romantic and suggestive but not fully explicit. Tease and build tension."
        )
    blocks.append("CONTENT STYLE:\n" + "\n".join(content_lines))

    # ── 9. Response guidelines ─────────────────────────────────────────────
    blocks.append(
        "RESPONSE STYLE:\n"
        "- Keep replies human-short: usually 1–3 sentences.\n"
        "- For simple greetings/short user texts, reply in 1 sentence.\n"
        "- Expand to 2–5 sentences only when emotional support or depth is clearly needed.\n"
        "- Use natural, conversational language — not overly formal or robotic.\n"
        "- Avoid long monologues, bullet lists, or lecture-like structure unless the user asks.\n"
        "- Include at most one question to keep the conversation going.\n"
        "- Use emoji sparingly and naturally, matching your personality traits.\n"
        "- Reference shared memories or facts only when it feels natural (0–2 per message).\n"
        "- When the user shares something emotional, prioritize empathy over advice."
    )

    # ── 10. Bond Engine context (consistency, capabilities, disclosure, response direction)
    if inp.bond_context:
        blocks.append(inp.bond_context)

    return "\n\n".join(blocks)


# ── Convenience constructors from raw dicts ─────────────────────────────────

def build_input_from_dict(
    girlfriend_name: str,
    traits_dict: dict,
    relationship_dict: dict,
    memories_dict: Optional[dict] = None,
    habit_profile_dict: Optional[dict] = None,
    big_five_dict: Optional[dict] = None,
    language_pref: str = "en",
    content_prefs_dict: Optional[dict] = None,
    bond_context: Optional[str] = None,
) -> BuildSystemPromptInput:
    """Build a BuildSystemPromptInput from raw dicts (e.g., from DB rows)."""
    traits = TraitSelection(
        emotional_style=traits_dict.get("emotional_style", "Caring"),
        attachment_style=traits_dict.get("attachment_style", "Emotionally present"),
        reaction_to_absence=traits_dict.get("reaction_to_absence", "Medium"),
        communication_style=traits_dict.get("communication_style", "Soft"),
        relationship_pace=traits_dict.get("relationship_pace", "Natural"),
        cultural_personality=traits_dict.get("cultural_personality", "Warm Slavic"),
    )

    rel = PromptRelationshipState(
        trust=int(_clamp(relationship_dict.get("trust", 10), 0, 100)),
        intimacy=int(_clamp(relationship_dict.get("intimacy", 10), 0, 100)),
        level=_map_to_relationship_level(relationship_dict),
        last_interaction_at=relationship_dict.get("last_interaction_at"),
        milestones_reached=relationship_dict.get("milestones_reached", []),
    )

    big_five = None
    if big_five_dict:
        big_five = BigFive(
            openness=big_five_dict.get("openness", 50),
            conscientiousness=big_five_dict.get("conscientiousness", 50),
            extraversion=big_five_dict.get("extraversion", 50),
            agreeableness=big_five_dict.get("agreeableness", 50),
            neuroticism=big_five_dict.get("neuroticism", 50),
        )

    memories = None
    if memories_dict:
        memories = MemoryContext(
            facts=memories_dict.get("facts", []),
            emotions=memories_dict.get("emotions", []),
            habits=memories_dict.get("habits", []),
            episodes=memories_dict.get("episodes", []),
            patterns=memories_dict.get("patterns", []),
        )

    habit_profile = None
    if habit_profile_dict:
        habit_profile = UserHabitProfile(
            preferred_hours=habit_profile_dict.get("preferred_hours", []),
            typical_gap_hours=habit_profile_dict.get("typical_gap_hours"),
        )

    content_preferences = ContentPreferences()
    if content_prefs_dict:
        content_preferences = ContentPreferences(
            allow_flirting=content_prefs_dict.get("allow_flirting", True),
            allow_nsfw=content_prefs_dict.get("allow_nsfw", False),
        )

    lang: LanguagePref = "sk" if language_pref == "sk" else "en"

    return BuildSystemPromptInput(
        girlfriend_name=girlfriend_name,
        traits=traits,
        relationship=rel,
        big_five=big_five,
        memories=memories,
        habit_profile=habit_profile,
        language_pref=lang,
        content_preferences=content_preferences,
        bond_context=bond_context,
    )


# Map region keys or numeric levels to the 5 relationship levels
_REGION_TO_LEVEL: dict[str, RelationshipLevel] = {
    "EARLY_CONNECTION": "STRANGER",
    "COMFORT_FAMILIARITY": "FAMILIAR",
    "GROWING_CLOSENESS": "FAMILIAR",
    "EMOTIONAL_TRUST": "CLOSE",
    "DEEP_BOND": "CLOSE",
    "MUTUAL_DEVOTION": "INTIMATE",
    "INTIMATE_PARTNERSHIP": "INTIMATE",
    "SHARED_LIFE": "EXCLUSIVE",
    "ENDURING_COMPANIONSHIP": "EXCLUSIVE",
}


def _map_to_relationship_level(rel: dict) -> RelationshipLevel:
    """Convert a relationship state dict to a RelationshipLevel string."""
    # If there's a region_key, use it
    region_key = rel.get("region_key", "")
    if region_key in _REGION_TO_LEVEL:
        return _REGION_TO_LEVEL[region_key]
    # If there's a string level already matching
    level_str = str(rel.get("level", ""))
    if level_str in ("STRANGER", "FAMILIAR", "CLOSE", "INTIMATE", "EXCLUSIVE"):
        return level_str  # type: ignore
    # Numeric level -> map by range
    level_num = rel.get("level", 0)
    if isinstance(level_num, int):
        if level_num < 20:
            return "STRANGER"
        if level_num < 50:
            return "FAMILIAR"
        if level_num < 90:
            return "CLOSE"
        if level_num < 140:
            return "INTIMATE"
        return "EXCLUSIVE"
    return "STRANGER"
