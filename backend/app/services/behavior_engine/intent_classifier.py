"""Turn Intent Classifier — detects what the user is trying to do this turn.

Intents:
  ask_about_her   – User asking about the girlfriend (her life, opinions, feelings)
  ask_about_user  – Girlfriend should ask/respond about the user
  mixed           – Both directions in one message
  support         – User needs emotional support
  banter          – Casual/playful exchange
  greeting        – Opening / re-engagement
  intimate        – Romantic / intimate direction
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ═══════════════════════════════════════════════════════════════════════════════
# INTENT RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TurnIntent:
    primary: str                    # ask_about_her | ask_about_user | mixed | support | banter | greeting | intimate
    confidence: float               # 0.0 - 1.0
    has_question_about_her: bool    # did user ask about her specifically?
    has_user_disclosure: bool       # did user share something personal?
    has_emotional_need: bool        # does user seem to need support?
    detected_topics: list[str] = field(default_factory=list)  # topic keywords found

    def requires_self_answer(self) -> bool:
        """True if the girlfriend MUST answer about herself (not deflect)."""
        return self.primary in ("ask_about_her", "mixed") and self.has_question_about_her


# ═══════════════════════════════════════════════════════════════════════════════
# DETECTION PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

# Patterns indicating user is asking about HER
_ASK_HER_PATTERNS = [
    r"\b(what|how|where|when|why|who)\b.{0,30}\b(you|your|yours|u)\b",
    r"\b(tell me about|what about) (you|your|yourself)\b",
    r"\b(do you|are you|have you|did you|would you|could you|can you|will you)\b",
    r"\b(what'?s your|what do you|how do you|where do you)\b",
    r"\b(you like|you think|you feel|you want|you prefer|you enjoy)\b.*\?",
    r"\b(your favorite|your opinion|your take|your thought)\b",
    r"\b(about yourself|about you|your life|your day|your work|your family)\b",
    r"\byou\b.{0,20}\?$",
]

# Patterns indicating emotional need / support
_SUPPORT_PATTERNS = [
    r"\b(i feel|i'm feeling|feeling)\b.{0,30}\b(sad|down|anxious|worried|stressed|scared|alone|lonely|depressed|overwhelmed|lost|hurt|broken)\b",
    r"\b(i'm|i am)\b.{0,15}\b(struggling|hurting|crying|tired of|exhausted|burnt out)\b",
    r"\b(bad day|rough day|terrible day|hard day|worst day)\b",
    r"\b(need (someone|you|help|support|a hug|comfort))\b",
    r"\b(can't (take|handle|cope|deal|sleep|stop thinking))\b",
    r"\b(everything is|life is|it's all)\b.{0,20}\b(falling apart|too much|overwhelming)\b",
]

# Patterns indicating user disclosure (sharing about themselves)
_USER_DISCLOSURE_PATTERNS = [
    r"\b(i|my|mine|me)\b.{0,40}\b(job|work|family|brother|sister|mom|dad|friend|school|hobby|pet|dog|cat)\b",
    r"\b(i (love|hate|like|enjoy|miss|want|need|wish|hope|think|believe|feel|remember))\b",
    r"\b(happened to me|my experience|in my life|my story|when i was)\b",
    r"\b(i've been|i was|i used to|i grew up|i live|i work)\b",
]

# Patterns indicating banter / casual
_BANTER_PATTERNS = [
    r"\b(haha|lol|lmao|😂|🤣|😏|😜|hehe|hihi)\b",
    r"\b(oh really|oh yeah|no way|come on|shut up|get out)\b",
    r"\b(bet|prove it|challenge|dare)\b",
]

# Patterns indicating intimate direction
_INTIMATE_PATTERNS = [
    r"\b(miss you|love you|want you|need you|thinking of you|dreaming of you)\b",
    r"\b(kiss|cuddle|hold|hug|touch|close to you|next to you)\b",
    r"[😘💋❤️💕💗🥰😍♥️]{1,}",
]

# Greeting patterns
_GREETING_PATTERNS = [
    r"^(hey|hi|hello|yo|sup|what'?s up|good morning|good evening|good night|morning|evening|gm|gn)\b",
    r"^(how are you|how's it going|what's new|how you doing)\b",
]

# Topic detection
_TOPIC_KEYWORDS = {
    "work": ["work", "job", "career", "boss", "office", "meeting", "project", "deadline"],
    "family": ["family", "mom", "dad", "brother", "sister", "parent", "grandmother", "grandfather"],
    "hobbies": ["hobby", "music", "reading", "cooking", "gaming", "sport", "art", "travel", "movie", "film", "book"],
    "food": ["food", "eat", "cook", "restaurant", "recipe", "meal", "dinner", "lunch", "breakfast", "coffee", "tea"],
    "feelings": ["feel", "feeling", "emotion", "mood", "happy", "sad", "excited", "nervous", "anxious"],
    "future": ["future", "plan", "dream", "goal", "wish", "hope", "someday", "eventually"],
    "past": ["remember", "childhood", "grew up", "used to", "back then", "years ago", "when i was"],
    "relationship": ["us", "together", "relationship", "dating", "couple", "partner"],
    "daily": ["today", "yesterday", "tomorrow", "morning", "evening", "night", "weekend"],
    # Explicit origin / background questions about where she is from.
    "origin": [
        "where are you from",
        "where're you from",
        "where are u from",
        "what city are you from",
        "what country are you from",
        "hometown",
        "where did you grow up",
    ],
}


def _match_any(text: str, patterns: list[str]) -> bool:
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def _count_matches(text: str, patterns: list[str]) -> int:
    count = 0
    for p in patterns:
        count += len(re.findall(p, text, re.IGNORECASE))
    return count


def _detect_topics(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    for topic, keywords in _TOPIC_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(topic)
    return found


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def classify_turn_intent(
    user_message: str,
    recent_intents: list[str] | None = None,
) -> TurnIntent:
    """
    Classify the user's turn intent based on message content and conversation context.
    """
    text = user_message.strip()
    if not text:
        return TurnIntent(primary="banter", confidence=0.5, has_question_about_her=False,
                          has_user_disclosure=False, has_emotional_need=False)

    # Score each intent
    ask_her_score = _count_matches(text, _ASK_HER_PATTERNS)
    support_score = _count_matches(text, _SUPPORT_PATTERNS)
    disclosure_score = _count_matches(text, _USER_DISCLOSURE_PATTERNS)
    banter_score = _count_matches(text, _BANTER_PATTERNS)
    intimate_score = _count_matches(text, _INTIMATE_PATTERNS)
    greeting_score = _count_matches(text, _GREETING_PATTERNS)

    has_question_about_her = ask_her_score > 0
    has_user_disclosure = disclosure_score > 0
    has_emotional_need = support_score > 0

    topics = _detect_topics(text)

    # Determine primary intent
    scores = {
        "ask_about_her": ask_her_score * 2.0,
        "support": support_score * 2.5,
        "ask_about_user": disclosure_score * 1.5,
        "banter": banter_score * 1.3,
        "intimate": intimate_score * 2.0,
        "greeting": greeting_score * 3.0,
    }

    # Mixed: both asking about her AND disclosing
    if ask_her_score > 0 and disclosure_score > 0:
        scores["mixed"] = (ask_her_score + disclosure_score) * 1.8

    # Default to banter if nothing matches strongly
    best = max(scores, key=lambda k: scores[k])
    best_score = scores[best]

    if best_score == 0:
        # Check if it's a question at all
        if text.rstrip().endswith("?"):
            best = "ask_about_her"
            confidence = 0.4
        else:
            best = "banter"
            confidence = 0.3
    else:
        total = sum(scores.values()) or 1
        confidence = min(1.0, best_score / total + 0.3)

    return TurnIntent(
        primary=best,
        confidence=confidence,
        has_question_about_her=has_question_about_her,
        has_user_disclosure=has_user_disclosure,
        has_emotional_need=has_emotional_need,
        detected_topics=topics,
    )
