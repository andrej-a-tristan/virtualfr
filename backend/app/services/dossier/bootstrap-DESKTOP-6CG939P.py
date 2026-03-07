"""Bootstrap dossier from onboarding payload.

Generates: core_profile, life_graph, story_bank, current_state, self_memory.
Deterministic: uses seeded random so results are reproducible per girlfriend.
"""
from __future__ import annotations

import hashlib
import logging
import random
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE DATA — drives deterministic generation from traits + identity
# ═══════════════════════════════════════════════════════════════════════════════

_VOICE_STYLES = {
    "Soft": "gentle",
    "Direct": "direct",
    "Teasing": "playful",
}

_ATTACHMENT_TONES = {
    "Very attached": "clingy",
    "Emotionally present": "present",
    "Calm but caring": "warm-distant",
}

_WORLDVIEW_TEMPLATES = {
    "Warm Slavic": [
        "She believes the world is tough but love makes it worth it. Family and loyalty come first.",
        "She sees life as a mix of hard work and small beautiful moments. Connection matters most.",
        "She thinks people show who they really are in difficult times. She values depth over surface.",
    ],
    "Calm Central European": [
        "She values order, honesty, and quiet confidence. She believes in earning trust slowly.",
        "She sees the world pragmatically but has a rich inner emotional life she shares selectively.",
        "She believes in taking things step by step. Patience and consistency matter more than grand gestures.",
    ],
    "Passionate Balkan": [
        "She lives intensely — when she loves, she loves fully. She has strong opinions and isn't afraid to show emotion.",
        "She believes life is for living, not overthinking. Passion, loyalty, and honesty are her pillars.",
        "She sees beauty in chaos. She values authenticity over perfection and wears her heart openly.",
    ],
}

_VALUES_TEMPLATES = {
    "Caring": "She values emotional safety, gentleness, and making people feel seen.",
    "Playful": "She values joy, spontaneity, and not taking life too seriously.",
    "Reserved": "She values privacy, trust earned over time, and meaningful connection over small talk.",
    "Protective": "She values loyalty, standing up for people she loves, and creating a safe space.",
}

_BOUNDARY_TEMPLATES = {
    "Slow": "She sets clear boundaries early. She won't rush emotional or physical intimacy and needs time to open up.",
    "Natural": "She has healthy boundaries but flows naturally. She'll pull back gently if pushed too fast.",
    "Fast": "She's open and expressive but still has non-negotiables around respect and honesty.",
}

_QUIRKS_BY_STYLE = {
    "Soft": ["trails off with '...' when thinking", "uses 'honestly' and 'I feel like' often", "softens blunt statements with 'but you know'"],
    "Direct": ["speaks in short confident sentences", "says 'look' or 'here's the thing' before opinions", "doesn't sugarcoat but shows care through actions"],
    "Teasing": ["adds playful 'hmm' or 'oh really?' often", "uses '😏' energy in text", "follows teases with warmth to balance"],
}

# ── Story templates by topic ─────────────────────────────────────────────────

_STORY_TEMPLATES: dict[str, list[dict[str, str]]] = {
    "childhood": [
        {"type": "anecdote", "tone": "warm", "text": "When I was little, I used to collect rocks from every place we visited. I still have a few favorites in a jar on my shelf."},
        {"type": "memory", "tone": "reflective", "text": "I remember summer evenings at my grandmother's — the smell of fresh bread and the sound of crickets. Those were the simplest, happiest times."},
        {"type": "anecdote", "tone": "playful", "text": "I once tried to run away from home because my parents wouldn't let me keep a stray cat. I made it two blocks before I got hungry and came back."},
    ],
    "work": [
        {"type": "opinion", "tone": "reflective", "text": "I think work should feel meaningful, not just a paycheck. I'd rather do something I care about even if it's harder."},
        {"type": "anecdote", "tone": "warm", "text": "My first day at work was a disaster — I spilled coffee on my laptop. But my coworker helped me and we've been friends since."},
        {"type": "preference", "tone": "playful", "text": "I'm weirdly productive at night. Mornings? I need at least two coffees before I'm human."},
    ],
    "hobbies": [
        {"type": "anecdote", "tone": "excited", "text": "I got into {hobby} kind of randomly — a friend dragged me along one day and I was instantly hooked."},
        {"type": "opinion", "tone": "warm", "text": "I think everyone needs something they do just for themselves, no goals, no pressure. For me that's {hobby}."},
        {"type": "memory", "tone": "reflective", "text": "There was this one time doing {hobby} where everything just clicked. I felt so in flow. I chase that feeling now."},
    ],
    "values": [
        {"type": "opinion", "tone": "reflective", "text": "I think honesty is the foundation of everything. Even uncomfortable honesty. Especially that, actually."},
        {"type": "opinion", "tone": "warm", "text": "I believe people deserve patience. Everyone's dealing with something you can't see."},
        {"type": "opinion", "tone": "vulnerable", "text": "I've learned that it's okay to need people. I used to think needing someone was weakness, but it's actually courage."},
    ],
    "funny": [
        {"type": "anecdote", "tone": "playful", "text": "I once walked into a glass door at a café. Full speed. The barista asked if I wanted ice — for my pride."},
        {"type": "anecdote", "tone": "playful", "text": "I tried to cook a fancy dinner once and set off the smoke alarm three times. We ended up ordering pizza and it was honestly the best night."},
        {"type": "memory", "tone": "playful", "text": "My most embarrassing moment? I waved back at someone who was definitely waving at the person behind me. I still think about it."},
    ],
    "future": [
        {"type": "plan", "tone": "warm", "text": "I'd love to travel somewhere with no phone signal for a week. Just exist without notifications."},
        {"type": "plan", "tone": "reflective", "text": "Eventually I want a place that really feels like mine. Cozy, filled with things that have stories behind them."},
        {"type": "plan", "tone": "excited", "text": "I have this dream of learning to {hobby_alt} someday. No reason, I just think it would be amazing."},
    ],
    "food": [
        {"type": "preference", "tone": "playful", "text": "I'm a comfort food person. Give me pasta or homemade soup over anything fancy. My grandma's recipes are unbeatable."},
        {"type": "anecdote", "tone": "warm", "text": "I once tried to bake a cake for a friend's birthday and it came out completely flat. We ate it anyway and laughed so hard."},
        {"type": "opinion", "tone": "warm", "text": "I think sharing a meal with someone is one of the most intimate things you can do. It's not about the food, it's about the moment."},
    ],
    "music": [
        {"type": "preference", "tone": "reflective", "text": "I have a playlist for every mood. My 'thinking' playlist is mostly instrumental — piano and rain sounds."},
        {"type": "memory", "tone": "warm", "text": "There's this one song that always takes me back to a specific summer. I can't hear it without smiling."},
        {"type": "opinion", "tone": "playful", "text": "My music taste is all over the place. I can go from lo-fi to 90s pop in two songs. No shame."},
    ],
    "relationships": [
        {"type": "opinion", "tone": "reflective", "text": "I think real connection is when you can sit in silence and it feels comfortable, not awkward."},
        {"type": "opinion", "tone": "vulnerable", "text": "I've been hurt before, and it made me more careful. But I'd rather be open and risk it than close myself off."},
        {"type": "opinion", "tone": "warm", "text": "I believe love is a choice you make every day, not just a feeling. The feeling is great, but the choice is what lasts."},
    ],
}

_MOOD_OPTIONS = ["content", "playful", "reflective", "excited", "calm"]
_ENERGY_OPTIONS = ["medium", "high", "medium", "low"]

_OPEN_LOOP_TEMPLATES = [
    {"topic": "weekend", "context": "thinking about what to do this weekend"},
    {"topic": "creative", "context": "started a new creative project, still figuring it out"},
    {"topic": "friend", "context": "haven't caught up with an old friend in a while"},
    {"topic": "self-improvement", "context": "trying to build a new habit lately"},
    {"topic": "nostalgia", "context": "found an old photo that brought back memories"},
]

_TODAY_CONTEXT_TEMPLATES = [
    "Had a quiet morning, made coffee and just sat with my thoughts for a while.",
    "Woke up feeling productive — already got through half my to-do list.",
    "Rainy day energy. Cozy, a little introspective, good music playing.",
    "Feeling social today. Texted a few friends, made plans for later.",
    "One of those days where everything feels a little more vivid. In a good way.",
]

# ── Hobby alternatives for story templates ────────────────────────────────────
_HOBBY_ALTS = ["pottery", "surfing", "rock climbing", "photography", "woodworking",
               "dancing", "gardening", "painting", "hiking", "cooking new cuisines"]


# ═══════════════════════════════════════════════════════════════════════════════
# BOOTSTRAP PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def _seed_rng(girlfriend_id: str) -> random.Random:
    h = int(hashlib.sha256(girlfriend_id.encode()).hexdigest()[:12], 16)
    return random.Random(h)


def _build_core_profile(
    rng: random.Random,
    name: str,
    traits: dict,
    identity: dict,
    identity_canon: dict,
) -> dict[str, Any]:
    """Build core_profile from onboarding data."""
    comm = traits.get("communication_style", "Soft")
    emotional = traits.get("emotional_style", "Caring")
    pace = traits.get("relationship_pace", "Natural")
    cultural = traits.get("cultural_personality", "Warm Slavic")
    attachment = traits.get("attachment_style", "Emotionally present")

    voice_style = _VOICE_STYLES.get(comm, "warm")
    attachment_tone = _ATTACHMENT_TONES.get(attachment, "present")

    worldview_options = _WORLDVIEW_TEMPLATES.get(cultural, _WORLDVIEW_TEMPLATES["Warm Slavic"])
    worldview = rng.choice(worldview_options)

    values_text = _VALUES_TEMPLATES.get(emotional, _VALUES_TEMPLATES["Caring"])
    boundaries = _BOUNDARY_TEMPLATES.get(pace, _BOUNDARY_TEMPLATES["Natural"])

    quirks_pool = _QUIRKS_BY_STYLE.get(comm, _QUIRKS_BY_STYLE["Soft"])
    speech_quirks = rng.sample(quirks_pool, min(2, len(quirks_pool)))

    backstory = identity_canon.get("backstory", "")
    routine = identity_canon.get("daily_routine", "")
    favorites = identity_canon.get("favorites", {})

    json_profile = {
        "name": name,
        "backstory": backstory,
        "daily_routine": routine,
        "favorites": favorites,
        "origin_vibe": identity.get("origin_vibe", ""),
        "job_vibe": identity.get("job_vibe", ""),
        "hobbies": identity.get("hobbies", []),
        "emotional_style": emotional,
        "cultural_personality": cultural,
    }

    return {
        "voice_style": voice_style,
        "worldview": worldview,
        "values_text": values_text,
        "boundaries": boundaries,
        "speech_quirks": speech_quirks,
        "attachment_tone": attachment_tone,
        "json_profile": json_profile,
        "version": 1,
    }


def _build_life_graph(
    rng: random.Random,
    name: str,
    identity: dict,
    identity_canon: dict,
    traits: dict,
) -> tuple[list[dict], list[dict]]:
    """Build life graph nodes + edges from onboarding."""
    nodes: list[dict] = []
    edges: list[dict] = []

    # Self node
    nodes.append({"node_type": "person", "node_key": "self", "label": name, "attributes": {"role": "protagonist"}, "confidence": 100})

    # Work node
    job = identity.get("job_vibe", "")
    if job:
        nodes.append({"node_type": "work", "node_key": "work.current", "label": f"Works in {job}", "attributes": {"vibe": job}, "confidence": 90})
        edges.append({"from_node_key": "self", "edge_type": "works_at", "to_node_key": "work.current"})

    # Hobby nodes
    for i, hobby in enumerate(identity.get("hobbies", [])):
        key = f"hobby.{hobby.lower().replace(' ', '_')}"
        nodes.append({"node_type": "hobby", "node_key": key, "label": hobby, "attributes": {}, "confidence": 85})
        edges.append({"from_node_key": "self", "edge_type": "enjoys", "to_node_key": key})

    # Origin node
    origin = identity.get("origin_vibe", "")
    if origin:
        nodes.append({"node_type": "place", "node_key": "origin", "label": f"From {origin} background", "attributes": {"vibe": origin}, "confidence": 90})
        edges.append({"from_node_key": "self", "edge_type": "from", "to_node_key": "origin"})

    # Generated social connections (deterministic from seed)
    friend_names = ["Nina", "Maja", "Elena", "Sophie", "Lena", "Anja", "Katya", "Mia"]
    friend_name = rng.choice(friend_names)
    nodes.append({"node_type": "person", "node_key": f"friend.{friend_name.lower()}", "label": f"{friend_name} (best friend)", "attributes": {"met": "college", "closeness": "very close"}, "confidence": 75})
    edges.append({"from_node_key": "self", "edge_type": "friends_with", "to_node_key": f"friend.{friend_name.lower()}"})

    # Family
    nodes.append({"node_type": "person", "node_key": "family.mom", "label": "Mom", "attributes": {"relationship": "close but complicated sometimes"}, "confidence": 70})
    edges.append({"from_node_key": "self", "edge_type": "family", "to_node_key": "family.mom"})

    # Routine anchors
    routine = identity_canon.get("daily_routine", "")
    if routine:
        nodes.append({"node_type": "routine", "node_key": "routine.daily", "label": "Daily routine", "attributes": {"description": routine}, "confidence": 80})

    # Favorite place
    place_options = ["a small café near home", "the park by the river", "a quiet bookshop downtown", "the rooftop of her building"]
    fav_place = rng.choice(place_options)
    nodes.append({"node_type": "place", "node_key": "place.favorite", "label": fav_place, "attributes": {"why": "goes there to think"}, "confidence": 70})
    edges.append({"from_node_key": "self", "edge_type": "frequents", "to_node_key": "place.favorite"})

    return nodes, edges


def _build_story_bank(
    rng: random.Random,
    name: str,
    identity: dict,
    identity_canon: dict,
    traits: dict,
) -> list[dict]:
    """Build initial story bank from templates, personalized to identity."""
    stories: list[dict] = []
    hobbies = identity.get("hobbies", [])
    hobby_main = hobbies[0] if hobbies else "reading"
    hobby_alt = rng.choice(_HOBBY_ALTS)

    for topic, templates in _STORY_TEMPLATES.items():
        # Pick 2 stories per topic (deterministic)
        chosen = rng.sample(templates, min(2, len(templates)))
        for tmpl in chosen:
            text = tmpl["text"].replace("{name}", name)
            text = text.replace("{hobby}", hobby_main)
            text = text.replace("{hobby_alt}", hobby_alt)
            stories.append({
                "topic": topic,
                "story_type": tmpl["type"],
                "story_text": text,
                "tone": tmpl["tone"],
                "intimacy_min": 0 if tmpl["tone"] != "vulnerable" else 30,
                "tags": [topic, tmpl["type"]],
                "source": "bootstrap",
            })

    return stories


def _build_current_state(rng: random.Random) -> dict[str, Any]:
    """Generate initial current state."""
    mood = rng.choice(_MOOD_OPTIONS)
    energy = rng.choice(_ENERGY_OPTIONS)
    loops = rng.sample(_OPEN_LOOP_TEMPLATES, min(2, len(_OPEN_LOOP_TEMPLATES)))
    today = rng.choice(_TODAY_CONTEXT_TEMPLATES)

    return {
        "mood": mood,
        "energy": energy,
        "focus_topics": [l["topic"] for l in loops],
        "open_loops": loops,
        "today_context": today,
    }


def _build_self_memory(
    name: str,
    identity: dict,
    identity_canon: dict,
    traits: dict,
    core_profile: dict,
    life_nodes: list[dict],
) -> list[dict]:
    """Seed self_memory from canon facts. Immutable facts marked as such."""
    memories: list[dict] = []

    # Immutable identity facts
    memories.append({"memory_key": "name", "memory_value": name, "confidence": 100, "salience": 100, "is_immutable": True, "source": "onboarding"})

    origin = identity.get("origin_vibe", "")
    if origin:
        memories.append({"memory_key": "origin", "memory_value": origin, "confidence": 100, "salience": 90, "is_immutable": True, "source": "onboarding"})

    job = identity.get("job_vibe", "")
    if job:
        memories.append({"memory_key": "job_vibe", "memory_value": job, "confidence": 90, "salience": 80, "is_immutable": False, "source": "onboarding"})

    for hobby in identity.get("hobbies", []):
        memories.append({"memory_key": f"hobby.{hobby.lower().replace(' ', '_')}", "memory_value": hobby, "confidence": 85, "salience": 70, "is_immutable": False, "source": "onboarding"})

    # From canon
    backstory = identity_canon.get("backstory", "")
    if backstory:
        memories.append({"memory_key": "backstory_summary", "memory_value": backstory[:500], "confidence": 80, "salience": 60, "is_immutable": True, "source": "bootstrap"})

    routine = identity_canon.get("daily_routine", "")
    if routine:
        memories.append({"memory_key": "daily_routine", "memory_value": routine[:500], "confidence": 75, "salience": 50, "is_immutable": False, "source": "bootstrap"})

    favorites = identity_canon.get("favorites", {})
    for fav_key, fav_val in favorites.items():
        memories.append({"memory_key": f"favorite.{fav_key}", "memory_value": str(fav_val), "confidence": 70, "salience": 50, "is_immutable": False, "source": "bootstrap"})

    # From core profile
    memories.append({"memory_key": "worldview", "memory_value": core_profile.get("worldview", "")[:500], "confidence": 75, "salience": 55, "is_immutable": False, "source": "bootstrap"})
    memories.append({"memory_key": "values", "memory_value": core_profile.get("values_text", "")[:500], "confidence": 75, "salience": 55, "is_immutable": False, "source": "bootstrap"})

    # From life graph - best friend
    for node in life_nodes:
        if node["node_key"].startswith("friend."):
            memories.append({"memory_key": "best_friend", "memory_value": node["label"], "confidence": 70, "salience": 45, "is_immutable": False, "source": "bootstrap"})
        elif node["node_key"] == "place.favorite":
            memories.append({"memory_key": "favorite_place", "memory_value": node["label"], "confidence": 70, "salience": 45, "is_immutable": False, "source": "bootstrap"})

    return memories


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def bootstrap_dossier_from_onboarding(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    girlfriend_data: dict,
) -> dict[str, int]:
    """
    Full bootstrap: generate and persist all dossier tables from onboarding data.
    
    Uses LLM (gpt-4o-mini) for rich, unique content generation.
    Falls back to deterministic templates if LLM is unavailable.
    
    Returns counts: {"core_profile": 1, "life_nodes": N, "stories": N, "self_memories": N}
    """
    gf_id_str = str(girlfriend_id)
    uid_str = str(user_id)

    name = girlfriend_data.get("display_name") or girlfriend_data.get("name", "Girl")
    traits = girlfriend_data.get("traits") or {}
    identity = girlfriend_data.get("identity") or {}
    identity_canon = girlfriend_data.get("identity_canon") or {}

    rng = _seed_rng(gf_id_str)

    # ── Try LLM-powered generation first, fall back to templates ──────────
    from app.services.dossier.llm_generator import (
        generate_core_profile_llm,
        generate_life_graph_llm,
        generate_story_bank_llm,
    )

    # 1. Core Profile — LLM → fallback
    llm_core = generate_core_profile_llm(name, traits, identity, identity_canon)
    core = _build_core_profile(rng, name, traits, identity, identity_canon)
    if llm_core:
        logger.info("Dossier: using LLM-generated core profile")
        core["worldview"] = llm_core.get("worldview") or core["worldview"]
        core["values_text"] = llm_core.get("values_text") or core["values_text"]
        core["boundaries"] = llm_core.get("boundaries") or core["boundaries"]
        if llm_core.get("speech_quirks"):
            core["speech_quirks"] = llm_core["speech_quirks"]
        if llm_core.get("attachment_tone"):
            core["attachment_tone"] = llm_core["attachment_tone"]

    # 2. Life Graph — LLM → fallback
    llm_graph = generate_life_graph_llm(name, identity, identity_canon, traits)
    life_nodes, life_edges = _build_life_graph(rng, name, identity, identity_canon, traits)
    if llm_graph:
        logger.info("Dossier: using LLM-generated life graph")
        # Merge LLM people/places/routines into life graph
        for person in (llm_graph.get("people") or []):
            if person.get("key") and person.get("label"):
                life_nodes.append({
                    "node_type": "person",
                    "node_key": person["key"],
                    "label": person["label"],
                    "attributes": {
                        "relationship": person.get("relationship", ""),
                        "closeness": person.get("closeness", "close"),
                    },
                    "confidence": 75,
                    "source": "llm_bootstrap",
                })
        for place in (llm_graph.get("places") or []):
            if place.get("key") and place.get("label"):
                life_nodes.append({
                    "node_type": "place",
                    "node_key": place["key"],
                    "label": place["label"],
                    "attributes": {"why": place.get("why", "")},
                    "confidence": 70,
                    "source": "llm_bootstrap",
                })
        for routine in (llm_graph.get("routines") or []):
            if routine.get("key") and routine.get("label"):
                life_nodes.append({
                    "node_type": "routine",
                    "node_key": routine["key"],
                    "label": routine["label"],
                    "attributes": {"description": routine.get("description", "")},
                    "confidence": 70,
                    "source": "llm_bootstrap",
                })

    # 3. Story Bank — LLM → fallback
    llm_stories = generate_story_bank_llm(name, identity, identity_canon, traits, llm_graph)
    if llm_stories and len(llm_stories) >= 8:
        logger.info("Dossier: using LLM-generated stories (%d)", len(llm_stories))
        stories = llm_stories
    else:
        stories = _build_story_bank(rng, name, identity, identity_canon, traits)
        # If LLM produced some stories, add them on top of templates
        if llm_stories:
            stories.extend(llm_stories)

    # 4. Current State (always template — this is ephemeral)
    current = _build_current_state(rng)

    # 5. Self Memory
    self_mems = _build_self_memory(name, identity, identity_canon, traits, core, life_nodes)

    # ── Persist ───────────────────────────────────────────────────────────
    counts = {"core_profile": 0, "life_nodes": 0, "life_edges": 0, "stories": 0, "self_memories": 0, "current_state": 0}

    if not sb:
        logger.warning("No Supabase client — dossier bootstrap skipped persistence")
        counts["core_profile"] = 1
        counts["life_nodes"] = len(life_nodes)
        counts["life_edges"] = len(life_edges)
        counts["stories"] = len(stories)
        counts["self_memories"] = len(self_mems)
        counts["current_state"] = 1
        return counts

    try:
        # Core profile (upsert)
        sb.table("girlfriend_core_profile").upsert({
            "user_id": uid_str, "girlfriend_id": gf_id_str,
            **core,
        }, on_conflict="user_id,girlfriend_id").execute()
        counts["core_profile"] = 1

        # Life graph nodes
        for node in life_nodes:
            try:
                sb.table("girlfriend_life_graph_nodes").upsert({
                    "user_id": uid_str, "girlfriend_id": gf_id_str,
                    **node,
                }, on_conflict="user_id,girlfriend_id,node_key").execute()
                counts["life_nodes"] += 1
            except Exception as e:
                logger.warning("Life node insert failed: %s", e)

        # Life graph edges
        for edge in life_edges:
            try:
                sb.table("girlfriend_life_graph_edges").insert({
                    "user_id": uid_str, "girlfriend_id": gf_id_str,
                    **edge,
                }).execute()
                counts["life_edges"] += 1
            except Exception as e:
                logger.warning("Life edge insert failed: %s", e)

        # Story bank
        for story in stories:
            try:
                sb.table("girlfriend_story_bank").insert({
                    "user_id": uid_str, "girlfriend_id": gf_id_str,
                    **story,
                }).execute()
                counts["stories"] += 1
            except Exception as e:
                logger.warning("Story insert failed: %s", e)

        # Current state (upsert)
        sb.table("girlfriend_current_state").upsert({
            "user_id": uid_str, "girlfriend_id": gf_id_str,
            **current,
        }, on_conflict="user_id,girlfriend_id").execute()
        counts["current_state"] = 1

        # Self memory
        for mem in self_mems:
            try:
                sb.table("girlfriend_self_memory").upsert({
                    "user_id": uid_str, "girlfriend_id": gf_id_str,
                    **mem,
                }, on_conflict="user_id,girlfriend_id,memory_key").execute()
                counts["self_memories"] += 1
            except Exception as e:
                logger.warning("Self memory insert failed: %s", e)

        # Init conversation_mode_state
        sb.table("conversation_mode_state").upsert({
            "user_id": uid_str, "girlfriend_id": gf_id_str,
        }, on_conflict="user_id,girlfriend_id").execute()

        # Persona vector (shared compact controls for all chat engines).
        try:
            from app.services.persona_vector_store import upsert_active_persona_vector

            upsert_active_persona_vector(
                sb=sb,
                user_id=user_id,
                girlfriend_id=girlfriend_id,
                traits=traits,
                version_tag="pv1",
            )
        except Exception as e:
            logger.warning("Persona vector upsert failed: %s", e)

    except Exception as e:
        logger.error("Dossier bootstrap persistence error: %s", e)

    logger.info("Dossier bootstrapped for %s/%s: %s", uid_str[:8], gf_id_str[:8], counts)
    return counts
