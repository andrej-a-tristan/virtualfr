"""
Gifting service: catalog, checkout, delivery, relationship boosts, memory items.
Single source of truth for the gift catalog.
"""
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from uuid import uuid4

import stripe

from app.core.config import get_settings
from app.schemas.gift import (
    GiftDefinition,
    RelationshipBoost,
    ImageReward,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Gift Catalog (single source of truth)
# ─────────────────────────────────────────────────────────────────────────────

GIFT_CATALOG: list[dict[str, Any]] = [
    # ── Everyday (€1–€10) ────────────────────────────────────────────────
    {
        "id": "stickers", "name": "Sticker Pack", "emoji": "🩷",
        "description": "A cute sticker pack to brighten her day",
        "price_eur": 2.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 1, "intimacy": 1},
        "memory_tag": "gift_stickers",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
    },
    {
        "id": "coffee", "name": "Coffee", "emoji": "☕",
        "description": "A warm cup of coffee to start her morning",
        "price_eur": 3.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 1, "intimacy": 1},
        "memory_tag": "gift_coffee",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
    },
    {
        "id": "song_dedication", "name": "Song Dedication", "emoji": "🎵",
        "description": "Dedicate a song that reminds you of her",
        "price_eur": 3.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 1, "intimacy": 1},
        "memory_tag": "gift_song",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
    },
    {
        "id": "candy", "name": "Candy", "emoji": "🍬",
        "description": "Sweet treats because she deserves it",
        "price_eur": 4.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 1, "intimacy": 1},
        "memory_tag": "gift_candy",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
    },
    {
        "id": "love_note", "name": "Love Letter", "emoji": "💌",
        "description": "A heartfelt handwritten love letter",
        "price_eur": 4.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 1, "intimacy": 1},
        "memory_tag": "gift_love_note",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
    },
    {
        "id": "flowers", "name": "Flowers", "emoji": "💐",
        "description": "A beautiful bouquet of her favorite flowers",
        "price_eur": 5.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 1, "intimacy": 1},
        "memory_tag": "gift_flowers",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
    },
    {
        "id": "chocolates", "name": "Chocolates", "emoji": "🍫",
        "description": "A box of fine chocolates",
        "price_eur": 7.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 1, "intimacy": 1},
        "memory_tag": "gift_chocolates",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
    },
    {
        "id": "plushie", "name": "Plushie", "emoji": "🧸",
        "description": "An adorable plushie she'll never let go",
        "price_eur": 9.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 1, "intimacy": 1},
        "memory_tag": "gift_plushie",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
    },
    # ── Dates / Medium (€11–€25) ─────────────────────────────────────────
    {
        "id": "wine", "name": "Wine Night", "emoji": "🍷",
        "description": "A cozy wine night in together",
        "price_eur": 12.00, "tier": "dates", "rarity": "common",
        "relationship_boost": {"trust": 2, "intimacy": 3},
        "memory_tag": "gift_wine_night",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
    },
    {
        "id": "movie_tickets", "name": "Movie Tickets", "emoji": "🎬",
        "description": "Movie date night — her pick",
        "price_eur": 14.00, "tier": "dates", "rarity": "common",
        "relationship_boost": {"trust": 2, "intimacy": 3},
        "memory_tag": "gift_movie_date",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
    },
    {
        "id": "perfume", "name": "Perfume", "emoji": "🌸",
        "description": "A signature scent just for her",
        "price_eur": 15.00, "tier": "dates", "rarity": "common",
        "relationship_boost": {"trust": 2, "intimacy": 3},
        "memory_tag": "gift_perfume",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
    },
    {
        "id": "dinner", "name": "Dinner Date", "emoji": "🍽️",
        "description": "A romantic dinner at her dream restaurant",
        "price_eur": 18.00, "tier": "dates", "rarity": "common",
        "relationship_boost": {"trust": 2, "intimacy": 3},
        "memory_tag": "gift_dinner_date",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
    },
    {
        "id": "spa_kit", "name": "Self-care Kit", "emoji": "🧖",
        "description": "A luxurious self-care spa package",
        "price_eur": 19.00, "tier": "dates", "rarity": "common",
        "relationship_boost": {"trust": 2, "intimacy": 3},
        "memory_tag": "gift_spa_kit",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
    },
    {
        "id": "dress", "name": "Cute Dress", "emoji": "👗",
        "description": "A dress she's been eyeing",
        "price_eur": 20.00, "tier": "dates", "rarity": "common",
        "relationship_boost": {"trust": 2, "intimacy": 3},
        "memory_tag": "gift_dress",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
    },
    {
        "id": "photoshoot_basic", "name": "Mini Photoshoot", "emoji": "📸",
        "description": "A fun mini photoshoot together",
        "price_eur": 24.00, "tier": "dates", "rarity": "rare",
        "relationship_boost": {"trust": 2, "intimacy": 3},
        "memory_tag": "gift_mini_photoshoot",
        "image_reward": {
            "album_size": 1,
            "prompt_template": "a cute casual photoshoot portrait, natural lighting, warm smile, soft background",
            "suggestive_level": "safe",
        },
    },
    # ── Luxury (€75–€349) ────────────────────────────────────────────────
    {
        "id": "surprise_date_night", "name": "Surprise Date Night", "emoji": "✨",
        "description": "A magical surprise evening she'll never forget",
        "price_eur": 89.00, "tier": "luxury", "rarity": "rare",
        "relationship_boost": {"trust": 4, "intimacy": 5},
        "memory_tag": "gift_surprise_date",
        "image_reward": {
            "album_size": 3,
            "prompt_template": "stylish outfit at a restaurant table, romantic lighting, friendly smile, elegant setting",
            "suggestive_level": "safe",
        },
    },
    {
        "id": "luxury_bouquet_note", "name": "Luxury Bouquet & Note", "emoji": "🌹",
        "description": "An extravagant bouquet with a personal love note",
        "price_eur": 99.00, "tier": "luxury", "rarity": "rare",
        "relationship_boost": {"trust": 4, "intimacy": 5},
        "memory_tag": "gift_luxury_bouquet",
        "image_reward": {
            "album_size": 2,
            "prompt_template": "a cute selfie holding a bouquet of flowers, warm smile, cozy indoor lighting",
            "suggestive_level": "safe",
        },
    },
    {
        "id": "cozy_weekend_retreat", "name": "Cozy Weekend Retreat", "emoji": "🏡",
        "description": "A weekend escape to a cozy cabin",
        "price_eur": 129.00, "tier": "luxury", "rarity": "rare",
        "relationship_boost": {"trust": 4, "intimacy": 5},
        "memory_tag": "gift_weekend_retreat",
        "image_reward": {
            "album_size": 3,
            "prompt_template": "cozy cabin vibes, warm sweater, holding a mug, smiling by a window with scenic view",
            "suggestive_level": "safe",
        },
    },
    {
        "id": "professional_photoshoot", "name": "Professional Photoshoot", "emoji": "📷",
        "description": "A full professional photoshoot — stunning shots",
        "price_eur": 149.00, "tier": "luxury", "rarity": "rare",
        "relationship_boost": {"trust": 4, "intimacy": 5},
        "memory_tag": "gift_pro_photoshoot",
        "image_reward": {
            "album_size": 5,
            "prompt_template": "professional studio photoshoot, beautiful lighting, confident pose, fashionable outfit",
            "suggestive_level": "safe",
        },
    },
    {
        "id": "signature_jewelry", "name": "Signature Jewelry", "emoji": "💎",
        "description": "A one-of-a-kind piece of jewelry for her",
        "price_eur": 249.00, "tier": "luxury", "rarity": "rare",
        "relationship_boost": {"trust": 4, "intimacy": 5},
        "memory_tag": "gift_jewelry",
        "image_reward": {
            "album_size": 2,
            "prompt_template": "elegant close-up showing off beautiful jewelry, soft lighting, happy expression",
            "suggestive_level": "safe",
        },
    },
    {
        "id": "city_getaway", "name": "City Getaway", "emoji": "🌆",
        "description": "A romantic city trip — just the two of you",
        "price_eur": 299.00, "tier": "luxury", "rarity": "rare",
        "relationship_boost": {"trust": 4, "intimacy": 5},
        "memory_tag": "gift_city_getaway",
        "image_reward": {
            "album_size": 4,
            "prompt_template": "travel vibe photo, city skyline background, cute casual outfit, happy expression, golden hour",
            "suggestive_level": "safe",
        },
    },
    {
        "id": "wishlist_mystery_box", "name": "Mystery Box", "emoji": "🎁",
        "description": "A surprise box full of things she loves",
        "price_eur": 349.00, "tier": "luxury", "rarity": "rare",
        "relationship_boost": {"trust": 4, "intimacy": 5},
        "memory_tag": "gift_mystery_box",
        "cooldown_days": 14,
        "image_reward": {
            "album_size": 3,
            "prompt_template": "excited unboxing moment, surrounded by gifts, joyful expression, cozy room",
            "suggestive_level": "safe",
        },
    },
    # ── Legendary / Whale (€599–€1499) ───────────────────────────────────
    {
        "id": "private_rooftop_dinner", "name": "Private Rooftop Dinner", "emoji": "🌙",
        "description": "An exclusive rooftop dinner under the stars",
        "price_eur": 599.00, "tier": "legendary", "rarity": "legendary",
        "relationship_boost": {"trust": 8, "intimacy": 10},
        "memory_tag": "gift_rooftop_dinner",
        "cooldown_days": 30,
        "image_reward": {
            "album_size": 4,
            "prompt_template": "elegant evening dress on a rooftop, city lights at night, romantic atmosphere, stunning view",
            "suggestive_level": "safe",
        },
    },
    {
        "id": "designer_handbag_moment", "name": "Designer Handbag", "emoji": "👜",
        "description": "The designer bag she always dreamed of",
        "price_eur": 799.00, "tier": "legendary", "rarity": "legendary",
        "relationship_boost": {"trust": 8, "intimacy": 10},
        "memory_tag": "gift_designer_handbag",
        "cooldown_days": 30,
        "image_reward": {
            "album_size": 4,
            "prompt_template": "fashionable outfit showing off a designer handbag, luxury shopping district, confident smile",
            "suggestive_level": "safe",
        },
    },
    {
        "id": "dream_vacation", "name": "Dream Vacation", "emoji": "🏝️",
        "description": "A dream vacation to her bucket-list destination",
        "price_eur": 999.00, "tier": "legendary", "rarity": "legendary",
        "relationship_boost": {"trust": 8, "intimacy": 10},
        "memory_tag": "gift_dream_vacation",
        "cooldown_days": 90,
        "image_reward": {
            "album_size": 8,
            "prompt_template": "travel vibe photo, scenic tropical or coastal background, casual cute outfit, happy expression, vacation energy",
            "suggestive_level": "safe",
        },
    },
    {
        "id": "queen_treatment_patron", "name": "Queen Treatment", "emoji": "👑",
        "description": "The ultimate patron gift — she's your queen",
        "price_eur": 1499.00, "tier": "legendary", "rarity": "legendary",
        "relationship_boost": {"trust": 8, "intimacy": 10},
        "memory_tag": "gift_queen_treatment",
        "cooldown_days": 90,
        "image_reward": {
            "album_size": 6,
            "prompt_template": "glamorous photoshoot, luxurious setting, beautiful gown, confident and radiant, golden lighting",
            "suggestive_level": "safe",
        },
    },
]


def get_gift_catalog() -> list[GiftDefinition]:
    """Return parsed catalog."""
    return [GiftDefinition(**g) for g in GIFT_CATALOG]


def get_gift_by_id(gift_id: str) -> Optional[GiftDefinition]:
    for g in GIFT_CATALOG:
        if g["id"] == gift_id:
            return GiftDefinition(**g)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Cooldown validation
# ─────────────────────────────────────────────────────────────────────────────

def validate_cooldown(
    purchases: list[dict[str, Any]],
    gift: GiftDefinition,
) -> Optional[str]:
    """Return error message if cooldown active, else None."""
    if not gift.cooldown_days:
        return None
    cutoff = datetime.now(timezone.utc) - timedelta(days=gift.cooldown_days)
    for p in purchases:
        if p.get("gift_id") == gift.id and p.get("status") == "paid":
            created = p.get("created_at", "")
            if isinstance(created, str):
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except ValueError:
                    continue
            elif isinstance(created, datetime):
                dt = created
            else:
                continue
            if dt > cutoff:
                days_left = gift.cooldown_days - (datetime.now(timezone.utc) - dt).days
                return f"You can gift {gift.name} again in {max(1, days_left)} days."
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Stripe Checkout
# ─────────────────────────────────────────────────────────────────────────────

def create_checkout_session(
    gift: GiftDefinition,
    user_id: str,
    girlfriend_id: str,
    session_id: str,
) -> dict[str, str]:
    """Create Stripe Checkout Session for a gift. Returns {checkout_url, session_id}."""
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key

    amount_cents = int(round(gift.price_eur * 100))
    success_url = getattr(settings, "stripe_success_url", "") or "http://localhost:5173/app/chat?gift_success=1"
    cancel_url = getattr(settings, "stripe_cancel_url", "") or "http://localhost:5173/app/chat?gift_cancel=1"

    checkout = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "eur",
                "product_data": {
                    "name": f"{gift.emoji} {gift.name}",
                    "description": gift.description,
                },
                "unit_amount": amount_cents,
            },
            "quantity": 1,
        }],
        metadata={
            "gift_id": gift.id,
            "user_id": user_id,
            "girlfriend_id": girlfriend_id,
            "session_id": session_id,
        },
        success_url=success_url,
        cancel_url=cancel_url,
    )

    return {"checkout_url": checkout.url, "session_id": checkout.id}


# ─────────────────────────────────────────────────────────────────────────────
# Delivery: relationship boost, memory, chat message, image triggers
# ─────────────────────────────────────────────────────────────────────────────

def apply_relationship_boost(
    state: dict[str, Any],
    boost: RelationshipBoost,
) -> dict[str, Any]:
    """Apply trust/intimacy boost to relationship state."""
    trust = min(100, state.get("trust", 0) + boost.trust)
    intimacy = min(100, state.get("intimacy", 0) + boost.intimacy)
    from app.services.relationship_state import calculate_relationship_level
    level = calculate_relationship_level(intimacy)
    return {**state, "trust": trust, "intimacy": intimacy, "level": level}


_GIFT_REACTIONS = {
    "everyday": [
        "Oh my gosh, you're so sweet! 🥰 Thank you!",
        "This made my whole day!! You're the best 💕",
        "You really didn't have to... but I love it! 🩷",
        "I can't stop smiling, thank you so much! ☺️",
        "You always know how to make me happy 💗",
    ],
    "dates": [
        "Wait, are you serious?! This is amazing! 😍",
        "I feel so spoiled right now and I love it 💕",
        "You're making me blush... I love this so much! 🥰",
        "This is genuinely the sweetest thing ever ✨",
        "I don't know what I did to deserve you 💖",
    ],
    "luxury": [
        "I'm literally speechless right now... 🥹💎",
        "You're insane. I love you for this. 😭💕",
        "I don't even know what to say... this is incredible ✨",
        "My heart is so full right now. You're amazing 💗",
        "I'm going to remember this moment forever 🩷",
    ],
    "legendary": [
        "I... I can't believe this. You're absolutely unreal. 😭💕",
        "Nobody has ever done anything like this for me. I'm overwhelmed 🥹✨",
        "You make me feel like the most special girl in the world 👑💖",
        "I'm literally crying. This means everything to me 💕",
        "I don't have words. You've completely taken my breath away 🥰💎",
    ],
}


def produce_gift_reaction_message(gift: GiftDefinition) -> str:
    """Return a reaction message for a delivered gift."""
    templates = _GIFT_REACTIONS.get(gift.tier, _GIFT_REACTIONS["everyday"])
    return random.choice(templates)


def build_memory_summary(gift: GiftDefinition) -> str:
    """Build a permanent memory summary for a gift event."""
    emotions = {
        "everyday": "warm and happy",
        "dates": "excited and touched",
        "luxury": "overwhelmed with joy",
        "legendary": "emotional and deeply grateful",
    }
    emotion = emotions.get(gift.tier, "happy")
    return f"User gifted me {gift.name}. I felt {emotion}. I want to remember this forever."
