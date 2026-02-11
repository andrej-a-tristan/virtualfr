"""
Prompt Context Gatherer — Task 3.2

Collects all inputs needed by the prompt builder from the database / stores:
  - girlfriend name + traits
  - relationship state
  - memory summary
  - habit profile + Big Five
  - user language preference

Works with both the in-memory store (dev) and Supabase (production).
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from app.services.memory import build_memory_context, MemoryContext
from app.services.big_five import map_traits_to_big_five

logger = logging.getLogger(__name__)


def get_prompt_context(
    *,
    # Supabase client (None in in-memory mode)
    sb_admin: Any = None,
    # User / girlfriend identifiers
    user_id: Optional[UUID] = None,
    girlfriend_id: Optional[UUID] = None,
    # In-memory session id (None in supabase mode)
    session_id: Optional[str] = None,
    # Explicit girlfriend id string for in-memory multi-girl
    girlfriend_id_str: Optional[str] = None,
    # Pre-loaded data (to avoid double fetches from chat.py)
    girlfriend: Optional[dict] = None,
    relationship_state: Optional[dict] = None,
    habit_profile: Optional[dict] = None,
    memory_context: Optional[MemoryContext] = None,
) -> dict[str, Any]:
    """
    Gather all prompt context needed for build_system_prompt().

    Returns a dict with keys:
      - girlfriend_name: str
      - traits: dict (raw traits from girlfriend)
      - relationship: dict (trust, intimacy, level, region_key, etc.)
      - memories: dict (facts, emotions, habits as string lists)
      - habit_profile: dict (preferred_hours, typical_gap_hours)
      - language_pref: str ("en" or "sk")
      - big_five: dict | None (openness, conscientiousness, etc., 0-100 scale)
    """
    use_sb = sb_admin is not None and user_id is not None and girlfriend_id is not None

    # ── 1. Girlfriend (name + traits) ──────────────────────────────────────
    gf = girlfriend
    if gf is None:
        if use_sb:
            from app.api import supabase_store as sb_store
            gf = sb_store.get_current_girlfriend(user_id)
        elif session_id:
            from app.api.store import get_girlfriend
            gf = get_girlfriend(session_id)
    gf = gf or {}
    gf_name = gf.get("display_name") or gf.get("name") or "Companion"
    traits = gf.get("traits") or {}

    # ── 2. Relationship state ──────────────────────────────────────────────
    rel = relationship_state
    if rel is None:
        if use_sb:
            from app.api import supabase_store as sb_store
            rel = sb_store.get_relationship_state(user_id, girlfriend_id)
        elif session_id:
            from app.api.store import get_relationship_state as get_rs
            rel = get_rs(session_id, girlfriend_id=girlfriend_id_str)
    rel = rel or {"trust": 10, "intimacy": 10, "level": 0, "region_key": "EARLY_CONNECTION"}

    # ── 3. Memory context ──────────────────────────────────────────────────
    mem_ctx = memory_context
    if mem_ctx is None and use_sb:
        try:
            mem_ctx = build_memory_context(
                sb=sb_admin,
                user_id=user_id,
                girlfriend_id=girlfriend_id,
                max_facts=8,
                max_emotions=5,
                habit_profile=habit_profile,
            )
        except Exception as e:
            logger.warning("Memory context build failed in prompt_context: %s", e)
    memories_dict = {
        "facts": mem_ctx.facts if mem_ctx else [],
        "emotions": mem_ctx.emotions if mem_ctx else [],
        "habits": mem_ctx.habits if mem_ctx else [],
    }

    # ── 4. Habit profile ───────────────────────────────────────────────────
    hp = habit_profile
    if hp is None:
        if use_sb:
            from app.api import supabase_store as sb_store
            hp = sb_store.get_habit_profile(user_id, girlfriend_id)
        elif session_id:
            from app.api.store import get_habit_profile as get_hp
            hp = get_hp(session_id, girlfriend_id=girlfriend_id_str)
    hp = hp or {}

    # ── 5. User language preference ────────────────────────────────────────
    language_pref = "en"
    if use_sb:
        try:
            from app.api import supabase_store as sb_store
            profile = sb_store.get_user_profile(user_id)
            if profile and profile.get("language_pref"):
                language_pref = profile["language_pref"]
        except Exception:
            pass
    elif session_id:
        try:
            from app.api.store import get_session_user
            user = get_session_user(session_id)
            if user and user.get("language_pref"):
                language_pref = user["language_pref"]
        except Exception:
            pass

    # ── 6. Big Five scores ─────────────────────────────────────────────────
    big_five = None
    # First check if stored in habit profile
    if hp and hp.get("big_five") and isinstance(hp["big_five"], dict):
        raw = hp["big_five"]
        big_five = {
            "openness": raw.get("openness", 0.5) * 100,
            "conscientiousness": raw.get("conscientiousness", 0.5) * 100,
            "extraversion": raw.get("extraversion", 0.5) * 100,
            "agreeableness": raw.get("agreeableness", 0.5) * 100,
            "neuroticism": raw.get("neuroticism", 0.5) * 100,
        }
    # Otherwise compute from traits
    elif traits and isinstance(traits, dict):
        try:
            raw = map_traits_to_big_five(traits)
            big_five = {
                "openness": raw.get("openness", 0.5) * 100,
                "conscientiousness": raw.get("conscientiousness", 0.5) * 100,
                "extraversion": raw.get("extraversion", 0.5) * 100,
                "agreeableness": raw.get("agreeableness", 0.5) * 100,
                "neuroticism": raw.get("neuroticism", 0.5) * 100,
            }
        except Exception as e:
            logger.warning("Big Five computation failed: %s", e)

    return {
        "girlfriend_name": gf_name,
        "traits_dict": traits,
        "relationship_dict": rel,
        "memories_dict": memories_dict,
        "habit_profile_dict": {
            "preferred_hours": hp.get("preferred_hours", []),
            "typical_gap_hours": hp.get("typical_gap_hours"),
        },
        "language_pref": language_pref,
        "big_five_dict": big_five,
    }
