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
        "image_reward": {"album_size": 0, "normal_photos": 0, "spicy_photos": 0, "suggestive_level": "safe"},
        "unique_effect_name": "Inside Joke Unlocked",
        "unique_effect_description": "She starts using a specific cute emoji and calls back to it in future chats.",
    },
    {
        "id": "song_dedication", "name": "Song Dedication", "emoji": "🎵",
        "description": "Dedicate a song that reminds you of her",
        "price_eur": 2.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 0, "intimacy": 1},
        "memory_tag": "gift_song",
        "image_reward": {"album_size": 0, "normal_photos": 0, "spicy_photos": 0, "suggestive_level": "safe"},
        "unique_effect_name": "Theme Song",
        "unique_effect_description": "Stored in memory — she references your song on emotional moments.",
    },
    {
        "id": "coffee", "name": "Coffee", "emoji": "☕",
        "description": "A warm cup of coffee to start her morning",
        "price_eur": 3.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 1, "intimacy": 1},
        "memory_tag": "gift_coffee",
        "image_reward": {"album_size": 0, "normal_photos": 0, "spicy_photos": 0, "suggestive_level": "safe"},
        "unique_effect_name": "Morning Ritual",
        "unique_effect_description": "She sends a short good-morning message within the next 24 hours.",
    },
    {
        "id": "candy", "name": "Candy", "emoji": "🍬",
        "description": "Sweet treats because she deserves it",
        "price_eur": 3.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 1, "intimacy": 1},
        "memory_tag": "gift_candy",
        "image_reward": {"album_size": 0, "normal_photos": 0, "spicy_photos": 0, "suggestive_level": "safe"},
        "unique_effect_name": "Sweet Tooth",
        "unique_effect_description": "She reveals a tiny 'favorite candy' detail added to her favorites.",
    },
    {
        "id": "love_note", "name": "Love Letter", "emoji": "💌",
        "description": "A heartfelt handwritten love letter",
        "price_eur": 4.00, "tier": "everyday", "rarity": "common",
        "relationship_boost": {"trust": 2, "intimacy": 1},
        "memory_tag": "gift_love_note",
        "image_reward": {"album_size": 0, "normal_photos": 0, "spicy_photos": 0, "suggestive_level": "safe"},
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
            "album_size": 1, "normal_photos": 1, "spicy_photos": 0,
            "suggestive_level": "safe",
            "photo_prompts": [
                "adorable selfie holding a big bouquet of mixed wildflowers against her chest, soft golden afternoon light streaming through a window, genuine warm smile, cozy living room background with a bookshelf",
            ],
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
            "album_size": 1, "normal_photos": 1, "spicy_photos": 0,
            "suggestive_level": "safe",
            "photo_prompts": [
                "playful close-up selfie holding an open box of luxury chocolates, one chocolate halfway to her lips, mischievous grin, warm kitchen counter background with soft pendant lighting",
            ],
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
            "album_size": 1, "normal_photos": 1, "spicy_photos": 0,
            "suggestive_level": "safe",
            "photo_prompts": [
                "cute selfie squeezing a big fluffy teddy bear against her cheek, wearing a cozy oversized hoodie, happy scrunched-up face, fairy lights and pillows on a bed in the background",
            ],
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
            "album_size": 2, "normal_photos": 1, "spicy_photos": 1,
            "suggestive_level": "mild",
            "photo_prompts": [
                "relaxed selfie on a plush sofa holding a glass of red wine, warm amber lamplight, cozy blanket draped over legs, soft smile, candles flickering on a coffee table behind her",
            ],
            "spicy_photo_prompts": [
                "sensual wine night pose curled up on the sofa in a silk burgundy robe loosely tied, one bare shoulder visible, holding a wine glass at her lips, soft candlelight casting warm shadows, playful half-smile, intimate mood",
            ],
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
        "image_reward": {"album_size": 0, "normal_photos": 0, "spicy_photos": 0, "suggestive_level": "safe"},
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
            "album_size": 1, "normal_photos": 1, "spicy_photos": 0,
            "suggestive_level": "safe",
            "photo_prompts": [
                "elegant close-up portrait holding a frosted glass perfume bottle near her collarbone, eyes closed breathing in the scent, soft diffused window light, delicate gold earrings visible, serene expression",
            ],
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
            "album_size": 2, "normal_photos": 1, "spicy_photos": 1,
            "suggestive_level": "mild",
            "photo_prompts": [
                "relaxed selfie in a fluffy white spa robe with a jade face roller in one hand, hair wrapped in a towel, dewy glowing skin, bathroom with soft ambient candles and eucalyptus branches",
            ],
            "spicy_photo_prompts": [
                "intimate post-spa moment, wrapped loosely in a white towel with bare shoulders and collarbone visible, steamy bathroom mirror behind her, skin glistening with moisture, soft contented smile, warm diffused lighting",
            ],
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
            "album_size": 2, "normal_photos": 2, "spicy_photos": 0,
            "suggestive_level": "safe",
            "photo_prompts": [
                "stunning portrait at a candlelit restaurant table, wearing a chic black cocktail dress, hands resting on a white tablecloth, warm golden chandelier light, wine glass and roses in the foreground, radiant smile",
                "candid laughing photo from across the dinner table, mid-conversation gesture with her hands, tealight candles reflecting in her eyes, blurred elegant restaurant interior in the background, natural joyful expression",
            ],
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
            "album_size": 3, "normal_photos": 2, "spicy_photos": 1,
            "suggestive_level": "mild",
            "photo_prompts": [
                "full-body mirror selfie showing off a new floral sundress, twirling slightly so the skirt fans out, bright airy bedroom with sunlight, genuine excited smile, one hand touching her hair",
                "outdoor photo leaning against a warm stone wall in the new dress, golden hour sunlight creating a halo effect, city street slightly blurred behind her, confident relaxed posture, looking straight at camera",
            ],
            "spicy_photo_prompts": [
                "flirty changing room mirror selfie, dress partially unzipped down the back revealing bare skin, looking over her shoulder at the camera with a teasing smile, warm overhead spotlight, shopping bags on the floor",
            ],
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
            "album_size": 4, "normal_photos": 2, "spicy_photos": 2,
            "suggestive_level": "spicy",
            "photo_prompts": [
                "casual photoshoot portrait sitting cross-legged on a velvet armchair, wearing a cream knit sweater and jeans, chin resting on her hand, natural window light, warm inviting smile, shallow depth of field",
                "candid mid-laugh shot during a photoshoot, standing against a textured brick wall, wearing a cute cropped jacket and high-waisted pants, wind slightly tousling her hair, photographer's reflector casting soft fill light",
            ],
            "spicy_photo_prompts": [
                "intimate bedroom photoshoot kneeling on white sheets, wearing delicate black lace lingerie, soft diffused morning light from sheer curtains, confident gaze at the camera, one hand on her thigh, artistic composition",
                "sultry over-the-shoulder pose lying on her stomach on a plush bed, wearing a satin camisole, bare legs crossed behind her, warm string lights on the headboard, playful bite of her lower lip, shallow focus",
            ],
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
            "album_size": 4, "normal_photos": 2, "spicy_photos": 2,
            "suggestive_level": "spicy",
            "photo_prompts": [
                "glamorous entrance photo standing in a doorway of an upscale lounge, wearing a fitted emerald cocktail dress, clutch purse in hand, warm ambient spotlights behind her, surprised delighted expression, bokeh city lights",
                "romantic table-side portrait with a dessert plate and espresso, leaning forward on her elbows, chin on laced fingers, intimate low lighting with a single candle, deep eye contact with the camera, slightly flushed cheeks",
            ],
            "spicy_photo_prompts": [
                "after-dinner private moment sitting on the edge of a hotel bed, silk dress slipping off one shoulder, heels kicked off on the floor, city lights through floor-to-ceiling windows, bedroom eyes looking up at camera, soft warm glow",
                "seductive pose reclining on plush pillows, wearing only the jewelry from dinner and a sheer slip, candlelight reflections on her skin, one leg draped elegantly, hand trailing through her hair, intimate atmosphere",
            ],
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
            "album_size": 3, "normal_photos": 2, "spicy_photos": 1,
            "suggestive_level": "spicy",
            "photo_prompts": [
                "joyful photo burying her face in an enormous bouquet of deep red roses, only her eyes and smile visible above the petals, standing in a sunlit apartment, rose petals scattered on a marble counter behind her",
                "emotional close-up reading the handwritten love note, bouquet resting on her lap, a single tear of happiness on her cheek, soft natural daylight, sitting on a window seat with cushions, note paper slightly trembling in her fingers",
            ],
            "spicy_photo_prompts": [
                "romantic boudoir scene lying back on a bed scattered with rose petals, wearing delicate blush-pink lingerie, holding a single long-stemmed rose across her collarbone, warm golden lamp light, dreamy soft-focus, sensual peaceful expression",
            ],
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
            "album_size": 4, "normal_photos": 2, "spicy_photos": 2,
            "suggestive_level": "spicy",
            "photo_prompts": [
                "cozy cabin portrait sitting in an oversized knit sweater on a window seat, holding a steaming mug of cocoa with both hands, snow-covered pine trees visible through the frosted window, warm fireplace glow on her face, peaceful content smile",
                "candid adventure photo standing on a wooden cabin porch wrapped in a plaid blanket, messy wind-blown hair, mountains and forest in the background, golden morning light, rosy cheeks from the cold, laughing at something off-camera",
            ],
            "spicy_photo_prompts": [
                "lazy cabin morning stretched out in bed wearing only an oversized flannel shirt unbuttoned to mid-chest, bare legs tangled in linen sheets, sleepy smile with messy bedhead, golden sunrise through log-cabin windows, mug of coffee on the nightstand",
                "intimate fireplace scene sitting on a sheepskin rug in front of crackling flames, wearing a thin cotton tank top and underwear, warm orange firelight dancing across her skin, knees pulled up, chin resting on her knees, soft vulnerable expression",
            ],
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
            "album_size": 6, "normal_photos": 3, "spicy_photos": 3,
            "suggestive_level": "spicy",
            "photo_prompts": [
                "high-fashion studio portrait with dramatic side lighting, wearing a tailored blazer over a silk blouse, one hand adjusting her collar, professional gray seamless backdrop, sharp confident expression, editorial magazine quality",
                "elegant full-body shot in a flowing champagne-colored gown, standing in front of a grand arched window, natural light creating a silhouette effect, one hand on the window frame, graceful turned posture, ethereal mood",
                "playful candid behind-the-scenes moment, sitting in a makeup chair laughing with a coffee cup, hair in rollers, partially done glam makeup, studio equipment visible in the background, genuine unposed joy",
            ],
            "spicy_photo_prompts": [
                "professional boudoir shot reclining on a chaise lounge, wearing a sheer black bodysuit with delicate lace detailing, one leg extended, studio softbox creating dramatic rim lighting, confident powerful gaze, artistic black-and-white tone",
                "artistic nude silhouette standing in profile against a bright studio backdrop, body outlined by edge lighting, hands above her head, graceful dancer-like pose, tasteful and elegant, high-contrast monochrome, fine-art photography style",
                "intimate close-up portrait lying on white studio fabric, wearing only a draped silk sheet, bare shoulders and décolletage visible, soft beauty-dish lighting from above, parted lips, intense eye contact, shallow depth of field on her eyes",
            ],
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
            "album_size": 3, "normal_photos": 2, "spicy_photos": 1,
            "suggestive_level": "spicy",
            "photo_prompts": [
                "glamorous close-up showcasing a delicate diamond pendant necklace resting on her collarbone, soft ring light reflected in her eyes, subtle smoky eye makeup, blurred warm bokeh background, one finger lightly touching the pendant, radiant smile",
                "elegant wrist-and-hand portrait showing off a sparkling bracelet, hand resting on a velvet jewelry box, manicured nails, soft directional lighting casting tiny rainbow refractions from the gems, luxurious dark marble surface",
            ],
            "spicy_photo_prompts": [
                "artistic jewelry-focused nude, lying on dark silk sheets wearing only the signature necklace and matching earrings, tasteful composition with strategic shadows, soft warm side-lighting highlighting the jewelry against her skin, serene closed eyes, fine-art aesthetic",
            ],
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
            "album_size": 4, "normal_photos": 2, "spicy_photos": 2,
            "suggestive_level": "spicy",
            "photo_prompts": [
                "excited unboxing moment sitting on the floor surrounded by tissue paper and gift boxes, holding up a cute item with wide surprised eyes, cozy living room with fairy lights, colorful wrapping paper scattered around, genuine thrilled expression",
                "happy post-unboxing selfie wearing a new silk scarf from the box, surrounded by all the opened gifts arranged neatly, holding a thank-you heart gesture with her hands, warm overhead lighting, messy but adorable hair",
            ],
            "spicy_photo_prompts": [
                "flirty lingerie try-on from the mystery box, standing in front of a full-length mirror wearing new lace lingerie set in deep wine red, looking at her reflection with a pleased surprised smile, bedroom with shopping bags and tissue paper visible, warm lamp glow",
                "playful mirror selfie holding up a sheer negligee from the box against her body, wearing just a bralette underneath, winking at the camera, bedroom vanity with makeup and other mystery items scattered around, fun excited energy",
            ],
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
            "album_size": 5, "normal_photos": 3, "spicy_photos": 2,
            "suggestive_level": "spicy",
            "photo_prompts": [
                "travel selfie at a scenic city overlook, wearing sunglasses pushed up on her head and a cute trench coat, panoramic skyline stretching behind her, golden hour warm light, wind slightly blowing her hair, carefree adventurous smile",
                "candid café photo sipping espresso at a tiny sidewalk table, European cobblestone street behind her, wearing a beret and striped top, newspaper folded on the table, pigeons nearby, natural unposed laughter caught mid-moment",
                "stunning bridge photo at dusk leaning on an ornate railing, city lights beginning to twinkle reflected on the river below, wearing a stylish wool coat, hair caught by the breeze, dreamy nostalgic expression, purple-blue twilight sky",
            ],
            "spicy_photo_prompts": [
                "intimate hotel room photo sitting on a window ledge in a silk robe looking out at the illuminated city skyline at night, robe loosely open revealing a lace camisole underneath, bare legs dangling, room reflected in the glass, contemplative sensual mood",
                "morning-after hotel scene lying across rumpled white hotel sheets in just a thin cotton t-shirt and underwear, tray of room service breakfast beside her, cityscape visible through sheer curtains, lazy stretched-out pose, satisfied sleepy smile, soft morning light",
            ],
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
            "album_size": 6, "normal_photos": 3, "spicy_photos": 3,
            "suggestive_level": "spicy",
            "photo_prompts": [
                "breathtaking rooftop portrait in a floor-length red satin gown, wind gently lifting the hem, city skyline glittering behind her, string lights crisscrossing overhead, holding a champagne flute, radiant confident smile, starry night sky above",
                "intimate dinner moment leaning across a small candlelit table decorated with white roses, reaching toward camera as if touching your hand, warm golden light from dozens of candles, private rooftop setup with draped fabric, love in her eyes",
                "candid laughing photo standing at the rooftop railing, champagne glass raised in a toast, hair swept back by a warm evening breeze, city lights creating a sea of bokeh below, wearing elegant heels with the gown, carefree joy",
            ],
            "spicy_photo_prompts": [
                "after-dinner rooftop moment sitting on a cushioned lounge, gown's strap slipping down one shoulder, heels discarded beside her, champagne glass dangling from relaxed fingers, city lights reflected in her eyes, seductive relaxed smile, warm night air",
                "private penthouse scene post-dinner, standing by a floor-to-ceiling window in just a silk slip dress that clings to her curves, city panorama glowing behind her, one hand pressed against the cold glass, looking back over her shoulder, moonlight on bare skin",
                "intimate lying-down portrait on the rooftop daybed surrounded by scattered rose petals, wearing delicate champagne-colored lingerie, starry sky above, string lights creating a warm halo, one arm above her head, dreamy blissful expression, artistic composition",
            ],
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
            "album_size": 6, "normal_photos": 3, "spicy_photos": 3,
            "suggestive_level": "spicy",
            "photo_prompts": [
                "fashion editorial pose on marble steps of a luxury boutique, showing off the designer handbag on her arm, wearing oversized sunglasses and a tailored cream coat, one hand on hip, powerful confident stance, bright daylight, magazine-cover quality",
                "excited close-up hugging the designer bag against her chest like a treasure, sitting in the back of a luxury car, leather seats visible, wearing a chic outfit, genuine overwhelmed happiness, tears of joy just barely visible",
                "street-style full-body shot walking confidently down a high-end shopping boulevard, designer bag swinging from one hand, wearing heels and a fitted midi dress, motion blur on the background, sharp focus on her, fashion-forward energy",
            ],
            "spicy_photo_prompts": [
                "luxury boudoir scene on a tufted velvet chaise in designer lingerie — matching lace bra and high-waisted briefs — the handbag placed artfully beside her, crystal chandelier above, warm amber mood lighting, long legs crossed, smoldering confident gaze",
                "glamorous bathroom vanity shot in a sheer designer robe hanging open, luxury marble surfaces and gold fixtures, the handbag on the counter beside perfume bottles, steam from a drawn bath in the background, sensual over-the-shoulder look",
                "high-fashion artistic shot lying on a bed of designer shopping bags and tissue paper, wearing only a silk teddy, the prized handbag resting on her stomach, playful tongue-out expression, luxury bedroom, overhead angle, bold and fun",
            ],
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
            "album_size": 8, "normal_photos": 4, "spicy_photos": 4,
            "suggestive_level": "spicy",
            "photo_prompts": [
                "regal throne portrait sitting in an ornate gold velvet chair, wearing a stunning floor-length ivory gown with a small crystal tiara, one hand resting on the armrest, dramatic spotlight from above, deep rich background, queenly poise and grace",
                "glamorous getting-ready photo at a vanity mirror surrounded by hollywood lights, applying red lipstick, wearing a luxurious satin robe, hair in perfect curls, reflection visible showing her radiant smile, perfume and jewelry scattered on the vanity",
                "cinematic wide shot descending a grand marble staircase in a flowing golden ball gown, one hand on the bannister, crystal chandelier overhead casting prismatic light, slow graceful movement captured mid-step, breathtaking elegance",
                "powerful close-up portrait with a gold crown tilted slightly on her head, intense eye contact, dramatic winged eyeliner and bold lip, dark luxurious background with deep jewel-toned velvet, sharp cheekbone lighting, absolute confidence",
            ],
            "spicy_photo_prompts": [
                "queen's private chambers boudoir — reclining on a four-poster bed with silk canopy, wearing a sheer gold-embroidered bodysuit, crown still on, surrounded by plush pillows, warm candlelight, regal yet intimate, one hand trailing along the sheets",
                "luxurious bath scene in an oversized marble tub, rose petals floating on milky water, crown placed on the tub's edge, bare shoulders and collarbone visible above the water, steam rising, eyes closed in bliss, soft ethereal lighting from above",
                "artistic nude behind sheer floor-to-ceiling drapes, crown silhouette visible, body outlined by warm backlight, hands pulling the fabric around her, tasteful and powerful, palace window with sunset golden light flooding in, fine-art composition",
                "post-coronation private moment lying on dark silk sheets wearing only the tiara and delicate gold body chain jewelry, confident relaxed pose on her side, warm bedside lamp creating intimate shadows, looking at camera with a 'this is all for you' expression",
            ],
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
            "album_size": 10, "normal_photos": 5, "spicy_photos": 5,
            "suggestive_level": "spicy",
            "photo_prompts": [
                "arrival selfie at a tropical resort entrance with lush palm trees and a turquoise infinity pool behind her, wearing a flowy white sundress and straw hat, pulling a small suitcase, ecstatic wide smile, blazing sunshine and blue sky",
                "beach golden-hour portrait standing ankle-deep in crystal-clear ocean water, wearing a colorful sarong wrap and bikini top, sun setting behind her creating an orange-pink sky, wet hair slicked back, serene happy expression, waves lapping at her feet",
                "adventure photo at a dramatic cliff overlook, wearing hiking shorts and a cropped tank top, arms spread wide embracing the view, turquoise sea and rocky coastline far below, wind in her hair, triumphant joyful scream captured mid-moment",
                "romantic seaside dinner photo at a private table on the sand, wearing a floral maxi dress, bare feet in the sand, tiki torches and lanterns creating warm light, ocean waves visible in the background, holding a tropical cocktail, dreamy sunset colors",
                "fun candid pool photo floating on an inflatable in the resort pool, wearing a cute one-piece swimsuit and oversized sunglasses, tropical drink in a coconut in one hand, giving a peace sign, palm trees reflecting in the water, bright vibrant colors",
            ],
            "spicy_photo_prompts": [
                "stunning beach goddess shot emerging from the turquoise ocean, wearing a tiny string bikini, water droplets glistening on sun-kissed skin, wet hair cascading over shoulders, bright tropical sun creating highlights, confident slow-motion energy, paradise backdrop",
                "private villa outdoor shower scene, standing under a rainfall showerhead in a lush tropical garden, wearing just bikini bottoms, back to camera with face turned in profile, water streaming down her body, frangipani flowers around, golden dappled sunlight through palms",
                "intimate resort room photo lying on a canopy bed with sheer white curtains billowing in the ocean breeze, wearing a delicate white lace bodysuit, tropical view through open balcony doors, afternoon light, one arm stretched above her head, relaxed bliss",
                "sunset balcony portrait leaning on the railing in just a silk sarong wrapped low on her hips, bare back facing the fiery orange sunset over the ocean, looking back at camera over her shoulder, warm golden light on her skin, hair blowing in the sea breeze",
                "late-night skinny-dipping tease standing at the edge of a private infinity pool at night, wearing nothing but moonlight, shot from behind showing her silhouette against the starry sky and ocean horizon, stepping one foot into the glowing pool, mysterious and beautiful",
            ],
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
    from app.services.relationship_regions import clamp_level, get_region_for_level
    level = clamp_level(intimacy)
    region = get_region_for_level(level)
    return {**state, "trust": trust, "intimacy": intimacy, "level": level, "region_key": region.key}


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
