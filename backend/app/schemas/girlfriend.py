"""Girlfriend / persona Pydantic schemas."""
from pydantic import BaseModel


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


class GirlfriendResponse(BaseModel):
    id: str
    display_name: str
    traits: dict
    created_at: str
