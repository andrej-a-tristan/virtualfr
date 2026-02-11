"""Profile page schemas — aggregated per-girlfriend stats."""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class RelationshipSnapshot(BaseModel):
    level_label: str  # STRANGER / FAMILIAR / CLOSE / INTIMATE / EXCLUSIVE
    trust_visible: int = 20
    trust_cap: int = 100
    intimacy_visible: int = 1
    intimacy_cap: int = 100
    current_region_index: Optional[int] = None
    region_title: Optional[str] = None


class ActivitySnapshot(BaseModel):
    message_count: int = 0
    last_interaction_at: Optional[str] = None  # ISO-8601
    streak_current_days: int = 0
    streak_best_days: int = 0
    streak_active_today: bool = False


class CollectionsSnapshot(BaseModel):
    photos: int = 0
    gifts_owned: int = 0
    gifts_total: int = 26
    relationship_achievements_unlocked: int = 0
    relationship_achievements_total: int = 54
    intimacy_achievements_unlocked: int = 0
    intimacy_achievements_total: int = 50


class GirlProfileStats(BaseModel):
    girlfriend_id: str
    name: str
    avatar_url: Optional[str] = None
    vibe_line: str = ""
    relationship: RelationshipSnapshot
    activity: ActivitySnapshot
    collections: CollectionsSnapshot


class ProfileTotals(BaseModel):
    girls: int = 0
    messages: int = 0
    photos: int = 0
    gifts_owned: int = 0


class ProfileGirlsResponse(BaseModel):
    girls: list[GirlProfileStats] = Field(default_factory=list)
    totals: ProfileTotals = Field(default_factory=ProfileTotals)
