"""Onboarding endpoints: prompt images and completion."""
import hashlib
import logging
import threading
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.api.deps import get_current_user
from app.api.store import create_image_job, get_girlfriend, set_girlfriend, update_image_job
from app.schemas.girlfriend import (
    GirlfriendResponse,
    OnboardingCompleteResponse,
    OnboardingCompletePayload,
)
from app.schemas.image_generation import (
    IdentityAppearance,
    IdentityGenerationConfig,
    IdentityGenerationRequest,
    IdentityPersona,
    IdentityPreferences,
)
from app.services.image_generation.onboarding_identity_service import (
    generate_initial_identity_package,
)
from app.utils.ai_images import pick_ai_image_url
from app.utils.identity_canon import generate_identity_canon


router = APIRouter(prefix="/onboarding", tags=["onboarding"])
logger = logging.getLogger(__name__)


# Per-question keys (one image per question)
_PROMPT_QUESTION_KEYS = [
    "appearance_vibe",
    "appearance_age_range",
    "appearance_ethnicity",
    "appearance_breast_size",
    "appearance_butt_size",
    "appearance_hair_color",
    "appearance_hair_style",
    "appearance_eye_color",
    "appearance_body_type",
    "content_spicy",
]

# Per-option keys (one image per option value, for appearance questions)
_APPEARANCE_OPTIONS = {
    "appearance_vibe": ["cute", "elegant", "sporty", "goth", "girl-next-door", "model"],
    "appearance_age_range": ["18", "19-21", "22-26", "27+"],
    "appearance_ethnicity": ["any", "asian", "black", "latina", "white", "middle-eastern", "south-asian"],
    "appearance_breast_size": ["small", "medium", "large", "massive"],
    "appearance_butt_size": ["small", "medium", "large", "massive"],
    "appearance_hair_color": ["black", "brown", "blonde", "red", "ginger", "unnatural"],
    "appearance_hair_style": ["long", "bob", "curly", "straight", "bun"],
    "appearance_eye_color": ["brown", "blue", "green", "hazel"],
    "appearance_body_type": ["slim", "athletic", "curvy"],
}


def _prompt_image_keys():
    """Build all prompt image keys: question-level + option-level."""
    keys = list(_PROMPT_QUESTION_KEYS)
    for qkey, values in _APPEARANCE_OPTIONS.items():
        for val in values:
            keys.append(f"{qkey}_{val}")
    return keys


@router.get("/prompt-images")
def get_prompt_images():
    """Return static prompt image URLs keyed by question and by option."""
    keys = _prompt_image_keys()
    return {
        key: pick_ai_image_url(key, fallback_url=f"https://picsum.photos/seed/{key}/640/360")
        for key in keys
    }


@router.post("/complete")
def complete_onboarding(request: Request, response: Response, body: OnboardingCompletePayload):
    """Finalize onboarding and start identity image generation job."""
    user = get_current_user(request, response)
    if not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    sid = request.cookies.get("session")
    girlfriend_name = body.identity.girlfriend_name.strip()

    traits = body.traits.model_dump()
    appearance_prefs = body.appearance_prefs.model_dump()
    content_prefs = body.content_prefs.model_dump()
    
    # Build identity object (anchors)
    identity = {
        "name": girlfriend_name,
        "job_vibe": body.identity.job_vibe,
        "hobbies": body.identity.hobbies,
        "origin_vibe": body.identity.origin_vibe,
    }

    gf_id = f"gf-{uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    # Generate identity canon (deterministic from gf_id)
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

    gf = {
        "id": gf_id,
        "name": girlfriend_name,
        "display_name": girlfriend_name,
        "avatar_url": None,
        "traits": traits,
        "appearance_prefs": appearance_prefs,
        "content_prefs": content_prefs,
        "identity": identity,
        "identity_canon": identity_canon.model_dump(),
        "identity_images": {
            "main_avatar_url": None,
            "face_ref_primary_url": None,
            "face_ref_secondary_url": None,
            "upper_body_ref_url": None,
            "body_ref_url": None,
            "candidate_urls": [],
        },
        "identity_metadata": {
            "identity_package_version": "identity_pack_v1",
            "workflow_version": "workflow_a_v1",
            "status": "pending",
        },
        "created_at": now,
    }

    set_girlfriend(sid, gf)
    saved = get_girlfriend(sid) or gf
    image_job = create_image_job(
        sid,
        girlfriend_id=gf_id,
        status="pending",
        job_type="identity_creation",
        progress_message="Queued identity generation",
        metadata={
            "identity_package_version": "identity_pack_v1",
            "workflow_version": "workflow_a_v1",
            "phase": "queued",
        },
    )

    # ── Bootstrap dossier + persona vector (compact runtime controls) ───────
    try:
        from app.core.supabase_client import get_supabase_admin
        from app.services.dossier.bootstrap import bootstrap_dossier_from_onboarding
        from app.services.persona_vector_store import upsert_active_persona_vector
        from uuid import UUID as _UUID

        sb_admin = get_supabase_admin()
        uid_str = user.get("user_id") or user.get("id")
        gf_id_str = saved.get("id", gf_id)
        if sb_admin and uid_str:
            try:
                user_uuid = _UUID(str(uid_str))
                gf_uuid = _UUID(str(gf_id_str))
                bootstrap_dossier_from_onboarding(sb_admin, user_uuid, gf_uuid, saved)
                upsert_active_persona_vector(
                    sb_admin,
                    user_uuid,
                    gf_uuid,
                    saved.get("traits") or {},
                    version_tag="pv1",
                )
            except (ValueError, TypeError):
                pass
    except Exception as e:
        logger.warning("Dossier bootstrap failed (non-fatal): %s", e)

    identity_request = IdentityGenerationRequest(
        girlfriend_id=gf_id,
        user_id=str(user.get("user_id") or user.get("id") or ""),
        appearance=IdentityAppearance(
            age_band=appearance_prefs.get("age_range") or "young adult",
            ethnicity=appearance_prefs.get("ethnicity") or "european",
            appearance_vibe=appearance_prefs.get("vibe") or "natural",
            body_type=appearance_prefs.get("body_type"),
            breast_size=appearance_prefs.get("breast_size"),
            butt_size=appearance_prefs.get("butt_size"),
            hair_color=appearance_prefs.get("hair_color") or "brown",
            hair_style=appearance_prefs.get("hair_style") or "long",
            eye_color=appearance_prefs.get("eye_color") or "brown",
        ),
        persona=IdentityPersona(
            display_name=girlfriend_name,
            traits=[
                traits.get("emotional_style", ""),
                traits.get("attachment_style", ""),
                traits.get("reaction_to_absence", ""),
                traits.get("communication_style", ""),
                traits.get("relationship_pace", ""),
                traits.get("cultural_personality", ""),
            ],
            job_vibe=body.identity.job_vibe,
            hobbies=body.identity.hobbies or [],
            origin_vibe=body.identity.origin_vibe,
        ),
        preferences=IdentityPreferences(
            spicy_photos_opt_in=bool(content_prefs.get("wants_spicy_photos")),
        ),
        generation=IdentityGenerationConfig(
            workflow_type="identity_creation",
            workflow_version="workflow_a_v1",
            candidate_count=4,
        ),
    )

    def _run_identity_generation_async() -> None:
        try:
            update_image_job(
                sid,
                girlfriend_id=gf_id,
                job_id=image_job["id"],
                status="running",
                progress_message="Generating 4 avatar candidates",
                metadata={"phase": "generating_candidates"},
            )
            generated = generate_initial_identity_package(identity_request, session_id=sid)
            identity_package = generated.identity_package.model_dump() if generated.identity_package else None
            update_image_job(
                sid,
                girlfriend_id=gf_id,
                job_id=image_job["id"],
                status="completed",
                image_url=(identity_package or {}).get("main_avatar_url") if identity_package else None,
                progress_message="Identity package ready",
                identity_package=identity_package,
                metadata={"phase": "completed"},
            )
        except Exception as exc:
            logger.exception("Identity generation failed for %s: %s", gf_id, exc)
            update_image_job(
                sid,
                girlfriend_id=gf_id,
                job_id=image_job["id"],
                status="failed",
                progress_message="Identity generation failed",
                error=str(exc),
                metadata={"phase": "failed"},
            )

    threading.Thread(target=_run_identity_generation_async, daemon=True).start()
    return OnboardingCompleteResponse(
        girlfriend=GirlfriendResponse(**saved),
        image_job_id=image_job["id"],
        image_job={
            "status": image_job["status"],
            "type": image_job.get("type"),
            "girlfriend_id": gf_id,
            "progress_message": image_job.get("progress_message"),
        },
        identity_package=None,
    )
