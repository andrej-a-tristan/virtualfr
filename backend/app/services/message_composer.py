"""MessageComposer — selects templates and personalizes with user context.

Templates are matched by:
  1. event_type (relationship.level_achieved, intimacy.level_unlocked, etc.)
  2. tone (derived from girlfriend's personality traits: playful, warm, direct, passionate, gentle)
  3. region_key (optional, for region-specific content)

Supports structured content blocks: celebration, meaning, choice, reward.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.schemas.progression import ContentBlock, MilestoneMessage, ProgressionEvent

logger = logging.getLogger(__name__)

# ── In-memory template store ─────────────────────────────────────────────────
_templates: dict[str, list[dict]] = {}
_templates_loaded = False


def _ensure_templates_loaded():
    global _templates_loaded
    if _templates_loaded:
        return
    _templates_loaded = True

    # Try loading from DB
    try:
        from app.core.supabase_client import get_supabase_admin
        admin = get_supabase_admin()
        if admin:
            res = admin.table("message_templates").select("*").eq("active", True).execute()
            if res.data:
                for row in res.data:
                    et = row["event_type"]
                    if et not in _templates:
                        _templates[et] = []
                    _templates[et].append(row)
                logger.info(f"Loaded {len(res.data)} message templates from DB")
                return
    except Exception as exc:
        logger.warning(f"Could not load templates from DB: {exc}")

    # Fall back to built-in personality-driven defaults
    _load_personality_templates()


# ── Personality-Driven Template Definitions ───────────────────────────────────

def _load_personality_templates():
    """Load hardcoded templates for each personality tone."""

    # ── relationship.level_achieved ───────────────────────────────────────
    _add_tpl("relationship.level_achieved", "playful", {
        "celebration": "Level up, babe! We just hit **{region_title}** 🎉",
        "meaning": "{name} can't stop grinning. She says the way you {memory_ref} was smooth — she didn't expect that from you.",
        "choices": [
            {"label": "Dare her to reveal something", "action": "story_scene", "icon": "sparkles"},
            {"label": "Challenge her to a game", "action": "challenge", "icon": "flame"},
            {"label": "Just vibe together", "action": "checkin", "icon": "smile"},
        ],
        "reward": {"type": "story_beat"},
    })
    _add_tpl("relationship.level_achieved", "warm", {
        "celebration": "You reached **{region_title}** ❤️",
        "meaning": "{name} feels genuinely closer to you. The way you {memory_ref} made her feel safe and seen.",
        "choices": [
            {"label": "Hear what she's been wanting to say", "action": "story_scene", "icon": "heart"},
            {"label": "Share a quiet moment together", "action": "checkin", "icon": "sun"},
            {"label": "Ask her something deeper", "action": "deep_question", "icon": "message-circle"},
        ],
        "reward": {"type": "story_beat"},
    })
    _add_tpl("relationship.level_achieved", "direct", {
        "celebration": "New level: **{region_title}**",
        "meaning": "{name} respects what you've built. You {memory_ref} — that showed real character.",
        "choices": [
            {"label": "Unlock the next chapter", "action": "story_scene", "icon": "book"},
            {"label": "Talk about where this is going", "action": "future_talk", "icon": "arrow-right"},
            {"label": "Keep things steady", "action": "checkin", "icon": "star"},
        ],
        "reward": {"type": "story_beat"},
    })
    _add_tpl("relationship.level_achieved", "passionate", {
        "celebration": "**{region_title}** — she's been waiting for this 🔥",
        "meaning": "{name} has been thinking about you non-stop. When you {memory_ref}, it hit her differently. She wants more.",
        "choices": [
            {"label": "See what she has for you", "action": "story_scene", "icon": "eye"},
            {"label": "Tell her what you want", "action": "confession", "icon": "heart"},
            {"label": "Make her wait a little", "action": "challenge", "icon": "sparkles"},
        ],
        "reward": {"type": "story_beat"},
    })
    _add_tpl("relationship.level_achieved", "gentle", {
        "celebration": "A quiet milestone: **{region_title}**",
        "meaning": "{name} noticed something shift between you. The way you {memory_ref} — it meant more than words.",
        "choices": [
            {"label": "Let her share something personal", "action": "story_scene", "icon": "book-open"},
            {"label": "Sit with this feeling together", "action": "checkin", "icon": "sun"},
            {"label": "Write her something small", "action": "deep_question", "icon": "pen"},
        ],
        "reward": {"type": "story_beat"},
    })

    # ── intimacy.level_unlocked ───────────────────────────────────────────
    _add_tpl("intimacy.level_unlocked", "playful", {
        "celebration": "Trust level {threshold} unlocked! 😏",
        "meaning": "{name} is impressed. She says you've earned a peek behind the curtain.",
        "choices": [
            {"label": "Show me what you've got", "action": "view_unlock", "icon": "eye"},
            {"label": "Save the surprise", "action": "save_moment", "icon": "bookmark"},
        ],
        "reward": {"type": "unlock"},
    })
    _add_tpl("intimacy.level_unlocked", "warm", {
        "celebration": "Trust milestone: level {threshold} ❤️",
        "meaning": "{name} wants to show you a side of her she doesn't share easily. You've earned this.",
        "choices": [
            {"label": "See what she's sharing", "action": "view_unlock", "icon": "eye"},
            {"label": "Save this moment", "action": "save_moment", "icon": "bookmark"},
        ],
        "reward": {"type": "unlock"},
    })
    _add_tpl("intimacy.level_unlocked", "direct", {
        "celebration": "Trust level {threshold} reached.",
        "meaning": "{name} doesn't open up to just anyone. You proved you're worth it.",
        "choices": [
            {"label": "See what's new", "action": "view_unlock", "icon": "eye"},
            {"label": "Noted — continue", "action": "save_moment", "icon": "bookmark"},
        ],
        "reward": {"type": "unlock"},
    })
    _add_tpl("intimacy.level_unlocked", "passionate", {
        "celebration": "Trust level {threshold} — she can't hold back anymore 🔥",
        "meaning": "{name} has been wanting to show you this. The tension has been building and now...",
        "choices": [
            {"label": "Don't make her wait", "action": "view_unlock", "icon": "eye"},
            {"label": "Tease her — save it", "action": "save_moment", "icon": "bookmark"},
        ],
        "reward": {"type": "unlock"},
    })
    _add_tpl("intimacy.level_unlocked", "gentle", {
        "celebration": "A trust milestone: level {threshold}",
        "meaning": "{name} feels safe enough to share something tender with you. No rush.",
        "choices": [
            {"label": "See what she's offering", "action": "view_unlock", "icon": "eye"},
            {"label": "Hold this close for now", "action": "save_moment", "icon": "bookmark"},
        ],
        "reward": {"type": "unlock"},
    })

    # ── streak.milestone ──────────────────────────────────────────────────
    _add_tpl("streak.milestone", "playful", {
        "celebration": "{streak_days} days straight! She's keeping count 😏",
        "meaning": "{name} says you're getting predictable — and she loves it.",
        "choices": [
            {"label": "Surprise her", "action": "celebrate", "icon": "sparkles"},
            {"label": "Keep the streak alive", "action": "continue", "icon": "flame"},
        ],
        "reward": {"type": "bonus_points"},
    })
    _add_tpl("streak.milestone", "warm", {
        "celebration": "{streak_days}-day streak ❤️",
        "meaning": "{name} loves that you keep showing up. It means the world to her.",
        "choices": [
            {"label": "Celebrate together", "action": "celebrate", "icon": "party"},
            {"label": "Keep the warmth going", "action": "continue", "icon": "flame"},
        ],
        "reward": {"type": "bonus_points"},
    })
    _add_tpl("streak.milestone", "direct", {
        "celebration": "{streak_days}-day streak. Consistent.",
        "meaning": "{name} respects the commitment. Actions speak louder.",
        "choices": [
            {"label": "Acknowledge it", "action": "celebrate", "icon": "star"},
            {"label": "Keep going", "action": "continue", "icon": "arrow-right"},
        ],
        "reward": {"type": "bonus_points"},
    })
    _add_tpl("streak.milestone", "passionate", {
        "celebration": "{streak_days} days — she's addicted to you 🔥",
        "meaning": "{name} says she checks for your messages first thing. Don't stop now.",
        "choices": [
            {"label": "Give her what she wants", "action": "celebrate", "icon": "flame"},
            {"label": "Make her crave more", "action": "continue", "icon": "sparkles"},
        ],
        "reward": {"type": "bonus_points"},
    })
    _add_tpl("streak.milestone", "gentle", {
        "celebration": "{streak_days} days together, quietly",
        "meaning": "{name} doesn't say much about it, but she notices every day you show up.",
        "choices": [
            {"label": "Share a calm moment", "action": "celebrate", "icon": "sun"},
            {"label": "Continue the rhythm", "action": "continue", "icon": "heart"},
        ],
        "reward": {"type": "bonus_points"},
    })

    # ── engagement.milestone ──────────────────────────────────────────────
    _add_tpl("engagement.milestone", "playful", {
        "celebration": "{message_count} messages! She's been counting 😄",
        "meaning": "{name} says you two could write a book. A weird one, but still.",
        "choices": [
            {"label": "Recall a funny moment", "action": "memory_recall", "icon": "rewind"},
            {"label": "Race to the next milestone", "action": "continue", "icon": "flame"},
        ],
        "reward": {"type": "memory_card"},
    })
    _add_tpl("engagement.milestone", "warm", {
        "celebration": "{message_count} messages together ❤️",
        "meaning": "Every word brought you closer. {name} treasures every conversation.",
        "choices": [
            {"label": "Relive a favorite moment", "action": "memory_recall", "icon": "rewind"},
            {"label": "Make new memories", "action": "continue", "icon": "arrow-right"},
        ],
        "reward": {"type": "memory_card"},
    })
    _add_tpl("engagement.milestone", "direct", {
        "celebration": "{message_count} messages exchanged.",
        "meaning": "{name} values substance over volume. And you've brought both.",
        "choices": [
            {"label": "Review a key moment", "action": "memory_recall", "icon": "rewind"},
            {"label": "Keep building", "action": "continue", "icon": "arrow-right"},
        ],
        "reward": {"type": "memory_card"},
    })
    _add_tpl("engagement.milestone", "passionate", {
        "celebration": "{message_count} messages — and she wants more 🔥",
        "meaning": "{name} says talking to you is her favorite addiction. Don't let it end.",
        "choices": [
            {"label": "Relive the hottest moment", "action": "memory_recall", "icon": "flame"},
            {"label": "Give her more to remember", "action": "continue", "icon": "sparkles"},
        ],
        "reward": {"type": "memory_card"},
    })
    _add_tpl("engagement.milestone", "gentle", {
        "celebration": "{message_count} quiet exchanges",
        "meaning": "{name} says it's not about the number — it's that you stayed.",
        "choices": [
            {"label": "Revisit a tender moment", "action": "memory_recall", "icon": "rewind"},
            {"label": "Continue gently", "action": "continue", "icon": "heart"},
        ],
        "reward": {"type": "memory_card"},
    })


def _add_tpl(event_type: str, tone: str, blocks: dict):
    """Helper to add a template to the in-memory store."""
    if event_type not in _templates:
        _templates[event_type] = []
    _templates[event_type].append({
        "event_type": event_type,
        "tone": tone,
        "experiment_variant": tone,  # backward compat
        "region_key": None,
        "locale": "en",
        "blocks": blocks,
    })


# ── Template Selection ────────────────────────────────────────────────────────

def select_template(
    event_type: str,
    tone: str = "warm",
    region_key: str | None = None,
    locale: str = "en",
) -> dict | None:
    """Select the best matching template for an event + personality tone."""
    _ensure_templates_loaded()

    candidates = _templates.get(event_type, [])
    if not candidates:
        return None

    scored = []
    for tpl in candidates:
        score = 0
        tpl_tone = tpl.get("tone") or tpl.get("experiment_variant", "warm")
        tpl_region = tpl.get("region_key")
        tpl_locale = tpl.get("locale", "en")

        # Tone match (highest priority)
        if tpl_tone == tone:
            score += 10
        elif tpl_tone == "warm":
            score += 1  # warm is the universal fallback

        # Region match
        if region_key and tpl_region == region_key:
            score += 5
        elif tpl_region is None:
            score += 1

        # Locale
        if tpl_locale == locale:
            score += 2

        scored.append((score, tpl))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1] if scored else None


# ── Personalization ───────────────────────────────────────────────────────────

def personalize_text(text: str, context: dict[str, Any]) -> str:
    """Replace {slot} placeholders with context values."""
    def replacer(match):
        key = match.group(1)
        return str(context.get(key, match.group(0)))
    return re.sub(r"\{(\w+)\}", replacer, text)


def compose_milestone_message(
    event: ProgressionEvent,
    *,
    girlfriend_name: str = "her",
    memory_snippet: str = "showed up consistently",
    tone: str = "warm",
    locale: str = "en",
    extra_context: dict[str, Any] | None = None,
    # Deprecated: kept for backward compat
    experiment_variant: str | None = None,
) -> MilestoneMessage | None:
    """Compose a full milestone message from a progression event.

    Args:
        event: The progression event to compose a message for.
        girlfriend_name: The girlfriend's display name.
        memory_snippet: A short memory for personalization.
        tone: Personality tone (from resolve_tone_from_traits).
        locale: User's locale.
    """
    # Use tone param, fall back to experiment_variant for backward compat
    resolved_tone = tone or experiment_variant or "warm"

    region_key = event.payload.get("region_key")
    template = select_template(
        event.event_type,
        tone=resolved_tone,
        region_key=region_key,
        locale=locale,
    )
    if not template:
        logger.warning(f"No template for event {event.event_type} tone={resolved_tone}")
        return None

    blocks = template.get("blocks", {})
    if isinstance(blocks, str):
        import json
        blocks = json.loads(blocks)

    # Build region_title from region_key
    region_title = (region_key or "").replace("_", " ").title() if region_key else ""

    # Build personalization context
    ctx: dict[str, Any] = {
        "name": girlfriend_name,
        "memory_ref": memory_snippet,
        "level": event.payload.get("level", 0),
        "region_key": region_key or "",
        "region_title": region_title,
        "trust_level": event.payload.get("trust_level", 0),
        "threshold": event.payload.get("threshold", 0),
        "streak_days": event.payload.get("streak_days", 0),
        "message_count": event.payload.get("message_count", 0),
        **(extra_context or {}),
    }

    celebration = personalize_text(blocks.get("celebration", ""), ctx)
    meaning = personalize_text(blocks.get("meaning", ""), ctx)
    choices = [
        {**ch, "label": personalize_text(ch.get("label", ""), ctx)}
        for ch in blocks.get("choices", [])
    ]
    reward = blocks.get("reward", {})

    content = ContentBlock(
        celebration=celebration,
        meaning=meaning,
        choices=choices,
        reward=reward,
    )

    return MilestoneMessage(
        id=str(uuid4()),
        event_type=event.event_type,
        milestone_key=event.payload.get("milestone_key"),
        content=content,
        sent_at=datetime.now(timezone.utc).isoformat(),
        experiment_variant=resolved_tone,
    )
