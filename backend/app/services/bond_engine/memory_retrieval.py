"""
Memory Retrieval — scored retrieval with diversity constraints.

Replaces "latest N facts/emotions" with scored, bounded retrieval:
  - Relevance to current user message
  - Recency weighting
  - Emotional priority weighting
  - Conflict penalty
  - Diversity rule (no same callback in recent N turns)

Output bundle for prompt_builder:
  - facts_top (max 4)
  - emotions_top (max 3)
  - episodes_top (max 2)
  - patterns_top (max 2)
  - avoid_callbacks (recently used memory ids)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

from app.services.bond_engine.memory_scoring import compute_memory_score
from app.core.config import get_settings
from app.services.embedding import embed_text
from app.services.vector_memory_store import search_memory, VectorSearchResult

logger = logging.getLogger(__name__)


# ── Retrieval Limits ─────────────────────────────────────────────────────────

MAX_FACTS = 4
MAX_EMOTIONS = 3
MAX_EPISODES = 2
MAX_PATTERNS = 2
DIVERSITY_WINDOW = 8  # don't repeat same memory callback within N turns


@dataclass
class MemoryBundle:
    """Structured memory bundle for prompt injection."""
    facts_top: list[dict] = field(default_factory=list)        # max 4
    emotions_top: list[dict] = field(default_factory=list)     # max 3
    episodes_top: list[dict] = field(default_factory=list)     # max 2
    patterns_top: list[dict] = field(default_factory=list)     # max 2
    avoid_callbacks: list[str] = field(default_factory=list)   # recently used memory ids

    def to_prompt_dict(self) -> dict:
        """Convert to the dict format consumed by prompt_builder."""
        return {
            "facts": [f["text"] for f in self.facts_top],
            "emotions": [e["text"] for e in self.emotions_top],
            "episodes": [ep["text"] for ep in self.episodes_top],
            "patterns": [p["text"] for p in self.patterns_top],
            "habits": [p["text"] for p in self.patterns_top],  # backward compat
        }

    def has_content(self) -> bool:
        return bool(self.facts_top or self.emotions_top or self.episodes_top or self.patterns_top)


# ── Recently Used Tracking ───────────────────────────────────────────────────

def get_recently_used_memory_ids(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    window: int = DIVERSITY_WINDOW,
) -> list[str]:
    """Get memory IDs used in the last N response fingerprints."""
    if not sb:
        return []
    try:
        r = (
            sb.table("response_fingerprints")
            .select("memory_ids_used")
            .eq("user_id", str(user_id))
            .eq("girlfriend_id", str(girlfriend_id))
            .order("created_at", desc=True)
            .limit(window)
            .execute()
        )
        ids: list[str] = []
        for row in (r.data or []):
            ids.extend(row.get("memory_ids_used") or [])
        return ids
    except Exception:
        return []


# ── Score and Rank ───────────────────────────────────────────────────────────

def _score_and_rank(
    items: list[dict],
    current_message: str,
    avoid_ids: list[str],
    text_key: str = "text",
    max_items: int = 4,
) -> list[dict]:
    """Score items and return top N, excluding recently used."""
    scored: list[tuple[float, dict]] = []
    for item in items:
        item_id = item.get("id", "")
        if item_id in avoid_ids:
            continue  # diversity constraint
        score = compute_memory_score(
            salience=item.get("salience", 50),
            confidence=item.get("confidence", 80),
            last_reinforced_at=item.get("last_reinforced_at") or item.get("last_seen_at") or item.get("occurred_at"),
            memory_text=item.get(text_key, ""),
            current_message=current_message,
            valence=item.get("valence", 0),
            intensity=item.get("intensity", 0),
            is_resolved=item.get("is_resolved", True),
            is_conflicted=item.get("is_conflicted", False),
            conflict_count=item.get("conflict_count", 0),
            semantic_boost=item.get("semantic_boost", 0.0),
        )
        scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:max_items]]


# ── Fetch Raw Memories ───────────────────────────────────────────────────────

def _fetch_factual(sb: Any, user_id: UUID, girlfriend_id: UUID, limit: int = 20) -> list[dict]:
    if not sb:
        return []
    try:
        r = (
            sb.table("factual_memory")
            .select("id, key, value, confidence, salience, last_seen_at, last_reinforced_at, is_conflicted, conflict_count")
            .eq("user_id", str(user_id))
            .eq("girlfriend_id", str(girlfriend_id))
            .order("last_seen_at", desc=True)
            .limit(limit)
            .execute()
        )
        results = []
        for row in (r.data or []):
            # Build human-readable text
            key = row.get("key", "")
            value = row.get("value", "")
            text = _fact_to_text(key, value)
            results.append({**row, "text": text})
        return results
    except Exception as e:
        logger.warning("Fetch factual memory failed: %s", e)
        return []


def _fetch_emotional(sb: Any, user_id: UUID, girlfriend_id: UUID, limit: int = 15) -> list[dict]:
    if not sb:
        return []
    try:
        r = (
            sb.table("emotional_memory")
            .select("id, event, emotion_tags, valence, intensity, occurred_at, salience, confidence, is_resolved")
            .eq("user_id", str(user_id))
            .eq("girlfriend_id", str(girlfriend_id))
            .order("occurred_at", desc=True)
            .limit(limit)
            .execute()
        )
        results = []
        for row in (r.data or []):
            tags = ", ".join(row.get("emotion_tags") or [])
            text = f"{row.get('event', '')} (felt {tags})"
            results.append({**row, "text": text, "last_reinforced_at": row.get("occurred_at")})
        return results
    except Exception as e:
        logger.warning("Fetch emotional memory failed: %s", e)
        return []


def _fetch_episodic(sb: Any, user_id: UUID, girlfriend_id: UUID, limit: int = 10) -> list[dict]:
    if not sb:
        return []
    try:
        r = (
            sb.table("memory_episodes")
            .select("id, episode_type, summary, emotion_tags, salience, confidence, last_reinforced_at, is_resolved")
            .eq("user_id", str(user_id))
            .eq("girlfriend_id", str(girlfriend_id))
            .order("salience", desc=True)
            .limit(limit)
            .execute()
        )
        results = []
        for row in (r.data or []):
            results.append({**row, "text": row.get("summary", "")})
        return results
    except Exception as e:
        logger.warning("Fetch episodic memory failed: %s", e)
        return []


def _fetch_patterns(sb: Any, user_id: UUID, girlfriend_id: UUID) -> list[dict]:
    if not sb:
        return []
    try:
        r = (
            sb.table("memory_patterns")
            .select("id, pattern_type, pattern_key, pattern_value, salience, confidence, last_reinforced_at")
            .eq("user_id", str(user_id))
            .eq("girlfriend_id", str(girlfriend_id))
            .order("salience", desc=True)
            .limit(10)
            .execute()
        )
        results = []
        for row in (r.data or []):
            text = _pattern_to_text(row)
            results.append({**row, "text": text})
        return results
    except Exception as e:
        logger.warning("Fetch pattern memory failed: %s", e)
        return []


# ── Text Formatters ──────────────────────────────────────────────────────────

_FACT_TEMPLATES: dict[str, str] = {
    "user.name": "Your name is {value}",
    "user.city": "You live in {value}",
    "user.country": "You're from {value}",
    "user.study": "You study {value}",
    "user.work": "You work as {value}",
    "user.age": "You're {value} years old",
    "user.pet": "You have a {value}",
    "pref.music": "You like {value} music",
    "pref.food": "You enjoy {value}",
    "pref.hobby": "You enjoy {value}",
    "schedule.exam": "You have an exam: {value}",
    "schedule.birthday": "Your birthday: {value}",
    "schedule.interview": "You have an interview: {value}",
}


def _fact_to_text(key: str, value: str) -> str:
    template = _FACT_TEMPLATES.get(key)
    if template:
        return template.format(value=value)
    if key.startswith("pref.like."):
        return f"You like {value}"
    if key.startswith("pref.dislike."):
        return f"You dislike {value}"
    return f"{key}: {value}"


def _pattern_to_text(row: dict) -> str:
    ptype = row.get("pattern_type", "")
    pval = row.get("pattern_value") or {}

    if ptype == "time_habit":
        hours = pval.get("hours", [])
        if hours:
            hours_str = ", ".join(f"{h}:00" for h in hours[:4])
            return f"You usually message around {hours_str}"
        return "Your messaging times vary"

    if ptype == "response_latency":
        gap = pval.get("avg_gap_minutes")
        if gap:
            if gap < 60:
                return f"You typically reply within {int(gap)} minutes"
            return f"You typically reply every {round(gap / 60, 1)} hours"
        return "Your reply cadence varies"

    if ptype == "style_preference":
        avg_len = pval.get("avg_length", 0)
        emoji_rate = pval.get("emoji_rate", 0)
        desc = []
        if avg_len > 100:
            desc.append("detailed messages")
        elif avg_len < 30:
            desc.append("brief messages")
        if emoji_rate > 0.3:
            desc.append("with frequent emoji")
        return f"You tend to send {', '.join(desc)}" if desc else "Your message style varies"

    if ptype == "topic_cycle":
        topics = sorted(pval.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0, reverse=True)
        if topics:
            top = [t[0] for t in topics[:3]]
            return f"You often talk about: {', '.join(top)}"
        return "Your conversation topics vary"

    return f"Pattern: {ptype}"


# ── Main Retrieval Function ──────────────────────────────────────────────────

def build_memory_bundle(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    current_message: str,
) -> MemoryBundle:
    """Build a scored, bounded memory bundle for prompt injection.
    
    Retrieval contract:
      - 1-2 emotionally relevant recalls
      - 1 contextual fact
      - 0-1 pattern callback
      - Hard diversity constraint (no same callback in N turns)
    """
    settings = get_settings()

    # Get recently used memory IDs for diversity
    avoid_ids = get_recently_used_memory_ids(sb, user_id, girlfriend_id)

    # Fetch raw candidates from structured memory
    raw_facts = _fetch_factual(sb, user_id, girlfriend_id)
    raw_emotions = _fetch_emotional(sb, user_id, girlfriend_id)
    raw_episodes = _fetch_episodic(sb, user_id, girlfriend_id)
    raw_patterns = _fetch_patterns(sb, user_id, girlfriend_id)

    # ── Optional: semantic retrieval via Pinecone ──────────────────────────
    # We run this in hybrid mode: vector candidates can augment or slightly
    # reorder the default scoring, but on any error we silently fall back.
    try:
        if not settings.vector_memory_enabled or not sb:
            logger.debug("Vector memory search skipped (enabled=%s, sb=%s)", settings.vector_memory_enabled, bool(sb))
        elif settings.vector_memory_enabled and sb:
            # Build a retrieval query from the current message (can be expanded
            # later to include a small window).
            query_text = (current_message or "").strip()
            if not query_text:
                logger.debug("Vector memory search skipped (empty current_message)")
            else:
                logger.info("Vector memory search running (query_len=%d, user_id=%s, gf_id=%s)", len(query_text), str(user_id), str(girlfriend_id))
                embedding = embed_text(query_text)
                vec_results = search_memory(
                    query_embedding=embedding,
                    user_id=str(user_id),
                    girlfriend_id=str(girlfriend_id),
                    top_k=16,
                )
                logger.info("Vector memory search done (hits=%d)", len(vec_results))
                # Hybrid re-ranking: attach scores back onto structured items
                # where possible, using a simple boost without breaking the
                # existing compute_memory_score logic.
                boost_map: dict[str, float] = {}
                for r in vec_results:
                    meta = r.metadata or {}
                    src_type = meta.get("source_type")
                    src_id = meta.get("source_id")
                    if not src_type or not src_id:
                        continue
                    key = f"{src_type}:{src_id}"
                    boost_map[key] = max(boost_map.get(key, 0.0), float(r.score or 0.0))

                def _attach_boost(items: list[dict], src_type: str) -> None:
                    for item in items:
                        mid = str(item.get("id", ""))
                        key = f"{src_type}:{mid}"
                        if key in boost_map:
                            item["semantic_boost"] = boost_map[key]

                _attach_boost(raw_facts, "factual")
                _attach_boost(raw_emotions, "emotional")
                _attach_boost(raw_episodes, "episode")
    except Exception as e:
        logger.debug("Semantic vector retrieval failed (fallback to heuristic): %s", e)

    # Score and rank with diversity constraints
    facts_top = _score_and_rank(raw_facts, current_message, avoid_ids, max_items=MAX_FACTS)
    emotions_top = _score_and_rank(raw_emotions, current_message, avoid_ids, max_items=MAX_EMOTIONS)
    episodes_top = _score_and_rank(raw_episodes, current_message, avoid_ids, max_items=MAX_EPISODES)
    patterns_top = _score_and_rank(raw_patterns, current_message, avoid_ids, max_items=MAX_PATTERNS)

    return MemoryBundle(
        facts_top=facts_top,
        emotions_top=emotions_top,
        episodes_top=episodes_top,
        patterns_top=patterns_top,
        avoid_callbacks=avoid_ids,
    )
