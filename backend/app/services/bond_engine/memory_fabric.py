"""
Memory Fabric — unified memory orchestration layer.

Combines all memory sub-modules into a single coherent interface:
  - Semantic memory (stable facts) via memory_ingest + memory_retrieval
  - Emotional memory (feeling traces + unresolved stressors)
  - Episodic memory (important moments, conflicts, wins, promises)
  - Pattern memory (time habits, topic cycles, response latency, style)

Provides two main entry points for chat.py:
  1. ingest_user_turn(...) — called after user message save
  2. build_prompt_memory_bundle(...) — called before prompt build
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from app.services.bond_engine.memory_ingest import ingest_user_turn as _raw_ingest
from app.services.bond_engine.memory_retrieval import (
    MemoryBundle,
    build_memory_bundle as _raw_build_bundle,
)

logger = logging.getLogger(__name__)


def ingest_user_turn(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    turn_id: str,
    text: str,
    all_user_timestamps: list[str] | None = None,
    all_user_messages: list[str] | None = None,
) -> dict:
    """Ingest a single user turn into all memory layers.
    
    Called from chat.py after user message is saved.
    Handles: fact extraction, emotion detection, episodic events,
    entity normalization, pattern updates, conflict detection.
    """
    try:
        return _raw_ingest(
            sb=sb,
            user_id=user_id,
            girlfriend_id=girlfriend_id,
            turn_id=turn_id,
            text=text,
            all_user_timestamps=all_user_timestamps,
            all_user_messages=all_user_messages,
        )
    except Exception as e:
        logger.warning("Memory ingestion failed (non-blocking): %s", e)
        return {
            "facts_extracted": 0,
            "emotions_detected": [],
            "episodes_created": 0,
            "conflicts_found": 0,
        }


def build_prompt_memory_bundle(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    current_message: str,
) -> MemoryBundle:
    """Build a scored, bounded memory bundle for prompt injection.
    
    Called from chat.py before prompt building.
    Provides structured memory with diversity constraints.
    
    Retrieval contract:
      - facts_top (max 4) — stable, high-confidence facts
      - emotions_top (max 3) — with priority on unresolved emotional threads
      - episodes_top (max 2) — important shared moments / promises / conflicts
      - patterns_top (max 2) — time habits, topic preferences
      - avoid_callbacks — recently used memory IDs (no repeat within N turns)
    """
    try:
        return _raw_build_bundle(
            sb=sb,
            user_id=user_id,
            girlfriend_id=girlfriend_id,
            current_message=current_message,
        )
    except Exception as e:
        logger.warning("Memory bundle build failed (non-blocking): %s", e)
        return MemoryBundle()


def record_used_memories(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    turn_id: str,
    memory_ids_used: list[str],
    fingerprint: dict | None = None,
) -> None:
    """Record which memory items were used in a response (for diversity tracking)."""
    if not sb or not memory_ids_used:
        return
    try:
        from datetime import datetime, timezone
        sb.table("response_fingerprints").insert({
            "user_id": str(user_id),
            "girlfriend_id": str(girlfriend_id),
            "turn_id": turn_id,
            "memory_ids_used": memory_ids_used,
            "fingerprint": fingerprint or {},
        }).execute()
    except Exception as e:
        logger.debug("Failed to record used memories: %s", e)


def get_unresolved_emotional_threads(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    limit: int = 3,
) -> list[dict]:
    """Get unresolved negative emotional threads (for initiation/follow-up)."""
    if not sb:
        return []
    try:
        r = (
            sb.table("emotional_memory")
            .select("id, event, emotion_tags, valence, intensity, occurred_at")
            .eq("user_id", str(user_id))
            .eq("girlfriend_id", str(girlfriend_id))
            .eq("is_resolved", False)
            .lt("valence", 0)
            .order("occurred_at", desc=True)
            .limit(limit)
            .execute()
        )
        return r.data or []
    except Exception:
        return []


def get_pending_promises(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
) -> list[dict]:
    """Get unresolved promises/commitments for follow-up."""
    if not sb:
        return []
    try:
        r = (
            sb.table("memory_episodes")
            .select("id, summary, created_at")
            .eq("user_id", str(user_id))
            .eq("girlfriend_id", str(girlfriend_id))
            .eq("episode_type", "promise")
            .eq("is_resolved", False)
            .order("created_at", desc=True)
            .limit(3)
            .execute()
        )
        return r.data or []
    except Exception:
        return []


def get_recent_wins(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    limit: int = 2,
) -> list[dict]:
    """Get recent wins/achievements for celebration callbacks."""
    if not sb:
        return []
    try:
        r = (
            sb.table("memory_episodes")
            .select("id, summary, created_at")
            .eq("user_id", str(user_id))
            .eq("girlfriend_id", str(girlfriend_id))
            .eq("episode_type", "win")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return r.data or []
    except Exception:
        return []
