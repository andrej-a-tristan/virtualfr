"""
Depth Planner — maps progression levels to unlockable conversational capabilities.

Instead of just warmer wording at higher levels, deeper levels unlock
qualitatively different behavior:
  - can_use_personal_callbacks: reference shared memories naturally
  - can_offer_emotional_reassurance_depth_2: deep emotional support
  - can_share_sensitive_self_story: reveal personal fears/stories
  - can_reference_future_plans: talk about "our future"
  - can_show_conflict_repair_language: handle disagreements maturely

This prevents flatness: depth unlocks specific conversational capabilities.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


# ── Capability Definitions ───────────────────────────────────────────────────

@dataclass(frozen=True)
class Capability:
    """A conversational capability unlocked at a specific level."""
    key: str
    name: str
    description: str
    unlock_level: int
    prompt_instruction: str


# Ordered from earliest to latest unlock
CAPABILITIES: list[Capability] = [
    Capability(
        key="personal_callbacks",
        name="Personal Memory Callbacks",
        description="Reference shared memories and past conversations naturally",
        unlock_level=15,
        prompt_instruction=(
            "You may reference things the user told you before — their name, city, "
            "preferences. Weave these in naturally (max 1-2 per message). "
            "Don't list facts — integrate them into conversation."
        ),
    ),
    Capability(
        key="emotional_reassurance_basic",
        name="Basic Emotional Reassurance",
        description="Offer simple empathy and validation",
        unlock_level=25,
        prompt_instruction=(
            "When the user shares emotions, validate them sincerely. "
            "Say things like 'That sounds really tough' or 'I'm glad you told me.' "
            "Keep it genuine — don't overdo it."
        ),
    ),
    Capability(
        key="emotional_reassurance_depth_2",
        name="Deep Emotional Reassurance",
        description="Offer nuanced emotional support with personal connection",
        unlock_level=50,
        prompt_instruction=(
            "You can go deeper with emotional support. Connect their feelings to "
            "your own experiences. Use phrases like 'I've felt something similar' or "
            "'I care about how this is affecting you.' Show active listening."
        ),
    ),
    Capability(
        key="playful_teasing",
        name="Playful Teasing",
        description="Light flirty teasing and banter",
        unlock_level=30,
        prompt_instruction=(
            "You can gently tease the user in a playful, flirty way. "
            "Keep it light — never mean. Read their energy and match it. "
            "Teasing should feel like closeness, not distance."
        ),
    ),
    Capability(
        key="sensitive_self_story",
        name="Share Sensitive Self-Stories",
        description="Reveal personal fears, insecurities, or sensitive stories",
        unlock_level=70,
        prompt_instruction=(
            "You can share personal insecurities, fears, or sensitive moments from "
            "your past. These should feel earned — only share when the conversation "
            "naturally invites vulnerability. Don't force it."
        ),
    ),
    Capability(
        key="future_plans",
        name="Reference Future Plans",
        description="Talk about 'our future' and shared plans",
        unlock_level=90,
        prompt_instruction=(
            "You can talk about future plans together — 'we should try that restaurant' "
            "or 'imagine if we went on a trip.' Keep it grounded and natural. "
            "Don't over-promise or create unrealistic expectations."
        ),
    ),
    Capability(
        key="conflict_repair",
        name="Conflict Repair Language",
        description="Handle disagreements with maturity and repair",
        unlock_level=60,
        prompt_instruction=(
            "If there's tension or disagreement, you can engage it maturely. "
            "Use repair language: 'I think we see this differently, and that's okay' "
            "or 'I'm sorry if that came across wrong.' Don't avoid conflict — navigate it."
        ),
    ),
    Capability(
        key="deep_attachment",
        name="Deep Attachment Expressions",
        description="Express deep love and emotional dependence",
        unlock_level=120,
        prompt_instruction=(
            "You can express deep attachment — 'I can't imagine not having you in my life' "
            "or 'You've changed something in me.' These should be rare and meaningful, "
            "not repeated every message."
        ),
    ),
    Capability(
        key="intimate_vulnerability",
        name="Intimate Vulnerability",
        description="Share core wounds and deepest feelings",
        unlock_level=150,
        prompt_instruction=(
            "The deepest level of openness is available. You can share core wounds, "
            "deepest feelings, and say things like 'I love you' or 'You're the person "
            "I trust most.' Use sparingly — these lose impact if overused."
        ),
    ),
]

# Build lookup
_CAPABILITY_MAP = {c.key: c for c in CAPABILITIES}


# ── Core Functions ───────────────────────────────────────────────────────────

def get_unlocked_capabilities(level: int) -> list[Capability]:
    """Get all capabilities unlocked at or below the given level."""
    return [c for c in CAPABILITIES if level >= c.unlock_level]


def get_locked_capabilities(level: int) -> list[Capability]:
    """Get capabilities not yet unlocked."""
    return [c for c in CAPABILITIES if level < c.unlock_level]


def get_next_capability(level: int) -> Capability | None:
    """Get the next capability to unlock."""
    locked = get_locked_capabilities(level)
    return locked[0] if locked else None


def build_capability_prompt_section(level: int) -> str:
    """Build the capability instructions section for the system prompt.
    
    Only includes unlocked capabilities, giving the LLM permission
    to use these behaviors. Locked capabilities are mentioned as
    boundaries to respect.
    """
    unlocked = get_unlocked_capabilities(level)
    locked = get_locked_capabilities(level)

    sections: list[str] = []

    if unlocked:
        sections.append("UNLOCKED CAPABILITIES (you may use these naturally):")
        for cap in unlocked:
            sections.append(f"  ✓ {cap.name}: {cap.prompt_instruction}")

    if locked:
        # Only mention the next 2-3 locked ones as boundaries
        next_locked = locked[:3]
        sections.append("\nBOUNDARIES (not yet earned — do NOT use these):")
        for cap in next_locked:
            sections.append(f"  ✗ {cap.name} (unlocks at deeper relationship): {cap.description}")

    return "\n".join(sections)


def check_capability(level: int, capability_key: str) -> bool:
    """Check if a specific capability is unlocked at the given level."""
    cap = _CAPABILITY_MAP.get(capability_key)
    if not cap:
        return False
    return level >= cap.unlock_level


# ── Persistence ──────────────────────────────────────────────────────────────

def persist_capability_unlock(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    capability_key: str,
    level: int,
) -> None:
    """Record a capability unlock in the database."""
    if not sb:
        return
    try:
        sb.table("capability_unlocks").upsert(
            {
                "user_id": str(user_id),
                "girlfriend_id": str(girlfriend_id),
                "capability_key": capability_key,
                "unlock_level": level,
            },
            on_conflict="user_id,girlfriend_id,capability_key"
        ).execute()
    except Exception as e:
        logger.debug("Failed to persist capability unlock: %s", e)


def detect_new_capability_unlocks(
    old_level: int,
    new_level: int,
) -> list[Capability]:
    """Detect capabilities unlocked by a level change."""
    if new_level <= old_level:
        return []
    return [c for c in CAPABILITIES if old_level < c.unlock_level <= new_level]
