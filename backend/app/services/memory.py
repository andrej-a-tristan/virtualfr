"""
Memory System (Task 1.2)
Provides short-term, long-term factual, and emotional memory for the Personality Engine.

Memory Types:
1. Short-term: Last N messages (already in messages table)
2. Long-term factual: Stable facts about user (name, city, preferences)
3. Emotional: Events + feelings (stress, affection, etc.)

All memory is scoped per (user_id, girlfriend_id).
"""
import re
import logging
from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import UUID
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------

MemoryType = Literal["factual", "emotional"]


class FactualMemoryItem(BaseModel):
    """A stable fact about the user."""
    id: str
    key: str                    # e.g. "user.name", "user.city", "pref.music"
    value: str
    confidence: int             # 0-100
    first_seen_at: str
    last_seen_at: str
    source_message_id: Optional[str] = None


class EmotionalMemoryItem(BaseModel):
    """An emotional event/feeling."""
    id: str
    event: str                  # short summary
    emotion_tags: list[str]     # e.g. ["stress", "anxiety"]
    valence: int                # -5 to +5
    intensity: int              # 1-5
    occurred_at: str
    source_message_id: Optional[str] = None


class MemoryContext(BaseModel):
    """Compact memory context for prompt building."""
    facts: list[str]            # Human-readable fact summaries (max 8)
    emotions: list[str]         # Human-readable emotion summaries (max 5)
    habits: list[str]           # Optional habit hints


# -----------------------------------------------------------------------------
# Emotion Classification (Keyword-based, v1)
# -----------------------------------------------------------------------------

EMOTION_KEYWORDS: dict[str, list[str]] = {
    "stress": ["stressed", "stress", "anxious", "anxiety", "panic", "overwhelmed", "nervous", "worried"],
    "sadness": ["sad", "down", "depressed", "lonely", "upset", "crying", "cry", "heartbroken"],
    "anger": ["angry", "mad", "pissed", "furious", "annoyed", "frustrated"],
    "affection": ["miss you", "love you", "❤️", "♥️", "xoxo", "hug", "hugs", "kiss", "kisses", "adore"],
    "excitement": ["excited", "can't wait", "hyped", "thrilled", "amazing", "awesome"],
    "happiness": ["happy", "glad", "joyful", "cheerful", "great day", "good day"],
    "fear": ["scared", "afraid", "terrified", "fearful", "frightened"],
}

EMOTION_VALENCE: dict[str, int] = {
    "stress": -3,
    "sadness": -4,
    "anger": -3,
    "fear": -3,
    "affection": 4,
    "excitement": 3,
    "happiness": 4,
}

INTENSITY_BOOSTERS = ["really", "so", "extremely", "very", "super", "incredibly", "absolutely"]

# -----------------------------------------------------------------------------
# Factual Extraction Patterns (Deterministic, v1)
# -----------------------------------------------------------------------------

FACTUAL_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    # (key, display_name, regex pattern)
    ("user.name", "name", re.compile(r"(?:my name is|i'm called|call me|i am)\s+([A-Z][a-z]+)", re.IGNORECASE)),
    ("user.city", "city", re.compile(r"(?:i'm from|i live in|i'm living in|from)\s+([A-Z][a-zA-Z\s]+?)(?:\.|,|$)", re.IGNORECASE)),
    ("user.country", "country", re.compile(r"(?:i'm from|i live in)\s+([A-Z][a-zA-Z\s]+?)(?:\.|,|$)", re.IGNORECASE)),
    ("user.study", "studies", re.compile(r"(?:i study|i'm studying|studying)\s+([a-zA-Z\s]+?)(?:\.|,|$)", re.IGNORECASE)),
    ("user.work", "job", re.compile(r"(?:i work as|i'm a|my job is|i work at)\s+([a-zA-Z\s]+?)(?:\.|,|$)", re.IGNORECASE)),
    ("user.age", "age", re.compile(r"(?:i'm|i am)\s+(\d{1,2})\s*(?:years old|yo)?", re.IGNORECASE)),
    ("pref.music", "music preference", re.compile(r"(?:i (?:like|love) listening to|my favorite music is|i listen to)\s+([a-zA-Z\s]+?)(?:\.|,|$)", re.IGNORECASE)),
    ("pref.food", "food preference", re.compile(r"(?:i (?:like|love) eating|my favorite food is)\s+([a-zA-Z\s]+?)(?:\.|,|$)", re.IGNORECASE)),
    ("pref.hobby", "hobby", re.compile(r"(?:i (?:like|love) to|my hobby is|i enjoy)\s+([a-zA-Z\s]+?)(?:\.|,|$)", re.IGNORECASE)),
    ("schedule.exam", "exam", re.compile(r"(?:i have an? exam|my exam is|exam (?:on|tomorrow|next))\s*([a-zA-Z0-9\s]+?)(?:\.|,|$)", re.IGNORECASE)),
    ("schedule.birthday", "birthday", re.compile(r"(?:my birthday is|birthday (?:on|is))\s+([a-zA-Z0-9\s]+?)(?:\.|,|$)", re.IGNORECASE)),
]

# Generic like/dislike patterns
LIKE_PATTERN = re.compile(r"(?:i (?:really )?(?:like|love|enjoy))\s+([a-zA-Z\s]+?)(?:\.|,|!|$)", re.IGNORECASE)
DISLIKE_PATTERN = re.compile(r"(?:i (?:really )?(?:hate|dislike|can't stand))\s+([a-zA-Z\s]+?)(?:\.|,|!|$)", re.IGNORECASE)

# Content filter for explicit/sexual content
EXPLICIT_KEYWORDS = [
    "sex", "fuck", "cock", "dick", "pussy", "naked", "nude", "porn",
    "horny", "cum", "orgasm", "masturbat", "erotic", "xxx"
]


def _contains_explicit_content(text: str) -> bool:
    """Check if text contains explicit sexual content."""
    lower = text.lower()
    return any(kw in lower for kw in EXPLICIT_KEYWORDS)


# -----------------------------------------------------------------------------
# Read Functions
# -----------------------------------------------------------------------------

def get_short_term_messages(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    limit: int = 20
) -> list[dict[str, Any]]:
    """Get last N messages for conversation context."""
    if not sb:
        return []
    try:
        r = (
            sb.table("messages")
            .select("id, role, content, created_at")
            .eq("user_id", str(user_id))
            .eq("girlfriend_id", str(girlfriend_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        if r.data:
            return list(reversed(r.data))  # oldest first for context
        return []
    except Exception as e:
        logger.warning("get_short_term_messages error: %s", e)
        return []


def get_factual_memory(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    limit: int = 20
) -> list[FactualMemoryItem]:
    """Get factual memories, ordered by recency and confidence."""
    if not sb:
        return []
    try:
        r = (
            sb.table("factual_memory")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("girlfriend_id", str(girlfriend_id))
            .order("last_seen_at", desc=True)
            .order("confidence", desc=True)
            .limit(limit)
            .execute()
        )
        if not r.data:
            return []
        return [
            FactualMemoryItem(
                id=row["id"],
                key=row["key"],
                value=row["value"],
                confidence=row["confidence"],
                first_seen_at=row["first_seen_at"],
                last_seen_at=row["last_seen_at"],
                source_message_id=row.get("source_message_id"),
            )
            for row in r.data
        ]
    except Exception as e:
        logger.warning("get_factual_memory error: %s", e)
        return []


def get_emotional_memory(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    limit: int = 10
) -> list[EmotionalMemoryItem]:
    """Get emotional memories, ordered by recency and intensity."""
    if not sb:
        return []
    try:
        r = (
            sb.table("emotional_memory")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("girlfriend_id", str(girlfriend_id))
            .order("occurred_at", desc=True)
            .order("intensity", desc=True)
            .limit(limit)
            .execute()
        )
        if not r.data:
            return []
        return [
            EmotionalMemoryItem(
                id=row["id"],
                event=row["event"],
                emotion_tags=row.get("emotion_tags") or [],
                valence=row["valence"],
                intensity=row["intensity"],
                occurred_at=row["occurred_at"],
                source_message_id=row.get("source_message_id"),
            )
            for row in r.data
        ]
    except Exception as e:
        logger.warning("get_emotional_memory error: %s", e)
        return []


# -----------------------------------------------------------------------------
# Build Memory Context (for Prompt Builder)
# -----------------------------------------------------------------------------

# Key to human-readable description mapping
KEY_DESCRIPTIONS: dict[str, str] = {
    "user.name": "Your name is {value}",
    "user.city": "You live in {value}",
    "user.country": "You're from {value}",
    "user.study": "You study {value}",
    "user.work": "You work as {value}",
    "user.age": "You're {value} years old",
    "pref.music": "You like {value} music",
    "pref.food": "You enjoy {value}",
    "pref.hobby": "You enjoy {value}",
    "pref.like": "You like {value}",
    "pref.dislike": "You dislike {value}",
    "schedule.exam": "You have an exam: {value}",
    "schedule.birthday": "Your birthday: {value}",
}


def _fact_to_sentence(item: FactualMemoryItem) -> str:
    """Convert a factual memory item to a human-readable sentence."""
    template = KEY_DESCRIPTIONS.get(item.key)
    if template:
        return template.format(value=item.value)
    # Generic fallback
    if item.key.startswith("pref.like."):
        return f"You like {item.value}"
    if item.key.startswith("pref.dislike."):
        return f"You dislike {item.value}"
    return f"{item.key}: {item.value}"


def _emotion_to_sentence(item: EmotionalMemoryItem) -> str:
    """Convert an emotional memory item to a human-readable sentence."""
    tags_str = ", ".join(item.emotion_tags) if item.emotion_tags else "mixed feelings"
    intensity_desc = {1: "mildly", 2: "somewhat", 3: "", 4: "quite", 5: "very"}
    intensity_word = intensity_desc.get(item.intensity, "")
    if intensity_word:
        return f"Recently {intensity_word} felt {tags_str}: {item.event}"
    return f"Recently felt {tags_str}: {item.event}"


def build_memory_context(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    max_facts: int = 8,
    max_emotions: int = 5,
    habit_profile: Optional[dict] = None
) -> MemoryContext:
    """
    Build a compact memory context for the prompt builder.
    Returns facts, emotions, and habit hints as human-readable strings.
    """
    # Get memories
    facts_raw = get_factual_memory(sb, user_id, girlfriend_id, limit=max_facts)
    emotions_raw = get_emotional_memory(sb, user_id, girlfriend_id, limit=max_emotions)
    
    # Convert to sentences
    facts = [_fact_to_sentence(f) for f in facts_raw]
    emotions = [_emotion_to_sentence(e) for e in emotions_raw]
    
    # Build habit hints from habit_profile
    habits: list[str] = []
    if habit_profile:
        preferred_hours = habit_profile.get("preferred_hours")
        if preferred_hours and len(preferred_hours) > 0:
            hours_str = ", ".join(f"{h}:00" for h in preferred_hours[:3])
            habits.append(f"Often messages around {hours_str}")
        typical_gap = habit_profile.get("typical_gap_hours")
        if typical_gap:
            habits.append(f"Typically replies every {typical_gap} hours")
    
    return MemoryContext(facts=facts, emotions=emotions, habits=habits)


# -----------------------------------------------------------------------------
# Write Functions
# -----------------------------------------------------------------------------

def _extract_emotions(text: str) -> tuple[list[str], int, int]:
    """
    Extract emotions from text using keyword matching.
    Returns: (emotion_tags, valence, intensity)
    """
    lower = text.lower()
    detected_emotions: list[str] = []
    
    for emotion, keywords in EMOTION_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                if emotion not in detected_emotions:
                    detected_emotions.append(emotion)
                break
    
    if not detected_emotions:
        return [], 0, 0
    
    # Calculate valence (average of detected emotions)
    valence_sum = sum(EMOTION_VALENCE.get(e, 0) for e in detected_emotions)
    valence = round(valence_sum / len(detected_emotions)) if detected_emotions else 0
    
    # Calculate intensity
    intensity = 3  # default
    # Boost if intensity words present
    if any(booster in lower for booster in INTENSITY_BOOSTERS):
        intensity = min(5, intensity + 1)
    # Boost if multiple emotion keywords
    keyword_count = sum(1 for e in detected_emotions for kw in EMOTION_KEYWORDS[e] if kw in lower)
    if keyword_count >= 3:
        intensity = min(5, intensity + 1)
    
    return detected_emotions, valence, intensity


def _extract_facts(text: str) -> list[tuple[str, str]]:
    """
    Extract factual information from text using pattern matching.
    Returns: list of (key, value) tuples
    """
    facts: list[tuple[str, str]] = []
    
    # Try specific patterns
    for key, _, pattern in FACTUAL_PATTERNS:
        match = pattern.search(text)
        if match:
            value = match.group(1).strip()
            if len(value) > 1 and len(value) < 100:
                facts.append((key, value))
    
    # Try generic like/dislike patterns
    for match in LIKE_PATTERN.finditer(text):
        value = match.group(1).strip()
        if len(value) > 1 and len(value) < 50:
            # Create a normalized key
            key = f"pref.like.{value.lower().replace(' ', '_')[:20]}"
            facts.append((key, value))
    
    for match in DISLIKE_PATTERN.finditer(text):
        value = match.group(1).strip()
        if len(value) > 1 and len(value) < 50:
            key = f"pref.dislike.{value.lower().replace(' ', '_')[:20]}"
            facts.append((key, value))
    
    return facts


def _generate_event_summary(text: str, emotions: list[str]) -> str:
    """Generate a short event summary for emotional memory."""
    if not emotions:
        return "User shared something"
    
    # Map emotions to event descriptions
    emotion_to_event = {
        "stress": "User expressed stress",
        "sadness": "User felt down",
        "anger": "User expressed frustration",
        "fear": "User felt worried",
        "affection": "User expressed affection",
        "excitement": "User was excited",
        "happiness": "User was happy",
    }
    
    # Use first emotion for summary
    primary = emotions[0]
    base = emotion_to_event.get(primary, f"User expressed {primary}")
    
    # Try to add context (first 50 chars of message, cleaned)
    short_text = text[:50].strip()
    if short_text:
        return f"{base} about: {short_text}..."
    
    return base


def write_memories_from_message(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    message_id: str,
    role: str,
    text: str
) -> None:
    """
    Extract and write memories from a message.
    Only processes user messages (not assistant).
    """
    if not sb or not text:
        return
    
    # Only process user messages
    if role != "user":
        return
    
    now = datetime.now(timezone.utc).isoformat()
    
    # --- Factual memory extraction ---
    facts = _extract_facts(text)
    for key, value in facts:
        try:
            # Upsert: update if exists, insert if not
            sb.table("factual_memory").upsert(
                {
                    "user_id": str(user_id),
                    "girlfriend_id": str(girlfriend_id),
                    "key": key,
                    "value": value,
                    "confidence": 80,
                    "last_seen_at": now,
                    "source_message_id": message_id,
                },
                on_conflict="user_id,girlfriend_id,key"
            ).execute()
            logger.debug("Upserted factual memory: %s = %s", key, value)
        except Exception as e:
            logger.warning("Failed to write factual memory: %s", e)
    
    # --- Emotional memory extraction ---
    emotions, valence, intensity = _extract_emotions(text)
    if emotions and intensity > 0:
        event = _generate_event_summary(text, emotions)
        try:
            sb.table("emotional_memory").insert({
                "user_id": str(user_id),
                "girlfriend_id": str(girlfriend_id),
                "event": event,
                "emotion_tags": emotions,
                "valence": valence,
                "intensity": intensity,
                "occurred_at": now,
                "source_message_id": message_id,
            }).execute()
            logger.debug("Inserted emotional memory: %s (%s)", event, emotions)
        except Exception as e:
            logger.warning("Failed to write emotional memory: %s", e)

    # Optional: enqueue semantic vector docs for this turn (legacy path).
    try:
        from app.services.vector_memory_ingest import enqueue_vector_docs_for_turn

        enqueue_vector_docs_for_turn(
            sb=sb,
            user_id=user_id,
            girlfriend_id=girlfriend_id,
            turn_id=message_id,
            raw_text=text,
        )
    except Exception as e:
        logger.debug("Vector memory enqueue (legacy) failed: %s", e)


# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------

def get_memory_summary(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID
) -> dict[str, Any]:
    """Get a summary of memory counts and recent items (for debugging/UI)."""
    factual = get_factual_memory(sb, user_id, girlfriend_id, limit=50)
    emotional = get_emotional_memory(sb, user_id, girlfriend_id, limit=50)
    
    return {
        "factual_count": len(factual),
        "emotional_count": len(emotional),
        "recent_facts": [{"key": f.key, "value": f.value} for f in factual[:5]],
        "recent_emotions": [{"event": e.event, "tags": e.emotion_tags} for e in emotional[:5]],
    }


def delete_memory(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    memory_type: MemoryType,
    memory_id: str
) -> bool:
    """Delete a specific memory item."""
    if not sb:
        return False
    table = "factual_memory" if memory_type == "factual" else "emotional_memory"
    try:
        sb.table(table).delete().eq("id", memory_id).eq("user_id", str(user_id)).execute()
        return True
    except Exception as e:
        logger.warning("Failed to delete memory: %s", e)
        return False
