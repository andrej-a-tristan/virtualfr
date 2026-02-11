"""Intimacy Achievements schemas — catalog items & SSE event payloads."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel


class IntimacyAchievementSchema(BaseModel):
    """Public-facing schema for a single intimacy achievement (catalog item)."""
    id: str
    tier: int                               # 0..6
    title: str
    subtitle: str
    rarity: str                             # "COMMON" | "UNCOMMON" | "RARE" | "EPIC" | "LEGENDARY"
    sort_order: int
    required_region_index: int
    required_intimacy_visible: int | None = None
    is_secret: bool = False
    # Filled per-girlfriend at query time
    unlocked: bool = False
    unlocked_at: str | None = None
    image_url: str | None = None


class IntimacyAchievementUnlockedEvent(BaseModel):
    """SSE payload when an intimacy achievement is unlocked."""
    id: str
    title: str
    subtitle: str
    rarity: str
    tier: int
    unlocked_at: str
    girlfriend_id: str


class IntimacyPhotoReadyEvent(BaseModel):
    """SSE payload when the photo for an unlocked intimacy achievement is ready."""
    id: str               # achievement_id
    image_url: str
    tier: int
    girlfriend_id: str
