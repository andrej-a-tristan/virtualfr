"""
Big Five Behavior Modulation (Task 2.2)

Deterministic module that takes Big Five personality values and modulates
the BehaviorProfile from Task 2.1. Affects:
- Emotional intensity (warmth, expressiveness, emoji usage)
- Anxiety/reassurance (absence reactions, check-in behavior)
- Message length and structure
- Initiative frequency and timing

All modulation is deterministic with no randomness.
No guilt/pressure language is ever introduced.

Mirrors frontend: frontend/src/lib/engines/big_five_modulation.ts
"""
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Any
from copy import deepcopy

from app.services.trait_behavior_rules import (
    BehaviorProfile,
    ToneProfile,
    ResponseStyle,
    EmojiStyle,
    PetNameStyle,
    MessageStylingProfile,
    RelationshipBehavior,
    InitiationBehavior,
    AbsenceReaction,
    PromptBehavior,
    TraitSelection,
)

# =============================================================================
# TYPES
# =============================================================================

@dataclass
class BigFive:
    """Big Five personality values (0-100 scale)."""
    openness: float = 50           # 0-100: conventional ↔ creative/curious
    conscientiousness: float = 50  # 0-100: spontaneous ↔ organized/reliable
    extraversion: float = 50       # 0-100: introverted ↔ outgoing/expressive
    agreeableness: float = 50      # 0-100: independent ↔ warm/trusting
    neuroticism: float = 50        # 0-100: stable ↔ emotionally sensitive


BigFiveSource = Literal["base", "trait_mapped"]


@dataclass
class BigFiveProfile:
    """Big Five profile with source tracking."""
    values: BigFive
    source: BigFiveSource = "base"


RelationshipLevel = Literal["STRANGER", "FAMILIAR", "CLOSE", "INTIMATE", "EXCLUSIVE"]


@dataclass
class RelationshipState:
    """Simplified relationship state for modulation."""
    trust: float = 10
    intimacy: float = 10
    level: RelationshipLevel = "STRANGER"
    last_interaction_at: Optional[str] = None
    milestones_reached: List[str] = field(default_factory=list)


@dataclass
class AffectionExtensions:
    """Affection parameters (0-3 scale)."""
    reassurance_level: int = 1      # 1-3: how much reassurance to provide
    check_in_frequency: int = 1     # 0-3: how often to check in
    protectiveness: int = 1         # 0-3: protective behavior intensity


@dataclass
class PhrasingExtensions:
    """Phrasing parameters."""
    emoji_rate: int = 2             # 0-3: emoji frequency boost
    directness: int = 2             # 1-3: how direct in communication
    teasing_level: int = 1          # 0-3: playful teasing intensity
    flirtiness: int = 1             # 0-3: flirtatious behavior level


@dataclass
class InitiationExtensions:
    """Extended initiation parameters."""
    probability_boost: float = 0.0   # 0.00-0.12: added to base frequency
    min_intimacy_to_initiate: int = 20  # 10-35: minimum intimacy to initiate


@dataclass
class ModulatedBehaviorExtensions:
    """Extended behavior parameters added by Big Five modulation."""
    affection: AffectionExtensions = field(default_factory=AffectionExtensions)
    phrasing: PhrasingExtensions = field(default_factory=PhrasingExtensions)
    initiation_ext: InitiationExtensions = field(default_factory=InitiationExtensions)


@dataclass
class ModulatedBehaviorProfile:
    """Modulated behavior profile with extensions."""
    tone: ToneProfile
    message_styling: MessageStylingProfile
    relationship: RelationshipBehavior
    initiation: InitiationBehavior
    absence: AbsenceReaction
    prompt: PromptBehavior
    derived_from: TraitSelection
    extensions: ModulatedBehaviorExtensions
    modulation_applied: bool = True


@dataclass
class ModulationResult:
    """Result of Big Five modulation."""
    profile: ModulatedBehaviorProfile
    notes: List[str]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def clamp(num: float, min_val: float, max_val: float) -> float:
    """Clamp a number to [min, max] range."""
    return max(min_val, min(max_val, num))


def normalize100(x: float) -> float:
    """Normalize 0-100 value to 0-1 range."""
    return clamp(x, 0, 100) / 100


def z(x: float) -> float:
    """
    Convert 0-100 value to centered -1 to +1 range.
    Formula: (x - 50) / 25, clamped to [-1, 1]
    """
    return clamp((x - 50) / 25, -1, 1)


def step_sentence_length(
    current: Literal["short", "medium", "long"],
    direction: Literal["up", "down"]
) -> Literal["short", "medium", "long"]:
    """Step sentence length up or down."""
    order = ["short", "medium", "long"]
    idx = order.index(current)
    if direction == "up":
        return order[min(idx + 1, 2)]
    else:
        return order[max(idx - 1, 0)]


EMOJI_FREQ_TO_RATE = {"none": 0, "rare": 1, "moderate": 2, "frequent": 3}
RATE_TO_EMOJI_FREQ = ["none", "rare", "moderate", "frequent"]


def emoji_frequency_to_rate(freq: str) -> int:
    """Map emoji frequency string to numeric rate (0-3)."""
    return EMOJI_FREQ_TO_RATE.get(freq, 2)


def rate_to_emoji_frequency(rate: int) -> str:
    """Map numeric rate (0-3) to emoji frequency string."""
    clamped = int(clamp(round(rate), 0, 3))
    return RATE_TO_EMOJI_FREQ[clamped]


INTENSITY_TO_NUM = {"gentle": 1, "moderate": 2, "concerned": 3}
NUM_TO_INTENSITY = ["gentle", "moderate", "concerned"]


def intensity_to_number(intensity: str) -> int:
    """Map absence reaction intensity string to numeric (1-3)."""
    return INTENSITY_TO_NUM.get(intensity, 2)


def number_to_intensity(num: int) -> str:
    """Map numeric (1-3) to absence reaction intensity string."""
    clamped = int(clamp(round(num), 1, 3))
    return NUM_TO_INTENSITY[clamped - 1]


LEVEL_ORDER = ["STRANGER", "FAMILIAR", "CLOSE", "INTIMATE", "EXCLUSIVE"]


def level_index(level: str) -> int:
    """Get relationship level order index (0-4)."""
    return LEVEL_ORDER.index(level) if level in LEVEL_ORDER else 0


# =============================================================================
# DEFAULT EXTENSIONS
# =============================================================================

def create_default_extensions(base: BehaviorProfile) -> ModulatedBehaviorExtensions:
    """Create default modulation extensions based on base profile."""
    # Derive initial values from base profile
    emoji_rate = emoji_frequency_to_rate(base.message_styling.emoji.frequency)
    
    # Directness from tone assertiveness
    directness = 3 if base.tone.assertiveness >= 0.7 else (2 if base.tone.assertiveness >= 0.4 else 1)
    
    # Teasing from playfulness
    teasing_level = 2 if base.tone.playfulness >= 0.7 else (1 if base.tone.playfulness >= 0.5 else 0)
    
    # Flirtiness starts conservative
    flirtiness = 1 if base.tone.warmth >= 0.7 else 0
    
    # Reassurance from warmth + vulnerability
    reassurance_level = 2 if base.tone.warmth >= 0.7 else 1
    
    # Check-in frequency from attachment behavior
    check_in_frequency = 2 if base.initiation.base_frequency >= 0.2 else 1
    
    # Protectiveness from assertiveness
    protectiveness = 2 if base.tone.assertiveness >= 0.6 else 1
    
    return ModulatedBehaviorExtensions(
        affection=AffectionExtensions(
            reassurance_level=int(clamp(reassurance_level, 1, 3)),
            check_in_frequency=int(clamp(check_in_frequency, 0, 3)),
            protectiveness=int(clamp(protectiveness, 0, 3)),
        ),
        phrasing=PhrasingExtensions(
            emoji_rate=int(clamp(emoji_rate, 0, 3)),
            directness=int(clamp(directness, 1, 3)),
            teasing_level=int(clamp(teasing_level, 0, 3)),
            flirtiness=int(clamp(flirtiness, 0, 3)),
        ),
        initiation_ext=InitiationExtensions(
            probability_boost=0.0,
            min_intimacy_to_initiate=20,
        ),
    )


# =============================================================================
# MAIN MODULATION FUNCTION
# =============================================================================

def apply_big_five_modulation(
    base: BehaviorProfile,
    big_five: BigFiveProfile,
    relationship: RelationshipState,
    hours_inactive: float = 0.0
) -> ModulationResult:
    """
    Apply Big Five modulation to a base BehaviorProfile.
    
    Args:
        base: Base behavior profile from traits
        big_five: Big Five personality values
        relationship: Current relationship state
        hours_inactive: Hours since last interaction
        
    Returns:
        ModulationResult with modulated profile and debug notes
    """
    notes: List[str] = []
    
    # Deep clone base to avoid mutations
    profile_tone = ToneProfile(
        warmth=base.tone.warmth,
        playfulness=base.tone.playfulness,
        expressiveness=base.tone.expressiveness,
        vulnerability=base.tone.vulnerability,
        assertiveness=base.tone.assertiveness,
        formality=base.tone.formality,
    )
    
    profile_response = ResponseStyle(
        avg_sentence_length=base.message_styling.response.avg_sentence_length,
        preferred_message_length=base.message_styling.response.preferred_message_length,
        uses_filler_words=base.message_styling.response.uses_filler_words,
        uses_contractions=base.message_styling.response.uses_contractions,
        punctuation_style=base.message_styling.response.punctuation_style,
        capitalization_style=base.message_styling.response.capitalization_style,
    )
    
    profile_emoji = EmojiStyle(
        frequency=base.message_styling.emoji.frequency,
        preferred_emojis=list(base.message_styling.emoji.preferred_emojis),
        hearts_frequency=base.message_styling.emoji.hearts_frequency,
        uses_kaomoji=base.message_styling.emoji.uses_kaomoji,
    )
    
    profile_pet_names = PetNameStyle(
        enabled=base.message_styling.pet_names.enabled,
        start_at_level=base.message_styling.pet_names.start_at_level,
        casual_names=list(base.message_styling.pet_names.casual_names),
        affectionate_names=list(base.message_styling.pet_names.affectionate_names),
        intimate_names=list(base.message_styling.pet_names.intimate_names),
    )
    
    profile_initiation = InitiationBehavior(
        base_frequency=base.initiation.base_frequency,
        cooldown_hours=base.initiation.cooldown_hours,
        preferred_time_of_day=base.initiation.preferred_time_of_day,
        message_variety=base.initiation.message_variety,
        level_multipliers=dict(base.initiation.level_multipliers),
    )
    
    profile_absence = AbsenceReaction(
        trigger_hours=base.absence.trigger_hours,
        escalation_hours=base.absence.escalation_hours,
        max_intensity=base.absence.max_intensity,
        message_style=base.absence.message_style,
    )
    
    # Initialize extensions
    ext = create_default_extensions(base)
    
    # Extract Big Five z-scores
    E = z(big_five.values.extraversion)
    A = z(big_five.values.agreeableness)
    N = z(big_five.values.neuroticism)
    C = z(big_five.values.conscientiousness)
    O = z(big_five.values.openness)
    
    # Track original values for notes
    orig_emoji = ext.phrasing.emoji_rate
    orig_reassurance = ext.affection.reassurance_level
    
    # =========================================================================
    # A) EMOTIONAL INTENSITY (affection + expressiveness)
    # =========================================================================
    
    # Reassurance level: A*0.6 + N*0.4
    reassurance_delta = round(A * 0.6 + N * 0.4)
    ext.affection.reassurance_level = int(clamp(ext.affection.reassurance_level + reassurance_delta, 1, 3))
    
    # Emoji rate: E*0.6 + A*0.3 - C*0.2
    emoji_delta = round(E * 0.6 + A * 0.3 - C * 0.2)
    ext.phrasing.emoji_rate = int(clamp(ext.phrasing.emoji_rate + emoji_delta, 0, 3))
    
    # Update emoji frequency in profile
    profile_emoji.frequency = rate_to_emoji_frequency(ext.phrasing.emoji_rate)
    
    # Sentence length: step based on E + O
    eo_sum = E + O
    if eo_sum > 0.8:
        profile_response.avg_sentence_length = step_sentence_length(
            profile_response.avg_sentence_length, "up"
        )
        notes.append("High extraversion+openness increased message length")
    elif eo_sum < -0.8:
        profile_response.avg_sentence_length = step_sentence_length(
            profile_response.avg_sentence_length, "down"
        )
        notes.append("Low extraversion+openness decreased message length")
    
    # Check-in frequency: A*0.5 + E*0.3 - C*0.2
    check_in_delta = round(A * 0.5 + E * 0.3 - C * 0.2)
    ext.affection.check_in_frequency = int(clamp(ext.affection.check_in_frequency + check_in_delta, 0, 3))
    
    # Update tone expressiveness based on E
    if E > 0.5:
        profile_tone.expressiveness = clamp(profile_tone.expressiveness + 0.15, 0, 1)
    
    # =========================================================================
    # B) ANXIETY / REASSURANCE (no guilt, no spam)
    # =========================================================================
    
    # High neuroticism (N > 0.8)
    if N > 0.8:
        # Change absence reaction style to calm check-in
        is_intimate = level_index(relationship.level) >= level_index("INTIMATE")
        if not (profile_absence.message_style == "worried" and is_intimate):
            profile_absence.message_style = "neutral"
            notes.append("High neuroticism softened absence reaction style")
        
        # Increase intensity but NOT frequency
        current_intensity = intensity_to_number(profile_absence.max_intensity)
        profile_absence.max_intensity = number_to_intensity(current_intensity + 1)
        
        # Softer phrasing: reduce directness if not already "direct"
        if base.derived_from.communication_style != "Direct":
            ext.phrasing.directness = int(clamp(ext.phrasing.directness - 1, 1, 3))
    
    # High conscientiousness (C > 0.8)
    if C > 0.8:
        # Reduce absence intensity (more composed)
        current_intensity = intensity_to_number(profile_absence.max_intensity)
        profile_absence.max_intensity = number_to_intensity(current_intensity - 1)
        
        # Reduce protectiveness unless base emotional style is "Protective"
        if base.derived_from.emotional_style != "Protective":
            ext.affection.protectiveness = int(clamp(ext.affection.protectiveness - 1, 0, 3))
        
        notes.append("High conscientiousness increased composure")
    
    # =========================================================================
    # C) INITIATIVE FREQUENCY (healthy, no spam)
    # =========================================================================
    
    # Probability boost: E*0.04 + A*0.02, clamped to [-0.02, 0.08]
    prob_boost = clamp(E * 0.04 + A * 0.02, -0.02, 0.08)
    ext.initiation_ext.probability_boost = clamp(prob_boost, 0, 0.12)
    
    # Cooldown hours: reduced by E
    cooldown_delta = round(E * 1.2)
    profile_initiation.cooldown_hours = int(clamp(
        profile_initiation.cooldown_hours - cooldown_delta, 3, 12
    ))
    
    # Min intimacy to initiate: reduced by E
    intimacy_delta = round(E * 4)
    ext.initiation_ext.min_intimacy_to_initiate = int(clamp(
        ext.initiation_ext.min_intimacy_to_initiate - intimacy_delta, 10, 35
    ))
    
    # Apply probability boost to base frequency
    profile_initiation.base_frequency = clamp(
        profile_initiation.base_frequency + ext.initiation_ext.probability_boost, 0, 0.35
    )
    
    if E > 0.5:
        notes.append("High extraversion increased initiation frequency")
    
    # =========================================================================
    # D) VARIETY / NOVELTY (openness)
    # =========================================================================
    
    if O > 0.8:
        # Increase teasing if base allows
        if (base.derived_from.communication_style == "Teasing" or 
            base.derived_from.emotional_style == "Playful"):
            ext.phrasing.teasing_level = int(clamp(ext.phrasing.teasing_level + 1, 0, 3))
            notes.append("High openness increased playful variety")
    elif O < -0.8:
        # Reduce teasing, prefer simpler messages
        ext.phrasing.teasing_level = int(clamp(ext.phrasing.teasing_level - 1, 0, 3))
        
        # Cap sentence length at medium unless EXCLUSIVE
        if (relationship.level != "EXCLUSIVE" and 
            profile_response.avg_sentence_length == "long"):
            profile_response.avg_sentence_length = "medium"
    
    # =========================================================================
    # E) STEADINESS / STRUCTURE (conscientiousness)
    # =========================================================================
    
    if C > 0.8:
        # Tend toward medium sentence length
        is_soft_intimate = (
            base.derived_from.communication_style == "Soft" and
            level_index(relationship.level) >= level_index("INTIMATE")
        )
        
        if not is_soft_intimate and profile_response.avg_sentence_length == "long":
            profile_response.avg_sentence_length = "medium"
        
        # Increase directness if already direct
        if base.derived_from.communication_style == "Direct":
            ext.phrasing.directness = int(clamp(ext.phrasing.directness + 1, 1, 3))
        
        # Reduce emoji rate if > 1
        if ext.phrasing.emoji_rate > 1:
            ext.phrasing.emoji_rate = int(clamp(ext.phrasing.emoji_rate - 1, 0, 3))
            profile_emoji.frequency = rate_to_emoji_frequency(ext.phrasing.emoji_rate)
    
    # =========================================================================
    # RELATIONSHIP-LEVEL GATING (final pass)
    # =========================================================================
    
    if relationship.level == "STRANGER":
        # Enforce conservative settings
        ext.initiation_ext.probability_boost = 0
        profile_initiation.base_frequency = base.initiation.base_frequency
        profile_initiation.cooldown_hours = max(profile_initiation.cooldown_hours, 8)
        profile_pet_names.enabled = False
        ext.phrasing.flirtiness = min(ext.phrasing.flirtiness, 1)
        
        notes.append("Stranger level: conservative initiation enforced")
    
    # Pace-based flirtiness caps
    if base.derived_from.relationship_pace == "Slow":
        max_flirtiness_at_level = {
            "STRANGER": 0,
            "FAMILIAR": 1,
            "CLOSE": 1,
            "INTIMATE": 2,
            "EXCLUSIVE": 3,
        }
        cap = max_flirtiness_at_level.get(relationship.level, 1)
        ext.phrasing.flirtiness = min(ext.phrasing.flirtiness, cap)
    
    # =========================================================================
    # ADD SUMMARY NOTES
    # =========================================================================
    
    if ext.phrasing.emoji_rate != orig_emoji:
        if ext.phrasing.emoji_rate > orig_emoji:
            notes.append("Big Five increased emoji usage")
        else:
            notes.append("Big Five decreased emoji usage")
    
    if ext.affection.reassurance_level != orig_reassurance:
        if ext.affection.reassurance_level > orig_reassurance:
            notes.append("Big Five increased reassurance behavior")
    
    # Limit notes to 6 max
    final_notes = notes[:6]
    
    # =========================================================================
    # ASSEMBLE FINAL PROFILE
    # =========================================================================
    
    profile = ModulatedBehaviorProfile(
        tone=profile_tone,
        message_styling=MessageStylingProfile(
            response=profile_response,
            emoji=profile_emoji,
            pet_names=profile_pet_names,
        ),
        relationship=base.relationship,  # Not modified by Big Five
        initiation=profile_initiation,
        absence=profile_absence,
        prompt=PromptBehavior(
            tone=profile_tone,
            response_patterns=list(base.prompt.response_patterns),
            avoid_patterns=list(base.prompt.avoid_patterns),
            contextual_rules=list(base.prompt.contextual_rules),
        ),
        derived_from=base.derived_from,
        extensions=ext,
        modulation_applied=True,
    )
    
    return ModulationResult(profile=profile, notes=final_notes)


def maybe_apply_big_five_modulation(
    base: BehaviorProfile,
    big_five: Optional[BigFiveProfile],
    relationship: Optional[RelationshipState],
    hours_inactive: float = 0.0
) -> BehaviorProfile:
    """
    Apply Big Five modulation if BigFiveProfile is provided.
    Returns unmodified base profile if big_five is None.
    """
    if big_five is None or relationship is None:
        return base
    
    result = apply_big_five_modulation(base, big_five, relationship, hours_inactive)
    return result.profile


# =============================================================================
# UTILITY: CREATE BIG FIVE FROM DICT
# =============================================================================

def big_five_from_dict(data: Dict[str, float]) -> BigFiveProfile:
    """Create BigFiveProfile from a dictionary."""
    values = BigFive(
        openness=data.get("openness", 50),
        conscientiousness=data.get("conscientiousness", 50),
        extraversion=data.get("extraversion", 50),
        agreeableness=data.get("agreeableness", 50),
        neuroticism=data.get("neuroticism", 50),
    )
    return BigFiveProfile(values=values, source="trait_mapped")


def relationship_state_from_dict(data: Dict[str, Any]) -> RelationshipState:
    """Create RelationshipState from a dictionary."""
    return RelationshipState(
        trust=data.get("trust", 10),
        intimacy=data.get("intimacy", 10),
        level=data.get("level", "STRANGER"),
        last_interaction_at=data.get("last_interaction_at"),
        milestones_reached=data.get("milestones_reached", []),
    )
