from __future__ import annotations

"""Hooks for creating vector-memory documents from structured memories.

These helpers are called from the existing memory ingestion paths to:
  1. Map new/updated factual, emotional, and episodic memories for a turn
     into rows in `memory_vector_documents`.
  2. Enqueue `memory_vector_sync_jobs` entries for the background worker.

All operations are best-effort and non-blocking — failures should never break
chat or the primary memory pipeline.
"""

from typing import Any, List
from uuid import UUID

import logging

from app.services.vector_memory_mapper import (
    MemoryVectorDocInput,
    from_episode,
    from_emotional_memory,
    from_factual_memory,
    from_chat_chunk,
)
from app.services.memory import get_short_term_messages

logger = logging.getLogger(__name__)


def _upsert_vector_doc(sb: Any, doc: MemoryVectorDocInput) -> str | None:
    """Upsert a single vector-document row and return its id (or None)."""
    try:
        row = doc.to_row()
        # Upsert by (user_id, girlfriend_id, source_type, source_id)
        r = (
            sb.table("memory_vector_documents")
            .upsert(
                {
                    **row,
                },
                on_conflict="user_id,girlfriend_id,source_type,source_id",
            )
            .select("id")
            .eq("user_id", row["user_id"])
            .eq("girlfriend_id", row["girlfriend_id"])
            .eq("source_type", row["source_type"])
            .eq("source_id", row["source_id"])
            .maybe_single()
            .execute()
        )
        if r and r.data:
            return r.data["id"]
    except Exception as e:
        logger.warning("Vector doc upsert failed: %s", e)
    return None


def _enqueue_sync_job(sb: Any, user_id: str, girlfriend_id: str, document_id: str, job_type: str = "upsert") -> None:
    """Create a sync job row for the given document id."""
    try:
        sb.table("memory_vector_sync_jobs").insert(
            {
                "user_id": user_id,
                "girlfriend_id": girlfriend_id,
                "document_id": document_id,
                "job_type": job_type,
                "status": "pending",
            }
        ).execute()
    except Exception as e:
        logger.debug("Failed to enqueue vector sync job: %s", e)


def enqueue_vector_docs_for_turn(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    turn_id: str,
    raw_text: str | None = None,
) -> None:
    """Create vector-document rows for memories associated with a single turn.

    Looks up:
      - factual_memory rows with source_message_id == turn_id
      - emotional_memory rows with source_message_id == turn_id
      - memory_episodes rows with source_turn_id == turn_id
      - an optional chat chunk built from the recent message window
    """
    if not sb:
        return

    uid_str = str(user_id)
    gid_str = str(girlfriend_id)

    try:
        # Factual memories for this turn
        f_res = (
            sb.table("factual_memory")
            .select("*")
            .eq("user_id", uid_str)
            .eq("girlfriend_id", gid_str)
            .eq("source_message_id", turn_id)
            .execute()
        )
        factual_rows = f_res.data or []
    except Exception as e:
        logger.debug("Vector ingest: factual lookup failed: %s", e)
        factual_rows = []

    try:
        e_res = (
            sb.table("emotional_memory")
            .select("*")
            .eq("user_id", uid_str)
            .eq("girlfriend_id", gid_str)
            .eq("source_message_id", turn_id)
            .execute()
        )
        emotional_rows = e_res.data or []
    except Exception as e:
        logger.debug("Vector ingest: emotional lookup failed: %s", e)
        emotional_rows = []

    try:
        ep_res = (
            sb.table("memory_episodes")
            .select("*")
            .eq("user_id", uid_str)
            .eq("girlfriend_id", gid_str)
            .eq("source_turn_id", turn_id)
            .execute()
        )
        episode_rows = ep_res.data or []
    except Exception as e:
        logger.debug("Vector ingest: episodes lookup failed: %s", e)
        episode_rows = []

    docs: List[MemoryVectorDocInput] = []
    for row in factual_rows:
        docs.append(from_factual_memory(row))
    for row in emotional_rows:
        docs.append(from_emotional_memory(row))
    for row in episode_rows:
        docs.append(from_episode(row))

    # Optional chat chunk from recent context
    try:
        # Build a small window including the current turn if we have text
        messages = get_short_term_messages(sb, user_id, girlfriend_id, limit=8)
        if messages:
            parts = []
            for m in messages:
                role = m.get("role", "user")
                prefix = "User: " if role == "user" else "Girl: "
                content = (m.get("content") or "").strip()
                if content:
                    parts.append(prefix + content)
            window_text = " ".join(parts)
            if window_text:
                docs.append(
                    from_chat_chunk(
                        user_id=uid_str,
                        girlfriend_id=gid_str,
                        source_id=turn_id,
                        window_text=window_text[:600],
                    )
                )
    except Exception as e:
        logger.debug("Vector ingest: chat window build failed: %s", e)

    # Persist docs and enqueue jobs
    for doc in docs:
        doc_id = _upsert_vector_doc(sb, doc)
        if doc_id:
            _enqueue_sync_job(sb, uid_str, gid_str, doc_id, job_type="upsert")

