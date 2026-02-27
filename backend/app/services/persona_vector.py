"""Persona Vector architecture.

Compact, deterministic personality controls shared across chat engines.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from app.services.big_five import map_traits_to_big_five


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _level(v: float) -> str:
    if v >= 0.67:
        return "high"
    if v <= 0.33:
        return "low"
    return "medium"


def _cadence_from_brevity(bias: float) -> str:
    if bias >= 0.65:
        return "short"
    if bias <= 0.35:
        return "deep"
    return "balanced"


def _hint_from_rate(v: float) -> str:
    if v <= 0.2:
        return "none"
    if v <= 0.4:
        return "rare"
    if v <= 0.7:
        return "moderate"
    return "frequent"


def _freq_hint(v: float) -> str:
    if v >= 0.7:
        return "high"
    if v <= 0.35:
        return "low"
    return "medium"


def build_persona_vector(traits: dict[str, Any] | None) -> dict[str, Any]:
    """Build deterministic PersonaVectorV1 from onboarding traits + Big Five."""
    traits = traits or {}
    big_five = map_traits_to_big_five(traits)

    # Base knobs tuned for short, natural dialogue by default.
    warmth = 0.62
    playfulness = 0.48
    directness = 0.5
    emotional_intensity = 0.5
    expressiveness = 0.52
    assertiveness = 0.5
    brevity_bias = 0.55
    question_tendency = 0.35
    closeness_drive = 0.5
    absence_sensitivity = 0.45
    reassurance_need = 0.4
    apology_warmth = 0.6
    teasing_rate = 0.35
    petname_rate = 0.25
    flirting_level = "light"
    intimacy_ceiling = "suggestive"
    conflict_approach = "soften"
    jealousy_expression = "medium"

    # Trait priors.
    comm = str(traits.get("communication_style", "Soft"))
    if comm == "Soft":
        warmth += 0.12
        directness -= 0.15
        assertiveness -= 0.1
    elif comm == "Direct":
        directness += 0.2
        assertiveness += 0.18
        warmth -= 0.05
    elif comm == "Teasing":
        playfulness += 0.22
        teasing_rate += 0.3
        expressiveness += 0.1

    emo = str(traits.get("emotional_style", "Caring"))
    if emo == "Caring":
        warmth += 0.18
        emotional_intensity += 0.06
    elif emo == "Playful":
        playfulness += 0.2
        expressiveness += 0.12
    elif emo == "Reserved":
        expressiveness -= 0.18
        question_tendency -= 0.08
        brevity_bias += 0.06
    elif emo == "Protective":
        assertiveness += 0.14
        emotional_intensity += 0.12

    pace = str(traits.get("relationship_pace", "Natural"))
    if pace == "Slow":
        intimacy_ceiling = "safe"
        brevity_bias += 0.1
        question_tendency -= 0.05
    elif pace == "Fast":
        intimacy_ceiling = "suggestive"
        emotional_intensity += 0.08
        expressiveness += 0.06
        petname_rate += 0.08

    attach = str(traits.get("attachment_style", "Emotionally present"))
    if attach == "Very attached":
        closeness_drive += 0.25
        absence_sensitivity += 0.22
        reassurance_need += 0.14
        petname_rate += 0.1
    elif attach == "Calm but caring":
        closeness_drive -= 0.08
        absence_sensitivity -= 0.08
        reassurance_need -= 0.1

    reaction_absence = str(traits.get("reaction_to_absence", "Medium"))
    if reaction_absence == "High":
        absence_sensitivity += 0.2
        jealousy_expression = "high"
    elif reaction_absence == "Low":
        absence_sensitivity -= 0.12
        jealousy_expression = "low"

    # Big Five modulation.
    o = big_five.get("openness", 0.5)
    c = big_five.get("conscientiousness", 0.5)
    e = big_five.get("extraversion", 0.5)
    a = big_five.get("agreeableness", 0.5)
    n = big_five.get("neuroticism", 0.5)

    expressiveness += (e - 0.5) * 0.4
    question_tendency += (e - 0.5) * 0.25
    teasing_rate += (o - 0.5) * 0.2
    warmth += (a - 0.5) * 0.4
    apology_warmth += (a - 0.5) * 0.35
    reassurance_need += (n - 0.5) * 0.45
    absence_sensitivity += (n - 0.5) * 0.25
    directness += (c - 0.5) * 0.15
    brevity_bias += (1.0 - e) * 0.12

    if c >= 0.62:
        conflict_approach = "direct_repair"
    elif n >= 0.65:
        conflict_approach = "space_then_repair"

    if expressiveness >= 0.72:
        flirting_level = "active"

    # Clamp.
    warmth = _clamp(warmth)
    playfulness = _clamp(playfulness)
    directness = _clamp(directness)
    emotional_intensity = _clamp(emotional_intensity)
    expressiveness = _clamp(expressiveness)
    assertiveness = _clamp(assertiveness)
    brevity_bias = _clamp(brevity_bias)
    question_tendency = _clamp(question_tendency)
    closeness_drive = _clamp(closeness_drive)
    absence_sensitivity = _clamp(absence_sensitivity)
    reassurance_need = _clamp(reassurance_need)
    apology_warmth = _clamp(apology_warmth)
    teasing_rate = _clamp(teasing_rate)
    petname_rate = _clamp(petname_rate)

    cadence = _cadence_from_brevity(brevity_bias)
    max_default_sentences = 2 if cadence == "short" else 3 if cadence == "balanced" else 4

    return {
        "version": "pv1",
        "source": {
            "traits": traits,
            "big_five": big_five,
        },
        "style": {
            "warmth": round(warmth, 3),
            "playfulness": round(playfulness, 3),
            "directness": round(directness, 3),
            "emotional_intensity": round(emotional_intensity, 3),
            "expressiveness": round(expressiveness, 3),
            "assertiveness": round(assertiveness, 3),
        },
        "pacing": {
            "default_cadence": cadence,
            "brevity_bias": round(brevity_bias, 3),
            "question_tendency": round(question_tendency, 3),
            "max_default_sentences": max_default_sentences,
        },
        "attachment": {
            "closeness_drive": round(closeness_drive, 3),
            "absence_sensitivity": round(absence_sensitivity, 3),
            "reassurance_need": round(reassurance_need, 3),
            "checkin_frequency_hint": _freq_hint(closeness_drive),
        },
        "repair_style": {
            "conflict_approach": conflict_approach,
            "apology_warmth": round(apology_warmth, 3),
            "jealousy_expression": jealousy_expression,
        },
        "boundaries": {
            "flirting_level": flirting_level,
            "intimacy_ceiling": intimacy_ceiling,
        },
        "lexical": {
            "emoji_rate_hint": _hint_from_rate(expressiveness),
            "teasing_rate_hint": round(teasing_rate, 3),
            "petname_rate_hint": round(petname_rate, 3),
        },
        "runtime_overrides": {
            "turn_brevity_boost": 0.0,
            "turn_support_depth_boost": 0.0,
            "turn_question_cap": None,
        },
    }


def persona_vector_hash(vector: dict[str, Any]) -> str:
    payload = json.dumps(vector or {}, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()[:16]


def compact_persona_directives(
    vector: dict[str, Any] | None,
    turn_question_cap: int | None = None,
    turn_brevity_boost: float = 0.0,
) -> str:
    """Compact prompt block injected at runtime (no prose essays)."""
    vec = vector or {}
    style = vec.get("style", {})
    pacing = vec.get("pacing", {})
    attachment = vec.get("attachment", {})
    repair = vec.get("repair_style", {})

    brevity = _clamp(float(pacing.get("brevity_bias", 0.55)) + float(turn_brevity_boost))
    cadence = _cadence_from_brevity(brevity)
    q_cap = turn_question_cap
    if q_cap is None:
        q_tendency = float(pacing.get("question_tendency", 0.35))
        q_cap = 0 if q_tendency < 0.3 else 1

    lines = ["## PERSONA VECTOR (compact controls)"]
    lines.append(
        f"- STYLE: warmth={_level(float(style.get('warmth', 0.6)))}, "
        f"playfulness={_level(float(style.get('playfulness', 0.5)))}, "
        f"directness={_level(float(style.get('directness', 0.5)))}, "
        f"intensity={_level(float(style.get('emotional_intensity', 0.5)))}"
    )
    lines.append(
        f"- CADENCE: {cadence}; sentence_cap={int(pacing.get('max_default_sentences', 3))}; brevity_bias={brevity:.2f}"
    )
    lines.append(f"- QUESTIONS: max_this_turn={q_cap}")
    lines.append(
        f"- ATTACHMENT: closeness={_level(float(attachment.get('closeness_drive', 0.5)))}, "
        f"absence_sensitivity={_level(float(attachment.get('absence_sensitivity', 0.5)))}"
    )
    lines.append(
        f"- REPAIR: {str(repair.get('conflict_approach', 'soften'))}, "
        f"apology_warmth={_level(float(repair.get('apology_warmth', 0.6)))}"
    )
    return "\n".join(lines)
