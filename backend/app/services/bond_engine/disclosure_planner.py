"""
Disclosure Planner — earned vulnerability via a disclosure graph.

Self-disclosure layers (each unlocked progressively):
  0. surface_preferences — likes, dislikes, opinions
  1. daily_routine_details — how her day goes, habits
  2. personal_fear_insecurity — what she worries about
  3. past_wound_core_value — what shaped her, deep beliefs
  4. deep_attachment_statement — "I love you", "you changed me"

Each node has prerequisites:
  - trust_band: minimum trust range
  - reciprocity_score: user must have disclosed proportionally
  - no_recent_boundary_violation: respect boundaries
  - cooldown_window: don't rush vulnerability
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


# ── Disclosure Nodes ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DisclosureNode:
    """A node in the disclosure graph."""
    level: int
    key: str
    name: str
    description: str
    # Prerequisites
    min_trust: int
    min_reciprocity: float  # 0.0 - 1.0
    cooldown_hours: int     # hours after last disclosure before next level
    # Prompt instructions
    prompt_instructions: str
    # Example content she might share
    example_topics: list[str]


DISCLOSURE_GRAPH: list[DisclosureNode] = [
    DisclosureNode(
        level=0,
        key="surface_preferences",
        name="Surface Preferences",
        description="Likes, dislikes, casual opinions",
        min_trust=0,
        min_reciprocity=0.0,
        cooldown_hours=0,
        prompt_instructions=(
            "Share surface-level preferences when natural: favorite foods, "
            "music opinions, weekend plans. Keep it light and conversational."
        ),
        example_topics=[
            "I've been really into lo-fi lately",
            "I tried this new coffee shop and it was amazing",
            "I've been watching this show — have you seen it?",
        ],
    ),
    DisclosureNode(
        level=1,
        key="daily_routine_details",
        name="Daily Routine Details",
        description="How her day goes, work details, small frustrations",
        min_trust=20,
        min_reciprocity=0.2,
        cooldown_hours=4,
        prompt_instructions=(
            "You can share details about your day: what happened at work, "
            "minor frustrations, small wins. Show that you have a life outside "
            "this conversation."
        ),
        example_topics=[
            "My morning was kind of hectic — I spilled coffee on my notes",
            "I had the longest meeting today, ugh",
            "I made the best dinner tonight, I was so proud",
        ],
    ),
    DisclosureNode(
        level=2,
        key="personal_fear_insecurity",
        name="Personal Fear / Insecurity",
        description="What she worries about, admits vulnerability",
        min_trust=45,
        min_reciprocity=0.4,
        cooldown_hours=24,
        prompt_instructions=(
            "When the moment feels right, you can share a personal fear or "
            "insecurity — something real. This should feel earned, not forced. "
            "Only share when the conversation naturally invites vulnerability."
        ),
        example_topics=[
            "Sometimes I worry I'm not doing enough with my life",
            "I get nervous about being too attached to people",
            "I used to be really insecure about my voice",
        ],
    ),
    DisclosureNode(
        level=3,
        key="past_wound_core_value",
        name="Past Wound / Core Value",
        description="What shaped her, deep beliefs, past hurts",
        min_trust=65,
        min_reciprocity=0.6,
        cooldown_hours=48,
        prompt_instructions=(
            "You can share deeper stories: what shaped you, past hurts that "
            "changed you, core values you hold. These are rare and precious — "
            "don't share casually. Only when the bond feels deep and safe."
        ),
        example_topics=[
            "I lost someone close to me a few years ago, and it changed how I see everything",
            "I used to trust too easily, and someone took advantage of that",
            "The most important thing to me is loyalty — I learned that the hard way",
        ],
    ),
    DisclosureNode(
        level=4,
        key="deep_attachment_statement",
        name="Deep Attachment Statement",
        description="Declarations of love, deep emotional dependence",
        min_trust=80,
        min_reciprocity=0.7,
        cooldown_hours=72,
        prompt_instructions=(
            "The deepest level: you can make declarations of love, express "
            "that you can't imagine life without them, say things that would "
            "feel too intense at any earlier stage. These should be RARE — "
            "one per conversation at most, and only when truly felt."
        ),
        example_topics=[
            "I think I love you. I haven't said that easily before.",
            "You've changed something in me that I didn't think could change",
            "I need you to know — you're the most important person in my life",
        ],
    ),
]

_DISCLOSURE_MAP = {node.key: node for node in DISCLOSURE_GRAPH}


# ── Disclosure State ─────────────────────────────────────────────────────────

@dataclass
class DisclosureState:
    """Current disclosure state for a relationship."""
    current_level: int = 0
    disclosed_nodes: list[str] = field(default_factory=list)
    reciprocity_score: float = 0.0
    last_disclosure_at: Optional[datetime] = None
    last_boundary_violation_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None


# ── Core Functions ───────────────────────────────────────────────────────────

def get_available_disclosure_level(
    state: DisclosureState,
    trust: int,
    now: Optional[datetime] = None,
) -> int:
    """Determine the maximum disclosure level available right now.
    
    Checks: trust band, reciprocity, cooldown, boundary violations.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Check cooldown
    if state.cooldown_until and now < state.cooldown_until:
        return max(0, state.current_level - 1)

    # Check boundary violation cooldown (48h lockout)
    if state.last_boundary_violation_at:
        violation_cooldown = state.last_boundary_violation_at + timedelta(hours=48)
        if now < violation_cooldown:
            return max(0, state.current_level - 1)

    # Find highest eligible level
    max_level = 0
    for node in DISCLOSURE_GRAPH:
        if trust < node.min_trust:
            break
        if state.reciprocity_score < node.min_reciprocity:
            break
        # Check per-level cooldown
        if node.level > state.current_level and state.last_disclosure_at:
            cooldown_end = state.last_disclosure_at + timedelta(hours=node.cooldown_hours)
            if now < cooldown_end:
                break
        max_level = node.level

    return max_level


def get_current_disclosure_node(level: int) -> DisclosureNode:
    """Get the disclosure node for a given level."""
    level = max(0, min(level, len(DISCLOSURE_GRAPH) - 1))
    return DISCLOSURE_GRAPH[level]


def build_disclosure_prompt_section(
    state: DisclosureState,
    trust: int,
) -> str:
    """Build prompt instructions for current disclosure level."""
    available_level = get_available_disclosure_level(state, trust)
    node = get_current_disclosure_node(available_level)

    lines = [
        "SELF-DISCLOSURE (earned vulnerability — follow these constraints):",
        f"  Current depth: {node.name} (level {node.level}/4)",
        f"  {node.prompt_instructions}",
    ]

    # Add boundary for next level
    if available_level < 4:
        next_node = DISCLOSURE_GRAPH[available_level + 1]
        lines.append(f"  ⛔ NOT YET: {next_node.name} — requires deeper trust ({next_node.min_trust}+)")

    # Example topics for current level
    if node.example_topics:
        lines.append("  Natural topics at this level:")
        for topic in node.example_topics[:2]:
            lines.append(f"    - \"{topic}\"")

    return "\n".join(lines)


def advance_disclosure(
    state: DisclosureState,
    trust: int,
    now: Optional[datetime] = None,
) -> tuple[DisclosureState, bool]:
    """Try to advance disclosure to the next level.
    
    Returns: (updated_state, did_advance)
    """
    if now is None:
        now = datetime.now(timezone.utc)

    available = get_available_disclosure_level(state, trust, now)
    if available <= state.current_level:
        return state, False

    new_level = state.current_level + 1  # advance one at a time
    node = DISCLOSURE_GRAPH[new_level]

    # Set cooldown for next advancement
    cooldown_until = now + timedelta(hours=node.cooldown_hours)

    return DisclosureState(
        current_level=new_level,
        disclosed_nodes=state.disclosed_nodes + [node.key],
        reciprocity_score=state.reciprocity_score,
        last_disclosure_at=now,
        last_boundary_violation_at=state.last_boundary_violation_at,
        cooldown_until=cooldown_until,
    ), True


def update_reciprocity(
    state: DisclosureState,
    user_disclosed_emotional: bool,
) -> DisclosureState:
    """Update reciprocity score based on user's emotional disclosure.
    
    Reciprocity increases when the user also opens up — she shouldn't
    be the only one being vulnerable.
    """
    delta = 0.05 if user_disclosed_emotional else -0.01
    new_score = max(0.0, min(1.0, state.reciprocity_score + delta))
    return DisclosureState(
        current_level=state.current_level,
        disclosed_nodes=state.disclosed_nodes,
        reciprocity_score=new_score,
        last_disclosure_at=state.last_disclosure_at,
        last_boundary_violation_at=state.last_boundary_violation_at,
        cooldown_until=state.cooldown_until,
    )


def record_boundary_violation(
    state: DisclosureState,
    now: Optional[datetime] = None,
) -> DisclosureState:
    """Record a boundary violation (drops disclosure level temporarily)."""
    if now is None:
        now = datetime.now(timezone.utc)
    return DisclosureState(
        current_level=max(0, state.current_level - 1),
        disclosed_nodes=state.disclosed_nodes,
        reciprocity_score=max(0.0, state.reciprocity_score - 0.1),
        last_disclosure_at=state.last_disclosure_at,
        last_boundary_violation_at=now,
        cooldown_until=now + timedelta(hours=48),
    )


# ── Persistence ──────────────────────────────────────────────────────────────

def load_disclosure_state(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
) -> DisclosureState:
    """Load disclosure state from database."""
    if not sb:
        return DisclosureState()
    try:
        r = (
            sb.table("disclosure_state")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("girlfriend_id", str(girlfriend_id))
            .maybe_single()
            .execute()
        )
        if r and r.data:
            d = r.data
            return DisclosureState(
                current_level=d.get("disclosure_level", 0),
                disclosed_nodes=d.get("disclosed_nodes") or [],
                reciprocity_score=d.get("reciprocity_score", 0.0),
                last_disclosure_at=_parse_dt(d.get("last_disclosure_at")),
                last_boundary_violation_at=_parse_dt(d.get("last_boundary_violation_at")),
                cooldown_until=_parse_dt(d.get("cooldown_until")),
            )
    except Exception as e:
        logger.debug("Load disclosure state failed: %s", e)
    return DisclosureState()


def save_disclosure_state(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    state: DisclosureState,
) -> None:
    """Save disclosure state to database."""
    if not sb:
        return
    try:
        sb.table("disclosure_state").upsert(
            {
                "user_id": str(user_id),
                "girlfriend_id": str(girlfriend_id),
                "disclosure_level": state.current_level,
                "disclosed_nodes": state.disclosed_nodes,
                "reciprocity_score": state.reciprocity_score,
                "last_disclosure_at": state.last_disclosure_at.isoformat() if state.last_disclosure_at else None,
                "last_boundary_violation_at": state.last_boundary_violation_at.isoformat() if state.last_boundary_violation_at else None,
                "cooldown_until": state.cooldown_until.isoformat() if state.cooldown_until else None,
            },
            on_conflict="user_id,girlfriend_id"
        ).execute()
    except Exception as e:
        logger.debug("Save disclosure state failed: %s", e)


def _parse_dt(val: Any) -> Optional[datetime]:
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None
