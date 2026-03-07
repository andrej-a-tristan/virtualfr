"""Girlfriend CRUD: create, list, get current, switch.
Supports multiple girlfriends per user (Free: 1, Plus: 3, Premium: 3).
Uses Supabase when configured, else in-memory store."""
import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4, UUID

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.schemas.girlfriend import (
    CreateGirlfriendRequest,
    GirlfriendResponse,
    OnboardingCompletePayload,
    IdentityResponse,
)
from app.api.deps import get_current_user
from app.api.store import (
    get_session_user,
    set_session_user,
    get_girlfriend,
    set_girlfriend,
    get_all_girlfriends,
    add_girlfriend,
    get_girlfriend_count,
    set_current_girlfriend_id,
)
from app.api.request_context import get_current_user
from app.core.supabase_client import get_supabase_admin
from app.api.supabase_store import (
    create_girlfriend as sb_create_girlfriend,
    get_current_girlfriend as sb_get_current_girlfriend,
    upsert_habit_profile,
)
from app.services.big_five import map_traits_to_big_five
from app.utils.identity_canon import generate_identity_canon
from app.utils.ai_images import pick_ai_image_url

router = APIRouter(prefix="/girlfriends", tags=["girlfriends"])

PLAN_LIMITS = {"free": 1, "plus": 3, "premium": 3}


def _session_id(request: Request) -> str | None:
    return request.cookies.get("session")


def _require_user(request: Request) -> tuple[str, dict]:
    sid, user, _, _ = get_current_user(request)
    if not sid or not user:
        raise HTTPException(status_code=401, detail="unauthorized")
    return sid, user


def _gf_to_response(gf: dict) -> GirlfriendResponse:
    return GirlfriendResponse(**gf)


def _use_supabase(user_id) -> bool:
    if not get_supabase_admin() or not user_id:
        return False
    try:
        UUID(str(user_id))
        return True
    except (ValueError, TypeError):
        return False


# ── POST /api/girlfriends (create first girl — backward compat) ──────────────

@router.post("")
def create_girlfriend(request: Request, body: CreateGirlfriendRequest):
    """Create current girlfriend from displayName + traits (first onboarding)."""
    sid, user, user_id, _ = get_current_user(request)
    if not sid or not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    traits = body.traits.model_dump()

    # Supabase path
    if _use_supabase(user_id) and user_id:
        try:
            gf = sb_create_girlfriend(user_id, body.display_name, traits)
            gf_uuid = UUID(str(gf["id"]))
            big_five_scores = map_traits_to_big_five(traits)
            upsert_habit_profile(user_id, gf_uuid, {"big_five": big_five_scores})
            from app.api.store import set_session_girlfriend_id
            set_session_girlfriend_id(sid, str(gf["id"]))
            return GirlfriendResponse(**gf)
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    # In-memory path
    gf_id = f"gf-{uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    gf = {
        "id": gf_id,
        "display_name": body.display_name,
        "traits": traits,
        "created_at": now,
    }
    set_girlfriend(sid, gf)
    saved = get_girlfriend(sid) or gf
    return GirlfriendResponse(**saved)


# ── GET /api/girlfriends (list all) ──────────────────────────────────────────

@router.get("")
def list_girlfriends(request: Request):
    """Return all girlfriends for the current user."""
    sid, user = _require_user(request)
    gfs = get_all_girlfriends(sid)
    current_id = user.get("current_girlfriend_id")
    plan = user.get("plan", "free")
    girls_max = PLAN_LIMITS.get(plan, 1)
    return {
        "girlfriends": [_gf_to_response(gf) for gf in gfs],
        "current_girlfriend_id": current_id,
        "girls_max": girls_max,
        "can_create_more": len(gfs) < girls_max,
    }


# ── GET /api/girlfriends/current ─────────────────────────────────────────────

@router.get("/current")
def get_current_girlfriend_route(request: Request):
    """Return current girlfriend or 404."""
    sid, user, user_id, _ = get_current_user(request)
    if not sid or not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    if _use_supabase(user_id) and user_id:
        gf = sb_get_current_girlfriend(user_id)
    else:
        gf = get_girlfriend(sid)
    if not gf:
        return JSONResponse(status_code=404, content={"error": "no_girlfriend"})
    return GirlfriendResponse(**gf)


# ── POST /api/girlfriends/current (switch) ───────────────────────────────────

class SetCurrentRequest(BaseModel):
    girlfriend_id: str


@router.post("/current")
def switch_girlfriend(request: Request, body: SetCurrentRequest):
    """Switch to a different girlfriend."""
    sid, user = _require_user(request)
    ok = set_current_girlfriend_id(sid, body.girlfriend_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Girlfriend not found")
    gfs = get_all_girlfriends(sid)
    return {
        "girlfriends": [_gf_to_response(gf) for gf in gfs],
        "current_girlfriend_id": body.girlfriend_id,
    }


# ── POST /api/girlfriends/create (additional girl — premium gated) ───────────

@router.post("/create")
def create_additional_girlfriend(request: Request, body: OnboardingCompletePayload):
    """Create an additional girlfriend. Enforces plan limits (Free: 1, Plus: 3, Premium: 5)."""
    sid, user = _require_user(request)

    plan = user.get("plan", "free")
    girls_max = PLAN_LIMITS.get(plan, 1)
    current_count = get_girlfriend_count(sid)

    if current_count >= girls_max:
        if plan in ("premium", "plus"):
            raise HTTPException(status_code=403, detail=f"You can have up to {girls_max} girlfriends on your plan.")
        else:
            raise HTTPException(status_code=403, detail="Upgrade to Plus or Premium to create more girlfriends.")

    girlfriend_name = body.identity.girlfriend_name.strip()
    traits = body.traits.model_dump()
    appearance_prefs = body.appearance_prefs.model_dump()
    content_prefs = body.content_prefs.model_dump()

    identity = {
        "name": girlfriend_name,
        "job_vibe": body.identity.job_vibe,
        "hobbies": body.identity.hobbies,
        "origin_vibe": body.identity.origin_vibe,
    }

    gf_id = f"gf-{uuid4().hex[:8]}"
    seed_source = f'{user["id"]}|{gf_id}|{json.dumps(appearance_prefs, sort_keys=True)}'
    avatar_seed = hashlib.sha256(seed_source.encode("utf-8")).hexdigest()[:16]
    avatar_url = pick_ai_image_url(
        f"avatar:{avatar_seed}",
        fallback_url=f"https://picsum.photos/seed/{avatar_seed}/512/512",
    )

    canon_seed = int(hashlib.sha256(gf_id.encode("utf-8")).hexdigest()[:8], 16)
    identity_canon = generate_identity_canon(
        name=girlfriend_name,
        job_vibe=body.identity.job_vibe or "in-between",
        hobbies=body.identity.hobbies,
        origin_vibe=body.identity.origin_vibe or "",
        traits=traits,
        content_prefs=content_prefs,
        seed=canon_seed,
    )

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    gf = {
        "id": gf_id,
        "name": girlfriend_name,
        "display_name": girlfriend_name,
        "avatar_url": avatar_url,
        "traits": traits,
        "appearance_prefs": appearance_prefs,
        "content_prefs": content_prefs,
        "identity": identity,
        "identity_canon": identity_canon.model_dump(),
        "created_at": now,
    }

    add_girlfriend(sid, gf)
    current = get_girlfriend(sid) or gf
    gfs = get_all_girlfriends(sid)

    # ── Bootstrap dossier for the new girlfriend ──────────────────────────
    try:
        from app.core.supabase_client import get_supabase_admin
        from app.services.dossier.bootstrap import bootstrap_dossier_from_onboarding

        sb_admin = get_supabase_admin()
        uid_str = user.get("user_id") or user.get("id")
        if sb_admin and uid_str:
            try:
                from uuid import UUID as _UUID
                user_uuid = _UUID(str(uid_str))
                gf_uuid = _UUID(str(gf_id))
                bootstrap_dossier_from_onboarding(sb_admin, user_uuid, gf_uuid, gf)
            except (ValueError, TypeError):
                pass
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Dossier bootstrap failed (non-fatal): %s", e)

    return {
        "girlfriend": _gf_to_response(current),
        "girlfriends": [_gf_to_response(g) for g in gfs],
        "current_girlfriend_id": current.get("id", gf_id),
    }
