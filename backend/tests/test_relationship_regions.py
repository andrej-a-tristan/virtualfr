"""Tests for the relationship region system."""
import pytest
from app.services.relationship_regions import (
    MAX_RELATIONSHIP_LEVEL,
    REGIONS,
    Region,
    clamp_level,
    get_region_for_level,
)


def test_max_level_is_200():
    assert MAX_RELATIONSHIP_LEVEL == 200


def test_regions_count_is_nine():
    assert len(REGIONS) == 9


def test_regions_cover_full_range():
    """Every level from 1 to 200 must land in exactly one region."""
    for lvl in range(1, MAX_RELATIONSHIP_LEVEL + 1):
        matches = [r for r in REGIONS if r.min_level <= lvl <= r.max_level]
        assert len(matches) == 1, f"Level {lvl} matched {len(matches)} regions"


def test_level_zero_maps_to_early_connection():
    region = get_region_for_level(0)
    assert region.key == "EARLY_CONNECTION"


def test_level_one_maps_to_early_connection():
    region = get_region_for_level(1)
    assert region.key == "EARLY_CONNECTION"


def test_level_ten_maps_to_early_connection():
    region = get_region_for_level(10)
    assert region.key == "EARLY_CONNECTION"


def test_level_eleven_maps_to_comfort_familiarity():
    region = get_region_for_level(11)
    assert region.key == "COMFORT_FAMILIARITY"


def test_level_seventy_maps_to_emotional_trust():
    region = get_region_for_level(70)
    assert region.key == "EMOTIONAL_TRUST"


def test_level_200_maps_to_enduring_companionship():
    region = get_region_for_level(200)
    assert region.key == "ENDURING_COMPANIONSHIP"


def test_clamp_level_negative():
    assert clamp_level(-5) == 0


def test_negative_five_region_is_early_connection():
    region = get_region_for_level(-5)
    assert region.key == "EARLY_CONNECTION"


def test_clamp_level_above_max():
    assert clamp_level(999) == MAX_RELATIONSHIP_LEVEL


def test_level_999_region_is_enduring_companionship():
    region = get_region_for_level(999)
    assert region.key == "ENDURING_COMPANIONSHIP"


def test_region_boundaries():
    """Verify every region boundary is correct."""
    expected = [
        ("EARLY_CONNECTION", 1, 10),
        ("COMFORT_FAMILIARITY", 11, 25),
        ("GROWING_CLOSENESS", 26, 45),
        ("EMOTIONAL_TRUST", 46, 70),
        ("DEEP_BOND", 71, 105),
        ("MUTUAL_DEVOTION", 106, 135),
        ("INTIMATE_PARTNERSHIP", 136, 165),
        ("SHARED_LIFE", 166, 185),
        ("ENDURING_COMPANIONSHIP", 186, 200),
    ]
    for i, (key, mn, mx) in enumerate(expected):
        r = REGIONS[i]
        assert r.key == key
        assert r.min_level == mn
        assert r.max_level == mx
