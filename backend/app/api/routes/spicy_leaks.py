"""Spicy Leaks: independent collectible photo collection with slot machine spin.

Completely independent of intimacy progression and achievements.
50 collectible leaked photos that users unlock by spinning slots.
"""
import hashlib
import logging
import uuid
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import get_settings
from app.api.store import (
    get_session_user,
    set_session_user,
    get_spicy_leaks_unlocked,
    mark_spicy_leak_unlocked,
    add_gallery_item,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spicy-leaks", tags=["spicy-leaks"])

SESSION_COOKIE = "session"


# ═══════════════════════════════════════════════════════════════════════════════
# LEAKED PHOTO CATALOG — 50 collectible photos, flat (no tier gating)
# ═══════════════════════════════════════════════════════════════════════════════

RARITY_NAMES = ["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"]


class LeakedPhoto:
    def __init__(self, id: str, title: str, subtitle: str, rarity: str,
                 icon: str, scene: str):
        self.id = id
        self.title = title
        self.subtitle = subtitle
        self.rarity = rarity
        self.icon = icon
        self.scene = scene  # image generation prompt


LEAKED_PHOTOS_LIST: list[LeakedPhoto] = [
    # ── COMMON (12) — Dirty selfies, teasing flashes, "accidental" nip slips ─
    LeakedPhoto("lp_nip_slip", "Nip Slip", "Oops… that top is way too loose.", "COMMON", "🤭",
                "Woman leaning forward in a loose tank top, nipple clearly visible slipping out, surprised expression, kitchen counter, warm light"),
    LeakedPhoto("lp_ass_selfie", "Ass Selfie", "She couldn't resist showing it off.", "COMMON", "🍑",
                "Woman in a thong taking an over-the-shoulder mirror selfie of her bare ass, bedroom mirror, biting her lip"),
    LeakedPhoto("lp_braless_jog", "Braless Jog", "You can see everything bouncing.", "COMMON", "🏃‍♀️",
                "Woman jogging braless in thin white tank top, nipples poking through fabric, sweaty skin, park setting, candid angle"),
    LeakedPhoto("lp_upskirt_tease", "Upskirt Tease", "She 'forgot' to cross her legs.", "COMMON", "👀",
                "Woman sitting on bar stool in short skirt, legs slightly parted, panties visible, looking at camera with sly grin, bar lighting"),
    LeakedPhoto("lp_wet_bikini", "Wet Bikini", "That bikini hides absolutely nothing wet.", "COMMON", "👙",
                "Woman stepping out of pool in white bikini gone completely see-through, nipples and everything visible, sun-drenched"),
    LeakedPhoto("lp_changing_caught", "Caught Changing", "Door was open the whole time.", "COMMON", "🚪",
                "Woman mid-undress caught through open bedroom door, bra unhooked dangling, panties halfway down, startled look"),
    LeakedPhoto("lp_cleavage_snap", "Deep Cleavage Snap", "She knows exactly what she's doing.", "COMMON", "📸",
                "Extreme close-up selfie of massive cleavage in push-up bra, tongue out, phone held high, bathroom mirror"),
    LeakedPhoto("lp_booty_shorts", "Booty Shorts", "Those shorts are criminal.", "COMMON", "🩳",
                "Woman bending over in tiny booty shorts, ass cheeks hanging out, picking something off floor, tight crop top, kitchen"),
    LeakedPhoto("lp_shower_peek", "Shower Peek", "The curtain was wide open.", "COMMON", "🚿",
                "Woman in shower with curtain pulled aside, wet body on display, steam rising, one hand running through hair, side view"),
    LeakedPhoto("lp_bed_spread", "Morning Spread", "Woke up like this… and stayed.", "COMMON", "🛏️",
                "Woman sprawled on bed in just a tiny thong, face down, legs slightly apart, morning sunlight on bare back and ass"),
    LeakedPhoto("lp_mirror_lift", "Shirt Lift", "Just checking… with the camera on.", "COMMON", "🤳",
                "Woman lifting shirt to flash bare tits in bathroom mirror selfie, playful smirk, phone in other hand, bright lighting"),
    LeakedPhoto("lp_skinny_dip_snap", "Skinny Dip Snap", "No suit required.", "COMMON", "🏊",
                "Woman wading into pool completely naked at night, ass and bare back visible, looking back at camera, pool lights glowing"),

    # ── UNCOMMON (10) — Stripping, lingerie, panty peels, teasing nudes ──────
    LeakedPhoto("lp_panty_peel", "Panty Peel", "Sliding them down, nice and slow.", "UNCOMMON", "🩲",
                "Woman pulling panties down over her hips with thumbs hooked in waistband, looking down, bare stomach, bedroom, dim lamp"),
    LeakedPhoto("lp_bra_dangle", "Bra Dangle", "It just came off.", "UNCOMMON", "👙",
                "Woman holding unhooked bra dangling from one finger, bare chest with arm barely covering nipples, bedroom, smirking"),
    LeakedPhoto("lp_gstring_bend", "G-String Bend", "The view from behind.", "UNCOMMON", "🍑",
                "Woman bent over in nothing but a g-string, ass up toward camera, looking back between her legs, bedroom floor, low angle"),
    LeakedPhoto("lp_titty_squeeze", "Titty Squeeze", "She couldn't keep her hands off herself.", "UNCOMMON", "🤲",
                "Woman squeezing her bare tits together with both hands, head tilted back, eyes closed, biting lip, dark background"),
    LeakedPhoto("lp_strip_sequence", "Strip Tease", "She sent all four photos.", "UNCOMMON", "📱",
                "Collage-style four photos showing woman progressively stripping from dress to fully nude, bedroom, each frame more explicit"),
    LeakedPhoto("lp_garter_spread", "Garter Spread", "Thigh highs and nothing else.", "UNCOMMON", "🦵",
                "Woman on bed in only garter belt and thigh-high stockings, legs spread open, hands on inner thighs, seductive stare, red light"),
    LeakedPhoto("lp_wet_tshirt_nips", "Soaked Through", "Might as well be naked.", "UNCOMMON", "🌧️",
                "Woman in soaking wet white t-shirt clinging to every curve, nipples fully visible through fabric, no bra, outdoor rain"),
    LeakedPhoto("lp_topless_cook", "Topless Cooking", "Breakfast with a view.", "UNCOMMON", "🍳",
                "Woman cooking at stove completely topless, wearing only tiny panties, bare tits visible from side, morning light, spatula in hand"),
    LeakedPhoto("lp_mirror_spread", "Mirror Flash", "Full frontal in the hotel mirror.", "UNCOMMON", "🪞",
                "Woman standing nude in front of full-length hotel mirror, one hand on hip, everything on display, moody hotel room lighting"),
    LeakedPhoto("lp_lap_grind", "Lap Grind", "Riding that chair like she means it.", "UNCOMMON", "💺",
                "Woman straddling a chair in just a thong, grinding motion, arched back, tits out, dim lighting, hair tossed back, filming herself"),

    # ── RARE (10) — Fully nude, explicit poses, self-pleasure, spread shots ──
    LeakedPhoto("lp_legs_wide", "Legs Wide Open", "She's showing you everything.", "RARE", "🦋",
                "Woman lying on bed with legs spread wide open toward camera, completely nude, hands on inner thighs pulling apart, direct eye contact"),
    LeakedPhoto("lp_finger_tease", "Touching Herself", "Her hand wandered south.", "RARE", "🤤",
                "Woman lying back on bed, one hand between her legs, eyes closed in pleasure, mouth open, nude, soft warm lighting"),
    LeakedPhoto("lp_all_fours", "On All Fours", "Presenting from behind.", "RARE", "🐾",
                "Woman on hands and knees on bed, ass raised high toward camera, looking back over shoulder, completely nude, arch in back"),
    LeakedPhoto("lp_shower_spread", "Shower Spread", "She opened up under the water.", "RARE", "💦",
                "Woman in shower, one leg up on tile wall, spreading herself open, water cascading down body, steam, glass door, direct angle"),
    LeakedPhoto("lp_nude_squat", "Deep Squat", "Everything on display from below.", "RARE", "🏋️",
                "Woman in deep squat position fully nude, low angle looking up between spread thighs, gym mat, confident expression"),
    LeakedPhoto("lp_tit_grab_nude", "Full Grab", "Handful in each hand.", "RARE", "🫳",
                "Woman standing nude squeezing both tits hard, pinching nipples, head thrown back moaning, dark bedroom, dramatic lighting"),
    LeakedPhoto("lp_ass_spread", "Bent & Spread", "She's pulling herself apart for you.", "RARE", "🍑",
                "Woman bent over grabbing and spreading her own ass cheeks with both hands, looking back at camera, nude, bedroom"),
    LeakedPhoto("lp_bathtub_open", "Bath Spread", "Nothing hidden under the water.", "RARE", "🛁",
                "Woman in clear bath water with legs open and spread against tub walls, fully visible beneath water, candles, looking at camera"),
    LeakedPhoto("lp_tongue_drip", "Tongue Out", "Drooling with anticipation.", "RARE", "👅",
                "Woman on knees, nude, tongue out dripping saliva, looking up at her own phone camera with desperate needy eyes, selfie angle, dim light"),
    LeakedPhoto("lp_dildo_tease", "Toy Tease", "Look what she got in the mail.", "RARE", "📦",
                "Woman holding a toy suggestively near her lips, nude on bed, other hand between legs, unboxing scene, playful expression"),

    # ── EPIC (10) — Hardcore explicit, toys inside, submission, filthy poses ──
    LeakedPhoto("lp_toy_deep", "Deep Inside", "She pushed it all the way in.", "EPIC", "🔥",
                "Woman lying back on bed using toy between spread legs, back arched off mattress, mouth wide open in ecstasy, close-up angle"),
    LeakedPhoto("lp_face_down_ass_up", "Face Down Ass Up", "Her favorite position, caught on camera.", "EPIC", "⬇️",
                "Woman face-down on bed with ass raised high, completely nude, face pressed into pillow, hands gripping sheets, rear angle"),
    LeakedPhoto("lp_riding_toy", "Riding It", "Bouncing like her life depends on it.", "EPIC", "🤠",
                "Woman straddling and riding a toy mounted on bed, head thrown back, tits bouncing, sweat on skin, action shot, bedroom"),
    LeakedPhoto("lp_collar_crawl", "Collar & Crawl", "She put the collar on herself.", "EPIC", "⛓️",
                "Woman on all fours wearing self-fastened collar with dangling leash, tits hanging, staring into phone propped on floor, solo selfie, dark room"),
    LeakedPhoto("lp_oil_drench", "Oil Drenched", "Every inch of her is glistening.", "EPIC", "💧",
                "Woman standing nude drenched in baby oil, entire body glistening, oil dripping off tits and ass, hands running over curves, dark backdrop"),
    LeakedPhoto("lp_tied_spread", "Tied Open", "She tied herself up and hit record.", "EPIC", "🪢",
                "Woman self-restrained spread-eagle on bed with velcro cuffs she fastened herself, completely nude and exposed, phone on tripod recording, red satin sheets"),
    LeakedPhoto("lp_double_handful", "Double Handful", "Squeezing everything she's got.", "EPIC", "🫴",
                "Woman on knees grabbing one tit and reaching between legs simultaneously, face contorted in pleasure, nude, mirror behind showing rear"),
    LeakedPhoto("lp_whip_marks", "Whip Marks", "She did this to herself and loved it.", "EPIC", "🏇",
                "Woman bent over showing self-inflicted red marks on bare ass, riding crop in her own hand, looking back at camera with satisfied grin, dim red lighting"),
    LeakedPhoto("lp_dripping_wet", "Dripping Wet", "She's absolutely soaking.", "EPIC", "💦",
                "Extreme close-up of woman's inner thighs glistening with arousal, fingers spreading wetness, nude body in background soft focus"),
    LeakedPhoto("lp_mirror_masturbate", "Mirror Show", "She watched herself the whole time.", "EPIC", "🪞",
                "Woman sitting spread-legged in front of full-length mirror, one hand between legs, watching her own reflection, nude, mascara smudged, panting"),

    # ── LEGENDARY (8) — The filthiest, most depraved leaked photos ───────────
    LeakedPhoto("lp_marathon_finish", "Marathon Finish", "Her vibrator's been buzzing for hours.", "LEGENDARY", "🎉",
                "Woman lying on bed soaked in sweat, hair a mess, satisfied exhausted grin, vibrator still buzzing between legs, destroyed sheets, body trembling"),
    LeakedPhoto("lp_full_anal", "Backdoor Entry", "She took it in the ass and loved every second.", "LEGENDARY", "🔥",
                "Woman bent over bed gripping sheets, ass in air with toy inserted from behind, face showing pure ecstasy, rear close-up angle"),
    LeakedPhoto("lp_squirt_mess", "The Flood", "She soaked the entire bed.", "LEGENDARY", "💦",
                "Woman lying back on drenched sheets, thighs glistening, body trembling from squirting orgasm, face in pure bliss, wet stain spreading beneath her"),
    LeakedPhoto("lp_double_stuff", "Double Stuffed", "Both holes, same time.", "LEGENDARY", "🤯",
                "Woman using two toys simultaneously, one in each hole, lying on back with legs pulled to chest, extreme pleasure face"),
    LeakedPhoto("lp_public_flash", "Public Flash", "Naked in the parking lot and loving it.", "LEGENDARY", "🏙️",
                "Woman fully nude in a parking garage, leaning against car, legs spread, touching herself, security camera angle, night"),
    LeakedPhoto("lp_self_choke", "Self-Choke", "One hand on her throat, the other between her legs.", "LEGENDARY", "🤐",
                "Woman lying on back choking herself with one hand, other hand between spread legs, nude, back arched, eyes rolling back in ecstasy"),
    LeakedPhoto("lp_slave_pose", "Total Submission", "She collared and cuffed herself, waiting for you.", "LEGENDARY", "👑",
                "Woman kneeling solo, self-fastened collar and leash, wrists cuffed behind her own back, nude, head bowed, phone on timer capturing everything"),
    LeakedPhoto("lp_destroyed", "Completely Ruined", "She wrecked herself and loved every second.", "LEGENDARY", "💀",
                "Woman lying face-down on destroyed bed, toys scattered around her, body trembling and glistening with sweat, utterly spent but smiling blissfully"),
]

LEAKED_PHOTOS: dict[str, LeakedPhoto] = {p.id: p for p in LEAKED_PHOTOS_LIST}
TOTAL_LEAKED_PHOTOS = len(LEAKED_PHOTOS_LIST)

# Box definitions for the slot machine — progressively naughtier
LEAK_BOXES: dict[str, dict] = {
    "tease": {
        "id": "tease",
        "name": "Naughty Tease",
        "emoji": "🍑",
        "price_eur": 4.99,
        "free_on_plan": "plus",
        "description": "Teasing selfies, towel drops, and accidental flashes.",
        "weights": {"COMMON": 0.50, "UNCOMMON": 0.30, "RARE": 0.13, "EPIC": 0.05, "LEGENDARY": 0.02},
    },
    "explicit": {
        "id": "explicit",
        "name": "Explicit Stash",
        "emoji": "🔞",
        "price_eur": 8.49,
        "free_on_plan": "premium",
        "description": "Full nudes, provocative angles, and private photos she never meant to share.",
        "weights": {"COMMON": 0.0, "UNCOMMON": 0.25, "RARE": 0.40, "EPIC": 0.28, "LEGENDARY": 0.07},
    },
    "forbidden": {
        "id": "forbidden",
        "name": "Forbidden Vault",
        "emoji": "🔐",
        "price_eur": 13.99,
        "free_on_plan": "premium",
        "description": "Her most private, dirtiest photos — the ones she swore nobody would ever see.",
        "weights": {"COMMON": 0.0, "UNCOMMON": 0.0, "RARE": 0.15, "EPIC": 0.45, "LEGENDARY": 0.40},
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _session_id(request: Request) -> str | None:
    return (
        request.cookies.get("session")
        or request.cookies.get("session_id")
        or request.headers.get("x-session-id")
        or None
    )


def _require_user(request: Request) -> tuple[str, dict]:
    sid = _session_id(request)
    if not sid:
        raise HTTPException(status_code=401, detail="unauthorized")
    user = get_session_user(sid)
    if not user:
        raise HTTPException(status_code=401, detail="unauthorized")
    return sid, user


def _get_default_pm(user: dict, sid: str) -> tuple[str, str]:
    settings = get_settings()
    if not settings.stripe_secret_key:
        return "", ""

    stripe.api_key = settings.stripe_secret_key

    stripe_customer_id = user.get("stripe_customer_id")
    if not stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.get("email", ""),
            metadata={"user_id": user.get("id", "")},
        )
        stripe_customer_id = customer.id
        set_session_user(sid, {**user, "stripe_customer_id": stripe_customer_id})

    default_pm = user.get("default_payment_method_id")
    if not default_pm:
        pms = stripe.Customer.list_payment_methods(stripe_customer_id, type="card", limit=1)
        if pms.data:
            default_pm = pms.data[0].id
            set_session_user(sid, {**user, "default_payment_method_id": default_pm})

    return stripe_customer_id, default_pm or ""


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/spicy-leaks/collection — full catalog with unlock status
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/collection")
def get_collection(request: Request, girlfriend_id: str | None = None):
    """Return the full 50-photo leaked collection with unlock status per girlfriend."""
    sid = _session_id(request)
    user = get_session_user(sid) if sid else None

    unlocked_map: dict[str, str] = {}
    if sid and user:
        if not girlfriend_id:
            girlfriend_id = (user or {}).get("current_girlfriend_id")
        if girlfriend_id:
            unlocked_map = get_spicy_leaks_unlocked(sid, girlfriend_id=girlfriend_id)

    photos = []
    for p in LEAKED_PHOTOS_LIST:
        is_unlocked = p.id in unlocked_map
        image_url = None
        if is_unlocked and girlfriend_id:
            seed = hashlib.md5(f"{girlfriend_id}:{p.id}".encode()).hexdigest()[:10]
            image_url = f"https://picsum.photos/seed/{seed}/400/400"

        photos.append({
            "id": p.id,
            "title": p.title,
            "subtitle": p.subtitle,
            "rarity": p.rarity,
            "icon": p.icon,
            "unlocked": is_unlocked,
            "unlocked_at": unlocked_map.get(p.id),
            "image_url": image_url,
        })

    total_unlocked = len(unlocked_map)
    return {
        "photos": photos,
        "total": TOTAL_LEAKED_PHOTOS,
        "unlocked": total_unlocked,
        "boxes": [
            {
                "id": b["id"],
                "name": b["name"],
                "emoji": b["emoji"],
                "price_eur": b["price_eur"],
                "description": b["description"],
                "weights": b["weights"],
            }
            for b in LEAK_BOXES.values()
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/spicy-leaks/spin — spin the slot machine to unlock a leaked photo
# ═══════════════════════════════════════════════════════════════════════════════

class SpinRequest(BaseModel):
    box_id: str
    photo_id: str  # frontend picks the winner (weighted random) and sends it
    girlfriend_id: str | None = None


@router.post("/spin")
def spin_leak(request: Request, body: SpinRequest):
    """Charge the user's card, then unlock the leaked photo.

    Returns:
      - status: "succeeded" | "requires_action" | "no_card" | "free"
      - Photo unlock data
    """
    sid, user = _require_user(request)

    box = LEAK_BOXES.get(body.box_id)
    if not box:
        raise HTTPException(status_code=400, detail="Invalid box_id")

    girlfriend_id = body.girlfriend_id or user.get("current_girlfriend_id")
    if not girlfriend_id:
        raise HTTPException(status_code=400, detail="no_girlfriend")

    # Validate photo exists
    photo = LEAKED_PHOTOS.get(body.photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="photo_not_found")

    # Check not already unlocked
    unlocked = get_spicy_leaks_unlocked(sid, girlfriend_id=girlfriend_id)
    if body.photo_id in unlocked:
        seed = hashlib.md5(f"{girlfriend_id}:{photo.id}".encode()).hexdigest()[:10]
        image_url = f"https://picsum.photos/seed/{seed}/400/400"
        return {
            "status": "free",
            "ok": True,
            "already_unlocked": True,
            "photo_id": photo.id,
            "title": photo.title,
            "subtitle": photo.subtitle,
            "rarity": photo.rarity,
            "icon": photo.icon,
            "image_url": image_url,
        }

    # Check if box is free on user's plan
    plan = user.get("plan", "free")
    plan_order = {"free": 0, "plus": 1, "premium": 2}
    free_on = box.get("free_on_plan", "")
    is_free = plan_order.get(plan, 0) >= plan_order.get(free_on, 99)

    payment_status = "free" if is_free else "pending"
    client_secret = None

    if not is_free:
        stripe_customer_id, default_pm = _get_default_pm(user, sid)

        if not stripe_customer_id or not default_pm:
            settings = get_settings()
            if not settings.stripe_secret_key:
                logger.info("DEV MODE: Leaked photo delivered free (no Stripe)")
                payment_status = "free"
            else:
                return {
                    "status": "no_card",
                    "error": "No card on file. Please add a card first.",
                }
        else:
            amount_cents = int(round(box["price_eur"] * 100))
            try:
                pi = stripe.PaymentIntent.create(
                    amount=amount_cents,
                    currency="eur",
                    customer=stripe_customer_id,
                    payment_method=default_pm,
                    off_session=True,
                    confirm=True,
                    description=f"Leaked Photo: {box['name']}",
                    metadata={
                        "type": "spicy_leak",
                        "box_id": body.box_id,
                        "photo_id": body.photo_id,
                        "user_id": user.get("id", ""),
                        "girlfriend_id": girlfriend_id,
                        "session_id": sid,
                    },
                )

                if pi.status == "succeeded":
                    payment_status = "succeeded"
                elif pi.status == "requires_action":
                    return {
                        "status": "requires_action",
                        "client_secret": pi.client_secret,
                        "payment_intent_id": pi.id,
                    }
                else:
                    raise HTTPException(status_code=402, detail=f"Payment failed: {pi.status}")
            except stripe.error.CardError as e:
                raise HTTPException(status_code=402, detail=str(e.user_message or e))

    # Unlock the photo
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    mark_spicy_leak_unlocked(sid, photo.id, now_iso, girlfriend_id=girlfriend_id)

    seed = hashlib.md5(f"{girlfriend_id}:{photo.id}".encode()).hexdigest()[:10]
    image_url = f"https://picsum.photos/seed/{seed}/400/400"

    add_gallery_item(sid, {
        "id": f"leak-{photo.id}-{uuid.uuid4().hex[:6]}",
        "url": image_url,
        "created_at": now_iso,
        "caption": f"{photo.icon} {photo.title}",
        "source": "spicy_leak",
        "photo_id": photo.id,
    }, girlfriend_id=girlfriend_id)

    logger.info("Spicy leak unlocked: %s via box %s (rarity=%s, paid=%s)",
                photo.id, body.box_id, photo.rarity, payment_status)

    return {
        "status": payment_status,
        "ok": True,
        "already_unlocked": False,
        "photo_id": photo.id,
        "title": photo.title,
        "subtitle": photo.subtitle,
        "rarity": photo.rarity,
        "icon": photo.icon,
        "image_url": image_url,
        "unlocked_at": now_iso,
    }
