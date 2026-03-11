from __future__ import annotations

"""Pinecone client wrapper for semantic memory.

This module hides the concrete Pinecone client so other services can depend on
simple helper functions and the app can gracefully run when Pinecone is not
configured.
"""

from typing import Any, Iterable, Optional

import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_index: Any | None = None


def _init_index() -> Any | None:
    """Lazily initialize the Pinecone index client.

    Returns None if vector memory is disabled or configuration is incomplete.
    """
    global _index
    if _index is not None:
        return _index

    settings = get_settings()
    if not settings.vector_memory_enabled:
        logger.info("Vector memory disabled via config; Pinecone client not initialized.")
        return None

    if not settings.pinecone_api_key or not settings.pinecone_index_name:
        logger.warning("Pinecone not configured (missing API key or index name).")
        return None

    try:
        from pinecone import Pinecone  # type: ignore[import-not-found]
    except Exception as e:  # pragma: no cover - import-time failure
        logger.warning("Pinecone client import failed: %s", e)
        return None

    try:
        client = Pinecone(api_key=settings.pinecone_api_key)
        _index = client.Index(settings.pinecone_index_name)
        logger.info("Pinecone index '%s' initialized for semantic memory.", settings.pinecone_index_name)
        return _index
    except Exception as e:  # pragma: no cover - runtime config error
        logger.error("Failed to initialize Pinecone index: %s", e)
        _index = None
        return None


def get_pinecone_index() -> Any | None:
    """Return the Pinecone index instance or None if not available."""
    return _init_index()


def upsert_vectors(
    vectors: Iterable[tuple[str, list[float], dict[str, Any]]],
) -> None:
    """Upsert vectors into Pinecone.

    Each item is (id, embedding, metadata).
    Silently no-ops when Pinecone is not configured/enabled.
    """
    index = get_pinecone_index()
    if not index:
        return
    try:
        index.upsert(vectors=list(vectors))
    except Exception as e:
        logger.warning("Pinecone upsert failed: %s", e)


def delete_vectors(ids: list[str]) -> None:
    """Delete vectors by id."""
    index = get_pinecone_index()
    if not index or not ids:
        return
    try:
        index.delete(ids=ids)
    except Exception as e:
        logger.warning("Pinecone delete failed: %s", e)


def query_vectors(
    embedding: list[float],
    user_id: str,
    girlfriend_id: str,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """Query Pinecone for closest vectors with strict tenant filtering.

    Returns a list of matches in the raw Pinecone format:
      [{"id": ..., "score": ..., "metadata": {...}}, ...]
    """
    index = get_pinecone_index()
    if not index:
        return []

    settings = get_settings()
    try:
        res = index.query(
            vector=embedding,
            top_k=top_k,
            include_metadata=True,
            filter={
                "user_id": user_id,
                "girlfriend_id": girlfriend_id,
                "schema_version": settings.vector_schema_version,
            },
        )
        # pinecone-client v5 returns .matches list
        matches = getattr(res, "matches", None)
        if matches is None:
            return []
        out: list[dict[str, Any]] = []
        for m in matches:
            out.append(
                {
                    "id": m.id,
                    "score": m.score,
                    "metadata": getattr(m, "metadata", {}) or {},
                }
            )
        return out
    except Exception as e:
        logger.warning("Pinecone query failed: %s", e)
        return []

