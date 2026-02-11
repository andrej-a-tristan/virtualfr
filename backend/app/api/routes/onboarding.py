"""Onboarding endpoints: prompt images and completion."""
import hashlib
import json

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.api.deps import get_current_user
from app.api.store import set_girlfriend, get_girlfriend
from app.schemas.girlfriend import (
    GirlfriendResponse,
    IdentityResponse,
    OnboardingCompletePayload,
)
from app.utils.identity_canon import generate_identity_canon


router = APIRouter(prefix="/onboarding", tags=["onboarding"])


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
    return {key: f"https://picsum.photos/seed/{key}/640/360" for key in keys}


@router.post("/complete")
def complete_onboarding(request: Request, response: Response, body: OnboardingCompletePayload):
    """Finalize onboarding by creating a single girlfriend avatar."""
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

    # Deterministic seed for avatar and canon
    from uuid import uuid4
    gf_id = f"gf-{uuid4().hex[:8]}"
    seed_source = (
        f'{user["id"]}|'
        f"{json.dumps(appearance_prefs, sort_keys=True)}|"
        f"{json.dumps(traits, sort_keys=True)}"
    )
    avatar_seed = hashlib.sha256(seed_source.encode("utf-8")).hexdigest()[:16]
    avatar_url = f"https://picsum.photos/seed/{avatar_seed}/512/512"
    
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
        "avatar_url": avatar_url,
        "traits": traits,
        "appearance_prefs": appearance_prefs,
        "content_prefs": content_prefs,
        "identity": identity,
        "identity_canon": identity_canon.model_dump(),
        "created_at": "2025-01-01T00:00:00Z",
    }

    set_girlfriend(sid, gf)
    saved = get_girlfriend(sid) or gf
    return GirlfriendResponse(**saved)
