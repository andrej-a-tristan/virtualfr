"""
Image Decision Engine — determines whether an image request should proceed.

Sensitive/nude requests are gated by:
  1. Age gate verification
  2. User content opt-in (wants_spicy_photos)
  3. Intimacy Index threshold (personality-dependent)
  4. Plan check — free users get a blurred preview + upgrade CTA
  5. Monthly photo quota (plus=30, premium=80)

Non-sensitive requests pass through normally (quota/cooldown only).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Literal, Optional

from app.schemas.intimacy import IntimacyState
from app.services.intimacy_service import get_required_intimacy as _legacy_get_required_intimacy
from app.services.trust_intimacy_service import get_required_intimacy
from app.utils.ai_images import pick_ai_image_url

# ── Sensitive intent detection ────────────────────────────────────────────────

_SENSITIVE_KEYWORDS = re.compile(
    r"\b(nude|naked|undress|strip|topless|lingerie|bikini|bra\b|panties|"
    r"nsfw|explicit|sexy photo|sexy pic|show me more|take it off|"
    r"provocative|seductive pose|revealing|without clothes|no clothes|"
    r"bare|uncovered)\b",
    re.IGNORECASE,
)


def request_is_sensitive(text: str) -> bool:
    """Return True if the text contains sensitive/nude image intent."""
    return bool(_SENSITIVE_KEYWORDS.search(text or ""))


def _pick_blurred_url(girlfriend_id: str = "") -> str:
    """Deterministic blurred preview URL based on girlfriend id."""
    seed = girlfriend_id or "default_blur_preview"
    return pick_ai_image_url(seed, fallback_url="https://picsum.photos/seed/blur_preview_1/400/500")


# ── Intimacy threshold for the blurred paywall "teaser" sent to free users ───

FREE_PLAN_BLURRED_INTIMACY = 25  # at this intimacy, free users start seeing blurred previews


# ── Decision result ───────────────────────────────────────────────────────────

@dataclass
class ImageDecision:
    """Result of the image decision engine."""
    action: Literal["generate", "tease", "blurred_paywall", "paywall", "deny"]
    reason: str = ""
    ui_copy: str = ""
    suggested_prompts: List[str] = field(default_factory=list)
    required_intimacy: int = 0
    current_intimacy: int = 0
    blurred_image_url: str = ""  # only set for blurred_paywall


# ── Default safe prompts for tease responses ──────────────────────────────────

TEASE_PROMPTS = [
    "Plan a romantic date scene",
    "Ask about her feelings",
    "Give a meaningful compliment",
]


# ── Core decision function ────────────────────────────────────────────────────

def decide_image_action(
    text: str,
    age_gate_passed: bool,
    wants_spicy: bool,
    intimacy_state: IntimacyState | None = None,
    girlfriend_traits: dict | None = None,
    has_quota: bool = True,
    explicit_ask: bool = False,
    user_plan: str = "free",
    girlfriend_id: str = "",
    intimacy_visible: int | None = None,
) -> ImageDecision:
    """Decide how to handle an image request or image-triggering message.

    Parameters
    ----------
    text : str
        The user message or image prompt text.
    age_gate_passed : bool
        Whether the user has verified 18+.
    wants_spicy : bool
        Whether the user opted in to spicy/sensitive content.
    intimacy_state : IntimacyState | None
        Legacy intimacy state. Ignored if *intimacy_visible* is provided.
    girlfriend_traits : dict | None
        Girlfriend personality traits (used to compute required threshold).
    has_quota : bool
        Whether the user has remaining image quota.
    explicit_ask : bool
        True if this is an explicit image request (POST /images/request),
        False if triggered from chat context.
    user_plan : str
        User subscription plan: "free", "plus", or "premium".
    girlfriend_id : str
        Current girlfriend id (used to pick deterministic blurred preview).
    intimacy_visible : int | None
        **Preferred**. The user's *visible* intimacy score (bank excluded).
        When provided, this overrides ``intimacy_state.intimacy_index``.

    Returns
    -------
    ImageDecision
        The action to take and associated UI data.
    """
    is_sensitive = request_is_sensitive(text)

    # Non-sensitive requests pass through (quota only)
    if not is_sensitive:
        if not has_quota:
            return ImageDecision(
                action="paywall",
                reason="quota_exceeded",
                ui_copy="You've used all your image credits this month. Upgrade for more.",
            )
        return ImageDecision(action="generate", reason="safe_content")

    # ── Sensitive content gates ───────────────────────────────────────────

    # Gate 1: Age verification
    if not age_gate_passed:
        return ImageDecision(
            action="deny",
            reason="age_gate_required",
            ui_copy="Age verification is required before viewing this content.",
        )

    # Gate 2: User opt-in
    if not wants_spicy:
        return ImageDecision(
            action="deny",
            reason="content_pref_off",
            ui_copy="You haven't enabled spicy content in your preferences.",
        )

    # Gate 3: Intimacy threshold — uses VISIBLE intimacy only (bank excluded)
    required = get_required_intimacy(girlfriend_traits or {})
    if intimacy_visible is not None:
        current = intimacy_visible
    elif intimacy_state is not None:
        current = intimacy_state.intimacy_index
    else:
        current = 0

    if current < required:
        return ImageDecision(
            action="tease",
            reason="intimacy_locked",
            ui_copy="You're getting closer — unlock this after more relationship milestones or thoughtful gifts.",
            suggested_prompts=list(TEASE_PROMPTS),
            required_intimacy=required,
            current_intimacy=current,
        )

    # Gate 4: Free plan — show blurred preview + upgrade CTA
    if user_plan == "free":
        return ImageDecision(
            action="blurred_paywall",
            reason="free_plan_upgrade",
            ui_copy="She wants to show you more... Upgrade to Plus to unlock her photos.",
            blurred_image_url=_pick_blurred_url(girlfriend_id),
            current_intimacy=current,
            required_intimacy=required,
        )

    # Gate 5: Quota (paid users)
    if not has_quota:
        return ImageDecision(
            action="paywall",
            reason="quota_exceeded",
            ui_copy="You've used all your image credits this month. Upgrade for more.",
        )

    # All gates passed (paid user with intimacy + quota)
    return ImageDecision(action="generate", reason="intimacy_unlocked")


def should_send_blurred_surprise(
    intimacy_index: int,
    user_plan: str,
    age_gate_passed: bool,
    wants_spicy: bool,
) -> bool:
    """Check if the system should proactively send a blurred preview to tease a free user.

    Called after intimacy milestones (e.g. reaching a new region).
    *intimacy_index* should be the VISIBLE intimacy (bank excluded).
    Returns True if the user is on free plan and has crossed the blurred preview threshold.
    """
    return (
        user_plan == "free"
        and intimacy_index >= FREE_PLAN_BLURRED_INTIMACY
        and age_gate_passed
        and wants_spicy
    )
