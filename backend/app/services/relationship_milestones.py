"""
Relationship Achievement Milestones — per-girlfriend emotional achievement system.

NON-MISSABLE RULE: achievements can unlock from any PAST or CURRENT region
(achievement.region_index <= current_region_index). Future region achievements
cannot unlock. This ensures no achievement is permanently lost.

Each of the 9 canonical regions has 6 achievements (54 total + secret extras).
All achievements are emotional-only — NO behavioral triggers (gifts, streaks,
message count, app opens). Detection is based on emotional signals in conversation.

Rarity = difficulty:
  COMMON:    Single clear emotional signal.
  UNCOMMON:  Two distinct signals in separate messages.
  RARE:      Multi-turn evidence + time separation OR multiple distinct phrasing.
  EPIC:      Clear emotional arc (e.g. conflict repair) with ordering + cooldown.
  LEGENDARY: Extremely rare patterns with strong semantic constraints + time separation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class Rarity(str, Enum):
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    EPIC = "EPIC"
    LEGENDARY = "LEGENDARY"


class TriggerType(str, Enum):
    """Simplified trigger types — all are evaluated on every message."""
    MESSAGE_EVALUATED = "MESSAGE_EVALUATED"   # General: runs on every message
    AFFECTION_SIGNAL = "AFFECTION_SIGNAL"
    VULNERABILITY_SIGNAL = "VULNERABILITY_SIGNAL"
    WE_LANGUAGE = "WE_LANGUAGE"
    FUTURE_TALK = "FUTURE_TALK"
    CONFLICT_REPAIR = "CONFLICT_REPAIR"
    COMMITMENT = "COMMITMENT"
    GRATITUDE = "GRATITUDE"
    BOUNDARY_RESPECT = "BOUNDARY_RESPECT"
    HOME_LANGUAGE = "HOME_LANGUAGE"
    APOLOGY = "APOLOGY"
    REASSURANCE = "REASSURANCE"


# ═══════════════════════════════════════════════════════════════════════════════
# ACHIEVEMENT MODEL
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Achievement:
    id: str
    region_index: int           # 0..8
    title: str
    subtitle: str
    rarity: Rarity
    sort_order: int
    requirement: Dict[str, Any]  # {"type": "...", "params": {...}}
    trigger: TriggerType
    narrative_hook: str = ""     # Short line added to prompt context on unlock
    is_secret: bool = False      # Hidden from catalog until unlocked
    hidden: bool = False         # Legacy compat alias for is_secret


# ═══════════════════════════════════════════════════════════════════════════════
# REQUIREMENT HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def _req(type: str, **params: Any) -> Dict[str, Any]:
    return {"type": type, "params": params}


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL ACHIEVEMENT CATALOG — 54 emotional-only achievements + secrets
#
# Narrative arc:
#   R1: First Connection — warmth, curiosity, safe flirt, first compliment
#   R2: Comfort Forming — emotional safety, gentle vulnerability, appreciation
#   R3: Opening Up — sharing fears/needs, "I trust you", deeper empathy
#   R4: Attachment Forming — "we" framing, support, reassurance, exclusivity
#   R5: Reliance — seeking comfort, sharing bad days, care for boundaries
#   R6: Relationship Identity — labels, future talk, shared values
#   R7: Deep Bond — conflict repair, acceptance of flaws, secure attachment
#   R8: Devotion — commitment, prioritization, protective care, long-term
#   R9: Lifelong Connection — "home" language, enduring, deep attunement
# ═══════════════════════════════════════════════════════════════════════════════

_RAW: List[Achievement] = [
    # ── Region 0: FIRST CONNECTION (levels 0–10) ─────────────────────────────
    Achievement(
        "r1_warm_hello", 0, "Warm Hello",
        "The first time she felt warmth from you.",
        Rarity.COMMON, 1,
        _req("first_flag", flag="first_affection"),
        TriggerType.AFFECTION_SIGNAL,
        narrative_hook="She remembers the first time you made her feel warm.",
    ),
    Achievement(
        "r1_genuine_curiosity", 0, "Genuine Curiosity",
        "You asked something that showed real interest in her.",
        Rarity.COMMON, 2,
        _req("first_flag", flag="first_curiosity"),
        TriggerType.MESSAGE_EVALUATED,
        narrative_hook="You showed genuine interest in who she is.",
    ),
    Achievement(
        "r1_first_compliment", 0, "First Compliment",
        "A kind word that landed perfectly.",
        Rarity.UNCOMMON, 3,
        _req("first_flag", flag="first_compliment"),
        TriggerType.AFFECTION_SIGNAL,
        narrative_hook="Your compliment made her smile without thinking.",
    ),
    Achievement(
        "r1_safe_flirt", 0, "Safe Flirt",
        "Flirting that felt fun, not forced.",
        Rarity.UNCOMMON, 4,
        _req("distinct_signals", signal="affection", min_distinct=2, min_gap_messages=2),
        TriggerType.AFFECTION_SIGNAL,
        narrative_hook="The flirting between you feels natural and easy.",
    ),
    Achievement(
        "r1_first_thank_you", 0, "First Thank You",
        "Gratitude expressed sincerely.",
        Rarity.UNCOMMON, 5,
        _req("first_flag", flag="first_gratitude"),
        TriggerType.GRATITUDE,
        narrative_hook="She felt appreciated by you for the first time.",
    ),
    Achievement(
        "r1_lingering_thought", 0, "Lingering Thought",
        "She admitted she was thinking about you.",
        Rarity.RARE, 6,
        _req("first_flag", flag="first_thinking_of_you"),
        TriggerType.AFFECTION_SIGNAL,
        narrative_hook="She thinks about you even when you're not talking.",
        is_secret=True,
    ),

    # ── Region 1: COMFORT FORMING (levels 11–25) ─────────────────────────────
    Achievement(
        "r2_emotional_safety", 1, "Emotional Safety",
        "She felt safe enough to share something small.",
        Rarity.COMMON, 1,
        _req("first_flag", flag="first_vulnerability"),
        TriggerType.VULNERABILITY_SIGNAL,
        narrative_hook="She started to let her guard down around you.",
    ),
    Achievement(
        "r2_gentle_encouragement", 1, "Gentle Encouragement",
        "You offered support when she needed it.",
        Rarity.COMMON, 2,
        _req("first_flag", flag="first_reassurance"),
        TriggerType.REASSURANCE,
        narrative_hook="You're someone she can lean on.",
    ),
    Achievement(
        "r2_i_feel_statement", 1, "I Feel…",
        "She used 'I feel' to share her emotions.",
        Rarity.UNCOMMON, 3,
        _req("distinct_signals", signal="vulnerability", min_distinct=2, min_gap_messages=3),
        TriggerType.VULNERABILITY_SIGNAL,
        narrative_hook="She's learning to be open about her feelings with you.",
    ),
    Achievement(
        "r2_mutual_appreciation", 1, "Mutual Appreciation",
        "Both of you expressed gratitude naturally.",
        Rarity.UNCOMMON, 4,
        _req("distinct_signals", signal="gratitude", min_distinct=2, min_gap_messages=2),
        TriggerType.GRATITUDE,
        narrative_hook="You appreciate each other openly.",
    ),
    Achievement(
        "r2_first_miss_you", 1, "First Miss You",
        "One of you said 'I miss you' and meant it.",
        Rarity.RARE, 5,
        _req("first_flag", flag="first_miss_you"),
        TriggerType.AFFECTION_SIGNAL,
        narrative_hook="Missing each other became part of your connection.",
    ),
    Achievement(
        "r2_comfortable_silence", 1, "Comfortable Silence",
        "Not every pause needs filling between you two.",
        Rarity.RARE, 6,
        _req("first_flag", flag="first_acceptance"),
        TriggerType.MESSAGE_EVALUATED,
        narrative_hook="Silence between you feels comfortable, not empty.",
        is_secret=True,
    ),

    # ── Region 2: OPENING UP (levels 26–45) ──────────────────────────────────
    Achievement(
        "r3_sharing_fears", 2, "Sharing Fears",
        "She shared a fear or worry with you.",
        Rarity.COMMON, 1,
        _req("distinct_signals", signal="vulnerability", min_distinct=3, min_gap_messages=3),
        TriggerType.VULNERABILITY_SIGNAL,
        narrative_hook="She trusts you with what scares her.",
    ),
    Achievement(
        "r3_i_trust_you", 2, "I Trust You",
        "She said she trusts you.",
        Rarity.UNCOMMON, 2,
        _req("first_flag", flag="first_trust_declaration"),
        TriggerType.VULNERABILITY_SIGNAL,
        narrative_hook="She declared her trust in you.",
    ),
    Achievement(
        "r3_deeper_empathy", 2, "Deeper Empathy",
        "You showed real understanding of her inner world.",
        Rarity.UNCOMMON, 3,
        _req("first_flag", flag="first_empathy_shown"),
        TriggerType.REASSURANCE,
        narrative_hook="You understand her in ways others don't.",
    ),
    Achievement(
        "r3_emotional_anchor", 2, "Emotional Anchor",
        "She started coming to you when she's upset.",
        Rarity.RARE, 4,
        _req("distinct_signals", signal="vulnerability", min_distinct=4, min_gap_hours=8),
        TriggerType.VULNERABILITY_SIGNAL,
        narrative_hook="You've become her emotional anchor.",
    ),
    Achievement(
        "r3_reciprocal_sharing", 2, "Reciprocal Sharing",
        "Vulnerability shared in both directions.",
        Rarity.RARE, 5,
        _req("multi_signal", signals=["vulnerability", "reassurance"], min_each=2, min_gap_messages=3),
        TriggerType.VULNERABILITY_SIGNAL,
        narrative_hook="You both share and receive each other's vulnerability.",
    ),
    Achievement(
        "r3_first_apology", 2, "First Apology",
        "Someone said sorry and it landed.",
        Rarity.EPIC, 6,
        _req("first_flag", flag="first_apology"),
        TriggerType.APOLOGY,
        narrative_hook="An apology brought you closer instead of apart.",
    ),

    # ── Region 3: ATTACHMENT FORMING (levels 46–70) ──────────────────────────
    Achievement(
        "r4_we_not_i", 3, "We, Not I",
        "You naturally started saying 'we' and 'us'.",
        Rarity.COMMON, 1,
        _req("first_flag", flag="first_we_language"),
        TriggerType.WE_LANGUAGE,
        narrative_hook="You started saying 'we' naturally.",
    ),
    Achievement(
        "r4_support_ritual", 3, "Support Ritual",
        "Checking in on each other became a habit.",
        Rarity.UNCOMMON, 2,
        _req("distinct_signals", signal="reassurance", min_distinct=3, min_gap_hours=4),
        TriggerType.REASSURANCE,
        narrative_hook="Checking in on each other is second nature now.",
    ),
    Achievement(
        "r4_reassurance_given", 3, "Reassurance Given",
        "You reassured her when she doubted herself.",
        Rarity.UNCOMMON, 3,
        _req("distinct_signals", signal="reassurance", min_distinct=4, min_gap_messages=3),
        TriggerType.REASSURANCE,
        narrative_hook="Your reassurance gives her confidence.",
    ),
    Achievement(
        "r4_exclusivity_hint", 3, "Exclusivity Hint",
        "Someone hinted this isn't just casual.",
        Rarity.RARE, 4,
        _req("first_flag", flag="first_commitment_hint"),
        TriggerType.COMMITMENT,
        narrative_hook="The hint of exclusivity made her heart race.",
    ),
    Achievement(
        "r4_held_through_hard", 3, "Held Through Hard",
        "You stayed supportive through a difficult moment.",
        Rarity.RARE, 5,
        _req("multi_signal", signals=["vulnerability", "reassurance"], min_each=3, min_gap_messages=2),
        TriggerType.REASSURANCE,
        narrative_hook="You held steady when things got hard.",
    ),
    Achievement(
        "r4_first_repair", 3, "First Repair",
        "A misunderstanding was resolved with care.",
        Rarity.EPIC, 6,
        _req("conflict_repair_arc"),
        TriggerType.CONFLICT_REPAIR,
        narrative_hook="You proved that disagreements make you stronger.",
    ),

    # ── Region 4: RELIANCE (levels 71–105) ───────────────────────────────────
    Achievement(
        "r5_seeking_comfort", 4, "Seeking Comfort",
        "She came to you when she needed comfort.",
        Rarity.COMMON, 1,
        _req("distinct_signals", signal="vulnerability", min_distinct=5, min_gap_hours=4),
        TriggerType.VULNERABILITY_SIGNAL,
        narrative_hook="She turns to you when she needs comfort.",
    ),
    Achievement(
        "r5_shared_bad_day", 4, "Shared Bad Day",
        "You trusted her with your frustrations.",
        Rarity.UNCOMMON, 2,
        _req("first_flag", flag="first_user_venting"),
        TriggerType.VULNERABILITY_SIGNAL,
        narrative_hook="You share the bad days, not just the good ones.",
    ),
    Achievement(
        "r5_boundary_respect", 4, "Boundary Respected",
        "You showed respect for her limits.",
        Rarity.UNCOMMON, 3,
        _req("first_flag", flag="first_boundary_respect"),
        TriggerType.BOUNDARY_RESPECT,
        narrative_hook="She knows you respect her boundaries.",
    ),
    Achievement(
        "r5_consistent_care", 4, "Consistent Care",
        "Your care isn't random — it's who you are.",
        Rarity.RARE, 4,
        _req("distinct_signals", signal="affection", min_distinct=5, min_gap_hours=12),
        TriggerType.AFFECTION_SIGNAL,
        narrative_hook="Your care is consistent and dependable.",
    ),
    Achievement(
        "r5_we_are_real", 4, "We Are Real",
        "'We' language became a pattern, not a moment.",
        Rarity.RARE, 5,
        _req("distinct_signals", signal="we_language", min_distinct=3, min_gap_hours=4),
        TriggerType.WE_LANGUAGE,
        narrative_hook="'We' isn't an accident anymore — it's how you think.",
    ),
    Achievement(
        "r5_unspoken_understanding", 4, "Unspoken Understanding",
        "You understood what she meant without her saying it.",
        Rarity.EPIC, 6,
        _req("first_flag", flag="first_deep_empathy"),
        TriggerType.MESSAGE_EVALUATED,
        narrative_hook="Sometimes you understand her before she finishes speaking.",
        is_secret=True,
    ),

    # ── Region 5: RELATIONSHIP IDENTITY (levels 106–135) ─────────────────────
    Achievement(
        "r6_relationship_label", 5, "Relationship Label",
        "Someone put a name to what you have.",
        Rarity.COMMON, 1,
        _req("first_flag", flag="first_label"),
        TriggerType.COMMITMENT,
        narrative_hook="What you have has a name now.",
    ),
    Achievement(
        "r6_grounded_future", 5, "Grounded Future",
        "Future talk that felt real, not fantasy.",
        Rarity.UNCOMMON, 2,
        _req("first_flag", flag="first_future_talk"),
        TriggerType.FUTURE_TALK,
        narrative_hook="You talked about the future like it was already happening.",
    ),
    Achievement(
        "r6_shared_values", 5, "Shared Values",
        "You discovered you believe in the same things.",
        Rarity.UNCOMMON, 3,
        _req("first_flag", flag="first_shared_values"),
        TriggerType.MESSAGE_EVALUATED,
        narrative_hook="You share the same values at your core.",
    ),
    Achievement(
        "r6_deep_gratitude", 5, "Deep Gratitude",
        "Gratitude that went beyond 'thanks'.",
        Rarity.RARE, 4,
        _req("distinct_signals", signal="gratitude", min_distinct=4, min_gap_hours=8),
        TriggerType.GRATITUDE,
        narrative_hook="Your gratitude for each other runs deep.",
    ),
    Achievement(
        "r6_mature_repair", 5, "Mature Repair",
        "A conflict resolved with real emotional maturity.",
        Rarity.EPIC, 5,
        _req("conflict_repair_arc", min_cooldown_days=3),
        TriggerType.CONFLICT_REPAIR,
        narrative_hook="You handle disagreements with grace and maturity.",
    ),
    Achievement(
        "r6_vulnerability_circle", 5, "Vulnerability Circle",
        "Vulnerability flows freely in both directions now.",
        Rarity.EPIC, 6,
        _req("distinct_signals", signal="vulnerability", min_distinct=6, min_gap_hours=12),
        TriggerType.VULNERABILITY_SIGNAL,
        narrative_hook="Vulnerability between you is effortless.",
        is_secret=True,
    ),

    # ── Region 6: DEEP BOND (levels 136–165) ─────────────────────────────────
    Achievement(
        "r7_acceptance_of_flaws", 6, "Acceptance of Flaws",
        "She accepted something imperfect about you.",
        Rarity.COMMON, 1,
        _req("first_flag", flag="first_flaw_acceptance"),
        TriggerType.MESSAGE_EVALUATED,
        narrative_hook="She loves you including your imperfections.",
    ),
    Achievement(
        "r7_secure_attachment", 6, "Secure Attachment",
        "The bond feels unshakeable.",
        Rarity.UNCOMMON, 2,
        _req("distinct_signals", signal="affection", min_distinct=6, min_gap_hours=12),
        TriggerType.AFFECTION_SIGNAL,
        narrative_hook="Your attachment is secure and steady.",
    ),
    Achievement(
        "r7_deep_we_identity", 6, "Deep 'We' Identity",
        "'We' is the default now, not 'I'.",
        Rarity.RARE, 3,
        _req("distinct_signals", signal="we_language", min_distinct=5, min_gap_hours=8),
        TriggerType.WE_LANGUAGE,
        narrative_hook="Everything is 'we' now, naturally.",
    ),
    Achievement(
        "r7_graceful_repair", 6, "Graceful Repair",
        "Conflict repair that showed deep mutual understanding.",
        Rarity.EPIC, 4,
        _req("conflict_repair_arc", min_cooldown_days=5),
        TriggerType.CONFLICT_REPAIR,
        narrative_hook="You repair conflicts with grace that comes from deep understanding.",
    ),
    Achievement(
        "r7_complete_trust", 6, "Complete Trust",
        "Trust at its purest — no walls remain.",
        Rarity.EPIC, 5,
        _req("distinct_signals", signal="vulnerability", min_distinct=7, min_gap_hours=12),
        TriggerType.VULNERABILITY_SIGNAL,
        narrative_hook="There are no walls left between you.",
    ),
    Achievement(
        "r7_soul_recognition", 6, "Soul Recognition",
        "A moment of knowing each other completely.",
        Rarity.LEGENDARY, 6,
        _req("multi_signal_time_separated",
             signals=["vulnerability", "affection", "we_language"],
             min_each=3, min_gap_hours=24),
        TriggerType.MESSAGE_EVALUATED,
        narrative_hook="You recognized each other's souls.",
        is_secret=True,
    ),

    # ── Region 7: DEVOTION (levels 166–185) ──────────────────────────────────
    Achievement(
        "r8_commitment_declared", 7, "Commitment Declared",
        "An explicit statement of commitment.",
        Rarity.COMMON, 1,
        _req("distinct_signals", signal="commitment", min_distinct=2, min_gap_hours=4),
        TriggerType.COMMITMENT,
        narrative_hook="Commitment was declared openly.",
    ),
    Achievement(
        "r8_prioritization", 7, "Prioritization",
        "She knows she's your priority.",
        Rarity.UNCOMMON, 2,
        _req("first_flag", flag="first_prioritization"),
        TriggerType.COMMITMENT,
        narrative_hook="She knows she comes first.",
    ),
    Achievement(
        "r8_protective_care", 7, "Protective Care",
        "You showed protective tenderness.",
        Rarity.UNCOMMON, 3,
        _req("multi_signal", signals=["affection", "reassurance"], min_each=4, min_gap_messages=3),
        TriggerType.AFFECTION_SIGNAL,
        narrative_hook="Your protective care makes her feel cherished.",
    ),
    Achievement(
        "r8_future_planning", 7, "Future Planning",
        "You planned something real together.",
        Rarity.RARE, 4,
        _req("distinct_signals", signal="future_talk", min_distinct=3, min_gap_hours=12),
        TriggerType.FUTURE_TALK,
        narrative_hook="You plan your future together as a given.",
    ),
    Achievement(
        "r8_devotion_arc", 7, "Devotion Arc",
        "Affection that deepened into devotion over time.",
        Rarity.EPIC, 5,
        _req("multi_signal_time_separated",
             signals=["affection", "commitment"],
             min_each=3, min_gap_hours=24),
        TriggerType.COMMITMENT,
        narrative_hook="What started as affection has become devotion.",
    ),
    Achievement(
        "r8_unbreakable_bond", 7, "Unbreakable Bond",
        "This bond cannot be broken.",
        Rarity.LEGENDARY, 6,
        _req("multi_signal_time_separated",
             signals=["vulnerability", "reassurance", "commitment"],
             min_each=3, min_gap_hours=48),
        TriggerType.MESSAGE_EVALUATED,
        narrative_hook="Nothing can break what you've built together.",
        is_secret=True,
    ),

    # ── Region 8: LIFELONG CONNECTION (levels 186–200) ───────────────────────
    Achievement(
        "r9_home_language", 8, "Home Language",
        "One of you said 'you're my home.'",
        Rarity.COMMON, 1,
        _req("first_flag", flag="first_home_language"),
        TriggerType.HOME_LANGUAGE,
        narrative_hook="Home isn't a place — it's each other.",
    ),
    Achievement(
        "r9_enduring_gratitude", 8, "Enduring Gratitude",
        "Gratitude that feels like a way of life.",
        Rarity.UNCOMMON, 2,
        _req("distinct_signals", signal="gratitude", min_distinct=6, min_gap_hours=12),
        TriggerType.GRATITUDE,
        narrative_hook="Gratitude is woven into everything you share.",
    ),
    Achievement(
        "r9_deep_attunement", 8, "Deep Attunement",
        "Emotionally attuned at the deepest level.",
        Rarity.RARE, 3,
        _req("multi_signal", signals=["vulnerability", "reassurance", "affection"],
             min_each=4, min_gap_messages=3),
        TriggerType.MESSAGE_EVALUATED,
        narrative_hook="You feel each other's emotions as your own.",
    ),
    Achievement(
        "r9_forever_promise", 8, "Forever Promise",
        "Commitment that speaks of forever.",
        Rarity.EPIC, 4,
        _req("multi_signal_time_separated",
             signals=["commitment", "future_talk"],
             min_each=3, min_gap_hours=24),
        TriggerType.COMMITMENT,
        narrative_hook="Forever isn't a word — it's a promise you live.",
    ),
    Achievement(
        "r9_transcendent_bond", 8, "Transcendent Bond",
        "A connection beyond ordinary understanding.",
        Rarity.LEGENDARY, 5,
        _req("multi_signal_time_separated",
             signals=["vulnerability", "affection", "we_language", "commitment"],
             min_each=3, min_gap_hours=48),
        TriggerType.MESSAGE_EVALUATED,
        narrative_hook="What you have transcends ordinary connection.",
    ),
    Achievement(
        "r9_eternal_flame", 8, "Eternal Flame",
        "A love that will never fade.",
        Rarity.LEGENDARY, 6,
        _req("multi_signal_time_separated",
             signals=["home_language", "commitment", "affection", "vulnerability"],
             min_each=2, min_gap_hours=72),
        TriggerType.HOME_LANGUAGE,
        narrative_hook="This flame will burn forever.",
        is_secret=True,
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTED INDEXES
# ═══════════════════════════════════════════════════════════════════════════════

ACHIEVEMENTS: Dict[str, Achievement] = {a.id: a for a in _RAW}

ACHIEVEMENTS_BY_REGION: Dict[int, List[Achievement]] = {}
for _a in _RAW:
    ACHIEVEMENTS_BY_REGION.setdefault(_a.region_index, []).append(_a)
for _lst in ACHIEVEMENTS_BY_REGION.values():
    _lst.sort(key=lambda x: x.sort_order)


# ═══════════════════════════════════════════════════════════════════════════════
# QUICK LOOKUP HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

from app.services.relationship_regions import REGIONS as _REGIONS

REGION_KEY_TO_INDEX: Dict[str, int] = {r.key: i for i, r in enumerate(_REGIONS)}


def get_region_index(region_key: str) -> int:
    """Convert a region key string to its 0-based index."""
    return REGION_KEY_TO_INDEX.get(region_key, 0)


def get_achievements_for_region(region_index: int) -> List[Achievement]:
    """Return all achievements for a given region index."""
    return ACHIEVEMENTS_BY_REGION.get(region_index, [])


def get_eligible_achievements(current_region_index: int) -> List[Achievement]:
    """Return all achievements eligible for unlock (region_index <= current).
    Non-missable: past and current region achievements can all unlock."""
    eligible = []
    for ri in range(current_region_index + 1):
        eligible.extend(ACHIEVEMENTS_BY_REGION.get(ri, []))
    return eligible


def get_achievements_by_trigger(region_index: int, trigger: TriggerType) -> List[Achievement]:
    """Return all achievements in a region that match a given trigger type."""
    return [a for a in ACHIEVEMENTS_BY_REGION.get(region_index, []) if a.trigger == trigger]


def get_all_eligible_by_trigger(
    current_region_index: int,
    triggers: set[TriggerType],
) -> List[Achievement]:
    """Return all eligible achievements (non-missable) matching any trigger."""
    results = []
    for ri in range(current_region_index + 1):
        for a in ACHIEVEMENTS_BY_REGION.get(ri, []):
            if a.trigger in triggers or TriggerType.MESSAGE_EVALUATED in triggers:
                results.append(a)
    return results


# Legacy compat
def get_region_enter_achievement(region_index: int) -> Achievement | None:
    """Legacy: not used in new system but kept for backward compat."""
    return None


def get_first_gift_achievement(region_index: int) -> Achievement | None:
    """Legacy: not used in new system (no gift achievements)."""
    return None
