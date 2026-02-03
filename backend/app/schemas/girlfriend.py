"""Girlfriend / persona Pydantic schemas."""
from pydantic import BaseModel


class TraitsPayload(BaseModel):
    emotional_style: str
    attachment_style: str
    jealousy_level: str
    communication_tone: str
    intimacy_pace: str
    cultural_personality: str


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


class OnboardingCompletePayload(BaseModel):
    traits: TraitsPayload
    appearance_prefs: AppearancePrefsPayload
    content_prefs: ContentPrefsPayload


class GirlfriendResponse(BaseModel):
    id: str
    name: str
    avatar_url: str | None = None
    traits: dict
    appearance_prefs: dict | None = None
    content_prefs: dict | None = None
    created_at: str

