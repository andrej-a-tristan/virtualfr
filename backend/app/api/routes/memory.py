"""
Memory API Routes (Task 1.2 + Bond Engine extensions)
Endpoints for accessing memory summary, raw memory items, episodes, patterns, conflicts.
"""
import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse

from app.api.request_context import get_current_user
from app.core.supabase_client import get_supabase_admin
from app.api import supabase_store as sb_store
from app.services.memory import (
    build_memory_context,
    get_factual_memory,
    get_emotional_memory,
    get_memory_summary,
    FactualMemoryItem,
    EmotionalMemoryItem,
    MemoryContext,
)
from app.services.bond_engine.memory_fabric import (
    build_prompt_memory_bundle,
    get_unresolved_emotional_threads,
    get_pending_promises,
    get_recent_wins,
)
from app.services.embedding import embed_text
from app.services.vector_memory_store import search_memory
from app.services.bond_engine.memory_patterns import get_patterns
from app.services.bond_engine.memory_conflict_resolution import get_unresolved_conflicts

router = APIRouter(prefix="/memory", tags=["memory"])
logger = logging.getLogger(__name__)


def _get_sb():
    """Get Supabase admin client."""
    return get_supabase_admin()


def _parse_girlfriend_id(gf_id_str: str) -> Optional[UUID]:
    """Parse girlfriend ID string to UUID, return None if invalid."""
    if not gf_id_str:
        return None
    try:
        return UUID(gf_id_str)
    except (ValueError, TypeError):
        return None


@router.get("/context")
def get_memory_context_endpoint(
    request: Request,
    girlfriendId: Optional[str] = Query(None, description="Girlfriend ID")
):
    """
    Get compact memory context for prompt building.
    Returns facts, emotions, and habit hints as human-readable strings.
    """
    sid, user, user_id, gf_id = get_current_user(request)
    if not sid or not user or not user_id:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    
    # Get girlfriend ID from query or session
    gf_uuid = _parse_girlfriend_id(girlfriendId) if girlfriendId else gf_id
    if not gf_uuid:
        # Try to get current girlfriend
        gf = sb_store.get_current_girlfriend(user_id)
        if gf:
            gf_uuid = UUID(str(gf["id"]))
    
    if not gf_uuid:
        return JSONResponse(status_code=400, content={"error": "no_girlfriend_id"})
    
    sb = _get_sb()
    if not sb:
        return JSONResponse(status_code=503, content={"error": "database_unavailable"})
    
    try:
        # Get habit profile for habit hints
        habit_profile = sb_store.get_habit_profile(user_id, gf_uuid)
        
        # Build memory context
        context = build_memory_context(
            sb=sb,
            user_id=user_id,
            girlfriend_id=gf_uuid,
            max_facts=8,
            max_emotions=5,
            habit_profile=habit_profile
        )
        
        return {
            "facts": context.facts,
            "emotions": context.emotions,
            "habits": context.habits,
        }
    except Exception as e:
        logger.exception("Error building memory context: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/stats")
def get_memory_stats_endpoint(
    request: Request,
    girlfriendId: Optional[str] = Query(None, description="Girlfriend ID")
):
    """
    Get memory statistics and recent items summary.
    """
    sid, user, user_id, gf_id = get_current_user(request)
    if not sid or not user or not user_id:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    
    # Get girlfriend ID from query or session
    gf_uuid = _parse_girlfriend_id(girlfriendId) if girlfriendId else gf_id
    if not gf_uuid:
        gf = sb_store.get_current_girlfriend(user_id)
        if gf:
            gf_uuid = UUID(str(gf["id"]))
    
    if not gf_uuid:
        return JSONResponse(status_code=400, content={"error": "no_girlfriend_id"})
    
    sb = _get_sb()
    if not sb:
        return JSONResponse(status_code=503, content={"error": "database_unavailable"})
    
    try:
        summary = get_memory_summary(sb, user_id, gf_uuid)
        return summary
    except Exception as e:
        logger.exception("Error getting memory stats: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── Bond Engine: extended memory endpoints ──────────────────────────────────

@router.get("/summary")
def get_extended_memory_summary(
    request: Request,
    girlfriendId: Optional[str] = Query(None, description="Girlfriend ID"),
):
    """
    Extended memory summary including episodes, patterns, and conflicts.
    """
    sid, user, user_id, gf_id = get_current_user(request)
    if not sid or not user or not user_id:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    gf_uuid = _parse_girlfriend_id(girlfriendId) if girlfriendId else gf_id
    if not gf_uuid:
        gf = sb_store.get_current_girlfriend(user_id)
        if gf:
            gf_uuid = UUID(str(gf["id"]))
    if not gf_uuid:
        return JSONResponse(status_code=400, content={"error": "no_girlfriend_id"})

    sb = _get_sb()
    if not sb:
        return JSONResponse(status_code=503, content={"error": "database_unavailable"})

    try:
        # Base summary
        base_summary = get_memory_summary(sb, user_id, gf_uuid)

        # Episodes
        episodes = []
        try:
            r = (
                sb.table("memory_episodes")
                .select("id, episode_type, summary, salience, created_at")
                .eq("user_id", str(user_id))
                .eq("girlfriend_id", str(gf_uuid))
                .order("created_at", desc=True)
                .limit(10)
                .execute()
            )
            episodes = r.data or []
        except Exception:
            pass

        # Patterns
        patterns_data = get_patterns(sb, user_id, gf_uuid)

        # Unresolved conflicts
        conflicts = get_unresolved_conflicts(sb, user_id, gf_uuid)

        # Unresolved emotional threads
        threads = get_unresolved_emotional_threads(sb, user_id, gf_uuid)

        # Pending promises
        promises = get_pending_promises(sb, user_id, gf_uuid)

        # Recent wins
        wins = get_recent_wins(sb, user_id, gf_uuid)

        return {
            **base_summary,
            "episodes": episodes,
            "episode_count": len(episodes),
            "patterns": patterns_data,
            "pattern_count": len(patterns_data),
            "unresolved_conflicts": conflicts,
            "conflict_count": len(conflicts),
            "unresolved_emotional_threads": threads,
            "pending_promises": promises,
            "recent_wins": wins,
        }
    except Exception as e:
        logger.exception("Error building extended memory summary: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/items")
def get_memory_items_extended(
    request: Request,
    girlfriendId: Optional[str] = Query(None, description="Girlfriend ID"),
    type: str = Query("factual", description="Memory type: factual, emotional, episodic, pattern, conflicts"),
    limit: int = Query(50, ge=1, le=100, description="Max items"),
):
    """
    Get raw memory items by type (extended to include episodes/patterns/conflicts).
    """
    sid, user, user_id, gf_id = get_current_user(request)
    if not sid or not user or not user_id:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    gf_uuid = _parse_girlfriend_id(girlfriendId) if girlfriendId else gf_id
    if not gf_uuid:
        gf = sb_store.get_current_girlfriend(user_id)
        if gf:
            gf_uuid = UUID(str(gf["id"]))
    if not gf_uuid:
        return JSONResponse(status_code=400, content={"error": "no_girlfriend_id"})

    sb = _get_sb()
    if not sb:
        return JSONResponse(status_code=503, content={"error": "database_unavailable"})

    try:
        if type == "factual":
            items = get_factual_memory(sb, user_id, gf_uuid, limit=limit)
            return {"type": "factual", "count": len(items), "items": [item.model_dump() for item in items]}
        elif type == "emotional":
            items = get_emotional_memory(sb, user_id, gf_uuid, limit=limit)
            return {"type": "emotional", "count": len(items), "items": [item.model_dump() for item in items]}
        elif type == "episodic":
            r = (
                sb.table("memory_episodes")
                .select("*")
                .eq("user_id", str(user_id))
                .eq("girlfriend_id", str(gf_uuid))
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            items = r.data or []
            return {"type": "episodic", "count": len(items), "items": items}
        elif type == "pattern":
            items = get_patterns(sb, user_id, gf_uuid, limit=limit)
            return {"type": "pattern", "count": len(items), "items": items}
        elif type == "conflicts":
            items = get_unresolved_conflicts(sb, user_id, gf_uuid, limit=limit)
            return {"type": "conflicts", "count": len(items), "items": items}
        else:
            return JSONResponse(status_code=400, content={"error": f"Unknown memory type: {type}"})
    except Exception as e:
        logger.exception("Error getting memory items: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/rebuild")
def rebuild_memory_index(
    request: Request,
    girlfriendId: Optional[str] = Query(None, description="Girlfriend ID"),
):
    """
    Optional: rebuild/reindex memory from chat history.
    Reprocesses all user messages to extract facts, emotions, episodes, and patterns.
    """
    sid, user, user_id, gf_id = get_current_user(request)
    if not sid or not user or not user_id:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    gf_uuid = _parse_girlfriend_id(girlfriendId) if girlfriendId else gf_id
    if not gf_uuid:
        gf = sb_store.get_current_girlfriend(user_id)
        if gf:
            gf_uuid = UUID(str(gf["id"]))
    if not gf_uuid:
        return JSONResponse(status_code=400, content={"error": "no_girlfriend_id"})

    sb = _get_sb()
    if not sb:
        return JSONResponse(status_code=503, content={"error": "database_unavailable"})

    try:
        from app.services.bond_engine.memory_ingest import ingest_user_turn

        # Fetch all user messages
        r = (
            sb.table("messages")
            .select("id, role, content, created_at")
            .eq("user_id", str(user_id))
            .eq("girlfriend_id", str(gf_uuid))
            .eq("role", "user")
            .order("created_at", desc=False)
            .limit(500)
            .execute()
        )
        messages = r.data or []

        all_timestamps = [m.get("created_at", "") for m in messages]
        all_texts = [m.get("content", "") for m in messages if m.get("content")]

        processed = 0
        for msg in messages:
            text = msg.get("content", "")
            if not text:
                continue
            ingest_user_turn(
                sb=sb,
                user_id=user_id,
                girlfriend_id=gf_uuid,
                turn_id=msg.get("id", ""),
                text=text,
                all_user_timestamps=all_timestamps,
                all_user_messages=all_texts,
            )
            processed += 1

        return {
            "status": "ok",
            "messages_processed": processed,
            "total_messages": len(messages),
        }
    except Exception as e:
        logger.exception("Memory rebuild failed: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/vector/search")
def vector_memory_search(
    request: Request,
    girlfriendId: Optional[str] = Query(None, description="Girlfriend ID"),
    q: str = Query(..., description="Search query text"),
    k: int = Query(8, ge=1, le=32, description="Top-k vector matches"),
):
    """
    Debug endpoint: run a semantic memory search for the current girlfriend.
    Returns raw vector hits plus source metadata.
    """
    sid, user, user_id, gf_id = get_current_user(request)
    if not sid or not user or not user_id:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    gf_uuid = _parse_girlfriend_id(girlfriendId) if girlfriendId else gf_id
    if not gf_uuid:
        gf = sb_store.get_current_girlfriend(user_id)
        if gf:
            gf_uuid = UUID(str(gf["id"]))
    if not gf_uuid:
        return JSONResponse(status_code=400, content={"error": "no_girlfriend_id"})

    sb = _get_sb()
    if not sb:
        return JSONResponse(status_code=503, content={"error": "database_unavailable"})

    try:
        embedding = embed_text(q)
        results = search_memory(
            query_embedding=embedding,
            user_id=str(user_id),
            girlfriend_id=str(gf_uuid),
            top_k=k,
        )

        # Attach source rows where possible for easier inspection
        enriched = []
        for r in results:
            meta = r.metadata or {}
            source_type = meta.get("source_type")
            source_id = meta.get("source_id")
            source_row = None
            try:
                if source_type == "factual":
                    src_res = (
                        sb.table("factual_memory")
                        .select("*")
                        .eq("id", source_id)
                        .maybe_single()
                        .execute()
                    )
                    source_row = src_res.data if src_res and src_res.data else None
                elif source_type == "emotional":
                    src_res = (
                        sb.table("emotional_memory")
                        .select("*")
                        .eq("id", source_id)
                        .maybe_single()
                        .execute()
                    )
                    source_row = src_res.data if src_res and src_res.data else None
                elif source_type == "episode":
                    src_res = (
                        sb.table("memory_episodes")
                        .select("*")
                        .eq("id", source_id)
                        .maybe_single()
                        .execute()
                    )
                    source_row = src_res.data if src_res and src_res.data else None
                elif source_type == "chat_chunk":
                    # For chat chunks, fetch the message and a tiny neighborhood.
                    msg_res = (
                        sb.table("messages")
                        .select("*")
                        .eq("id", source_id)
                        .maybe_single()
                        .execute()
                    )
                    source_row = msg_res.data if msg_res and msg_res.data else None
            except Exception:
                source_row = None

            enriched.append(
                {
                    "document_id": r.document_id,
                    "score": r.score,
                    "metadata": meta,
                    "source": source_row,
                }
            )

        return {"results": enriched}
    except Exception as e:
        logger.exception("Vector memory search failed: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})
