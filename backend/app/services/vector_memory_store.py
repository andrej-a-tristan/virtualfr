from __future__ import annotations

"""Vector memory store — thin wrapper around Pinecone for semantic memory.

This module is intentionally small: it assumes embeddings are already computed
and focuses purely on CRUD + filtered semantic search.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

import logging

from app.core.pinecone_client import upsert_vectors, delete_vectors, query_vectors

logger = logging.getLogger(__name__)


@dataclass
class VectorDocument:
    id: str
    embedding: List[float]
    metadata: Dict[str, Any]


@dataclass
class VectorSearchResult:
    document_id: str
    score: float
    metadata: Dict[str, Any]


def upsert_documents(docs: List[VectorDocument]) -> None:
    """Upsert a batch of vector documents into Pinecone."""
    if not docs:
        return
    vectors = [(d.id, d.embedding, d.metadata) for d in docs]
    upsert_vectors(vectors)


def delete_documents(doc_ids: List[str]) -> None:
    """Delete vector documents by id."""
    if not doc_ids:
        return
    delete_vectors(doc_ids)


def search_memory(
    query_embedding: List[float],
    user_id: str,
    girlfriend_id: str,
    top_k: int = 16,
) -> List[VectorSearchResult]:
    """Semantic search over memory vectors for a specific user/girlfriend."""
    raw_matches = query_vectors(
        embedding=query_embedding,
        user_id=user_id,
        girlfriend_id=girlfriend_id,
        top_k=top_k,
    )
    results: List[VectorSearchResult] = []
    for m in raw_matches:
        results.append(
            VectorSearchResult(
                document_id=m.get("id", ""),
                score=float(m.get("score", 0.0) or 0.0),
                metadata=m.get("metadata") or {},
            )
        )
    return results

