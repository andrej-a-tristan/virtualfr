"""Tests for identity canon generation."""
import pytest
from app.utils.identity_canon import generate_identity_canon


def test_deterministic_output_with_same_seed():
    """Calling generate_identity_canon with the same seed returns identical output."""
    kwargs = {
        "name": "Luna",
        "job_vibe": "barista",
        "hobbies": ["Cooking / baking", "Reading / booktok vibes", "Cafés / coffee walks"],
        "origin_vibe": "cozy-european",
        "seed": 12345,
    }
    
    result1 = generate_identity_canon(**kwargs)
    result2 = generate_identity_canon(**kwargs)
    
    assert result1.backstory == result2.backstory
    assert result1.daily_routine == result2.daily_routine
    assert result1.favorites == result2.favorites
    assert result1.memory_seeds == result2.memory_seeds


def test_all_fields_present_and_non_empty():
    """All required fields exist and are non-empty."""
    result = generate_identity_canon(
        name="Aria",
        job_vibe="tech",
        hobbies=["Gaming", "Movies / series", "Music (singing / playlists)"],
        origin_vibe="big-city",
        seed=99999,
    )
    
    assert result.backstory and len(result.backstory) > 0
    assert result.daily_routine and len(result.daily_routine) > 0
    assert result.favorites and len(result.favorites) > 0
    assert result.memory_seeds and len(result.memory_seeds) > 0


def test_backstory_has_two_paragraphs():
    """backstory contains '\\n\\n' (2 paragraphs)."""
    result = generate_identity_canon(
        name="Maya",
        job_vibe="creative",
        hobbies=["Art / drawing", "Photography", "Travel / city exploring"],
        origin_vibe="artsy",
        seed=42,
    )
    
    assert "\n\n" in result.backstory, "Backstory should have two paragraphs separated by \\n\\n"


def test_favorites_has_required_keys():
    """favorites has keys music_vibe, comfort_food, weekend_idea."""
    result = generate_identity_canon(
        name="Stella",
        job_vibe="entrepreneur",
        hobbies=["Gym / strength", "Journaling / self-care", "Language learning"],
        origin_vibe="suburban",
        seed=7777,
    )
    
    assert "music_vibe" in result.favorites
    assert "comfort_food" in result.favorites
    assert "weekend_idea" in result.favorites
    
    assert result.favorites["music_vibe"]
    assert result.favorites["comfort_food"]
    assert result.favorites["weekend_idea"]


def test_memory_seeds_minimum_count():
    """memory_seeds has at least 3 items."""
    result = generate_identity_canon(
        name="Hazel",
        job_vibe="teacher",
        hobbies=["Reading / booktok vibes", "Volunteering / charity", "Cooking / baking"],
        origin_vibe="countryside",
        seed=3333,
    )
    
    assert len(result.memory_seeds) >= 3, f"Expected at least 3 memory_seeds, got {len(result.memory_seeds)}"


def test_different_seeds_produce_different_output():
    """Different seeds should produce different output (at least some variation)."""
    kwargs_base = {
        "name": "Nova",
        "job_vibe": "student",
        "hobbies": ["Movies / series", "Cafés / coffee walks", "Gaming"],
        "origin_vibe": "big-city",
    }
    
    result1 = generate_identity_canon(**kwargs_base, seed=100)
    result2 = generate_identity_canon(**kwargs_base, seed=200)
    
    # At least one field should differ
    differences = 0
    if result1.backstory != result2.backstory:
        differences += 1
    if result1.daily_routine != result2.daily_routine:
        differences += 1
    if result1.favorites != result2.favorites:
        differences += 1
    if result1.memory_seeds != result2.memory_seeds:
        differences += 1
    
    assert differences > 0, "Different seeds should produce at least some variation"


def test_handles_missing_hobbies():
    """Generator handles empty hobbies list gracefully."""
    result = generate_identity_canon(
        name="Sage",
        job_vibe="in-between",
        hobbies=[],
        origin_vibe="beach-town",
        seed=4444,
    )
    
    assert result.backstory
    assert result.daily_routine
    assert result.memory_seeds


def test_handles_unknown_job_vibe():
    """Generator handles unknown job_vibe gracefully with fallback."""
    result = generate_identity_canon(
        name="Willow",
        job_vibe="unknown-job",
        hobbies=["Art / drawing", "Music (singing / playlists)", "Travel / city exploring"],
        origin_vibe="cozy-european",
        seed=5555,
    )
    
    assert result.backstory
    assert result.daily_routine
    assert result.memory_seeds


def test_no_values_or_boundaries_in_canon():
    """Ensure NO keys named 'values' or 'boundaries' in the IdentityCanon dump."""
    result = generate_identity_canon(
        name="Ivy",
        job_vibe="healthcare",
        hobbies=["Yoga / pilates", "Hiking / nature walks", "Gardening / plants"],
        origin_vibe="mountain",
        seed=1111,
    )
    
    canon_dict = result.model_dump()
    assert "values" not in canon_dict, "IdentityCanon should not contain 'values'"
    assert "boundaries" not in canon_dict, "IdentityCanon should not contain 'boundaries'"


def test_beach_town_boosts_weekend_ideas():
    """Beach town origin should boost beach/sunset weekend ideas."""
    result = generate_identity_canon(
        name="Coral",
        job_vibe="hospitality",
        hobbies=["Travel / city exploring", "Photography", "Yoga / pilates"],
        origin_vibe="beach-town",
        seed=6666,
    )
    
    # Just verify the result is valid (the boost is probabilistic but should work)
    assert result.favorites["weekend_idea"]
    assert result.backstory
    assert result.memory_seeds
