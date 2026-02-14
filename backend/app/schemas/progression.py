"""Pydantic schemas for the Progression System."""
from __future__ import annotations

from pydantic import BaseModel


# ── Domain Events ─────────────────────────────────────────────────────────────

class ProgressionEvent(BaseModel):
    """A domain event emitted when progression state changes."""
    event_type: str                          # e.g. "relationship.level_achieved"
    user_id: str
    girlfriend_id: str
    payload: dict = {}                       # level, region_key, trust, streak_days, etc.
    quality_score: float = 0.0               # session quality at time of event


class SessionQualitySignals(BaseModel):
    """Quality signals extracted from a single message or session."""
    message_length: int = 0
    has_question: bool = False
    emotional_keywords: int = 0              # count of emotional keywords found
    is_story_followup: bool = False          # user followed up on a quest/prompt
    is_preference_confirmation: bool = False # user confirmed/denied something
    sustained_conversation: bool = False     # 5+ messages in this session window
    reply_depth: int = 0                     # how many turns deep in the conversation


class SessionQualityScore(BaseModel):
    """Computed quality score with breakdown."""
    total: float = 0.0                       # 0-100
    breakdown: dict[str, float] = {}         # component → points


# ── Milestone Message ─────────────────────────────────────────────────────────

class ContentBlock(BaseModel):
    celebration: str = ""
    meaning: str = ""
    choices: list[dict] = []                 # [{label, action, icon}]
    reward: dict = {}                        # {type, ...}


class MilestoneMessage(BaseModel):
    """A rendered milestone message ready for delivery."""
    id: str
    event_type: str
    milestone_key: str | None = None
    content: ContentBlock
    sent_at: str
    read_at: str | None = None
    dismissed: bool = False
    experiment_variant: str | None = None


class MilestoneMessageList(BaseModel):
    messages: list[MilestoneMessage] = []
    unread_count: int = 0


# ── API Request/Response ──────────────────────────────────────────────────────

class EvaluateRequest(BaseModel):
    girlfriend_id: str
    message: str | None = None               # optional: the user message to evaluate
    event_key: str | None = None             # optional: explicit event trigger


class EvaluateResponse(BaseModel):
    quality_score: SessionQualityScore
    events: list[ProgressionEvent] = []
    messages_queued: int = 0


class MarkReadRequest(BaseModel):
    message_ids: list[str] = []


class ChoiceActionRequest(BaseModel):
    message_id: str
    action: str                              # e.g. "story_scene", "challenge", "checkin"


class ProgressionSummary(BaseModel):
    """Current progression state summary."""
    level: int = 0
    region_key: str = "EARLY_CONNECTION"
    trust_visible: int = 20
    intimacy_visible: int = 1
    streak_days: int = 0
    message_count: int = 0
    quality_score_avg_7d: float = 0.0
    milestones_reached: list[str] = []
    unread_messages: int = 0
    next_milestone: dict | None = None       # {key, title, progress_pct}
