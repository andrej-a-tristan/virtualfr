"""
Memory API Routes (Task 1.2)
Endpoints for accessing memory summary and raw memory items.
"""
import logging
from uuid import UUID
from typing import Literal, Optional
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


@router.get("/summary")
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


@router.get("/items")
def get_memory_items_endpoint(
    request: Request,
    girlfriendId: Optional[str] = Query(None, description="Girlfriend ID"),
    type: Literal["factual", "emotional"] = Query("factual", description="Memory type"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return")
):
    """
    Get raw memory items for debugging/UI.
    Returns list of factual or emotional memory items.
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
        if type == "factual":
            items = get_factual_memory(sb, user_id, gf_uuid, limit=limit)
            return {
                "type": "factual",
                "count": len(items),
                "items": [item.model_dump() for item in items]
            }
        else:
            items = get_emotional_memory(sb, user_id, gf_uuid, limit=limit)
            return {
                "type": "emotional",
                "count": len(items),
                "items": [item.model_dump() for item in items]
            }
    except Exception as e:
        logger.exception("Error getting memory items: %s", e)
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
