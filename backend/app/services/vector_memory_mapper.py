from __future__ import annotations

"""Mapping helpers: structured memory rows → canonical vector documents.

These helpers are used when creating rows in `memory_vector_documents` so the
worker can later embed `canonical_text` and sync to Pinecone.
"""

from dataclasses import dataclass
from typing import Any, Dict

import hashlib
from datetime import datetime


@dataclass
class MemoryVectorDocInput:
    """In-memory representation of a row for memory_vector_documents."""

    user_id: str
    girlfriend_id: str
    source_type: str           # factual|emotional|episode|chat_chunk
    source_id: str
    canonical_text: str
    memory_type: str           # user_fact|user_feeling|relationship_event|shared_episode|persona_fact|other
    salience: int = 50
    confidence: int = 80
    valence: int = 0
    intensity: int = 0
    is_resolved: bool = False
    occurred_at: str | None = None
    last_reinforced_at: str | None = None
    privacy_level: str = "private"

    def to_row(self) -> Dict[str, Any]:
        """Convert to a dict suitable for Supabase upsert."""
        text_hash = hashlib.sha256(self.canonical_text.encode("utf-8")).hexdigest()
        return {
            "user_id": self.user_id,
            "girlfriend_id": self.girlfriend_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "canonical_text": self.canonical_text,
            "text_hash": text_hash,
            "memory_type": self.memory_type,
            "salience": self.salience,
            "confidence": self.confidence,
            "valence": self.valence,
            "intensity": self.intensity,
            "is_resolved": self.is_resolved,
            "occurred_at": self.occurred_at,
            "last_reinforced_at": self.last_reinforced_at,
            "privacy_level": self.privacy_level,
        }


def _iso_or_none(v: Any) -> str | None:
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, str):
        return v
    return None


def from_factual_memory(row: Dict[str, Any]) -> MemoryVectorDocInput:
    """Map a factual_memory row to a vector doc input."""
    return MemoryVectorDocInput(
        user_id=str(row["user_id"]),
        girlfriend_id=str(row["girlfriend_id"]),
        source_type="factual",
        source_id=str(row["id"]),
        canonical_text=f"User fact: {row.get('key', '')}: {row.get('value', '')}",
        memory_type="user_fact",
        salience=int(row.get("salience", 50) or 50),
        confidence=int(row.get("confidence", 80) or 80),
        valence=0,
        intensity=0,
        is_resolved=bool(row.get("is_conflicted") is False),
        occurred_at=_iso_or_none(row.get("last_seen_at")),
        last_reinforced_at=_iso_or_none(row.get("last_reinforced_at")),
    )


def from_emotional_memory(row: Dict[str, Any]) -> MemoryVectorDocInput:
    """Map an emotional_memory row to a vector doc input."""
    tags = ", ".join(row.get("emotion_tags") or [])
    event = row.get("event", "")
    text = f"Emotional event: {event}"
    if tags:
        text += f" (feelings: {tags})"
    return MemoryVectorDocInput(
        user_id=str(row["user_id"]),
        girlfriend_id=str(row["girlfriend_id"]),
        source_type="emotional",
        source_id=str(row["id"]),
        canonical_text=text,
        memory_type="user_feeling",
        salience=int(row.get("salience", 50) or 50),
        confidence=int(row.get("confidence", 80) or 80),
        valence=int(row.get("valence", 0) or 0),
        intensity=int(row.get("intensity", 0) or 0),
        is_resolved=bool(row.get("is_resolved", False)),
        occurred_at=_iso_or_none(row.get("occurred_at")),
        last_reinforced_at=_iso_or_none(row.get("last_reinforced_at")),
    )


def from_episode(row: Dict[str, Any]) -> MemoryVectorDocInput:
    """Map a memory_episodes row to a vector doc input."""
    ep_type = row.get("episode_type", "episode")
    summary = row.get("summary", "")
    text = f"Relationship {ep_type}: {summary}"
    tags = ", ".join(row.get("emotion_tags") or [])
    if tags:
        text += f" (feelings: {tags})"
    return MemoryVectorDocInput(
        user_id=str(row["user_id"]),
        girlfriend_id=str(row["girlfriend_id"]),
        source_type="episode",
        source_id=str(row["id"]),
        canonical_text=text,
        memory_type="relationship_event",
        salience=int(row.get("salience", 60) or 60),
        confidence=int(row.get("confidence", 80) or 80),
        valence=0,
        intensity=0,
        is_resolved=bool(row.get("is_resolved", False)),
        occurred_at=_iso_or_none(row.get("created_at")),
        last_reinforced_at=_iso_or_none(row.get("last_reinforced_at")),
    )


def from_chat_chunk(
    user_id: str,
    girlfriend_id: str,
    source_id: str,
    window_text: str,
) -> MemoryVectorDocInput:
    """Create a vector doc from a chat chunk covering a short window."""
    canonical = f"Conversation snippet between user and girlfriend: {window_text}"
    return MemoryVectorDocInput(
        user_id=user_id,
        girlfriend_id=girlfriend_id,
        source_type="chat_chunk",
        source_id=source_id,
        canonical_text=canonical,
        memory_type="shared_episode",
        salience=55,
        confidence=75,
    )

