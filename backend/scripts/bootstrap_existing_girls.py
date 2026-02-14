"""One-time script: bootstrap dossier + generate identity for existing girlfriends.

Run from backend directory:
    source .venv/bin/activate && python -m scripts.bootstrap_existing_girls
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
from uuid import UUID

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

from app.core.supabase_client import get_supabase_admin

# ── LLM-powered identity generation ──────────────────────────────────────────

def generate_identity_from_traits(name: str, traits: dict) -> dict:
    """Use the LLM to generate a rich identity dict from traits alone."""
    from app.services.dossier.llm_generator import _call_llm

    cultural = traits.get("cultural_personality", "Warm Slavic")
    emotional = traits.get("emotional_style", "Caring")
    comm = traits.get("communication_style", "Soft")
    attachment = traits.get("attachment_style", "Emotionally present")
    pace = traits.get("relationship_pace", "Natural")

    system = (
        "You are a creative character designer. Generate a realistic, detailed identity "
        "for a virtual girlfriend character. Output valid JSON only."
    )
    user = f"""Create a detailed identity for a girlfriend character named "{name}" with these personality traits:
- Cultural personality: {cultural}
- Emotional style: {emotional}
- Communication style: {comm}
- Attachment style: {attachment}
- Relationship pace: {pace}

Generate JSON with these exact keys:
{{
  "name": "<her first name - pick something fitting for her cultural background>",
  "job_vibe": "<her job or what she does - be specific, e.g. 'graphic designer at a small studio' not 'works'>",
  "hobbies": ["<hobby1>", "<hobby2>", "<hobby3>"],
  "origin_vibe": "<where she's from and what it's like - e.g. 'small coastal town in Croatia'>",
  "age_range": "<age range like '22-25'>",
  "style_vibe": "<how she dresses/looks like>"
}}

Make it feel real and grounded, not fantasy. Match her cultural background."""

    result = _call_llm(system, user, max_tokens=500)
    if result:
        try:
            data = json.loads(result)
            return data
        except json.JSONDecodeError:
            # Try to extract JSON from markdown
            import re
            match = re.search(r'\{[^}]+\}', result, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
    # Fallback
    return _fallback_identity(name, traits)


def _fallback_identity(name: str, traits: dict) -> dict:
    """Deterministic fallback when LLM is unavailable."""
    cultural = traits.get("cultural_personality", "Warm Slavic")
    name_map = {
        "Warm Slavic": {"name": "Natasha", "origin": "a quiet neighborhood in Prague", "job": "freelance illustrator", "hobbies": ["sketching", "baking", "long walks"]},
        "Calm Central European": {"name": "Lena", "origin": "a small town near Vienna", "job": "UX designer at a startup", "hobbies": ["reading", "yoga", "coffee tasting"]},
        "Passionate Balkan": {"name": "Mila", "origin": "a seaside town in Montenegro", "job": "photographer and part-time barista", "hobbies": ["photography", "dancing", "cooking"]},
    }
    defaults = name_map.get(cultural, name_map["Warm Slavic"])
    return {
        "name": defaults["name"],
        "job_vibe": defaults["job"],
        "hobbies": defaults["hobbies"],
        "origin_vibe": defaults["origin"],
    }


def generate_identity_canon(name: str, identity: dict, traits: dict) -> dict:
    """Use the LLM to generate identity_canon (backstory, routine, favorites, memory seeds)."""
    from app.services.dossier.llm_generator import _call_llm

    job = identity.get("job_vibe", "freelancer")
    hobbies = ", ".join(identity.get("hobbies", ["reading"]))
    origin = identity.get("origin_vibe", "a European city")
    cultural = traits.get("cultural_personality", "Warm Slavic")
    emotional = traits.get("emotional_style", "Caring")

    system = (
        "You are a creative character writer. Generate a detailed backstory and daily life "
        "for a virtual girlfriend character. Output valid JSON only."
    )
    user = f"""Write detailed life context for {name}, a girl who:
- Is from {origin}
- Works as: {job}
- Enjoys: {hobbies}
- Cultural personality: {cultural}
- Emotional style: {emotional}

Generate JSON with these exact keys:
{{
  "backstory": "<3-4 sentences about her background, how she grew up, what shaped her>",
  "daily_routine": "<2-3 sentences about her typical day>",
  "favorites": {{
    "music_vibe": "<what kind of music she listens to>",
    "comfort_food": "<her go-to comfort food>",
    "weekend_idea": "<her ideal weekend activity>"
  }},
  "memory_seeds": [
    "<a specific memory or fact she might share - e.g. 'She once got lost hiking and found a hidden waterfall'>",
    "<another personal detail>",
    "<another one>",
    "<another one>",
    "<another one>"
  ]
}}

Make everything feel personal, specific, and human. Avoid clichés."""

    result = _call_llm(system, user, max_tokens=800)
    if result:
        try:
            data = json.loads(result)
            return data
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
    # Fallback
    return _fallback_canon(name, identity, traits)


def _fallback_canon(name: str, identity: dict, traits: dict) -> dict:
    """Deterministic fallback for identity_canon."""
    job = identity.get("job_vibe", "creative work")
    hobbies = identity.get("hobbies", ["reading"])
    origin = identity.get("origin_vibe", "a quiet European town")

    return {
        "backstory": f"{name} grew up in {origin}, raised by her mother and grandmother. She was always the quiet creative kid who observed more than she spoke. After school she moved to the city for work and found her rhythm in {job}. She still visits home for holidays and misses her grandmother's cooking.",
        "daily_routine": f"{name} starts her day with coffee and a quiet moment before work. She works on {job} during the day, takes breaks for walks, and evenings are for {hobbies[0] if hobbies else 'relaxing'} and winding down with music.",
        "favorites": {
            "music_vibe": "indie and lo-fi beats",
            "comfort_food": "homemade soup and fresh bread",
            "weekend_idea": f"morning coffee, {hobbies[0] if hobbies else 'reading'}, afternoon walk, evening cooking"
        },
        "memory_seeds": [
            f"She once got lost exploring a new city and stumbled into the best little bookshop she's ever seen",
            f"Her grandmother taught her to make bread from scratch — she still uses the same recipe",
            f"She has a small collection of postcards from places she's visited",
            f"She stayed up all night once watching meteor showers from her balcony",
            f"Her favorite spot in her apartment is the corner by the window where the light is perfect in the afternoon",
        ],
    }


# ── Main bootstrap ───────────────────────────────────────────────────────────

def main():
    sb = get_supabase_admin()
    if not sb:
        logger.error("No Supabase client available. Check .env")
        return

    user_id = "fac46e06-72e8-4364-9f09-9201d3fdde34"

    # Fetch all girlfriends
    r = sb.table("girlfriends").select("*").eq("user_id", user_id).order("created_at").execute()
    if not r.data:
        logger.error("No girlfriends found")
        return

    for gf in r.data:
        gf_id = gf["id"]
        name = gf.get("display_name") or "Girl"
        traits = gf.get("traits") or {}
        identity = gf.get("identity") or {}
        identity_canon = gf.get("identity_canon") or {}

        logger.info("=" * 60)
        logger.info("Processing: %s (%s)", name, gf_id[:8])
        logger.info("  Traits: %s", traits)
        logger.info("  Identity empty: %s, Canon empty: %s", not identity, not identity_canon)

        # Step 1: Generate identity if empty
        if not identity or not identity.get("name"):
            logger.info("  Generating identity via LLM...")
            identity = generate_identity_from_traits(name, traits)
            logger.info("  Generated: name=%s, job=%s, hobbies=%s, origin=%s",
                       identity.get("name"), identity.get("job_vibe"),
                       identity.get("hobbies"), identity.get("origin_vibe"))

        # Step 2: Generate identity_canon if empty
        if not identity_canon or not identity_canon.get("backstory"):
            logger.info("  Generating identity_canon via LLM...")
            identity_canon = generate_identity_canon(
                identity.get("name", name), identity, traits
            )
            logger.info("  Generated backstory: %s...", (identity_canon.get("backstory") or "")[:80])

        # Step 3: Update girlfriends table with identity + canon
        logger.info("  Updating girlfriends table...")
        sb.table("girlfriends").update({
            "identity": identity,
            "identity_canon": identity_canon,
        }).eq("id", gf_id).execute()
        logger.info("  ✓ identity and identity_canon saved")

        # Step 4: Run dossier bootstrap
        logger.info("  Running dossier bootstrap...")
        from app.services.dossier.bootstrap import bootstrap_dossier_from_onboarding
        gf_data = {**gf, "identity": identity, "identity_canon": identity_canon}
        counts = bootstrap_dossier_from_onboarding(sb, UUID(user_id), UUID(gf_id), gf_data)
        logger.info("  ✓ Dossier bootstrapped: %s", counts)

        # Step 5: Clean contaminated self-memory (AI-sounding claims)
        logger.info("  Cleaning contaminated self-memory...")
        bad_patterns = [
            "helping with questions", "figuring things out and helping",
            "I'm here to help", "designed to", "as an AI",
            "assist you", "I don't have feelings",
        ]
        try:
            mem_r = sb.table("girlfriend_self_memory").select("id,memory_key,memory_value").eq(
                "user_id", user_id).eq("girlfriend_id", gf_id).execute()
            deleted = 0
            for mem in (mem_r.data or []):
                val = (mem.get("memory_value") or "").lower()
                if any(pat.lower() in val for pat in bad_patterns):
                    sb.table("girlfriend_self_memory").delete().eq("id", mem["id"]).execute()
                    deleted += 1
                    logger.info("    Deleted contaminated: %s = %s", mem["memory_key"], mem["memory_value"][:60])
            logger.info("  ✓ Cleaned %d contaminated memories", deleted)
        except Exception as e:
            logger.warning("  Self-memory cleanup error: %s", e)

        logger.info("  Done: %s (%s)", identity.get("name", name), gf_id[:8])

    logger.info("=" * 60)
    logger.info("All girlfriends bootstrapped successfully!")


if __name__ == "__main__":
    main()
