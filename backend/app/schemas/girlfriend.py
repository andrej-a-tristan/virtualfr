"""Girlfriend / persona Pydantic schemas."""
from pydantic import BaseModel


class TraitsPayload(BaseModel):
    emotional_style: str
    attachment_style: str
    jealousy_level: str
    communication_tone: str
    intimacy_pace: str
    cultural_personality: str


class GirlfriendResponse(BaseModel):
    id: str
    name: str
    avatar_url: str | None = None
    traits: dict
    created_at: str
