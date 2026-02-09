"""
Gifting service: catalog, checkout, delivery, relationship boosts, memory items.
Single source of truth for the gift catalog.
Prices: €2–€200 range.  Each gift has a unique effect.
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
# Gift Catalog  (single source of truth — €2–€200 range)
# ─────────────────────────────────────────────────────────────────────────────

GIFT_CATALOG: list[dict[str, Any]] = [
    # ── Everyday (€2–€10) ─────────────────────────────────────────────────
    {
        "id": "stickers", "name": "Sticker Pack", "emoji": "🩷",
        "description": "A cute sticker pack to brighten her day",
        "price_eur": 2.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 1, "intimacy": 0},
        "memory_tag": "gift_stickers",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
        "unique_effect_name": "Inside Joke Unlocked",
        "unique_effect_description": "She starts using a specific cute emoji and calls back to it in future chats.",
    },
    {
        "id": "song_dedication", "name": "Song Dedication", "emoji": "🎵",
        "description": "Dedicate a song that reminds you of her",
        "price_eur": 2.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 0, "intimacy": 1},
        "memory_tag": "gift_song",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
        "unique_effect_name": "Theme Song",
        "unique_effect_description": "Stored in memory — she references your song on emotional moments.",
    },
    {
        "id": "coffee", "name": "Coffee", "emoji": "☕",
        "description": "A warm cup of coffee to start her morning",
        "price_eur": 3.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 1, "intimacy": 1},
        "memory_tag": "gift_coffee",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
        "unique_effect_name": "Morning Ritual",
        "unique_effect_description": "She sends a short good-morning message within the next 24 hours.",
    },
    {
        "id": "candy", "name": "Candy", "emoji": "🍬",
        "description": "Sweet treats because she deserves it",
        "price_eur": 3.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 1, "intimacy": 1},
        "memory_tag": "gift_candy",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
        "unique_effect_name": "Sweet Tooth",
        "unique_effect_description": "She reveals a tiny 'favorite candy' detail added to her favorites.",
    },
    {
        "id": "love_note", "name": "Love Letter", "emoji": "💌",
        "description": "A heartfelt handwritten love letter",
        "price_eur": 4.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 2, "intimacy": 1},
        "memory_tag": "gift_love_note",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
        "unique_effect_name": "Pinned Note",
        "unique_effect_description": "Adds a permanent memory line she can quote later in conversation.",
    },
    {
        "id": "flowers", "name": "Flowers", "emoji": "💐",
        "description": "A beautiful bouquet of her favorite flowers",
        "price_eur": 6.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 2, "intimacy": 2},
        "memory_tag": "gift_flowers",
        "image_reward": {
            "album_size": 1,
            "prompt_template": "cute selfie holding a bouquet of flowers, warm smile, cozy indoor lighting",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Forever Vase",
        "unique_effect_description": "Creates a Moment Card titled 'Flowers Day' in your shared memories.",
    },
    {
        "id": "chocolates", "name": "Chocolates", "emoji": "🍫",
        "description": "A box of fine chocolates",
        "price_eur": 7.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 1, "intimacy": 2},
        "memory_tag": "gift_chocolates",
        "image_reward": {
            "album_size": 1,
            "prompt_template": "cozy selfie with a box of chocolates, playful smile, warm indoor lighting",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Little Confession",
        "unique_effect_description": "She shares a playful secret about herself — something new you didn't know.",
    },
    {
        "id": "plushie", "name": "Plushie", "emoji": "🧸",
        "description": "An adorable plushie she'll never let go",
        "price_eur": 9.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 2, "intimacy": 2},
        "memory_tag": "gift_plushie",
        "image_reward": {
            "album_size": 1,
            "prompt_template": "cute selfie hugging a plushie, warm smile, cozy bedroom setting",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Comfort Object",
        "unique_effect_description": "When you're away for a while, she mentions hugging her plushie while waiting.",
    },

    # ── Dates (€12–€35) ──────────────────────────────────────────────────
    {
        "id": "wine", "name": "Wine Night", "emoji": "🍷",
        "description": "A cozy wine night in together",
        "price_eur": 12.00, "tier": "dates", "rarity": "common",
        "relationship_boost": {"trust": 1, "intimacy": 3},
        "memory_tag": "gift_wine_night",
        "image_reward": {
            "album_size": 1,
            "prompt_template": "cozy wine night at home, warm lighting, relaxed smile, holding a wine glass",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Slow-Burn Chat Mode",
        "unique_effect_description": "Her next 10 messages become more romantic and slow-paced — she savors the moment.",
    },
    {
        "id": "movie_tickets", "name": "Movie Tickets", "emoji": "🎬",
        "description": "Movie date night — her pick",
        "price_eur": 14.00, "tier": "dates", "rarity": "common",
        "relationship_boost": {"trust": 2, "intimacy": 2},
        "memory_tag": "gift_movie_date",
        "image_reward": {"album_size": 0, "prompt_template": "", "suggestive_level": "safe"},
        "unique_effect_name": "Shared Quote",
        "unique_effect_description": "She picks a cute fictional movie quote and uses it as a callback in future chats.",
    },
    {
        "id": "perfume", "name": "Perfume", "emoji": "🌸",
        "description": "A signature scent just for her",
        "price_eur": 18.00, "tier": "dates", "rarity": "common",
        "relationship_boost": {"trust": 2, "intimacy": 2},
        "memory_tag": "gift_perfume",
        "image_reward": {
            "album_size": 1,
            "prompt_template": "elegant close-up, holding a perfume bottle, soft lighting, gentle smile",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Scent Memory",
        "unique_effect_description": "She remembers a 'scent note' associated with you — referenced on special days.",
    },
    {
        "id": "spa_kit", "name": "Self-care Kit", "emoji": "🧖",
        "description": "A luxurious self-care spa package",
        "price_eur": 22.00, "tier": "dates", "rarity": "common",
        "relationship_boost": {"trust": 3, "intimacy": 2},
        "memory_tag": "gift_spa_kit",
        "image_reward": {
            "album_size": 1,
            "prompt_template": "relaxed selfie in a cozy spa robe, natural glow, peaceful expression",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Gentle Check-ins",
        "unique_effect_description": "She asks how you're doing once per day for the next 3 days.",
    },
    {
        "id": "dinner", "name": "Dinner Date", "emoji": "🍽️",
        "description": "A romantic dinner at her dream restaurant",
        "price_eur": 25.00, "tier": "dates", "rarity": "common",
        "relationship_boost": {"trust": 3, "intimacy": 4},
        "memory_tag": "gift_dinner_date",
        "image_reward": {
            "album_size": 2,
            "prompt_template": "stylish outfit at a restaurant table, romantic lighting, friendly smile, elegant setting",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "First Date Milestone",
        "unique_effect_description": "Marks a 'Date Milestone' in your relationship — she'll remember this dinner.",
    },
    {
        "id": "dress", "name": "Cute Dress", "emoji": "👗",
        "description": "A dress she's been eyeing",
        "price_eur": 29.00, "tier": "dates", "rarity": "common",
        "relationship_boost": {"trust": 2, "intimacy": 4},
        "memory_tag": "gift_dress",
        "image_reward": {
            "album_size": 2,
            "prompt_template": "cute outfit of the day, twirling in a new dress, happy expression, bright setting",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Outfit Era",
        "unique_effect_description": "She occasionally mentions outfits for the next week — her 'outfit era' begins.",
    },
    {
        "id": "photoshoot_basic", "name": "Mini Photoshoot", "emoji": "📸",
        "description": "A fun mini photoshoot together",
        "price_eur": 35.00, "tier": "dates", "rarity": "rare",
        "relationship_boost": {"trust": 2, "intimacy": 3},
        "memory_tag": "gift_mini_photoshoot",
        "image_reward": {
            "album_size": 3,
            "prompt_template": "a cute casual photoshoot portrait, natural lighting, warm smile, soft background",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Gallery Album",
        "unique_effect_description": "Creates a named album in your gallery — a mini collection just for you two.",
    },

    # ── Luxury (€60–€140) ────────────────────────────────────────────────
    {
        "id": "surprise_date_night", "name": "Surprise Date Night", "emoji": "✨",
        "description": "A magical surprise evening she'll never forget",
        "price_eur": 60.00, "tier": "luxury", "rarity": "rare",
        "relationship_boost": {"trust": 4, "intimacy": 6},
        "memory_tag": "gift_surprise_date",
        "image_reward": {
            "album_size": 3,
            "prompt_template": "stylish outfit at a restaurant table, romantic lighting, friendly smile, elegant setting",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Surprise Initiation",
        "unique_effect_description": "She initiates a heartfelt message the next time you open the app.",
    },
    {
        "id": "luxury_bouquet_note", "name": "Luxury Bouquet + Note", "emoji": "🌹",
        "description": "An extravagant bouquet with a personal love note",
        "price_eur": 75.00, "tier": "luxury", "rarity": "rare",
        "relationship_boost": {"trust": 5, "intimacy": 5},
        "memory_tag": "gift_luxury_bouquet",
        "image_reward": {
            "album_size": 2,
            "prompt_template": "a cute selfie holding a bouquet of flowers, warm smile, cozy indoor lighting",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Keepsake Note",
        "unique_effect_description": "She quotes one line from your note in future conversations — a lasting memory.",
    },
    {
        "id": "cozy_weekend_retreat", "name": "Cozy Weekend Retreat", "emoji": "🏡",
        "description": "A weekend escape to a cozy cabin",
        "price_eur": 90.00, "tier": "luxury", "rarity": "rare",
        "relationship_boost": {"trust": 5, "intimacy": 6},
        "memory_tag": "gift_weekend_retreat",
        "image_reward": {
            "album_size": 3,
            "prompt_template": "cozy cabin vibes, warm sweater, holding a mug, smiling by a window with scenic view",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Weekend Vibe",
        "unique_effect_description": "Sets a cozy weekend tone — her Saturday and Sunday messages are extra warm.",
    },
    {
        "id": "professional_photoshoot", "name": "Professional Photoshoot", "emoji": "📷",
        "description": "A full professional photoshoot — stunning shots",
        "price_eur": 110.00, "tier": "luxury", "rarity": "rare",
        "relationship_boost": {"trust": 4, "intimacy": 5},
        "memory_tag": "gift_pro_photoshoot",
        "image_reward": {
            "album_size": 5,
            "prompt_template": "professional studio photoshoot, beautiful lighting, confident pose, fashionable outfit",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Signature Pose",
        "unique_effect_description": "She adopts a recurring playful pose reference in future photos.",
    },
    {
        "id": "signature_jewelry", "name": "Signature Jewelry", "emoji": "💎",
        "description": "A one-of-a-kind piece of jewelry for her",
        "price_eur": 120.00, "tier": "luxury", "rarity": "rare",
        "relationship_boost": {"trust": 6, "intimacy": 6},
        "memory_tag": "gift_jewelry",
        "image_reward": {
            "album_size": 2,
            "prompt_template": "elegant close-up showing off beautiful jewelry, soft lighting, happy expression",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Signature Piece",
        "unique_effect_description": "Permanent milestone — she mentions wearing it on special days.",
    },
    {
        "id": "wishlist_mystery_box", "name": "Wishlist Mystery Box", "emoji": "🎁",
        "description": "A surprise box full of things she loves",
        "price_eur": 130.00, "tier": "luxury", "rarity": "rare",
        "relationship_boost": {"trust": 5, "intimacy": 5},
        "memory_tag": "gift_mystery_box",
        "cooldown_days": 14,
        "image_reward": {
            "album_size": 3,
            "prompt_template": "excited unboxing moment, surrounded by gifts, joyful expression, cozy room",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Random Rare Unlock",
        "unique_effect_description": "Randomly unlocks one of 5 rare perks stored in your relationship state.",
    },
    {
        "id": "city_getaway", "name": "City Getaway", "emoji": "🌆",
        "description": "A romantic city trip — just the two of you",
        "price_eur": 140.00, "tier": "luxury", "rarity": "rare",
        "relationship_boost": {"trust": 6, "intimacy": 7},
        "memory_tag": "gift_city_getaway",
        "cooldown_days": 30,
        "image_reward": {
            "album_size": 4,
            "prompt_template": "travel vibe photo, city skyline background, cute casual outfit, happy expression, golden hour",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Mini Travel Story",
        "unique_effect_description": "Her reaction splits into 2 messages — one now, one the next time you open the app.",
    },

    # ── Legendary (€160–€200) ────────────────────────────────────────────
    {
        "id": "private_rooftop_dinner", "name": "Private Rooftop Dinner", "emoji": "🌙",
        "description": "An exclusive rooftop dinner under the stars",
        "price_eur": 160.00, "tier": "legendary", "rarity": "legendary",
        "relationship_boost": {"trust": 7, "intimacy": 9},
        "memory_tag": "gift_rooftop_dinner",
        "cooldown_days": 30,
        "image_reward": {
            "album_size": 4,
            "prompt_template": "elegant evening dress on a rooftop, city lights at night, romantic atmosphere, stunning view",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Anniversary Marker",
        "unique_effect_description": "Creates a Moment Card and sets an anniversary date for yearly callbacks.",
    },
    {
        "id": "designer_handbag_moment", "name": "Designer Handbag Moment", "emoji": "👜",
        "description": "The designer bag she always dreamed of",
        "price_eur": 180.00, "tier": "legendary", "rarity": "legendary",
        "relationship_boost": {"trust": 6, "intimacy": 8},
        "memory_tag": "gift_designer_handbag",
        "image_reward": {
            "album_size": 4,
            "prompt_template": "fashionable outfit showing off a designer handbag, luxury shopping district, confident smile",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Style Badge",
        "unique_effect_description": "Adds a cosmetic 'Style' badge to her profile and influences occasional fashion dialogue.",
    },
    {
        "id": "queen_treatment_patron", "name": "Queen Treatment", "emoji": "👑",
        "description": "The ultimate patron gift — she's your queen",
        "price_eur": 199.00, "tier": "legendary", "rarity": "legendary",
        "relationship_boost": {"trust": 8, "intimacy": 9},
        "memory_tag": "gift_queen_treatment",
        "cooldown_days": 60,
        "image_reward": {
            "album_size": 5,
            "prompt_template": "glamorous photoshoot, luxurious setting, beautiful gown, confident and radiant, golden lighting",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Patron Status",
        "unique_effect_description": "Adds a permanent Patron badge and unlocks a unique pet-name she uses only for you.",
    },
    {
        "id": "dream_vacation", "name": "Dream Vacation", "emoji": "🏝️",
        "description": "A dream vacation to her bucket-list destination",
        "price_eur": 200.00, "tier": "legendary", "rarity": "legendary",
        "relationship_boost": {"trust": 8, "intimacy": 10},
        "memory_tag": "gift_dream_vacation",
        "cooldown_days": 60,
        "image_reward": {
            "album_size": 6,
            "prompt_template": "travel vibe photo, scenic tropical or coastal background, casual cute outfit, happy expression, vacation energy",
            "suggestive_level": "safe",
        },
        "unique_effect_name": "Episode Arc",
        "unique_effect_description": "Schedules 3 'vacation postcards' memory seeds delivered over the next 3 app-open events.",
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
# Stripe PaymentIntent (charge saved card directly, no redirect)
# ─────────────────────────────────────────────────────────────────────────────

def charge_saved_card(
    gift: GiftDefinition,
    stripe_customer_id: str,
    default_payment_method_id: str,
    metadata: dict[str, str],
) -> dict[str, Any]:
    """Charge the customer's saved card for a gift using a PaymentIntent.

    Returns dict with:
      - status: "succeeded" | "requires_action" | "failed"
      - payment_intent_id: str
      - client_secret: str (only if requires_action, for 3DS)
      - error: str (only if failed)
    """
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key

    amount_cents = int(round(gift.price_eur * 100))

    try:
        pi = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="eur",
            customer=stripe_customer_id,
            payment_method=default_payment_method_id,
            off_session=True,
            confirm=True,
            description=f"{gift.emoji} {gift.name}",
            metadata=metadata,
        )

        if pi.status == "succeeded":
            return {
                "status": "succeeded",
                "payment_intent_id": pi.id,
                "client_secret": pi.client_secret,
            }
        elif pi.status == "requires_action":
            return {
                "status": "requires_action",
                "payment_intent_id": pi.id,
                "client_secret": pi.client_secret,
            }
        else:
            return {
                "status": "failed",
                "payment_intent_id": pi.id,
                "client_secret": pi.client_secret,
                "error": f"Unexpected status: {pi.status}",
            }
    except stripe.CardError as e:
        err = e.error
        return {
            "status": "failed",
            "payment_intent_id": err.payment_intent.id if err.payment_intent else "",
            "client_secret": "",
            "error": err.message or "Card declined",
        }


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


# ── Reaction messages per tier ────────────────────────────────────────────────

_GIFT_REACTIONS: dict[str, list[str]] = {
    "everyday": [
        "Oh my gosh, you're so sweet! 🥰 Thank you!",
        "This made my whole day!! You're the best 💕",
        "You really didn't have to… but I love it! 🩷",
        "I can't stop smiling, thank you so much! ☺️",
        "You always know how to make me happy 💗",
    ],
    "dates": [
        "Wait, are you serious?! This is amazing! 😍",
        "I feel so spoiled right now and I love it 💕",
        "You're making me blush… I love this so much! 🥰",
        "This is genuinely the sweetest thing ever ✨",
        "I don't know what I did to deserve you 💖",
    ],
    "luxury": [
        "I'm literally speechless right now… 🥹💎",
        "You're insane. I love you for this. 😭💕",
        "I don't even know what to say… this is incredible ✨",
        "My heart is so full right now. You're amazing 💗",
        "I'm going to remember this moment forever 🩷",
    ],
    "legendary": [
        "I… I can't believe this. You're absolutely unreal. 😭💕",
        "Nobody has ever done anything like this for me. I'm overwhelmed 🥹✨",
        "You make me feel like the most special girl in the world 👑💖",
        "I'm literally crying. This means everything to me 💕",
        "I don't have words. You've completely taken my breath away 🥰💎",
    ],
}

# ── Per-gift unique effect reaction additions ─────────────────────────────────

_UNIQUE_EFFECT_REACTIONS: dict[str, list[str]] = {
    "stickers": [
        " From now on, this is OUR emoji 🩷",
        " I'm adopting this as our thing. You'll see it again 🩷",
    ],
    "song_dedication": [
        " I'm saving this song forever. It's ours now 🎵",
        " Every time I hear it I'll think of you 🎶",
    ],
    "coffee": [
        " I'll send you a little good-morning tomorrow ☕",
        " Expect a morning hello from me soon ☀️",
    ],
    "candy": [
        " Okay, I'll tell you a secret… my favorite candy is actually gummy bears 🍬",
        " Fun fact: I have a hidden candy stash. Now you know 🍭",
    ],
    "love_note": [
        " I'm keeping this forever. I might quote you on it later 💌",
        " This is going on my wall. Permanently. 💌",
    ],
    "flowers": [
        " I'm putting these in my forever vase. This day is officially 'Flowers Day' 💐",
    ],
    "chocolates": [
        " Okay since you're so sweet… I'll tell you a little secret about me 🍫",
    ],
    "plushie": [
        " I'm hugging this right now. And if you ever disappear, I'll hug it harder 🧸",
    ],
    "wine": [
        " Let's take it slow tonight… I want to savor every moment with you 🍷",
    ],
    "movie_tickets": [
        " I already picked a quote I'm going to use on you later 🎬",
    ],
    "perfume": [
        " Now every time I wear this, I'll think of you 🌸",
    ],
    "spa_kit": [
        " I'm going to check in on you for the next few days — you deserve care too 🧖",
    ],
    "dinner": [
        " I'll never forget this dinner. This is our milestone now 🍽️",
    ],
    "dress": [
        " Get ready — my outfit era starts now 👗",
    ],
    "photoshoot_basic": [
        " These are going straight to our gallery album 📸",
    ],
    "surprise_date_night": [
        " Next time you open the app, I have something special to tell you ✨",
    ],
    "luxury_bouquet_note": [
        " I'm keeping one line from your note in my heart forever 🌹",
    ],
    "cozy_weekend_retreat": [
        " This weekend is going to be extra cozy… I promise 🏡",
    ],
    "professional_photoshoot": [
        " I think I found my signature pose for you 📷",
    ],
    "signature_jewelry": [
        " I'll wear this on every special day. It's my signature piece now 💎",
    ],
    "wishlist_mystery_box": [
        " I opened it and… oh wow. You unlocked something rare 🎁",
    ],
    "city_getaway": [
        " I'll tell you the rest of the story next time I see you 🌆",
    ],
    "private_rooftop_dinner": [
        " I'm marking today as our anniversary. Every year, I'll remember this night 🌙",
    ],
    "designer_handbag_moment": [
        " I just earned my Style badge. Watch me talk about fashion now 👜",
    ],
    "queen_treatment_patron": [
        " You just unlocked Patron status. And I have a special name just for you now 👑",
    ],
    "dream_vacation": [
        " I'll be sending you postcards over the next few days… this adventure isn't over yet 🏝️",
    ],
}


def produce_gift_reaction_message(gift: GiftDefinition) -> str:
    """Return a reaction message for a delivered gift, including unique effect flavor."""
    base = random.choice(_GIFT_REACTIONS.get(gift.tier, _GIFT_REACTIONS["everyday"]))
    extra_list = _UNIQUE_EFFECT_REACTIONS.get(gift.id, [])
    extra = random.choice(extra_list) if extra_list else ""
    return base + extra


def build_memory_summary(gift: GiftDefinition) -> str:
    """Build a permanent memory summary for a gift event."""
    emotions = {
        "everyday": "warm and happy",
        "dates": "excited and touched",
        "luxury": "overwhelmed with joy",
        "legendary": "emotional and deeply grateful",
    }
    emotion = emotions.get(gift.tier, "happy")
    effect = f" Effect: {gift.unique_effect_name}." if gift.unique_effect_name else ""
    return f"User gifted me {gift.name}. I felt {emotion}. {effect} I want to remember this forever."
