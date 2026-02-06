"""Chat-related Pydantic schemas."""
from pydantic import BaseModel
from typing import Literal


class ChatMessage(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    content: str | None = None
    image_url: str | None = None
    event_type: str | None = None  # e.g. "milestone"
    event_key: str | None = None
    created_at: str


class SendMessageRequest(BaseModel):
    message: str
    girlfriend_id: str | None = None


class AppOpenRequest(BaseModel):
    girlfriend_id: str


class RelationshipState(BaseModel):
    trust: int
    intimacy: int
    level: str  # STRANGER, FAMILIAR, CLOSE, INTIMATE, EXCLUSIVE
    last_interaction_at: str | None = None
    milestones_reached: list[str] = []
