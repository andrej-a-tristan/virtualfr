"""Intimacy Achievement Engine — keyword-triggered photo reward system.

Separate from the relationship achievement system and from the image_decision_engine.
Does NOT award trust/intimacy points. One-time per achievement per girlfriend.
Server-side throttle: max 1 photo reward per 6 hours per girlfriend.

Unlock path: CHAT KEYWORDS — strictly gated by tier requirements
(required_region_index + required_intimacy_visible). Called from chat.py
on every user message.
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Tuple

from app.services.intimacy_milestones import (
    INTIMACY_ACHIEVEMENTS,
    ALL_INTIMACY_ACHIEVEMENTS,
    IntimacyAchievement,
)
from app.services.achievement_engine import get_current_region_index_for_girl
from app.api.store import (
    get_intimacy_achievements_unlocked,
    mark_intimacy_achievement_unlocked,
    get_intimacy_last_award_time,
    set_intimacy_last_award_time,
    get_photo_for_intimacy_achievement,
    set_photo_for_intimacy_achievement,
    add_pending_intimacy_photo,
    pop_pending_intimacy_photo,
    get_pending_intimacy_photos,
    get_intimacy_phrase_log,
    set_intimacy_phrase_log,
    add_gallery_item,
)

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
PHOTO_THROTTLE_HOURS = 6
PHRASE_SPAM_COOLDOWN_SECONDS = 300  # 5-minute cooldown per matched phrase


# ── Keyword Matching ──────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Lowercase + collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _match_keywords(message: str, keywords: List[str]) -> str | None:
    """Check if any keyword/phrase appears in the message.
    Returns the matched keyword or None. Uses word-boundary matching for
    single words, substring for multi-word phrases.
    """
    norm = _normalize(message)
    for kw in keywords:
        kw_norm = _normalize(kw)
        if not kw_norm:
            continue
        # Multi-word phrase: simple substring match
        if " " in kw_norm:
            if kw_norm in norm:
                return kw_norm
        else:
            # Single word: word boundary match
            if re.search(r"\b" + re.escape(kw_norm) + r"\b", norm):
                return kw_norm
    return None


def _phrase_hash(phrase: str) -> str:
    return hashlib.md5(phrase.encode()).hexdigest()[:12]


# ── Eligibility ───────────────────────────────────────────────────────────────

def is_eligible(
    ach: IntimacyAchievement,
    current_region_index: int,
    intimacy_visible: int,
) -> bool:
    """Check if a user meets the tier gate for this achievement."""
    if current_region_index < ach.required_region_index:
        return False
    if ach.required_intimacy_visible is not None:
        if intimacy_visible < ach.required_intimacy_visible:
            return False
    return True


# ── Photo Throttle ────────────────────────────────────────────────────────────

def _can_award_photo_now(session_id: str, girlfriend_id: str) -> bool:
    """Returns True if enough time passed since last photo award."""
    last = get_intimacy_last_award_time(session_id, girlfriend_id=girlfriend_id)
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - last_dt >= timedelta(hours=PHOTO_THROTTLE_HOURS)
    except Exception:
        return True


# ── Anti-Spam ─────────────────────────────────────────────────────────────────

def _check_phrase_spam(session_id: str, girlfriend_id: str, phrase: str, now_ts: float) -> bool:
    """Returns True if this phrase was recently used (spam). Cleans old entries."""
    ph = _phrase_hash(phrase)
    log = get_intimacy_phrase_log(session_id, girlfriend_id=girlfriend_id)
    # Clean entries older than cooldown
    cutoff = now_ts - PHRASE_SPAM_COOLDOWN_SECONDS
    log = {k: v for k, v in log.items() if v > cutoff}
    if ph in log:
        set_intimacy_phrase_log(session_id, log, girlfriend_id=girlfriend_id)
        return True  # spamming
    # Record this phrase
    log[ph] = now_ts
    set_intimacy_phrase_log(session_id, log, girlfriend_id=girlfriend_id)
    return False


# ── Image Generation (mock/picsum for now) ────────────────────────────────────

def _generate_image(achievement: IntimacyAchievement, girlfriend_id: str) -> str:
    """Generate a photo for the achievement. Returns image URL.
    Currently uses picsum placeholder. Replace with real generation pipeline later.
    """
    # Deterministic seed from achievement+girlfriend for consistency
    seed = hashlib.md5(f"{girlfriend_id}:{achievement.id}".encode()).hexdigest()[:10]
    return f"https://picsum.photos/seed/{seed}/400/400"


# ── Core Engine ───────────────────────────────────────────────────────────────

def evaluate_intimacy_achievements(
    session_id: str,
    girlfriend_id: str,
    user_message: str,
    current_region_index: int,
    intimacy_visible: int,
    age_gate_passed: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Evaluate all intimacy achievements against the latest user message.

    Returns:
        (unlock_events, photo_events)
        - unlock_events: list of dicts for SSE event_type="intimacy_achievement"
        - photo_events:  list of dicts for SSE event_type="intimacy_photo_ready"

    IMPORTANT: This function does NOT modify trust/intimacy scores.
    """
    if not user_message or not user_message.strip():
        return [], []

    now_ts = time.time()
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    unlocked = get_intimacy_achievements_unlocked(session_id, girlfriend_id=girlfriend_id)
    can_photo = _can_award_photo_now(session_id, girlfriend_id)

    unlock_events: List[Dict[str, Any]] = []
    photo_events: List[Dict[str, Any]] = []

    # Also try to generate photos for previously pending achievements
    if can_photo:
        pending = get_pending_intimacy_photos(session_id, girlfriend_id=girlfriend_id)
        for pending_id in pending:
            ach = INTIMACY_ACHIEVEMENTS.get(pending_id)
            if not ach:
                pop_pending_intimacy_photo(session_id, pending_id, girlfriend_id=girlfriend_id)
                continue
            # Check we don't already have a photo
            existing = get_photo_for_intimacy_achievement(session_id, pending_id, girlfriend_id=girlfriend_id)
            if existing:
                pop_pending_intimacy_photo(session_id, pending_id, girlfriend_id=girlfriend_id)
                continue
            # Generate
            image_url = _generate_image(ach, girlfriend_id)
            set_photo_for_intimacy_achievement(session_id, pending_id, image_url, girlfriend_id=girlfriend_id)
            add_gallery_item(session_id, {
                "id": f"intach-{pending_id}-{uuid.uuid4().hex[:6]}",
                "url": image_url,
                "created_at": now_iso,
                "caption": f"{ach.icon} {ach.title}",
                "source": "intimacy_achievement",
                "achievement_id": pending_id,
            }, girlfriend_id=girlfriend_id)
            pop_pending_intimacy_photo(session_id, pending_id, girlfriend_id=girlfriend_id)
            set_intimacy_last_award_time(session_id, now_iso, girlfriend_id=girlfriend_id)
            photo_events.append({
                "id": pending_id,
                "image_url": image_url,
                "tier": ach.tier,
                "girlfriend_id": girlfriend_id,
                "title": ach.title,
                "icon": ach.icon,
            })
            # Only 1 photo per call (throttle)
            can_photo = False
            break

    # Evaluate all achievements
    for ach in ALL_INTIMACY_ACHIEVEMENTS:
        # Already unlocked?
        if ach.id in unlocked:
            continue

        # Eligible?
        if not is_eligible(ach, current_region_index, intimacy_visible):
            continue

        # Keyword match
        matched = _match_keywords(user_message, ach.trigger_keywords)
        if not matched:
            continue

        # Anti-spam: same phrase too recently
        if _check_phrase_spam(session_id, girlfriend_id, matched, now_ts):
            continue

        # Unlock it
        mark_intimacy_achievement_unlocked(session_id, ach.id, now_iso, girlfriend_id=girlfriend_id)
        # Refresh unlocked set to prevent double-unlock in same pass
        unlocked[ach.id] = now_iso

        unlock_event = {
            "id": ach.id,
            "title": ach.title,
            "subtitle": ach.subtitle,
            "rarity": ach.rarity.value,
            "tier": ach.tier,
            "icon": ach.icon,
            "unlocked_at": now_iso,
            "girlfriend_id": girlfriend_id,
        }
        unlock_events.append(unlock_event)
        logger.info("Intimacy achievement unlocked: %s (tier=%d, rarity=%s)",
                     ach.id, ach.tier, ach.rarity.value)

        # Photo generation (throttled)
        if can_photo:
            image_url = _generate_image(ach, girlfriend_id)
            set_photo_for_intimacy_achievement(session_id, ach.id, image_url, girlfriend_id=girlfriend_id)
            add_gallery_item(session_id, {
                "id": f"intach-{ach.id}-{uuid.uuid4().hex[:6]}",
                "url": image_url,
                "created_at": now_iso,
                "caption": f"{ach.icon} {ach.title}",
                "source": "intimacy_achievement",
                "achievement_id": ach.id,
            }, girlfriend_id=girlfriend_id)
            set_intimacy_last_award_time(session_id, now_iso, girlfriend_id=girlfriend_id)
            photo_events.append({
                "id": ach.id,
                "image_url": image_url,
                "tier": ach.tier,
                "girlfriend_id": girlfriend_id,
                "title": ach.title,
                "icon": ach.icon,
            })
            can_photo = False  # throttle: max 1 per call
        else:
            # Queue for later
            add_pending_intimacy_photo(session_id, ach.id, girlfriend_id=girlfriend_id)
            logger.info("Intimacy photo queued (throttled): %s", ach.id)

    return unlock_events, photo_events
