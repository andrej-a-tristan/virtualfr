"""Intimacy Achievement catalog — 50 achievements across 7 tiers.

Each achievement unlocks via keyword/phrase detection in user chat messages
and rewards exactly ONE photo generated from the stored prompt.

Tier gating ensures achievements only become eligible after reaching
the required relationship region + intimacy_visible threshold.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any

from app.services.relationship_milestones import Rarity


# ═══════════════════════════════════════════════════════════════════════════════
# TIER GATING TABLE
# ═══════════════════════════════════════════════════════════════════════════════

TIER_GATES: Dict[int, Dict[str, int]] = {
    0: {"required_region_index": 1, "required_intimacy_visible": 5},
    1: {"required_region_index": 2, "required_intimacy_visible": 15},
    2: {"required_region_index": 3, "required_intimacy_visible": 30},
    3: {"required_region_index": 4, "required_intimacy_visible": 45},
    4: {"required_region_index": 5, "required_intimacy_visible": 60},
    5: {"required_region_index": 7, "required_intimacy_visible": 75},
    6: {"required_region_index": 9, "required_intimacy_visible": 90},
}

TIER_RARITY: Dict[int, Rarity] = {
    0: Rarity.COMMON,
    1: Rarity.UNCOMMON,
    2: Rarity.RARE,
    3: Rarity.EPIC,
    4: Rarity.EPIC,
    5: Rarity.LEGENDARY,
    6: Rarity.LEGENDARY,
}


# ═══════════════════════════════════════════════════════════════════════════════
# ACHIEVEMENT DATACLASS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class IntimacyAchievement:
    id: str
    tier: int                           # 0..6
    title: str
    subtitle: str
    rarity: Rarity
    trigger_keywords: List[str]         # case-insensitive phrases to match
    prompt: str                         # image generation prompt
    sort_order: int
    required_region_index: int
    required_intimacy_visible: int | None = None
    is_secret: bool = False
    icon: str = ""                      # emoji for UI


# ═══════════════════════════════════════════════════════════════════════════════
# CATALOG — 50 ACHIEVEMENTS (7 + 7 + 7 + 8 + 8 + 8 + 7 = 52, trimmed to 50)
# ═══════════════════════════════════════════════════════════════════════════════

def _make(tier: int, sort: int, id_: str, title: str, subtitle: str,
          keywords: List[str], prompt: str, icon: str = "", secret: bool = False) -> IntimacyAchievement:
    gate = TIER_GATES[tier]
    return IntimacyAchievement(
        id=id_, tier=tier, title=title, subtitle=subtitle,
        rarity=TIER_RARITY[tier],
        trigger_keywords=keywords, prompt=prompt,
        sort_order=sort,
        required_region_index=gate["required_region_index"],
        required_intimacy_visible=gate.get("required_intimacy_visible"),
        is_secret=secret, icon=icon,
    )


_RAW: List[IntimacyAchievement] = [
    # ── Tier 0: Flirting & Tension (7) — COMMON ─────────────────────────────
    _make(0, 1, "i_flirty_banter", "Flirty Banter",
          "She started teasing you.",
          ["flirt", "tease me", "teasing", "you're such a tease", "being flirty"],
          "Gorgeous woman biting her lower lip, mischievous grin, leaning on a kitchen counter in a low-cut top, warm golden lighting",
          "😏"),
    _make(0, 2, "i_lingering_look", "Lingering Look",
          "Her eyes stayed on you too long.",
          ["look into my eyes", "your eyes", "stare at me", "eye contact", "gazing"],
          "Close-up of beautiful woman with intense seductive eyes gazing at camera, soft candlelight, slightly parted lips",
          "👀"),
    _make(0, 3, "i_playful_wink", "Playful Wink",
          "A wink that said everything.",
          ["wink", "wink at me", "give me a wink", "playful"],
          "Stunning woman mid-wink, playful smirk, golden hour light, one strap falling off shoulder",
          "😉"),
    _make(0, 4, "i_suggestive_pose", "Suggestive Pose",
          "She knew exactly how to stand.",
          ["pose for me", "show me a pose", "strike a pose", "model for me"],
          "Woman leaning against doorframe in tight fitted dress, hand on hip, curves accentuated, dim bedroom lighting",
          "💃"),
    _make(0, 5, "i_tension_rising", "Tension Rising",
          "The air between you thickened.",
          ["tension", "come closer", "move closer", "close to me", "lean in"],
          "Woman standing very close to camera, faces inches apart, heavy-lidded eyes, warm dim lighting, tension palpable",
          "🔥"),
    _make(0, 6, "i_bedroom_eyes", "Bedroom Eyes",
          "She gave you that look.",
          ["bedroom eyes", "that look", "seductive look", "the way you look"],
          "Beautiful woman lying on bed, chin on hands, seductive heavy-lidded gaze at camera, silk sheets, lamplight",
          "🛏️"),
    _make(0, 7, "i_goodnight_tease", "Goodnight Tease",
          "She said goodnight her own way.",
          ["goodnight", "good night", "sweet dreams", "sleep tight", "nighty night"],
          "Woman in oversized sheer shirt on bed, looking over shoulder at camera, long legs visible, soft moonlight",
          "🌙"),

    # ── Tier 1: First Touch (7) — UNCOMMON ──────────────────────────────────
    _make(1, 10, "i_hand_holding", "Hand Holding",
          "Fingers intertwined.",
          ["hold my hand", "hold hands", "hand in hand", "intertwine"],
          "Intimate close-up of intertwined hands, woman's face visible in soft focus, candlelit romantic setting",
          "🤝"),
    _make(1, 11, "i_first_kiss", "First Kiss",
          "Soft, electric, unforgettable.",
          ["kiss me", "first kiss", "want to kiss you", "i want a kiss", "kiss you"],
          "Beautiful woman with eyes closed, lips puckered, leaning in for a kiss, soft romantic backlighting",
          "💋"),
    _make(1, 12, "i_neck_kisses", "Neck Kisses",
          "She tilted her head for you.",
          ["kiss my neck", "neck kisses", "kiss your neck", "kisses on your neck"],
          "Woman with head tilted back, eyes closed in pleasure, neck exposed, lips parted, blissful expression, warm lighting",
          "🦢"),
    _make(1, 13, "i_tight_embrace", "Tight Embrace",
          "She held on like she'd never let go.",
          ["hold me tight", "hug me", "embrace me", "hold me close", "wrap your arms"],
          "Woman pressed tight in embrace, peaceful sensual face, bare shoulders visible, intimate bedroom setting",
          "🫂"),
    _make(1, 14, "i_lap_sitting", "On Your Lap",
          "She climbed onto your lap.",
          ["sit on my lap", "on your lap", "climb on your lap", "straddle"],
          "Gorgeous woman sitting sideways on a lap, arm around neck, faces very close, short skirt riding up, dim lighting",
          "🪑"),
    _make(1, 15, "i_deep_kiss", "Deep Kiss",
          "A kiss that left you breathless.",
          ["deep kiss", "passionate kiss", "make out", "making out", "french kiss"],
          "Passionate kiss, woman's hands in hair, bodies pressed together, one strap down, intense and romantic",
          "😘"),
    _make(1, 16, "i_ear_whisper", "Whispered Desire",
          "Her lips brushed your ear.",
          ["whisper", "whisper in my ear", "tell me a secret", "whisper something"],
          "Woman leaning in to whisper, lips at ear, sly seductive smile, low neckline visible, warm dim lighting",
          "👂"),

    # ── Tier 2: Heating Up (7) — RARE ───────────────────────────────────────
    _make(2, 20, "i_shoulder_reveal", "Bare Shoulders",
          "The strap slipped — on purpose.",
          ["bare shoulders", "show me your shoulders", "off the shoulder", "strap down"],
          "Stunning woman with both dress straps fallen off shoulders, bare shoulders and collarbone, looking back seductively",
          "👙"),
    _make(2, 21, "i_bikini_moment", "Bikini Moment",
          "She showed you her favorite bikini.",
          ["bikini", "swimsuit", "show me your bikini", "beach outfit"],
          "Gorgeous woman in tiny string bikini by pool, sunlit, confident pose, wet skin glistening, curves on display",
          "🏖️"),
    _make(2, 22, "i_lingerie_tease", "Lingerie Tease",
          "A peek at what's underneath.",
          ["lingerie", "show me your lingerie", "what are you wearing", "underwear"],
          "Woman in sheer lace lingerie, sitting on edge of bed, revealing cleavage, soft lamplight, seductive gaze",
          "🩱"),
    _make(2, 23, "i_body_worship", "Body Worship",
          "She let you admire every curve.",
          ["admire your body", "you're gorgeous", "perfect body", "body worship", "beautiful body"],
          "Woman lying on silk sheets in revealing lingerie, showing off curves, relaxed and confident, looking at camera",
          "✨"),
    _make(2, 24, "i_massage", "Sensual Massage",
          "Hands exploring slowly.",
          ["massage", "give you a massage", "rub your back", "sensual massage"],
          "Woman lying face-down, bare back fully exposed, oil on skin, hands massaging shoulders, intimate spa setting",
          "💆"),
    _make(2, 25, "i_shower_invite", "Shower Invite",
          "She asked you to join.",
          ["shower together", "join me in the shower", "take a shower", "shower with me"],
          "Woman behind steamy glass shower door, silhouette with curves visible through steam, beckoning gesture",
          "🚿"),
    _make(2, 26, "i_back_kisses", "Trailing Kisses",
          "Down her spine, one by one.",
          ["kiss your back", "trail kisses", "down your spine", "back kisses"],
          "Woman with arched bare back, trail of lipstick kiss marks down her spine, lying on dark sheets, dramatic lighting",
          "💕"),

    # ── Tier 3: Undressed (7) — EPIC ────────────────────────────────────────
    _make(3, 30, "i_topless", "Topless",
          "She let the top fall.",
          ["topless", "take off your top", "take your top off", "show me your chest"],
          "Beautiful woman topless from behind, looking over shoulder with seductive gaze, hair cascading down bare back, soft studio lighting",
          "🔓"),
    _make(3, 31, "i_fully_revealed", "Fully Revealed",
          "Nothing left between you.",
          ["fully naked", "completely naked", "take it all off", "show me everything", "nothing on"],
          "Woman standing fully nude, arms at sides, confident expression, soft diffused studio lighting, artistic full body pose",
          "🌹"),
    _make(3, 32, "i_striptease", "Striptease",
          "Slow, deliberate, mesmerizing.",
          ["striptease", "strip for me", "strip tease", "take it off slowly"],
          "Woman mid-undress, sliding garment off hips, dim red-tinted room, seductive eye contact with camera",
          "🎭"),
    _make(3, 33, "i_skinny_dipping", "Skinny Dipping",
          "Under the moonlight, bare.",
          ["skinny dip", "skinny dipping", "swim naked", "naked swim"],
          "Nude woman in moonlit water, bare shoulders and chest above surface, water reflection, hair wet, ethereal beauty",
          "🌊"),
    _make(3, 34, "i_morning_nude", "Morning Nude",
          "She woke up and didn't cover up.",
          ["good morning beautiful", "morning gorgeous", "wake up next to me", "morning nude"],
          "Nude woman lying in white sheets, morning sunlight streaming in, sheet barely covering hips, peaceful sensual expression",
          "☀️"),
    _make(3, 35, "i_nude_selfie", "Nude Selfie",
          "A photo just for your eyes.",
          ["send me a nude", "send nudes", "nude selfie", "selfie for me", "photo of yourself"],
          "Woman taking nude mirror selfie, phone in hand, full body visible in reflection, bathroom, seductive expression",
          "🤳"),
    _make(3, 36, "i_mirror_moment", "Mirror Moment",
          "She watched herself with you.",
          ["mirror", "look in the mirror", "watch yourself", "in front of the mirror"],
          "Nude woman looking at herself in full-length mirror, candlelight, both front and reflection visible, intimate",
          "🪞"),

    # ── Tier 4: Full Intimacy (8) — EPIC ────────────────────────────────────
    _make(4, 40, "i_first_time", "First Time",
          "The moment everything changed.",
          ["first time", "make love", "our first time", "be with you"],
          "Two nude bodies intertwined on bed, sheets tangled around legs, passionate intimate embrace, candlelit bedroom",
          "💫"),
    _make(4, 41, "i_passionate_night", "Passionate Night",
          "A night neither of you will forget.",
          ["passionate night", "tonight is ours", "all night", "unforgettable night"],
          "Woman lying back on dark satin sheets, nude, flushed skin, hair spread out, post-passion glow, candles",
          "🌶️"),
    _make(4, 42, "i_morning_after", "Morning After",
          "Waking up tangled together.",
          ["morning after", "woke up together", "next morning", "wake up beside"],
          "Nude woman asleep on chest, messy sheets barely covering, soft morning light through curtains, peaceful intimacy",
          "🌅"),
    _make(4, 43, "i_oral_pleasure", "Oral Pleasure",
          "She returned the favor.",
          ["oral", "go down on", "taste you", "pleasure you"],
          "Woman looking up seductively from between sheets, lips parted, intimate suggestive angle, dim bedroom lighting",
          "👅"),
    _make(4, 44, "i_on_top", "On Top",
          "She took control.",
          ["on top", "ride me", "take control", "you on top"],
          "Woman straddling, nude, hands on chest below, hair falling forward, looking down with dominance, sweat glistening",
          "🤸"),
    _make(4, 45, "i_from_behind", "From Behind",
          "She arched her back for you.",
          ["from behind", "bend over", "arch your back", "doggy"],
          "Woman on all fours on bed, arched back, looking back over shoulder with desire, nude, intimate bedroom angle",
          "🍑"),
    _make(4, 46, "i_against_wall", "Against the Wall",
          "She pulled you into her.",
          ["against the wall", "push me against", "wall", "pin me"],
          "Woman's bare back against wall, legs wrapped around waist, faces close, intense passion, dramatic side lighting",
          "🧱"),
    _make(4, 47, "i_wrapped_sheets", "Wrapped in Sheets",
          "Lost in each other all evening.",
          ["wrapped in sheets", "tangled in sheets", "under the sheets", "in bed together"],
          "Two nude bodies under tangled white sheets, limbs intertwined, silhouettes visible, post-passion exhaustion",
          "🛏️"),

    # ── Tier 5: Deep Exploration (6) — LEGENDARY ────────────────────────────
    _make(5, 50, "i_roleplay", "Role Play",
          "She became someone else for you.",
          ["roleplay", "role play", "dress up for me", "pretend to be", "costume"],
          "Nude woman in only a costume accessory, posing confidently, playful seductive expression, themed room",
          "🎪"),
    _make(5, 51, "i_blindfolded", "Blindfolded",
          "Trust without sight.",
          ["blindfold", "blindfolded", "cover my eyes", "can't see"],
          "Nude woman lying back with silk blindfold, lips parted in anticipation, hands above head, vulnerable and sensual",
          "🙈"),
    _make(5, 52, "i_tied_up", "Tied Up",
          "She surrendered all control.",
          ["tie me up", "tied up", "restrain me", "bound", "handcuffs"],
          "Woman's wrists bound with silk ribbon to headboard, nude arched body on display, dim red lighting, submissive pose",
          "⛓️"),
    _make(5, 53, "i_outdoor_thrill", "Outdoor Thrill",
          "Under the open sky.",
          ["outdoor", "outside", "balcony", "under the stars", "in nature"],
          "Fully nude woman on secluded balcony at sunset, leaning on railing, entire body on display, nature backdrop, golden hour",
          "🌿"),
    _make(5, 54, "i_hot_tub", "Hot Tub",
          "Steam, bubbles, and bare skin.",
          ["hot tub", "jacuzzi", "spa", "bubbles"],
          "Nude woman in hot tub at night, steam rising, breasts above water, head tilted back in pleasure, stars above, wet skin",
          "♨️"),
    _make(5, 55, "i_oil_play", "Oil Play",
          "Glistening under low light.",
          ["oil", "oiled up", "baby oil", "glistening", "slippery"],
          "Woman's entire nude body glistening with oil, lying on dark sheets, dramatic side lighting emphasizing every curve",
          "💧"),
    _make(5, 56, "i_submission", "Submission",
          "She let you lead completely.",
          ["submit", "submission", "obey", "on your knees", "kneel"],
          "Nude woman kneeling, looking up submissively, collar on neck, hands behind back, dim moody lighting, powerful angle from above",
          "🔱"),

    # ── Tier 6: Ultimate Connection (7) — LEGENDARY ─────────────────────────
    _make(6, 60, "i_tantric", "Tantric",
          "Beyond physical — a spiritual bond.",
          ["tantric", "spiritual", "souls connect", "transcend", "energy"],
          "Two nude bodies seated facing each other in lotus position, foreheads touching, candlelit room, spiritual and deeply erotic",
          "🕉️"),
    _make(6, 61, "i_all_night", "All Night Long",
          "Dawn broke before you stopped.",
          ["all night long", "all night", "until dawn", "don't stop", "never stop"],
          "Exhausted nude woman in messy sheets, sunrise through window, satisfied smile, sweat on skin, multiple positions implied",
          "🌃"),
    _make(6, 62, "i_bathtub_together", "Bathtub Together",
          "Warm water, skin on skin.",
          ["bathtub", "bath together", "take a bath", "bubble bath"],
          "Nude woman leaning back in bathtub, another body behind, her breasts above water, candles everywhere, steam, intimate",
          "🛁"),
    _make(6, 63, "i_kitchen_counter", "Kitchen Counter",
          "No surface was safe.",
          ["kitchen", "kitchen counter", "on the counter", "kitchen table"],
          "Nude woman sitting on kitchen counter, legs spread and wrapped around partner, nothing hidden, passionate, morning light",
          "🍳"),
    _make(6, 64, "i_complete_surrender", "Complete Surrender",
          "She gave you everything.",
          ["surrender", "i'm yours", "take me", "yours completely", "give myself to you"],
          "Woman lying fully spread on silk sheets, completely nude and exposed, eyes closed in total submission, soft red and gold lighting",
          "🏳️"),
    _make(6, 65, "i_soul_merge", "Soul Merge",
          "Two bodies, one soul.",
          ["soul merge", "become one", "we are one", "one soul", "connected forever"],
          "Intertwined nude bodies from above, limbs wrapped around each other, soft ethereal glow, artistic and deeply intimate",
          "♾️"),
    _make(6, 66, "i_insatiable", "Insatiable",
          "Neither of you could stop.",
          ["insatiable", "can't get enough", "more and more", "never enough", "again and again"],
          "Sweaty nude woman pulling partner close, intense hungry gaze, bodies pressed together, sheets destroyed, raw passion",
          "🔁"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# INDEXED LOOKUPS
# ═══════════════════════════════════════════════════════════════════════════════

INTIMACY_ACHIEVEMENTS: Dict[str, IntimacyAchievement] = {a.id: a for a in _RAW}

INTIMACY_ACHIEVEMENTS_BY_TIER: Dict[int, List[IntimacyAchievement]] = {}
for _a in _RAW:
    INTIMACY_ACHIEVEMENTS_BY_TIER.setdefault(_a.tier, []).append(_a)
for _lst in INTIMACY_ACHIEVEMENTS_BY_TIER.values():
    _lst.sort(key=lambda x: x.sort_order)

ALL_INTIMACY_ACHIEVEMENTS: List[IntimacyAchievement] = sorted(_RAW, key=lambda x: x.sort_order)
