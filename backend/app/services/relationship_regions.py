"""
Relationship Regions: canonical region system replacing legacy stages.

Max level: 200. Continuous integers map to 9 named regions.
Level 0 is treated as EARLY_CONNECTION (pre-bond).
"""
from dataclasses import dataclass
from typing import List


MAX_RELATIONSHIP_LEVEL = 200


@dataclass(frozen=True)
class Region:
    """A named relationship region spanning a level range."""
    key: str
    title: str
    min_level: int
    max_level: int


REGIONS: List[Region] = [
    Region(key="EARLY_CONNECTION",       title="Early Connection",       min_level=1,   max_level=10),
    Region(key="COMFORT_FAMILIARITY",    title="Comfort & Familiarity",  min_level=11,  max_level=25),
    Region(key="GROWING_CLOSENESS",      title="Growing Closeness",      min_level=26,  max_level=45),
    Region(key="EMOTIONAL_TRUST",        title="Emotional Trust",        min_level=46,  max_level=70),
    Region(key="DEEP_BOND",              title="Deep Bond",              min_level=71,  max_level=105),
    Region(key="MUTUAL_DEVOTION",        title="Mutual Devotion",        min_level=106, max_level=135),
    Region(key="INTIMATE_PARTNERSHIP",   title="Intimate Partnership",   min_level=136, max_level=165),
    Region(key="SHARED_LIFE",            title="Shared Life",            min_level=166, max_level=185),
    Region(key="ENDURING_COMPANIONSHIP", title="Enduring Companionship", min_level=186, max_level=200),
]


def clamp_level(level: int) -> int:
    """Clamp a level to the valid range [0, MAX_RELATIONSHIP_LEVEL]."""
    return max(0, min(MAX_RELATIONSHIP_LEVEL, level))


def get_region_for_level(level: int) -> Region:
    """Return the Region that contains the given level.

    Level 0 and any negative value map to EARLY_CONNECTION.
    Levels above MAX_RELATIONSHIP_LEVEL map to ENDURING_COMPANIONSHIP.
    """
    clamped = clamp_level(level)
    if clamped == 0:
        return REGIONS[0]  # EARLY_CONNECTION (pre-bond)
    for region in REGIONS:
        if region.min_level <= clamped <= region.max_level:
            return region
    # Fallback (should never happen with correct data)
    return REGIONS[-1]
