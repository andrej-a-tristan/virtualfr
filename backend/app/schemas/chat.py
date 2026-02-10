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
    level: int
    region_key: str
    region_title: str
    region_min_level: int
    region_max_level: int
    last_interaction_at: str | None = None
    # Bank/cap fields for the visible/bank split
    trust_visible: int | None = None
    trust_bank: int | None = None
    trust_cap: int | None = None
    intimacy_visible: int | None = None
    intimacy_bank: int | None = None
    intimacy_cap: int | None = None
    # Achievement milestones (per-girlfriend, region-locked)
    milestones_reached: list[str] = []
    current_region_index: int | None = None