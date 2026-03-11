"""Girlfriend / persona Pydantic schemas."""
from typing import Any
from pydantic import BaseModel, field_validator, model_validator

from app.schemas.image_generation import IdentityPackage


class TraitsPayload(BaseModel):
    """Trait selection payload (snake_case for API)."""
    emotional_style: str  # Caring | Playful | Reserved | Protective
    attachment_style: str  # Very attached | Emotionally present | Calm but caring
    reaction_to_absence: str  # High | Medium | Low
    communication_style: str  # Soft | Direct | Teasing
    relationship_pace: str  # Slow | Natural | Fast
    cultural_personality: str  # Warm Slavic | Calm Central European | Passionate Balkan


class CreateGirlfriendRequest(BaseModel):
    display_name: str
    traits: TraitsPayload


class AppearancePrefsPayload(BaseModel):
    vibe: str | None = None
    age_range: str | None = None
    ethnicity: str | None = None
    breast_size: str | None = None
    butt_size: str | None = None
    hair_color: str | None = None
    hair_style: str | None = None
    eye_color: str | None = None
    body_type: str | None = None


class ContentPrefsPayload(BaseModel):
    wants_spicy_photos: bool


class IdentityPayload(BaseModel):
    girlfriend_name: str
    job_vibe: str | None = None
    hobbies: list[str] = []
    origin_vibe: str | None = None

    @field_validator("girlfriend_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1 or len(v) > 20:
            raise ValueError("Name must be 1-20 characters")
        return v


class IdentityResponse(BaseModel):
    name: str | None = None
    job_vibe: str | None = None
    hobbies: list[str] = []
    origin_vibe: str | None = None


class IdentityCanon(BaseModel):
    """Generated identity canon fields (server-side, template-based)."""
    backstory: str | None = None
    daily_routine: str | None = None
    favorites: dict[str, str] = {}
    memory_seeds: list[str] = []


class OnboardingCompletePayload(BaseModel):
    traits: TraitsPayload
    appearance_prefs: AppearancePrefsPayload
    content_prefs: ContentPrefsPayload
    identity: IdentityPayload


class GirlfriendResponse(BaseModel):
    id: str
    display_name: str | None = None
    name: str | None = None
    avatar_url: str | None = None
    traits: dict = {}
    appearance_prefs: dict | None = None
    content_prefs: dict | None = None
    identity: IdentityResponse | None = None
    identity_canon: IdentityCanon | None = None
    identity_images: dict | None = None
    identity_metadata: dict | None = None
    created_at: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_empty_dicts(cls, values: Any) -> Any:
        """Convert empty dicts to None for optional nested models.
        
        DB rows may store {} for identity/identity_canon when not yet populated.
        Pydantic would try to validate {} against the model and fail on required fields.
        """
        if isinstance(values, dict):
            for key in ("identity", "identity_canon"):
                val = values.get(key)
                if isinstance(val, dict) and not val:
                    values[key] = None
            # Ensure traits is always a dict
            if not values.get("traits"):
                values["traits"] = {}
        return values


class OnboardingCompleteResponse(BaseModel):
    girlfriend: GirlfriendResponse
    image_job_id: str
    image_job: dict[str, Any] | None = None
    identity_package: IdentityPackage | None = None

