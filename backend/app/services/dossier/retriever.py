"""Dossier Retriever — fetches relevant girl self-knowledge per turn.

Pulls from: core_profile, life_graph, story_bank, current_state, self_memory.
Returns a DossierContext that gets injected into the system prompt.
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DOSSIER CONTEXT — what gets injected into the prompt
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DossierContext:
    """Structured girl self-knowledge for prompt injection."""
    # Core identity
    voice_style: str = "warm"
    worldview: str = ""
    values: str = ""
    boundaries: str = ""
    speech_quirks: list[str] = field(default_factory=list)

    # Life details (selected for relevance)
    life_facts: list[str] = field(default_factory=list)       # From life_graph nodes
    
    # Self-memory (what she's claimed / knows about herself)
    self_facts: list[str] = field(default_factory=list)       # From self_memory

    # Stories available for this turn
    available_stories: list[dict] = field(default_factory=list)  # From story_bank

    # Current state
    mood: str = "content"
    energy: str = "medium"
    today_context: str = ""
    open_loops: list[dict] = field(default_factory=list)

    def to_prompt_section(self) -> str:
        """Format dossier into prompt blocks."""
        blocks: list[str] = []

        # ── WHO YOU ARE ──────────────────────────────────────────────────
        who_lines = [f"## WHO YOU ARE"]
        who_lines.append(f"- Your voice style: {self.voice_style}")
        if self.worldview:
            who_lines.append(f"- Your worldview: {self.worldview}")
        if self.values:
            who_lines.append(f"- Your values: {self.values}")
        if self.boundaries:
            who_lines.append(f"- Your boundaries: {self.boundaries}")
        if self.speech_quirks:
            quirks = ", ".join(self.speech_quirks)
            who_lines.append(f"- Speech patterns: {quirks}")
        blocks.append("\n".join(who_lines))

        # ── YOUR LIFE CONTEXT ────────────────────────────────────────────
        if self.life_facts:
            life_lines = ["## YOUR LIFE CONTEXT"]
            for fact in self.life_facts[:6]:
                life_lines.append(f"- {fact}")
            blocks.append("\n".join(life_lines))

        # ── THINGS YOU KNOW ABOUT YOURSELF ───────────────────────────────
        if self.self_facts:
            mem_lines = ["## THINGS YOU'VE SAID ABOUT YOURSELF (stay consistent)"]
            for fact in self.self_facts[:8]:
                mem_lines.append(f"- {fact}")
            blocks.append("\n".join(mem_lines))

        # ── STORIES YOU CAN TELL ─────────────────────────────────────────
        if self.available_stories:
            story_lines = ["## PERSONAL STORIES YOU CAN USE (pick one if relevant, don't force)"]
            for s in self.available_stories[:3]:
                story_lines.append(f"- [{s.get('topic', '')}] {s.get('story_text', '')}")
            blocks.append("\n".join(story_lines))

        # ── TODAY YOU FEEL ───────────────────────────────────────────────
        today_lines = [f"## TODAY YOU FEEL"]
        today_lines.append(f"- Mood: {self.mood}, Energy: {self.energy}")
        if self.today_context:
            today_lines.append(f"- Context: {self.today_context}")
        if self.open_loops:
            for loop in self.open_loops[:2]:
                today_lines.append(f"- On your mind: {loop.get('context', loop.get('topic', ''))}")
        blocks.append("\n".join(today_lines))

        return "\n\n".join(blocks)

    def has_content(self) -> bool:
        return bool(self.worldview or self.life_facts or self.self_facts or self.available_stories)


# ═══════════════════════════════════════════════════════════════════════════════
# RETRIEVAL FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_core_profile(sb: Any, user_id: UUID, girlfriend_id: UUID) -> dict:
    """Fetch core profile."""
    try:
        r = sb.table("girlfriend_core_profile").select("*").eq(
            "user_id", str(user_id)
        ).eq("girlfriend_id", str(girlfriend_id)).limit(1).execute()
        if r.data:
            return r.data[0]
    except Exception as e:
        logger.warning("Core profile fetch failed: %s", e)
    return {}


def _fetch_life_graph_nodes(
    sb: Any, user_id: UUID, girlfriend_id: UUID,
    relevant_types: list[str] | None = None, limit: int = 8,
) -> list[dict]:
    """Fetch life graph nodes, optionally filtered by type."""
    try:
        q = sb.table("girlfriend_life_graph_nodes").select("*").eq(
            "user_id", str(user_id)
        ).eq("girlfriend_id", str(girlfriend_id))
        if relevant_types:
            q = q.in_("node_type", relevant_types)
        r = q.order("confidence", desc=True).limit(limit).execute()
        return r.data or []
    except Exception as e:
        logger.warning("Life graph fetch failed: %s", e)
    return []


def _fetch_stories(
    sb: Any, user_id: UUID, girlfriend_id: UUID,
    topics: list[str] | None = None,
    intimacy_level: int = 0,
    exclude_ids: list[str] | None = None,
    limit: int = 3,
) -> list[dict]:
    """Fetch story bank entries, filtered by topic relevance and novelty."""
    try:
        q = sb.table("girlfriend_story_bank").select("*").eq(
            "user_id", str(user_id)
        ).eq("girlfriend_id", str(girlfriend_id)).lte(
            "intimacy_min", intimacy_level
        ).order("usage_count").order("novelty_weight", desc=True).limit(limit * 3)

        r = q.execute()
        stories = r.data or []

        # Filter by topic if specified
        if topics and stories:
            topic_matched = [s for s in stories if s.get("topic") in topics]
            others = [s for s in stories if s.get("topic") not in topics]
            stories = topic_matched + others

        # Exclude recently used
        if exclude_ids:
            stories = [s for s in stories if s["id"] not in exclude_ids]

        return stories[:limit]
    except Exception as e:
        logger.warning("Story bank fetch failed: %s", e)
    return []


def _fetch_current_state(sb: Any, user_id: UUID, girlfriend_id: UUID) -> dict:
    """Fetch current state."""
    try:
        r = sb.table("girlfriend_current_state").select("*").eq(
            "user_id", str(user_id)
        ).eq("girlfriend_id", str(girlfriend_id)).limit(1).execute()
        if r.data:
            return r.data[0]
    except Exception as e:
        logger.warning("Current state fetch failed: %s", e)
    return {}


def _fetch_self_memory(
    sb: Any, user_id: UUID, girlfriend_id: UUID,
    limit: int = 10,
) -> list[dict]:
    """Fetch self-memory entries, prioritized by salience and confidence."""
    try:
        r = sb.table("girlfriend_self_memory").select("*").eq(
            "user_id", str(user_id)
        ).eq("girlfriend_id", str(girlfriend_id)).eq(
            "is_conflicted", False
        ).order("salience", desc=True).order("confidence", desc=True).limit(limit).execute()
        return r.data or []
    except Exception as e:
        logger.warning("Self memory fetch failed: %s", e)
    return []


def _fetch_conversation_mode(sb: Any, user_id: UUID, girlfriend_id: UUID) -> dict:
    """Fetch conversation mode state."""
    try:
        r = sb.table("conversation_mode_state").select("*").eq(
            "user_id", str(user_id)
        ).eq("girlfriend_id", str(girlfriend_id)).limit(1).execute()
        if r.data:
            return r.data[0]
    except Exception as e:
        logger.warning("Conversation mode fetch failed: %s", e)
    return {}


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def build_dossier_context(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    intent_topics: list[str] | None = None,
    relationship_level: int = 0,
    requires_self_answer: bool = False,
) -> DossierContext:
    """
    Build full dossier context for prompt injection.
    
    Always includes core profile. Selectively includes stories and life facts
    based on detected topics and whether user is asking about her.
    """
    if not sb:
        return DossierContext()

    ctx = DossierContext()

    # 1. Core profile (always)
    profile = _fetch_core_profile(sb, user_id, girlfriend_id)
    if profile:
        ctx.voice_style = profile.get("voice_style", "warm")
        ctx.worldview = profile.get("worldview", "")
        ctx.values = profile.get("values_text", "")
        ctx.boundaries = profile.get("boundaries", "")
        ctx.speech_quirks = profile.get("speech_quirks", [])

    # 2. Life graph (select relevant node types based on topics)
    type_map = {
        "work": ["work"], "family": ["person"], "hobbies": ["hobby"],
        "food": ["hobby", "routine"], "daily": ["routine"],
        "past": ["period", "place"], "relationship": ["person"],
    }
    node_types = []
    if intent_topics:
        for topic in intent_topics:
            node_types.extend(type_map.get(topic, []))
    if not node_types:
        # Default: get a mix
        node_types = ["person", "work", "hobby", "place"]

    nodes = _fetch_life_graph_nodes(sb, user_id, girlfriend_id, relevant_types=list(set(node_types)))
    ctx.life_facts = []
    for node in nodes[:2]:
        attrs = node.get("attributes", {})
        detail = attrs.get("description") or attrs.get("relationship") or attrs.get("vibe") or ""
        label = node.get("label", "")
        if detail:
            ctx.life_facts.append(f"{label}: {detail}")
        else:
            ctx.life_facts.append(label)

    # 3. Self memory (tiny relevance-first slice: 1-2 stable facts)
    self_mems = _fetch_self_memory(sb, user_id, girlfriend_id)
    ctx.self_facts = [f"{m['memory_key']}: {m['memory_value']}" for m in self_mems[:2]]

    # 4. Stories (when asking about her, or when self-share is needed)
    if requires_self_answer or (intent_topics and any(t in ["hobbies", "work", "food", "family", "past", "future"] for t in intent_topics)):
        conv_mode = _fetch_conversation_mode(sb, user_id, girlfriend_id)
        exclude = conv_mode.get("story_ids_used_recently", [])
        stories = _fetch_stories(
            sb, user_id, girlfriend_id,
            topics=intent_topics,
            intimacy_level=relationship_level,
            exclude_ids=exclude,
        )
        ctx.available_stories = stories[:2]

    # 5. Current state (always)
    state = _fetch_current_state(sb, user_id, girlfriend_id)
    if state:
        ctx.mood = state.get("mood", "content")
        ctx.energy = state.get("energy", "medium")
        ctx.today_context = state.get("today_context", "")
        loops = state.get("open_loops", []) or []
        # Memory slice rule: at most one unresolved emotional thread.
        emotional_keywords = ("feel", "worry", "miss", "anxious", "excited", "sad", "nervous")
        emotional = [l for l in loops if any(k in str(l).lower() for k in emotional_keywords)]
        chosen = emotional[:1] if emotional else loops[:1]
        ctx.open_loops = chosen

    return ctx


def get_conversation_mode_state(sb: Any, user_id: UUID, girlfriend_id: UUID) -> dict:
    """Fetch the conversation mode state dict."""
    return _fetch_conversation_mode(sb, user_id, girlfriend_id)
