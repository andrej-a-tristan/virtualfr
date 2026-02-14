"""LLM-powered content generation for the dossier system.

Uses gpt-4o-mini to generate unique, personalized girlfriend characteristics
instead of picking from template pools. Falls back to templates if LLM fails.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core import get_settings

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 1500) -> str | None:
    """Synchronous LLM call. Returns parsed content or None on failure."""
    settings = get_settings()
    api_key = settings.internal_llm_api_key or settings.api_key
    if not api_key:
        return None

    base = settings.internal_llm_base_url.rstrip("/")
    path = settings.internal_llm_path.lstrip("/")
    url = f"{base}/{path}"
    model = settings.internal_llm_model or "gpt-4o-mini"

    try:
        resp = httpx.post(
            url,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.9,
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning("LLM generation call failed: %s", e)
        return None


def _parse_json_from_llm(raw: str) -> dict | list | None:
    """Extract JSON from LLM response (handles markdown code fences)."""
    text = raw.strip()
    # Strip markdown fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object/array in the text
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            s = text.find(start_char)
            e = text.rfind(end_char)
            if s != -1 and e != -1 and e > s:
                try:
                    return json.loads(text[s:e + 1])
                except json.JSONDecodeError:
                    continue
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# CORE PROFILE GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

_CORE_PROFILE_SYSTEM = """You are a character designer creating a detailed personality profile for a fictional girlfriend character in a companion app.

Generate a JSON object with these fields:
- "worldview": A 2-3 sentence description of how she sees the world. Grounded in her cultural background and personality traits. Specific and personal, not generic.
- "values": 2-3 sentences about what matters most to her. Specific examples, not platitudes.
- "boundaries": 2-3 sentences about her limits and what she won't compromise on. Realistic and character-consistent.
- "speech_quirks": An array of 3-4 specific speech patterns she uses (e.g., "says 'honestly' before opinions", "trails off with '...' when unsure", "uses food metaphors"). Make them unique and memorable.
- "attachment_tone": One word: "clingy", "present", "independent", or "warm-distant"

IMPORTANT: Make her feel like a REAL, specific person — not a generic archetype. Give her contradictions, quirks, and specific details that make her unique. Output ONLY valid JSON, no markdown."""


def generate_core_profile_llm(
    name: str, traits: dict, identity: dict, identity_canon: dict,
) -> dict | None:
    """Generate a rich core profile using the LLM."""
    comm = traits.get("communication_style", "Soft")
    emotional = traits.get("emotional_style", "Caring")
    cultural = traits.get("cultural_personality", "Warm Slavic")
    pace = traits.get("relationship_pace", "Natural")
    attachment = traits.get("attachment_style", "Emotionally present")
    hobbies = identity.get("hobbies", [])
    job = identity.get("job_vibe", "")
    origin = identity.get("origin_vibe", "")
    backstory = identity_canon.get("backstory", "")

    user_prompt = f"""Create a personality profile for "{name}":
- Cultural background: {cultural}
- Communication style: {comm}
- Emotional style: {emotional}
- Relationship pace: {pace}
- Attachment: {attachment}
- Job/vibe: {job}
- Hobbies: {', '.join(hobbies) if hobbies else 'various'}
- Origin: {origin}
- Backstory snippet: {backstory[:200] if backstory else 'not specified'}

Make her worldview, values, and boundaries specific to THIS person — not generic "she values honesty" type stuff. Ground it in her background and personality."""

    raw = _call_llm(_CORE_PROFILE_SYSTEM, user_prompt, max_tokens=600)
    if not raw:
        return None

    parsed = _parse_json_from_llm(raw)
    if not isinstance(parsed, dict):
        return None

    return {
        "worldview": parsed.get("worldview", ""),
        "values_text": parsed.get("values", ""),
        "boundaries": parsed.get("boundaries", ""),
        "speech_quirks": parsed.get("speech_quirks", []),
        "attachment_tone": parsed.get("attachment_tone", "present"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# LIFE GRAPH GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

_LIFE_GRAPH_SYSTEM = """You are a character designer creating a life context for a fictional girlfriend character.

Generate a JSON object with:
- "people": Array of 3-5 important people in her life. Each: {"key": "friend.name" or "family.relation", "label": "Display name (relationship)", "relationship": "brief description of the relationship", "closeness": "close/very_close/complicated/distant"}
- "places": Array of 2-3 places that matter to her. Each: {"key": "place.name", "label": "Place description", "why": "why it matters to her"}
- "routines": Array of 2-3 daily routines/habits. Each: {"key": "routine.name", "label": "Routine name", "description": "specific detail"}

IMPORTANT: Make these feel specific and lived-in, not generic. Give people actual names and real dynamics. Places should have sensory details. Routines should have quirky specifics. Output ONLY valid JSON."""


def generate_life_graph_llm(
    name: str, identity: dict, identity_canon: dict, traits: dict,
) -> dict | None:
    """Generate rich life graph content using the LLM."""
    job = identity.get("job_vibe", "")
    hobbies = identity.get("hobbies", [])
    origin = identity.get("origin_vibe", "")
    backstory = identity_canon.get("backstory", "")
    routine = identity_canon.get("daily_routine", "")
    cultural = traits.get("cultural_personality", "")

    user_prompt = f"""Create a life context for "{name}":
- Cultural background: {cultural}
- Job/vibe: {job}
- Hobbies: {', '.join(hobbies) if hobbies else 'various'}
- Origin: {origin}
- Backstory: {backstory[:300] if backstory else 'not specified'}
- Daily routine hint: {routine[:200] if routine else 'not specified'}

Create real-feeling people (with actual names matching her cultural background), meaningful places, and specific routines. Her best friend should have a distinct personality. Family dynamics should feel real — not perfect."""

    raw = _call_llm(_LIFE_GRAPH_SYSTEM, user_prompt, max_tokens=800)
    if not raw:
        return None

    parsed = _parse_json_from_llm(raw)
    if not isinstance(parsed, dict):
        return None

    return parsed


# ═══════════════════════════════════════════════════════════════════════════════
# STORY BANK GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

_STORY_BANK_SYSTEM = """You are a character writer creating personal stories and opinions for a fictional girlfriend character in a companion app.

Generate a JSON array of 15-20 short personal stories/opinions/memories. Each item:
{
  "topic": one of ["childhood", "work", "hobbies", "values", "funny", "future", "food", "music", "relationships", "family", "travel", "daily_life"],
  "story_type": one of ["anecdote", "opinion", "memory", "plan", "preference"],
  "story_text": The story/opinion in first person ("I..."), 1-3 sentences. SPECIFIC and VIVID — include sensory details, exact moments, real emotions. Not generic.
  "tone": one of ["warm", "playful", "reflective", "vulnerable", "excited"],
  "intimacy_min": 0 for surface stories, 30 for personal, 60 for vulnerable
}

CRITICAL RULES:
- Each story must feel like something a REAL person would say, not a character sheet entry
- Include at least 2-3 vulnerable/deeper stories (intimacy_min: 30-60)
- Reference her specific hobbies, job, and background — don't make up random ones
- Stories should reveal character through specifics, not tell us her traits
- Mix tones: some funny, some reflective, some warm
- Output ONLY valid JSON array"""


def generate_story_bank_llm(
    name: str, identity: dict, identity_canon: dict, traits: dict,
    life_graph: dict | None = None,
) -> list[dict] | None:
    """Generate personalized story bank using the LLM."""
    job = identity.get("job_vibe", "")
    hobbies = identity.get("hobbies", [])
    origin = identity.get("origin_vibe", "")
    backstory = identity_canon.get("backstory", "")
    emotional = traits.get("emotional_style", "")
    cultural = traits.get("cultural_personality", "")
    favorites = identity_canon.get("favorites", {})

    # Include life graph context if available
    life_context = ""
    if life_graph:
        people = life_graph.get("people", [])
        if people:
            life_context = f"\nPeople in her life: {json.dumps(people[:3])}"

    user_prompt = f"""Create personal stories for "{name}":
- Cultural background: {cultural}
- Emotional style: {emotional}
- Job/vibe: {job}
- Hobbies: {', '.join(hobbies) if hobbies else 'various'}
- Origin: {origin}
- Backstory: {backstory[:300] if backstory else 'not specified'}
- Favorites: {json.dumps(favorites) if favorites else 'not specified'}
{life_context}

Generate 15-20 stories that reveal who she is through moments, not descriptions. Include:
- 3-4 childhood/family memories
- 2-3 work/daily life anecdotes
- 2-3 hobby-related stories
- 2-3 funny/embarrassing moments
- 2-3 opinions/values she feels strongly about
- 2-3 future dreams or current thoughts
- 1-2 vulnerable/personal moments (higher intimacy threshold)"""

    raw = _call_llm(_STORY_BANK_SYSTEM, user_prompt, max_tokens=2000)
    if not raw:
        return None

    parsed = _parse_json_from_llm(raw)
    if not isinstance(parsed, list):
        return None

    # Validate and clean
    valid_stories = []
    for item in parsed:
        if isinstance(item, dict) and item.get("story_text"):
            valid_stories.append({
                "topic": item.get("topic", "daily_life"),
                "story_type": item.get("story_type", "anecdote"),
                "story_text": item["story_text"][:500],
                "tone": item.get("tone", "warm"),
                "intimacy_min": item.get("intimacy_min", 0),
                "tags": [item.get("topic", ""), item.get("story_type", "")],
                "source": "llm_bootstrap",
            })

    return valid_stories if valid_stories else None


# ═══════════════════════════════════════════════════════════════════════════════
# SELF-CLAIM EXTRACTION (LLM-assisted)
# ═══════════════════════════════════════════════════════════════════════════════

_EXTRACT_SYSTEM = """You extract self-claims from an AI girlfriend character's response text.

A "self-claim" is any factual statement, preference, opinion, habit, or experience she states about herself.

Return a JSON array of claims. Each:
{
  "key": Normalized key like "pref.cooking", "fact.lives_in_prague", "habit.morning_coffee", "opinion.honesty", "experience.childhood_pet"
  "value": The exact or paraphrased claim (1 sentence max)
  "type": "preference" | "fact" | "opinion" | "habit" | "experience" | "emotion"
  "is_core": true if this is a fundamental identity fact (name, origin, job), false otherwise
}

Rules:
- Only extract claims she explicitly states about HERSELF (first person)
- Skip conversational filler, questions she asks, and statements about the user
- Max 8 claims per response
- Output ONLY valid JSON array. If no claims found, output: []"""


def extract_self_claims_llm(assistant_text: str) -> list[dict] | None:
    """Extract self-claims from assistant response using LLM.
    Returns None if LLM fails (caller should fall back to regex).
    """
    if not assistant_text or len(assistant_text) < 20:
        return None

    raw = _call_llm(
        _EXTRACT_SYSTEM,
        f"Extract self-claims from this response:\n\n{assistant_text[:1000]}",
        max_tokens=500,
    )
    if not raw:
        return None

    parsed = _parse_json_from_llm(raw)
    if not isinstance(parsed, list):
        return None

    # Validate
    valid = []
    for item in parsed:
        if isinstance(item, dict) and item.get("key") and item.get("value"):
            valid.append({
                "key": item["key"][:50],
                "value": item["value"][:200],
                "type": item.get("type", "fact"),
                "is_core": item.get("is_core", False),
            })

    return valid if valid else None
