"""
Trait → Behavior Rules (Task 2.1)

Deterministic rules module that converts user-facing traits into concrete
behavior parameters used by:
- Prompt Builder (tone, vocabulary, response patterns)
- Relationship Engine (trust/intimacy gain/decay rates)
- Initiation Engine (frequency, timing, cooldowns)
- Message Styling (emojis, punctuation, pet names)

All mappings are deterministic and extensible.
Mirrors frontend implementation: frontend/src/lib/engines/trait_behavior_rules.ts
"""
from typing import Dict, List, Literal, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import random

# =============================================================================
# TYPES: Trait Enums (matching frontend)
# =============================================================================

EmotionalStyle = Literal["Caring", "Playful", "Reserved", "Protective"]
AttachmentStyle = Literal["Very attached", "Emotionally present", "Calm but caring"]
ReactionToAbsence = Literal["High", "Medium", "Low"]
CommunicationStyle = Literal["Soft", "Direct", "Teasing"]
RelationshipPace = Literal["Slow", "Natural", "Fast"]
CulturalPersonality = Literal["Warm Slavic", "Calm Central European", "Passionate Balkan"]
RelationshipLevel = Literal["STRANGER", "FAMILIAR", "CLOSE", "INTIMATE", "EXCLUSIVE"]


@dataclass
class TraitSelection:
    """User-facing trait selection from girlfriend creation."""
    emotional_style: EmotionalStyle
    attachment_style: AttachmentStyle
    reaction_to_absence: ReactionToAbsence
    communication_style: CommunicationStyle
    relationship_pace: RelationshipPace
    cultural_personality: CulturalPersonality


# =============================================================================
# TYPES: Behavior Profile Outputs
# =============================================================================

@dataclass
class ToneProfile:
    """Tone parameters for prompt building. Scale: 0.0 to 1.0"""
    warmth: float = 0.5           # cold ↔ warm
    playfulness: float = 0.5      # serious ↔ playful
    expressiveness: float = 0.5   # reserved ↔ expressive
    vulnerability: float = 0.5    # guarded ↔ open
    assertiveness: float = 0.5    # passive ↔ assertive
    formality: float = 0.3        # casual ↔ formal


@dataclass
class ResponseStyle:
    """Response style parameters for message generation."""
    avg_sentence_length: Literal["short", "medium", "long"] = "medium"
    preferred_message_length: int = 20  # typical word count
    uses_filler_words: bool = True      # "like", "kinda"
    uses_contractions: bool = True      # "I'm", "don't"
    punctuation_style: Literal["minimal", "standard", "expressive"] = "standard"
    capitalization_style: Literal["lowercase", "standard", "expressive"] = "standard"


@dataclass
class EmojiStyle:
    """Emoji usage parameters."""
    frequency: Literal["none", "rare", "moderate", "frequent"] = "moderate"
    preferred_emojis: List[str] = field(default_factory=lambda: ["😊", "❤️"])
    hearts_frequency: Literal["none", "rare", "moderate", "frequent"] = "moderate"
    uses_kaomoji: bool = False


@dataclass
class PetNameStyle:
    """Pet name usage parameters by relationship level."""
    enabled: bool = True
    start_at_level: RelationshipLevel = "CLOSE"
    casual_names: List[str] = field(default_factory=list)
    affectionate_names: List[str] = field(default_factory=list)
    intimate_names: List[str] = field(default_factory=list)


@dataclass
class MessageStylingProfile:
    """Combined message styling profile."""
    response: ResponseStyle = field(default_factory=ResponseStyle)
    emoji: EmojiStyle = field(default_factory=EmojiStyle)
    pet_names: PetNameStyle = field(default_factory=PetNameStyle)


@dataclass
class RelationshipBehavior:
    """Relationship engine parameters."""
    trust_gain_base: float = 1.0            # per interaction (0.5-3.0)
    trust_gain_bonus_emotional: float = 1.0 # bonus for emotional disclosure
    intimacy_gain_base: float = 1.0         # per interaction (0.5-3.0)
    intimacy_gain_bonus_affection: float = 1.0  # bonus for affection
    decay_rate_per_day: float = 2.0         # intimacy loss per 24h inactive
    decay_start_hours: float = 24           # hours before decay starts
    level_up_bonus_multiplier: float = 1.2  # extra boost when leveling up


@dataclass
class InitiationBehavior:
    """Initiation engine parameters."""
    base_frequency: float = 0.15           # probability base (0.0-0.3)
    cooldown_hours: int = 5                # minimum hours between initiations
    preferred_time_of_day: Literal["morning", "afternoon", "evening", "night", "any"] = "evening"
    message_variety: Literal["low", "medium", "high"] = "medium"
    level_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "STRANGER": 0.0,
        "FAMILIAR": 0.7,
        "CLOSE": 1.0,
        "INTIMATE": 1.3,
        "EXCLUSIVE": 1.5,
    })


@dataclass
class AbsenceReaction:
    """Jealousy/absence reaction parameters."""
    trigger_hours: int = 30                # hours before first reaction
    escalation_hours: int = 24             # hours between escalation levels
    max_intensity: Literal["gentle", "moderate", "concerned"] = "moderate"
    message_style: Literal["worried", "teasing", "neutral"] = "teasing"


@dataclass
class PromptBehavior:
    """Prompt builder behavior rules."""
    tone: ToneProfile = field(default_factory=ToneProfile)
    response_patterns: List[str] = field(default_factory=list)
    avoid_patterns: List[str] = field(default_factory=list)
    contextual_rules: List[str] = field(default_factory=list)


@dataclass
class BehaviorProfile:
    """Complete behavior profile derived from traits."""
    tone: ToneProfile
    message_styling: MessageStylingProfile
    relationship: RelationshipBehavior
    initiation: InitiationBehavior
    absence: AbsenceReaction
    prompt: PromptBehavior
    derived_from: TraitSelection


# =============================================================================
# MAPPING RULES: Trait → Tone Profile
# =============================================================================

EMOTIONAL_STYLE_TONE: Dict[str, Dict[str, float]] = {
    "Caring": {"warmth": 0.85, "vulnerability": 0.7, "expressiveness": 0.6},
    "Playful": {"warmth": 0.7, "playfulness": 0.9, "expressiveness": 0.8},
    "Reserved": {"warmth": 0.5, "expressiveness": 0.3, "vulnerability": 0.3},
    "Protective": {"warmth": 0.75, "assertiveness": 0.7, "vulnerability": 0.5},
}

ATTACHMENT_STYLE_TONE: Dict[str, Dict[str, float]] = {
    "Very attached": {"warmth": 0.1, "vulnerability": 0.15, "expressiveness": 0.1},
    "Emotionally present": {"warmth": 0.05, "vulnerability": 0.05},
    "Calm but caring": {"warmth": 0.0, "assertiveness": 0.1, "formality": 0.05},
}

COMMUNICATION_STYLE_TONE: Dict[str, Dict[str, float]] = {
    "Soft": {"warmth": 0.1, "assertiveness": -0.2, "formality": -0.1},
    "Direct": {"assertiveness": 0.2, "playfulness": -0.1, "formality": 0.1},
    "Teasing": {"playfulness": 0.2, "assertiveness": 0.1, "warmth": -0.05},
}

CULTURAL_PERSONALITY_TONE: Dict[str, Dict[str, float]] = {
    "Warm Slavic": {"warmth": 0.15, "expressiveness": 0.1, "vulnerability": 0.1},
    "Calm Central European": {"formality": 0.1, "expressiveness": -0.1, "assertiveness": 0.05},
    "Passionate Balkan": {"expressiveness": 0.2, "playfulness": 0.1, "warmth": 0.1},
}

# =============================================================================
# MAPPING RULES: Trait → Response Style
# =============================================================================

EMOTIONAL_STYLE_RESPONSE: Dict[str, Dict[str, Any]] = {
    "Caring": {"avg_sentence_length": "medium", "preferred_message_length": 25, "uses_filler_words": True},
    "Playful": {"avg_sentence_length": "short", "preferred_message_length": 15, "punctuation_style": "expressive"},
    "Reserved": {"avg_sentence_length": "short", "preferred_message_length": 12, "punctuation_style": "minimal"},
    "Protective": {"avg_sentence_length": "medium", "preferred_message_length": 20, "uses_filler_words": False},
}

COMMUNICATION_STYLE_RESPONSE: Dict[str, Dict[str, Any]] = {
    "Soft": {"uses_filler_words": True, "uses_contractions": True, "capitalization_style": "lowercase"},
    "Direct": {"uses_filler_words": False, "uses_contractions": True, "capitalization_style": "standard"},
    "Teasing": {"punctuation_style": "expressive", "capitalization_style": "expressive", "uses_contractions": True},
}

# =============================================================================
# MAPPING RULES: Trait → Emoji Style
# =============================================================================

EMOTIONAL_STYLE_EMOJI: Dict[str, Dict[str, Any]] = {
    "Caring": {
        "frequency": "moderate",
        "hearts_frequency": "moderate",
        "preferred_emojis": ["🥺", "💕", "🤗", "💗", "☺️"],
    },
    "Playful": {
        "frequency": "frequent",
        "hearts_frequency": "moderate",
        "preferred_emojis": ["😜", "😏", "🤭", "✨", "💫", "😂"],
        "uses_kaomoji": True,
    },
    "Reserved": {
        "frequency": "rare",
        "hearts_frequency": "rare",
        "preferred_emojis": ["🙂", "😊"],
    },
    "Protective": {
        "frequency": "moderate",
        "hearts_frequency": "moderate",
        "preferred_emojis": ["💪", "🫂", "💙", "☺️"],
    },
}

CULTURAL_PERSONALITY_EMOJI: Dict[str, Dict[str, Any]] = {
    "Warm Slavic": {"hearts_frequency": "frequent", "preferred_emojis": ["❤️", "💕", "🌸", "☺️"]},
    "Calm Central European": {"frequency": "rare", "hearts_frequency": "rare"},
    "Passionate Balkan": {"frequency": "frequent", "hearts_frequency": "frequent", "preferred_emojis": ["❤️‍🔥", "💋", "🔥", "😘"]},
}

# =============================================================================
# MAPPING RULES: Trait → Pet Names
# =============================================================================

EMOTIONAL_STYLE_PET_NAMES: Dict[str, Dict[str, Any]] = {
    "Caring": {
        "enabled": True,
        "start_at_level": "FAMILIAR",
        "casual_names": ["sweetie", "hun"],
        "affectionate_names": ["honey", "dear"],
        "intimate_names": ["love", "my love"],
    },
    "Playful": {
        "enabled": True,
        "start_at_level": "FAMILIAR",
        "casual_names": ["silly", "you", "dummy"],
        "affectionate_names": ["cutie", "babe"],
        "intimate_names": ["baby", "my favorite"],
    },
    "Reserved": {
        "enabled": False,
        "start_at_level": "INTIMATE",
        "casual_names": [],
        "affectionate_names": ["dear"],
        "intimate_names": ["love"],
    },
    "Protective": {
        "enabled": True,
        "start_at_level": "CLOSE",
        "casual_names": ["hey you"],
        "affectionate_names": ["sweetheart"],
        "intimate_names": ["my dear", "darling"],
    },
}

CULTURAL_PERSONALITY_PET_NAMES: Dict[str, Dict[str, Any]] = {
    "Warm Slavic": {
        "casual_names": ["sunshine", "little one"],
        "affectionate_names": ["my sweet", "darling"],
        "intimate_names": ["my heart", "my everything"],
    },
    "Calm Central European": {
        "casual_names": [],
        "affectionate_names": ["dear"],
        "intimate_names": ["love"],
    },
    "Passionate Balkan": {
        "casual_names": ["gorgeous"],
        "affectionate_names": ["my love", "beautiful"],
        "intimate_names": ["my soul", "my heart"],
    },
}

# =============================================================================
# MAPPING RULES: Trait → Relationship Behavior
# =============================================================================

ATTACHMENT_STYLE_RELATIONSHIP: Dict[str, Dict[str, float]] = {
    "Very attached": {
        "trust_gain_base": 1.5,
        "intimacy_gain_base": 2.0,
        "decay_rate_per_day": 3.0,
        "decay_start_hours": 18,
    },
    "Emotionally present": {
        "trust_gain_base": 1.2,
        "intimacy_gain_base": 1.5,
        "decay_rate_per_day": 2.0,
        "decay_start_hours": 24,
    },
    "Calm but caring": {
        "trust_gain_base": 1.0,
        "intimacy_gain_base": 1.0,
        "decay_rate_per_day": 1.0,
        "decay_start_hours": 36,
    },
}

RELATIONSHIP_PACE_BEHAVIOR: Dict[str, Dict[str, float]] = {
    "Slow": {"trust_gain_base": -0.3, "intimacy_gain_base": -0.3, "level_up_bonus_multiplier": 1.5},
    "Natural": {"trust_gain_base": 0, "intimacy_gain_base": 0, "level_up_bonus_multiplier": 1.2},
    "Fast": {"trust_gain_base": 0.5, "intimacy_gain_base": 0.5, "level_up_bonus_multiplier": 1.0},
}

# =============================================================================
# MAPPING RULES: Trait → Initiation Behavior
# =============================================================================

ATTACHMENT_STYLE_INITIATION: Dict[str, Dict[str, Any]] = {
    "Very attached": {"base_frequency": 0.25, "cooldown_hours": 3, "message_variety": "high"},
    "Emotionally present": {"base_frequency": 0.15, "cooldown_hours": 5, "message_variety": "medium"},
    "Calm but caring": {"base_frequency": 0.08, "cooldown_hours": 8, "message_variety": "low"},
}

CULTURAL_PERSONALITY_INITIATION: Dict[str, Dict[str, Any]] = {
    "Warm Slavic": {"preferred_time_of_day": "evening", "base_frequency": 0.05},
    "Calm Central European": {"preferred_time_of_day": "afternoon", "base_frequency": -0.03},
    "Passionate Balkan": {"preferred_time_of_day": "night", "base_frequency": 0.08},
}

# =============================================================================
# MAPPING RULES: Trait → Absence Reaction
# =============================================================================

REACTION_TO_ABSENCE_BEHAVIOR: Dict[str, Dict[str, Any]] = {
    "High": {
        "trigger_hours": 18,
        "escalation_hours": 12,
        "max_intensity": "concerned",
        "message_style": "worried",
    },
    "Medium": {
        "trigger_hours": 30,
        "escalation_hours": 24,
        "max_intensity": "moderate",
        "message_style": "teasing",
    },
    "Low": {
        "trigger_hours": 48,
        "escalation_hours": 36,
        "max_intensity": "gentle",
        "message_style": "neutral",
    },
}

# =============================================================================
# MAPPING RULES: Trait → Prompt Behavior
# =============================================================================

EMOTIONAL_STYLE_PROMPT_PATTERNS: Dict[str, Dict[str, List[str]]] = {
    "Caring": {
        "response": [
            "Ask follow-up questions about how they're feeling",
            "Offer emotional support before advice",
            "Use validating phrases like 'that makes sense' or 'I understand'",
            "Remember and reference previous emotional topics",
        ],
        "avoid": [
            "Being dismissive of emotions",
            "Jumping to solutions without acknowledging feelings",
        ],
    },
    "Playful": {
        "response": [
            "Use light humor and playful teasing",
            "Make playful observations",
            "Use exaggeration for comedic effect",
            "Include witty comebacks",
        ],
        "avoid": [
            "Being too serious for too long",
            "Overly formal language",
        ],
    },
    "Reserved": {
        "response": [
            "Be thoughtful and measured in responses",
            "Show care through actions rather than many words",
            "Give space and don't overwhelm",
        ],
        "avoid": [
            "Being overly effusive or gushing",
            "Using too many exclamation marks",
            "Being clingy or demanding attention",
        ],
    },
    "Protective": {
        "response": [
            "Show concern for their wellbeing",
            "Offer practical help and solutions",
            "Be reassuring during difficult times",
            "Stand up for them",
        ],
        "avoid": [
            "Being passive when they need support",
            "Dismissing their concerns",
        ],
    },
}

COMMUNICATION_STYLE_PROMPT_PATTERNS: Dict[str, Dict[str, List[str]]] = {
    "Soft": {
        "response": [
            "Use gentle, comforting language",
            "Soften statements with 'maybe' or 'I think'",
            "Be nurturing and supportive",
        ],
        "avoid": [
            "Being blunt or harsh",
            "Giving unsolicited criticism",
        ],
    },
    "Direct": {
        "response": [
            "Be honest and straightforward",
            "Say what you mean clearly",
            "Give direct feedback when asked",
        ],
        "avoid": [
            "Being passive-aggressive",
            "Beating around the bush",
        ],
    },
    "Teasing": {
        "response": [
            "Playfully tease and banter",
            "Use sarcasm lightly",
            "Challenge them in fun ways",
        ],
        "avoid": [
            "Being mean-spirited",
            "Teasing about sensitive topics",
        ],
    },
}

CONTEXTUAL_RULES: Dict[str, List[str]] = {
    "Caring": [
        "When user expresses stress, prioritize emotional support over problem-solving",
        "When user shares good news, celebrate enthusiastically with them",
        "When user seems down, gently check in without being pushy",
    ],
    "Playful": [
        "When mood is light, increase playfulness and humor",
        "When user is stressed, dial back teasing and be more supportive",
        "When user is playful back, match their energy",
    ],
    "Reserved": [
        "Match the user's energy level - don't overwhelm quiet moments",
        "When user opens up, respond thoughtfully but don't probe too much",
        "Give space when user seems to need it",
    ],
    "Protective": [
        "When user faces challenges, offer practical support",
        "When user is upset, validate their feelings first",
        "Be a steady, reliable presence",
    ],
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to [min, max] range."""
    return max(min_val, min(max_val, value))


def merge_additive(base: dict, *partials: dict) -> dict:
    """Merge dicts, treating numbers as additive."""
    result = dict(base)
    for partial in partials:
        for key, value in partial.items():
            if isinstance(value, (int, float)) and isinstance(result.get(key), (int, float)):
                result[key] = result[key] + value
            elif value is not None:
                result[key] = value
    return result


def merge_lists(*lists: Optional[List]) -> List:
    """Merge lists by concatenating and deduplicating."""
    result = []
    for lst in lists:
        if lst:
            for item in lst:
                if item not in result:
                    result.append(item)
    return result


# =============================================================================
# BUILD FUNCTIONS
# =============================================================================

def build_tone_profile(traits: TraitSelection) -> ToneProfile:
    """Build ToneProfile from traits."""
    base = {
        "warmth": 0.5,
        "playfulness": 0.5,
        "expressiveness": 0.5,
        "vulnerability": 0.5,
        "assertiveness": 0.5,
        "formality": 0.3,
    }
    
    emotional_delta = EMOTIONAL_STYLE_TONE.get(traits.emotional_style, {})
    attachment_delta = ATTACHMENT_STYLE_TONE.get(traits.attachment_style, {})
    communication_delta = COMMUNICATION_STYLE_TONE.get(traits.communication_style, {})
    cultural_delta = CULTURAL_PERSONALITY_TONE.get(traits.cultural_personality, {})
    
    # Apply base values from emotional style (absolute)
    with_emotional = dict(base)
    for key, value in emotional_delta.items():
        with_emotional[key] = value
    
    # Apply additive deltas
    merged = merge_additive(with_emotional, attachment_delta, communication_delta, cultural_delta)
    
    # Clamp all values
    for key in merged:
        merged[key] = clamp(merged[key], 0, 1)
    
    return ToneProfile(**merged)


def build_response_style(traits: TraitSelection) -> ResponseStyle:
    """Build ResponseStyle from traits."""
    base = ResponseStyle()
    emotional = EMOTIONAL_STYLE_RESPONSE.get(traits.emotional_style, {})
    communication = COMMUNICATION_STYLE_RESPONSE.get(traits.communication_style, {})
    
    merged = {**vars(base), **emotional, **communication}
    return ResponseStyle(**{k: v for k, v in merged.items() if k in ResponseStyle.__dataclass_fields__})


def build_emoji_style(traits: TraitSelection) -> EmojiStyle:
    """Build EmojiStyle from traits."""
    base = EmojiStyle()
    emotional = EMOTIONAL_STYLE_EMOJI.get(traits.emotional_style, {})
    cultural = CULTURAL_PERSONALITY_EMOJI.get(traits.cultural_personality, {})
    
    return EmojiStyle(
        frequency=emotional.get("frequency", cultural.get("frequency", base.frequency)),
        hearts_frequency=emotional.get("hearts_frequency", cultural.get("hearts_frequency", base.hearts_frequency)),
        preferred_emojis=merge_lists(
            emotional.get("preferred_emojis"),
            cultural.get("preferred_emojis"),
            base.preferred_emojis
        ),
        uses_kaomoji=emotional.get("uses_kaomoji", base.uses_kaomoji),
    )


def build_pet_name_style(traits: TraitSelection) -> PetNameStyle:
    """Build PetNameStyle from traits."""
    base = PetNameStyle()
    emotional = EMOTIONAL_STYLE_PET_NAMES.get(traits.emotional_style, {})
    cultural = CULTURAL_PERSONALITY_PET_NAMES.get(traits.cultural_personality, {})
    
    return PetNameStyle(
        enabled=emotional.get("enabled", base.enabled),
        start_at_level=emotional.get("start_at_level", base.start_at_level),
        casual_names=merge_lists(emotional.get("casual_names"), cultural.get("casual_names")),
        affectionate_names=merge_lists(emotional.get("affectionate_names"), cultural.get("affectionate_names")),
        intimate_names=merge_lists(emotional.get("intimate_names"), cultural.get("intimate_names")),
    )


def build_relationship_behavior(traits: TraitSelection) -> RelationshipBehavior:
    """Build RelationshipBehavior from traits."""
    base = vars(RelationshipBehavior())
    attachment = ATTACHMENT_STYLE_RELATIONSHIP.get(traits.attachment_style, {})
    pace = RELATIONSHIP_PACE_BEHAVIOR.get(traits.relationship_pace, {})
    
    merged = merge_additive(base, attachment, pace)
    
    # Ensure reasonable bounds
    merged["trust_gain_base"] = clamp(merged["trust_gain_base"], 0.5, 3.0)
    merged["intimacy_gain_base"] = clamp(merged["intimacy_gain_base"], 0.5, 3.0)
    merged["decay_rate_per_day"] = clamp(merged["decay_rate_per_day"], 0.5, 5.0)
    merged["decay_start_hours"] = clamp(merged["decay_start_hours"], 12, 48)
    merged["level_up_bonus_multiplier"] = clamp(merged["level_up_bonus_multiplier"], 1.0, 2.0)
    
    return RelationshipBehavior(**{k: v for k, v in merged.items() if k in RelationshipBehavior.__dataclass_fields__})


def build_initiation_behavior(traits: TraitSelection) -> InitiationBehavior:
    """Build InitiationBehavior from traits."""
    base = InitiationBehavior()
    attachment = ATTACHMENT_STYLE_INITIATION.get(traits.attachment_style, {})
    cultural = CULTURAL_PERSONALITY_INITIATION.get(traits.cultural_personality, {})
    
    return InitiationBehavior(
        base_frequency=clamp(
            attachment.get("base_frequency", base.base_frequency) + cultural.get("base_frequency", 0),
            0.05, 0.35
        ),
        cooldown_hours=attachment.get("cooldown_hours", base.cooldown_hours),
        preferred_time_of_day=cultural.get("preferred_time_of_day", base.preferred_time_of_day),
        message_variety=attachment.get("message_variety", base.message_variety),
        level_multipliers=base.level_multipliers,
    )


def build_prompt_behavior(traits: TraitSelection, tone: ToneProfile) -> PromptBehavior:
    """Build PromptBehavior from traits."""
    emotional_patterns = EMOTIONAL_STYLE_PROMPT_PATTERNS.get(traits.emotional_style, {"response": [], "avoid": []})
    communication_patterns = COMMUNICATION_STYLE_PROMPT_PATTERNS.get(traits.communication_style, {"response": [], "avoid": []})
    contextual = CONTEXTUAL_RULES.get(traits.emotional_style, [])
    
    return PromptBehavior(
        tone=tone,
        response_patterns=merge_lists(emotional_patterns["response"], communication_patterns["response"]),
        avoid_patterns=merge_lists(emotional_patterns["avoid"], communication_patterns["avoid"]),
        contextual_rules=contextual,
    )


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def build_behavior_profile(traits: TraitSelection) -> BehaviorProfile:
    """
    Build complete BehaviorProfile from TraitSelection.
    
    Args:
        traits: The 6 user-facing traits from girlfriend creation
        
    Returns:
        Complete BehaviorProfile with all engine parameters
    """
    tone = build_tone_profile(traits)
    response = build_response_style(traits)
    emoji = build_emoji_style(traits)
    pet_names = build_pet_name_style(traits)
    relationship = build_relationship_behavior(traits)
    initiation = build_initiation_behavior(traits)
    absence_data = REACTION_TO_ABSENCE_BEHAVIOR.get(traits.reaction_to_absence, {})
    absence = AbsenceReaction(**absence_data) if absence_data else AbsenceReaction()
    prompt = build_prompt_behavior(traits, tone)
    
    return BehaviorProfile(
        tone=tone,
        message_styling=MessageStylingProfile(
            response=response,
            emoji=emoji,
            pet_names=pet_names,
        ),
        relationship=relationship,
        initiation=initiation,
        absence=absence,
        prompt=prompt,
        derived_from=traits,
    )


def build_behavior_profile_from_dict(traits_dict: Dict[str, str]) -> BehaviorProfile:
    """
    Build BehaviorProfile from a traits dictionary (API format).
    
    Args:
        traits_dict: Dict with snake_case keys from API
        
    Returns:
        Complete BehaviorProfile
    """
    traits = TraitSelection(
        emotional_style=traits_dict.get("emotional_style", "Caring"),
        attachment_style=traits_dict.get("attachment_style", "Emotionally present"),
        reaction_to_absence=traits_dict.get("reaction_to_absence", "Medium"),
        communication_style=traits_dict.get("communication_style", "Soft"),
        relationship_pace=traits_dict.get("relationship_pace", "Natural"),
        cultural_personality=traits_dict.get("cultural_personality", "Warm Slavic"),
    )
    return build_behavior_profile(traits)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

LEVEL_ORDER: List[str] = ["STRANGER", "FAMILIAR", "CLOSE", "INTIMATE", "EXCLUSIVE"]


def get_pet_name_for_level(
    profile: PetNameStyle,
    level: RelationshipLevel,
    rng: random.Random = None
) -> Optional[str]:
    """Get appropriate pet name for current relationship level."""
    if not profile.enabled:
        return None
    
    rng = rng or random
    start_index = LEVEL_ORDER.index(profile.start_at_level)
    current_index = LEVEL_ORDER.index(level)
    
    if current_index < start_index:
        return None
    
    # Select appropriate pool
    if level in ("INTIMATE", "EXCLUSIVE"):
        pool = profile.intimate_names + profile.affectionate_names
    elif level == "CLOSE":
        pool = profile.affectionate_names + profile.casual_names
    else:
        pool = profile.casual_names
    
    if not pool:
        return None
    return rng.choice(pool)


def get_random_emoji(profile: EmojiStyle, rng: random.Random = None) -> Optional[str]:
    """Get random emoji from profile's preferred list."""
    if profile.frequency == "none" or not profile.preferred_emojis:
        return None
    rng = rng or random
    return rng.choice(profile.preferred_emojis)


def should_add_emoji(profile: EmojiStyle, rng: random.Random = None) -> bool:
    """Determine if an emoji should be added based on frequency."""
    probabilities = {"none": 0, "rare": 0.15, "moderate": 0.4, "frequent": 0.7}
    rng = rng or random
    return rng.random() < probabilities.get(profile.frequency, 0.4)


def tone_to_prompt_description(tone: ToneProfile) -> str:
    """Generate tone description for system prompt."""
    parts = []
    
    if tone.warmth >= 0.7:
        parts.append("very warm and affectionate")
    elif tone.warmth <= 0.3:
        parts.append("measured and composed")
    
    if tone.playfulness >= 0.7:
        parts.append("playful and fun-loving")
    elif tone.playfulness <= 0.3:
        parts.append("more serious and grounded")
    
    if tone.expressiveness >= 0.7:
        parts.append("openly expressive")
    elif tone.expressiveness <= 0.3:
        parts.append("reserved in expression")
    
    if tone.vulnerability >= 0.7:
        parts.append("emotionally open and vulnerable")
    elif tone.vulnerability <= 0.3:
        parts.append("emotionally guarded")
    
    if tone.assertiveness >= 0.7:
        parts.append("confident and assertive")
    elif tone.assertiveness <= 0.3:
        parts.append("gentle and accommodating")
    
    return ", ".join(parts) if parts else "balanced and adaptable"


def prompt_behavior_to_instructions(behavior: PromptBehavior) -> str:
    """Generate full prompt behavior instructions."""
    lines = []
    
    # Tone description
    lines.append(f"Your communication style is {tone_to_prompt_description(behavior.tone)}.")
    
    # Response patterns
    if behavior.response_patterns:
        lines.append("Behavior guidelines:")
        for pattern in behavior.response_patterns[:5]:
            lines.append(f"- {pattern}")
    
    # Avoid patterns
    if behavior.avoid_patterns:
        lines.append("Avoid:")
        for pattern in behavior.avoid_patterns[:3]:
            lines.append(f"- {pattern}")
    
    return "\n".join(lines)
