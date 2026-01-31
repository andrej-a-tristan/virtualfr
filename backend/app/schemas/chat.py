"""Chat-related Pydantic schemas."""
from pydantic import BaseModel
from typing import Literal


class ChatMessage(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    content: str | None = None
    image_url: str | None = None
    event_type: str | None = None  # e.g. "milestone"
    created_at: str


class SendMessageRequest(BaseModel):
    message: str
    girlfriend_id: str | None = None


class RelationshipState(BaseModel):
    trust: int
    intimacy: int
    level: int
    last_interaction_at: str | None = None
