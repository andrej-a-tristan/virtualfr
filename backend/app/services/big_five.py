"""
Big Five Personality Mapping from 6 onboarding traits.
Maps traits to Big Five scores (0.0-1.0 range) using architecture-defined mapping.
"""
import json
from pathlib import Path
from typing import Dict

# Load mapping JSON
_MAPPING_PATH = Path(__file__).parent / "big_five_mapping.json"
with open(_MAPPING_PATH) as f:
    _MAPPING = json.load(f)

_BASE = _MAPPING["base"]
_TRAIT_MAPPINGS = _MAPPING["traits"]

# Trait name normalization: API uses "Very attached", JSON uses "very_attached"
_TRAIT_NORMALIZE = {
    # emotional_style
    "Caring": "caring",
    "Playful": "playful",
    "Reserved": "reserved",
    "Protective": "protective",
    # attachment_style
    "Very attached": "very_attached",
    "Emotionally present": "emotionally_present",
    "Calm but caring": "calm_but_caring",
    # reaction_to_absence
    "High": "miss_me_and_say_something",
    "Medium": "tease_me_about_it",
    "Low": "calm_but_check_in",
    # communication_style
    "Soft": "soft_and_comforting",
    "Direct": "honest_and_direct",
    "Teasing": "playful_and_teasing",
    # relationship_pace
    "Slow": "slow_emotional_buildup",
    "Natural": "natural_over_time",
    "Fast": "clear_attraction_early",
    # cultural_personality
    "Warm Slavic": "warm_slavic",
    "Calm Central European": "calm_central_european",
    "Passionate Balkan": "passionate_balkan",
}


def _normalize_trait_value(trait_key: str, value: str) -> str:
    """Normalize trait value from API format to JSON mapping format."""
    if trait_key == "reaction_to_absence":
        # Special mapping for reaction_to_absence
        return _TRAIT_NORMALIZE.get(value, value.lower().replace(" ", "_"))
    return _TRAIT_NORMALIZE.get(value, value.lower().replace(" ", "_"))


def map_traits_to_big_five(traits: Dict[str, str]) -> Dict[str, float]:
    """
    Map 6 onboarding traits to Big Five scores (0.0-1.0 range).
    
    Architecture:
    - Start with base values (neutral but warm)
    - Apply additive deltas from traits
    - Clamp to 0.0-1.0
    
    Returns: {
        "openness": float (0.0-1.0),
        "conscientiousness": float (0.0-1.0),
        "extraversion": float (0.0-1.0),
        "agreeableness": float (0.0-1.0),
        "neuroticism": float (0.0-1.0)
    }
    """
    # Start with base values
    big_five = {
        "openness": _BASE["openness"],
        "conscientiousness": _BASE["conscientiousness"],
        "extraversion": _BASE["extraversion"],
        "agreeableness": _BASE["agreeableness"],
        "neuroticism": _BASE["neuroticism"],
    }
    
    # Apply trait deltas
    for trait_key, trait_value in traits.items():
        if trait_key not in _TRAIT_MAPPINGS:
            continue
        
        normalized_value = _normalize_trait_value(trait_key, trait_value)
        trait_mapping = _TRAIT_MAPPINGS[trait_key]
        
        if normalized_value not in trait_mapping:
            continue
        
        deltas = trait_mapping[normalized_value]
        for dimension, delta in deltas.items():
            big_five[dimension] += delta
    
    # Clamp all values to 0.0-1.0
    for dimension in big_five:
        big_five[dimension] = max(0.0, min(1.0, big_five[dimension]))
    
    return big_five


def big_five_to_description(scores: Dict[str, float]) -> str:
    """Convert Big Five scores (0.0-1.0) to natural language description for ChatGPT."""
    parts = []
    o, c, e, a, n = scores["openness"], scores["conscientiousness"], scores["extraversion"], scores["agreeableness"], scores["neuroticism"]
    
    if o >= 0.7:
        parts.append("highly creative and curious")
    elif o <= 0.3:
        parts.append("prefers routine and familiarity")
    
    if c >= 0.7:
        parts.append("very organized and reliable")
    elif c <= 0.3:
        parts.append("more spontaneous and flexible")
    
    if e >= 0.7:
        parts.append("outgoing and expressive")
    elif e <= 0.3:
        parts.append("more reserved and introspective")
    
    if a >= 0.7:
        parts.append("warm, trusting, and caring")
    elif a <= 0.3:
        parts.append("more independent and direct")
    
    if n >= 0.7:
        parts.append("emotionally sensitive")
    elif n <= 0.3:
        parts.append("very emotionally stable and calm")
    
    return ", ".join(parts) if parts else "balanced personality"
