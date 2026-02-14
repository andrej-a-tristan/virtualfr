"""Dossier API: debug/management endpoints for the Girl Dossier system."""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from app.api.request_context import get_current_user
from app.core.supabase_client import get_supabase_admin

router = APIRouter(prefix="/dossier", tags=["dossier"])
logger = logging.getLogger(__name__)


def _require_auth(request: Request):
    sid, user, user_id, gf_id = get_current_user(request)
    if not sid or not user or not user_id:
        raise HTTPException(status_code=401, detail="unauthorized")
    return sid, user, user_id, gf_id


# ── GET /api/dossier/summary ─────────────────────────────────────────────────

@router.get("/summary")
def get_dossier_summary(request: Request):
    """Return a summary of the girl's dossier for the current girlfriend."""
    sid, user, user_id, gf_id = _require_auth(request)
    sb = get_supabase_admin()
    if not sb or not gf_id:
        return {"error": "no_dossier", "message": "Supabase not configured or no girlfriend selected"}

    uid = str(user_id)
    gid = gf_id

    summary = {}

    # Core profile
    try:
        r = sb.table("girlfriend_core_profile").select("voice_style,worldview,values_text,boundaries,speech_quirks,attachment_tone,version").eq(
            "user_id", uid).eq("girlfriend_id", gid).limit(1).execute()
        summary["core_profile"] = r.data[0] if r.data else None
    except Exception:
        summary["core_profile"] = None

    # Life graph node count
    try:
        r = sb.table("girlfriend_life_graph_nodes").select("node_type,node_key,label", count="exact").eq(
            "user_id", uid).eq("girlfriend_id", gid).execute()
        summary["life_graph_nodes"] = r.data or []
        summary["life_graph_node_count"] = len(r.data or [])
    except Exception:
        summary["life_graph_nodes"] = []
        summary["life_graph_node_count"] = 0

    # Story bank count by topic
    try:
        r = sb.table("girlfriend_story_bank").select("topic,story_type,usage_count").eq(
            "user_id", uid).eq("girlfriend_id", gid).execute()
        summary["story_count"] = len(r.data or [])
        topics = {}
        for s in (r.data or []):
            t = s.get("topic", "unknown")
            topics[t] = topics.get(t, 0) + 1
        summary["stories_by_topic"] = topics
    except Exception:
        summary["story_count"] = 0
        summary["stories_by_topic"] = {}

    # Self memory count
    try:
        r = sb.table("girlfriend_self_memory").select("memory_key,memory_value,confidence,is_immutable,source").eq(
            "user_id", uid).eq("girlfriend_id", gid).order("salience", desc=True).execute()
        summary["self_memory_count"] = len(r.data or [])
        summary["self_memories"] = r.data or []
    except Exception:
        summary["self_memory_count"] = 0
        summary["self_memories"] = []

    # Current state
    try:
        r = sb.table("girlfriend_current_state").select("mood,energy,focus_topics,today_context,open_loops").eq(
            "user_id", uid).eq("girlfriend_id", gid).limit(1).execute()
        summary["current_state"] = r.data[0] if r.data else None
    except Exception:
        summary["current_state"] = None

    # Conversation mode
    try:
        r = sb.table("conversation_mode_state").select("question_ratio_10,self_disclosure_ratio_10,consecutive_questions,last_intents,last_cadences").eq(
            "user_id", uid).eq("girlfriend_id", gid).limit(1).execute()
        summary["conversation_mode"] = r.data[0] if r.data else None
    except Exception:
        summary["conversation_mode"] = None

    # Conflict count
    try:
        r = sb.table("girlfriend_self_conflicts").select("id", count="exact").eq(
            "user_id", uid).eq("girlfriend_id", gid).execute()
        summary["self_conflicts_count"] = len(r.data or [])
    except Exception:
        summary["self_conflicts_count"] = 0

    return summary


# ── GET /api/dossier/stories ─────────────────────────────────────────────────

@router.get("/stories")
def get_dossier_stories(request: Request, topic: str | None = None):
    """Return story bank entries, optionally filtered by topic."""
    sid, user, user_id, gf_id = _require_auth(request)
    sb = get_supabase_admin()
    if not sb or not gf_id:
        return {"stories": []}

    try:
        q = sb.table("girlfriend_story_bank").select("*").eq(
            "user_id", str(user_id)).eq("girlfriend_id", gf_id)
        if topic:
            q = q.eq("topic", topic)
        r = q.order("created_at").execute()
        return {"stories": r.data or []}
    except Exception as e:
        logger.warning("Stories fetch error: %s", e)
        return {"stories": []}


# ── POST /api/dossier/rebuild ────────────────────────────────────────────────

@router.post("/rebuild")
def rebuild_dossier(request: Request):
    """Re-bootstrap the dossier from the current girlfriend's onboarding data."""
    sid, user, user_id, gf_id = _require_auth(request)
    sb = get_supabase_admin()
    if not sb or not gf_id:
        return JSONResponse(status_code=400, content={"error": "Supabase not configured or no girlfriend"})

    from app.api.store import get_girlfriend
    gf = get_girlfriend(sid)
    if not gf:
        return JSONResponse(status_code=404, content={"error": "no_girlfriend"})

    try:
        from app.services.dossier.bootstrap import bootstrap_dossier_from_onboarding
        gf_uuid = UUID(str(gf_id))
        counts = bootstrap_dossier_from_onboarding(sb, user_id, gf_uuid, gf)
        return {"status": "ok", "counts": counts}
    except Exception as e:
        logger.error("Dossier rebuild error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})
