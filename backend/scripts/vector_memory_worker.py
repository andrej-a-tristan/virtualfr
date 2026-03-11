from __future__ import annotations

"""Background worker: sync memory_vector_documents to Pinecone.

Usage (from backend/ directory):
    python -m scripts.vector_memory_worker

This script is idempotent and safe to run periodically (e.g. via cron) or as a
long-running process with a small sleep between batches.
"""

import logging
import time
from typing import Any, List
from uuid import UUID

from app.core.supabase_client import get_supabase_admin
from app.core.config import get_settings
from app.services.embedding import embed_batch
from app.services.vector_memory_store import VectorDocument, upsert_documents

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

BATCH_SIZE = 10
SLEEP_SECONDS = 5


def _fetch_pending_jobs(sb: Any) -> List[dict]:
    r = (
        sb.table("memory_vector_sync_jobs")
        .select("*")
        .eq("status", "pending")
        .order("created_at", desc=False)
        .limit(BATCH_SIZE)
        .execute()
    )
    return r.data or []


def _load_documents(sb: Any, jobs: List[dict]) -> List[dict]:
    if not jobs:
        return []
    doc_ids = [j["document_id"] for j in jobs]
    r = (
        sb.table("memory_vector_documents")
        .select("*")
        .in_("id", doc_ids)
        .execute()
    )
    return r.data or []


def process_batch(sb: Any) -> int:
    """Process a single batch of sync jobs. Returns number of jobs handled."""
    jobs = _fetch_pending_jobs(sb)
    if not jobs:
        return 0

    docs = _load_documents(sb, jobs)
    docs_by_id = {d["id"]: d for d in docs}

    # Prepare embeddings for upsert jobs
    upsert_jobs = [j for j in jobs if j["job_type"] == "upsert"]
    delete_jobs = [j for j in jobs if j["job_type"] == "delete"]

    # Upserts
    if upsert_jobs:
        texts: List[str] = []
        meta_docs: List[tuple[str, dict]] = []
        for job in upsert_jobs:
            did = job["document_id"]
            doc = docs_by_id.get(did)
            if not doc:
                continue
            texts.append(doc["canonical_text"])
            meta_docs.append(
                (
                    did,
                    {
                        "user_id": doc["user_id"],
                        "girlfriend_id": doc["girlfriend_id"],
                        "source_type": doc["source_type"],
                        "source_id": doc["source_id"],
                        "memory_type": doc["memory_type"],
                        "salience": doc.get("salience"),
                        "confidence": doc.get("confidence"),
                        "valence": doc.get("valence"),
                        "intensity": doc.get("intensity"),
                        "is_resolved": doc.get("is_resolved"),
                        "occurred_at": doc.get("occurred_at"),
                        "privacy_level": doc.get("privacy_level"),
                        "schema_version": doc.get("schema_version"),
                    },
                )
            )

        if texts:
            try:
                embeddings = embed_batch(texts)
                vector_docs: List[VectorDocument] = []
                for (doc_id, metadata), emb in zip(meta_docs, embeddings):
                    vector_docs.append(VectorDocument(id=doc_id, embedding=emb, metadata=metadata))
                upsert_documents(vector_docs)
            except Exception as e:
                logger.warning("Embedding/upsert batch failed: %s", e)
                # Mark jobs as failed but leave attempts for retry
                for job in upsert_jobs:
                    try:
                        sb.table("memory_vector_sync_jobs").update(
                            {
                                "status": "failed",
                                "attempts": (job.get("attempts") or 0) + 1,
                                "last_error": str(e),
                            }
                        ).eq("id", job["id"]).execute()
                    except Exception:
                        pass
                return len(jobs)

    # Deletes are handled by ID only; no embedding needed
    if delete_jobs:
        from app.core.pinecone_client import delete_vectors

        delete_ids = [j["document_id"] for j in delete_jobs]
        try:
            delete_vectors(delete_ids)
        except Exception as e:
            logger.warning("Vector delete batch failed: %s", e)

    # Mark all jobs as done on success.
    for job in jobs:
        try:
            sb.table("memory_vector_sync_jobs").update(
                {
                    "status": "done",
                    "attempts": (job.get("attempts") or 0) + 1,
                    "last_error": None,
                }
            ).eq("id", job["id"]).execute()
        except Exception as e:
            logger.debug("Failed to mark vector sync job done: %s", e)

    return len(jobs)


def main() -> None:
    settings = get_settings()
    if not settings.vector_memory_enabled:
        logger.info("Vector memory disabled; worker will not run.")
        return

    sb = get_supabase_admin()
    if not sb:
        logger.error("Supabase admin client not available; aborting worker.")
        return

    logger.info("Starting vector memory worker (batch size=%d)...", BATCH_SIZE)
    try:
        while True:
            processed = process_batch(sb)
            if processed == 0:
                time.sleep(SLEEP_SECONDS)
            else:
                # Shorter sleep when there is back-pressure.
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Vector memory worker stopped.")


if __name__ == "__main__":
    main()

