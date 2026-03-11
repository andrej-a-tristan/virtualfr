from __future__ import annotations

"""Embedding service for semantic memory.

Uses the same OpenAI-compatible API key as the main chat gateway.
If no API key is configured, callers should treat embeddings as unavailable.
"""

from typing import List

import logging

from app.core import get_api_key
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _get_openai_client():
    """Return an OpenAI client instance or None if unavailable."""
    api_key = get_api_key()
    if not api_key:
        logger.info("Embedding service disabled: no API key configured.")
        return None
    try:
        from openai import OpenAI  # type: ignore[import-not-found]
    except Exception as e:  # pragma: no cover - import-time failure
        logger.warning("OpenAI client import failed for embeddings: %s", e)
        return None
    return OpenAI(api_key=api_key)


def embed_text(text: str) -> List[float]:
    """Embed a single text string.

    Raises RuntimeError if embeddings are not available so callers can handle
    fallback behavior.
    """
    client = _get_openai_client()
    if client is None:
        raise RuntimeError("Embedding client not available (missing API key or OpenAI library).")

    settings = get_settings()
    model = settings.vector_embedding_model or "text-embedding-3-small"

    try:
        resp = client.embeddings.create(model=model, input=text)
        if not resp.data:
            raise RuntimeError("Empty embedding response.")
        return list(resp.data[0].embedding)
    except Exception as e:
        logger.error("Embedding request failed: %s", e)
        raise


def embed_batch(texts: List[str]) -> List[List[float]]:
    """Embed a batch of texts; order-preserving."""
    if not texts:
        return []
    client = _get_openai_client()
    if client is None:
        raise RuntimeError("Embedding client not available (missing API key or OpenAI library).")

    settings = get_settings()
    model = settings.vector_embedding_model or "text-embedding-3-small"

    try:
        resp = client.embeddings.create(model=model, input=texts)
        if not resp.data or len(resp.data) != len(texts):
            # Some providers may return fewer rows; be defensive.
            logger.warning("Embedding batch size mismatch: %d texts, %d embeddings", len(texts), len(resp.data or []))
        # resp.data is ordered by input index.
        return [list(item.embedding) for item in resp.data]
    except Exception as e:
        logger.error("Embedding batch request failed: %s", e)
        raise

