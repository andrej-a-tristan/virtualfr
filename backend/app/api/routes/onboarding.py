"""Onboarding endpoints: prompt images and completion."""
import hashlib
import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.store import get_session_user, set_girlfriend
from app.schemas.girlfriend import (
    GirlfriendResponse,
    OnboardingCompletePayload,
)


router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _session_id(request: Request) -> str | None:
    return request.cookies.get("session")


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
def complete_onboarding(request: Request, body: OnboardingCompletePayload):
    """Finalize onboarding by creating a single girlfriend avatar."""
    sid = _session_id(request)
    if not sid:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    user = get_session_user(sid)
    if not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    traits = body.traits.model_dump()
    appearance_prefs = body.appearance_prefs.model_dump()
    content_prefs = body.content_prefs.model_dump()

    seed_source = (
        f'{user["id"]}|'
        f"{json.dumps(appearance_prefs, sort_keys=True)}|"
        f"{json.dumps(traits, sort_keys=True)}"
    )
    seed = hashlib.sha256(seed_source.encode("utf-8")).hexdigest()[:16]
    avatar_url = f"https://picsum.photos/seed/{seed}/512/512"

    gf = {
        "id": "gf-1",
        "name": "Luna",
        "avatar_url": avatar_url,
        "traits": traits,
        "appearance_prefs": appearance_prefs,
        "content_prefs": content_prefs,
        "created_at": "2025-01-01T00:00:00Z",
    }

    set_girlfriend(sid, gf)
    return GirlfriendResponse(**gf)

