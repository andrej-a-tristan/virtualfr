"""
Memory Ingestion Pipeline — extracts structured memories from each user turn.

Per user message:
  1. Extract candidate facts/emotions/events
  2. Normalize entities/keys
  3. Detect contradictions vs existing facts
  4. Upsert with reinforcement/decay logic
  5. Update pattern memory (hour, gap, weekday, response style)
  6. Create episodic memories for significant moments
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from app.services.bond_engine.memory_conflict_resolution import (
    update_factual_with_conflict_check,
)
from app.services.bond_engine.memory_patterns import update_all_patterns

logger = logging.getLogger(__name__)


# ── Factual Extraction Patterns (extended from memory.py) ────────────────────

FACTUAL_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("user.name", re.compile(r"(?:my name is|i'm called|call me|i am)\s+([A-Z][a-z]+)", re.IGNORECASE)),
    ("user.city", re.compile(r"(?:i'm from|i live in|i'm living in|from)\s+([A-Z][a-zA-Z\s]+?)(?:\.|,|$)", re.IGNORECASE)),
    ("user.country", re.compile(r"(?:i'm from|i live in)\s+([A-Z][a-zA-Z\s]+?)(?:\.|,|$)", re.IGNORECASE)),
    ("user.study", re.compile(r"(?:i study|i'm studying|studying)\s+([a-zA-Z\s]+?)(?:\.|,|$)", re.IGNORECASE)),
    ("user.work", re.compile(r"(?:i work as|i'm a|my job is|i work at)\s+([a-zA-Z\s]+?)(?:\.|,|$)", re.IGNORECASE)),
    ("user.age", re.compile(r"(?:i'm|i am)\s+(\d{1,2})\s*(?:years old|yo)?", re.IGNORECASE)),
    ("user.pet", re.compile(r"(?:i have a|my)\s+(dog|cat|pet|bird|fish|hamster|rabbit)(?:\s+named\s+(\w+))?", re.IGNORECASE)),
    ("user.sibling", re.compile(r"(?:my)\s+(brother|sister|sibling)(?:'s name is|\s+is|\s+named)\s+([A-Z][a-z]+)", re.IGNORECASE)),
    ("pref.music", re.compile(r"(?:i (?:like|love) listening to|my favorite music is|i listen to)\s+([a-zA-Z\s]+?)(?:\.|,|$)", re.IGNORECASE)),
    ("pref.food", re.compile(r"(?:i (?:like|love) eating|my favorite food is)\s+([a-zA-Z\s]+?)(?:\.|,|$)", re.IGNORECASE)),
    ("pref.hobby", re.compile(r"(?:i (?:like|love) to|my hobby is|i enjoy)\s+([a-zA-Z\s]+?)(?:\.|,|$)", re.IGNORECASE)),
    ("schedule.exam", re.compile(r"(?:i have an? exam|my exam is|exam (?:on|tomorrow|next))\s*([a-zA-Z0-9\s]+?)(?:\.|,|$)", re.IGNORECASE)),
    ("schedule.birthday", re.compile(r"(?:my birthday is|birthday (?:on|is))\s+([a-zA-Z0-9\s]+?)(?:\.|,|$)", re.IGNORECASE)),
    ("schedule.interview", re.compile(r"(?:i have an? interview|interview (?:on|tomorrow|today|next))\s*([a-zA-Z0-9\s]*?)(?:\.|,|$)", re.IGNORECASE)),
]

LIKE_PATTERN = re.compile(r"(?:i (?:really )?(?:like|love|enjoy))\s+([a-zA-Z\s]+?)(?:\.|,|!|$)", re.IGNORECASE)
DISLIKE_PATTERN = re.compile(r"(?:i (?:really )?(?:hate|dislike|can't stand))\s+([a-zA-Z\s]+?)(?:\.|,|!|$)", re.IGNORECASE)


# ── Emotion Classification ───────────────────────────────────────────────────

EMOTION_KEYWORDS: dict[str, list[str]] = {
    "stress": ["stressed", "stress", "anxious", "anxiety", "panic", "overwhelmed", "nervous", "worried"],
    "sadness": ["sad", "down", "depressed", "lonely", "upset", "crying", "cry", "heartbroken"],
    "anger": ["angry", "mad", "pissed", "furious", "annoyed", "frustrated"],
    "affection": ["miss you", "love you", "❤️", "♥️", "xoxo", "hug", "hugs", "kiss", "kisses", "adore"],
    "excitement": ["excited", "can't wait", "hyped", "thrilled", "amazing", "awesome"],
    "happiness": ["happy", "glad", "joyful", "cheerful", "great day", "good day"],
    "fear": ["scared", "afraid", "terrified", "fearful", "frightened"],
    "gratitude": ["thank you", "thanks", "grateful", "appreciate", "thankful"],
    "loneliness": ["alone", "lonely", "no one", "nobody", "isolated"],
    "hope": ["hope", "hoping", "wish", "fingers crossed", "looking forward"],
}

EMOTION_VALENCE: dict[str, int] = {
    "stress": -3, "sadness": -4, "anger": -3, "fear": -3,
    "affection": 4, "excitement": 3, "happiness": 4,
    "gratitude": 3, "loneliness": -3, "hope": 2,
}

INTENSITY_BOOSTERS = ["really", "so", "extremely", "very", "super", "incredibly", "absolutely"]


# ── Episodic Event Detection ─────────────────────────────────────────────────

_PROMISE_PATTERNS = [
    re.compile(r"(?:i promise|i'll|i will|i'm going to)\s+(.+?)(?:\.|!|$)", re.IGNORECASE),
]

_VULNERABILITY_PATTERNS = [
    re.compile(r"(?:i(?:'ve)? never told anyone|no one knows|secret|confession|honestly)", re.IGNORECASE),
    re.compile(r"(?:i'm afraid|i'm scared|i feel vulnerable|it's hard to say)", re.IGNORECASE),
]

_CONFLICT_PATTERNS = [
    re.compile(r"(?:i'm upset|you don't understand|i disagree|that hurt|i'm disappointed)", re.IGNORECASE),
    re.compile(r"(?:you always|you never|we need to talk|this isn't working)", re.IGNORECASE),
]

_SHARED_MOMENT_PATTERNS = [
    re.compile(r"(?:remember when|that time we|our|we should|let's|together)", re.IGNORECASE),
]

_WIN_PATTERNS = [
    re.compile(r"(?:i got the job|i passed|i did it|i made it|i won|i finally|good news)", re.IGNORECASE),
]

EXPLICIT_KEYWORDS = [
    "sex", "fuck", "cock", "dick", "pussy", "naked", "nude", "porn",
    "horny", "cum", "orgasm", "masturbat", "erotic", "xxx"
]


def _contains_explicit_content(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in EXPLICIT_KEYWORDS)


# ── Core Extraction Functions ────────────────────────────────────────────────

def extract_facts(text: str) -> list[tuple[str, str]]:
    """Extract factual information from text. Returns list of (key, value)."""
    if _contains_explicit_content(text):
        return []
    facts: list[tuple[str, str]] = []
    for key, pattern in FACTUAL_PATTERNS:
        match = pattern.search(text)
        if match:
            value = match.group(1).strip()
            if 1 < len(value) < 100:
                facts.append((key, value))
    for match in LIKE_PATTERN.finditer(text):
        value = match.group(1).strip()
        if 1 < len(value) < 50:
            key = f"pref.like.{value.lower().replace(' ', '_')[:20]}"
            facts.append((key, value))
    for match in DISLIKE_PATTERN.finditer(text):
        value = match.group(1).strip()
        if 1 < len(value) < 50:
            key = f"pref.dislike.{value.lower().replace(' ', '_')[:20]}"
            facts.append((key, value))
    return facts


def extract_emotions(text: str) -> tuple[list[str], int, int]:
    """Extract emotions from text. Returns (emotion_tags, valence, intensity)."""
    lower = text.lower()
    detected: list[str] = []
    for emotion, keywords in EMOTION_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                if emotion not in detected:
                    detected.append(emotion)
                break
    if not detected:
        return [], 0, 0
    valence_sum = sum(EMOTION_VALENCE.get(e, 0) for e in detected)
    valence = round(valence_sum / len(detected))
    intensity = 3
    if any(b in lower for b in INTENSITY_BOOSTERS):
        intensity = min(5, intensity + 1)
    keyword_count = sum(1 for e in detected for kw in EMOTION_KEYWORDS[e] if kw in lower)
    if keyword_count >= 3:
        intensity = min(5, intensity + 1)
    return detected, valence, intensity


def detect_episodic_events(text: str) -> list[dict]:
    """Detect episodic events (promises, vulnerabilities, conflicts, wins, shared moments)."""
    events: list[dict] = []
    lower = text.lower()

    for p in _PROMISE_PATTERNS:
        m = p.search(text)
        if m:
            events.append({
                "episode_type": "promise",
                "summary": f"User made a promise: {m.group(1)[:80]}",
                "salience": 70,
            })
            break

    for p in _VULNERABILITY_PATTERNS:
        if p.search(text):
            events.append({
                "episode_type": "vulnerability",
                "summary": f"User shared something vulnerable: {text[:80]}...",
                "salience": 80,
            })
            break

    for p in _CONFLICT_PATTERNS:
        if p.search(text):
            events.append({
                "episode_type": "conflict",
                "summary": f"Potential conflict: {text[:80]}...",
                "salience": 75,
            })
            break

    for p in _WIN_PATTERNS:
        if p.search(text):
            events.append({
                "episode_type": "win",
                "summary": f"User achieved something: {text[:80]}...",
                "salience": 65,
            })
            break

    for p in _SHARED_MOMENT_PATTERNS:
        if p.search(text):
            events.append({
                "episode_type": "shared_moment",
                "summary": f"Shared moment referenced: {text[:80]}...",
                "salience": 55,
            })
            break

    return events


def generate_event_summary(text: str, emotions: list[str]) -> str:
    """Generate a short event summary for emotional memory."""
    if not emotions:
        return "User shared something"
    emotion_to_event = {
        "stress": "User expressed stress",
        "sadness": "User felt down",
        "anger": "User expressed frustration",
        "fear": "User felt worried",
        "affection": "User expressed affection",
        "excitement": "User was excited",
        "happiness": "User was happy",
        "gratitude": "User expressed gratitude",
        "loneliness": "User felt lonely",
        "hope": "User expressed hope",
    }
    primary = emotions[0]
    base = emotion_to_event.get(primary, f"User expressed {primary}")
    short_text = text[:60].strip()
    if short_text:
        return f"{base} about: {short_text}..."
    return base


# ── Main Ingestion Function ──────────────────────────────────────────────────

def ingest_user_turn(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    turn_id: str,
    text: str,
    all_user_timestamps: list[str] | None = None,
    all_user_messages: list[str] | None = None,
) -> dict:
    """Full ingestion pipeline for one user message.
    
    1. Extract facts with conflict detection
    2. Extract and store emotions
    3. Detect and store episodic events
    4. Update pattern memory
    
    Returns: {"facts_extracted": int, "emotions_detected": list, 
              "episodes_created": int, "conflicts_found": int}
    """
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "facts_extracted": 0,
        "emotions_detected": [],
        "episodes_created": 0,
        "conflicts_found": 0,
    }
    
    if not text or not sb:
        return result

    # ── 1. Factual memory with conflict check ────────────────────────────
    facts = extract_facts(text)
    for key, value in facts:
        cr = update_factual_with_conflict_check(
            sb, user_id, girlfriend_id,
            key=key,
            new_value=value,
            source_turn_id=turn_id,
        )
        result["facts_extracted"] += 1
        if cr["action"] == "conflict_resolved":
            result["conflicts_found"] += 1

    # ── 2. Emotional memory ──────────────────────────────────────────────
    emotions, valence, intensity = extract_emotions(text)
    if emotions and intensity > 0:
        event_summary = generate_event_summary(text, emotions)
        try:
            sb.table("emotional_memory").insert({
                "user_id": str(user_id),
                "girlfriend_id": str(girlfriend_id),
                "event": event_summary,
                "emotion_tags": emotions,
                "valence": valence,
                "intensity": intensity,
                "occurred_at": now,
                "source_message_id": turn_id,
                "salience": min(90, 40 + intensity * 10),
                "confidence": 80,
                "is_resolved": False,
            }).execute()
            result["emotions_detected"] = emotions
        except Exception as e:
            logger.warning("Failed to write emotional memory: %s", e)

    # ── 3. Episodic events ───────────────────────────────────────────────
    episodes = detect_episodic_events(text)
    for ep in episodes:
        try:
            ep_emotions, ep_valence, ep_intensity = extract_emotions(text)
            sb.table("memory_episodes").insert({
                "user_id": str(user_id),
                "girlfriend_id": str(girlfriend_id),
                "episode_type": ep["episode_type"],
                "summary": ep["summary"],
                "detail": text[:500],
                "emotion_tags": ep_emotions or [],
                "salience": ep.get("salience", 60),
                "confidence": 80,
                "source_turn_id": turn_id,
            }).execute()
            result["episodes_created"] += 1
        except Exception as e:
            logger.warning("Failed to create episodic memory: %s", e)

    # ── 4. Entity extraction ─────────────────────────────────────────────
    for key, value in facts:
        # Normalize into entity table for cross-referencing
        entity_type = "preference" if key.startswith("pref.") else "person" if "name" in key else "thing"
        try:
            sb.table("memory_entities").upsert(
                {
                    "user_id": str(user_id),
                    "girlfriend_id": str(girlfriend_id),
                    "entity_type": entity_type,
                    "entity_key": key,
                    "entity_value": value,
                    "salience": 50,
                    "confidence": 80,
                    "last_reinforced_at": now,
                    "source_turn_id": turn_id,
                },
                on_conflict="user_id,girlfriend_id,entity_key"
            ).execute()
        except Exception as e:
            logger.debug("Entity upsert failed: %s", e)

    # ── 5. Pattern memory update ─────────────────────────────────────────
    if all_user_timestamps and all_user_messages:
        try:
            update_all_patterns(
                sb, user_id, girlfriend_id,
                user_timestamps=all_user_timestamps[-50:],
                user_messages=all_user_messages[-50:],
            )
        except Exception as e:
            logger.debug("Pattern memory update failed: %s", e)

    return result
