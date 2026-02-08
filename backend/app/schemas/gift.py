"""Gift system schemas."""
from typing import Optional
from pydantic import BaseModel


class ImageReward(BaseModel):
    album_size: int = 0
    prompt_template: str = ""
    suggestive_level: str = "safe"  # "safe" | "mild"


class RelationshipBoost(BaseModel):
    trust: int = 0
    intimacy: int = 0


class GiftDefinition(BaseModel):
    id: str
    name: str
    description: str
    price_eur: float
    tier: str  # everyday | dates | luxury | legendary
    relationship_boost: RelationshipBoost
    memory_tag: str
    image_reward: ImageReward
    cooldown_days: Optional[int] = None
    rarity: str = "common"  # common | rare | legendary
    emoji: str = "🎁"


class GiftListResponse(BaseModel):
    gifts: list[GiftDefinition]


class CreateGiftCheckoutRequest(BaseModel):
    gift_id: str


class CreateGiftCheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class GiftHistoryItem(BaseModel):
    id: str
    gift_id: str
    gift_name: str
    amount_eur: float
    status: str  # pending | paid | failed
    created_at: str
    emoji: str = "🎁"


class GiftHistoryResponse(BaseModel):
    purchases: list[GiftHistoryItem]


class GiftDeliverEvent(BaseModel):
    gift_id: str
    gift_name: str
    reaction_text: str
    image_urls: list[str] = []
    trust_gained: int = 0
    intimacy_gained: int = 0
