"""
Prompt Preview — Debug endpoint (Task 3.2)

GET /api/prompt/preview?girlfriendId=...
Returns the full system prompt for debugging/testing.

Only enabled when ENABLE_PROMPT_PREVIEW=true in .env.
"""
import logging
import os
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse

from app.api.request_context import get_current_user
from app.core.supabase_client import get_supabase_admin
from app.api.store import get_girlfriend
from app.services.prompt_context import get_prompt_context
from app.services.prompt_builder import build_system_prompt, build_input_from_dict

router = APIRouter(prefix="/prompt", tags=["prompt"])
logger = logging.getLogger(__name__)


def _is_preview_enabled() -> bool:
    """Check if prompt preview is enabled via environment variable."""
    val = os.environ.get("ENABLE_PROMPT_PREVIEW", "").lower()
    return val in ("true", "1", "yes")


@router.get("/preview")
def prompt_preview(
    request: Request,
    girlfriendId: Optional[str] = Query(None, description="Girlfriend ID"),
):
    """
    Return the full system prompt for debugging.
    Only available when ENABLE_PROMPT_PREVIEW=true.
    """
    if not _is_preview_enabled():
        return JSONResponse(
            status_code=403,
            content={"error": "Prompt preview is disabled. Set ENABLE_PROMPT_PREVIEW=true in .env"},
        )

    sid, user, user_id, gf_id = get_current_user(request)
    if not sid or not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    # Resolve girlfriend
    use_sb = get_supabase_admin() and user_id is not None
    gf_uuid = None
    gf = None
    resolved_gf_id = girlfriendId

    if use_sb and user_id:
        from app.api import supabase_store as sb
        if girlfriendId:
            try:
                gf_uuid = UUID(girlfriendId)
            except (ValueError, TypeError):
                pass
        if not gf_uuid:
            gf = sb.get_current_girlfriend(user_id)
            if gf:
                gf_uuid = UUID(str(gf["id"]))
                resolved_gf_id = str(gf["id"])
    else:
        gf = get_girlfriend(sid)
        if gf:
            resolved_gf_id = gf.get("id") or girlfriendId

    if not gf and not gf_uuid:
        return JSONResponse(status_code=400, content={"error": "no_girlfriend"})

    try:
        ctx = get_prompt_context(
            sb_admin=get_supabase_admin() if use_sb else None,
            user_id=user_id if use_sb else None,
            girlfriend_id=gf_uuid if use_sb else None,
            session_id=sid if not use_sb else None,
            girlfriend_id_str=resolved_gf_id if not use_sb else None,
            girlfriend=gf,
        )
        prompt_input = build_input_from_dict(**ctx)
        system_prompt = build_system_prompt(prompt_input)

        rel = ctx.get("relationship_dict", {})
        mem = ctx.get("memories_dict", {})
        return {
            "systemPrompt": system_prompt,
            "inputSummary": {
                "girlfriendName": ctx["girlfriend_name"],
                "traits": ctx.get("traits_dict", {}),
                "relationshipLevel": rel.get("region_key") or rel.get("level"),
                "trust": rel.get("trust"),
                "intimacy": rel.get("intimacy"),
                "memoryFactCount": len(mem.get("facts", [])),
                "memoryEmotionCount": len(mem.get("emotions", [])),
                "hasBigFive": ctx.get("big_five_dict") is not None,
                "languagePref": ctx.get("language_pref", "en"),
            },
            "promptLength": len(system_prompt),
        }
    except Exception as e:
        logger.exception("Prompt preview failed: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})
