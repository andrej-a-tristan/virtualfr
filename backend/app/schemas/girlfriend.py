"""Girlfriend / persona Pydantic schemas."""
from pydantic import BaseModel, field_validator


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
    name: str
    job_vibe: str | None = None
    hobbies: list[str] = []
    origin_vibe: str | None = None


class IdentityCanon(BaseModel):
    """Generated identity canon fields (server-side, template-based)."""
    backstory: str
    daily_routine: str
    favorites: dict[str, str]
    memory_seeds: list[str]


class OnboardingCompletePayload(BaseModel):
    traits: TraitsPayload
    appearance_prefs: AppearancePrefsPayload
    content_prefs: ContentPrefsPayload
    identity: IdentityPayload


class GirlfriendResponse(BaseModel):
    id: str
    display_name: str
    traits: dict
    appearance_prefs: dict | None = None
    content_prefs: dict | None = None
    identity: IdentityResponse | None = None
    identity_canon: IdentityCanon | None = None
    created_at: str

