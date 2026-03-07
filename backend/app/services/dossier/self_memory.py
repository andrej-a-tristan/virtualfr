"""Self-Memory Writer — extracts and validates self-claims from assistant responses.

After the LLM generates a response, this module:
1. Extracts facts the girlfriend claimed about herself
2. Checks them against existing self_memory for contradictions
3. Inserts new facts / reinforces existing / logs conflicts
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# SELF-FACT EXTRACTION PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

# Patterns where the assistant claims something about herself
# These match first-person statements
_SELF_CLAIM_PATTERNS: list[tuple[str, str]] = [
    # Preferences
    (r"(?:i|my) (?:really )?(love|adore|enjoy|like|prefer)\b.{3,50}", "preference"),
    (r"(?:my favorite|i'm a fan of|i'm into|i'm obsessed with)\b.{3,50}", "preference"),
    # Facts
    (r"i (?:work|study|live|grew up|come from|am from|moved to)\b.{3,60}", "fact"),
    (r"i (?:have|had) (?:a |an )?\b(?:brother|sister|dog|cat|pet|friend|roommate)\b.{3,50}", "fact"),
    # Opinions
    (r"i (?:think|believe|feel like|honestly think|always thought)\b.{5,80}", "opinion"),
    # Habits
    (r"i (?:usually|always|never|sometimes|tend to|often)\b.{5,60}", "habit"),
    # Experiences
    (r"(?:when i was|i remember|i once|this one time|i used to)\b.{5,80}", "experience"),
    # Emotions about self
    (r"i (?:get|feel|am) (?:really |so )?\b(?:nervous|excited|happy|scared|anxious|shy|confident)\b.{0,40}(?:when|about|around)", "emotion"),
]


def extract_self_claims(assistant_text: str) -> list[dict[str, str]]:
    """
    Extract self-claims from assistant response text.
    
    Returns list of {"key": "...", "value": "...", "type": "preference|fact|opinion|habit|experience|emotion"}
    """
    text = assistant_text.strip()
    if not text:
        return []

    claims: list[dict[str, str]] = []
    seen_keys: set[str] = set()

    for pattern, claim_type in _SELF_CLAIM_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            matched_text = match.group(0).strip()
            # Generate a key from the claim
            key = _generate_claim_key(matched_text, claim_type)
            if key and key not in seen_keys:
                seen_keys.add(key)
                claims.append({
                    "key": key,
                    "value": matched_text[:200],
                    "type": claim_type,
                })

    return claims[:10]  # Cap at 10 per turn


def _generate_claim_key(text: str, claim_type: str) -> str | None:
    """Generate a normalized key for a self-claim."""
    t = text.lower().strip()

    # Try to extract a meaningful noun phrase
    # "I love cooking" → "love.cooking"
    # "I work in tech" → "work.tech"
    # "My favorite color is blue" → "favorite.color"

    # Preference keys
    pref_match = re.search(r"(?:love|adore|enjoy|like|prefer|favorite|fan of|into|obsessed with)\s+(\w[\w\s]{1,20})", t)
    if pref_match and claim_type == "preference":
        obj = pref_match.group(1).strip().replace(" ", "_")[:30]
        return f"pref.{obj}"

    # Fact keys
    fact_match = re.search(r"(?:work|study|live|grew up|come from|am from|moved to)\s+(?:in |at |as )?(\w[\w\s]{1,20})", t)
    if fact_match and claim_type == "fact":
        obj = fact_match.group(1).strip().replace(" ", "_")[:30]
        return f"fact.{obj}"

    # Habit keys
    habit_match = re.search(r"(?:usually|always|never|sometimes|tend to|often)\s+(\w[\w\s]{1,25})", t)
    if habit_match and claim_type == "habit":
        obj = habit_match.group(1).strip().replace(" ", "_")[:30]
        return f"habit.{obj}"

    # Opinion keys
    if claim_type == "opinion":
        # Use first few words after "think/believe"
        op_match = re.search(r"(?:think|believe|feel like)\s+(.{5,30})", t)
        if op_match:
            obj = op_match.group(1).strip().replace(" ", "_")[:30]
            return f"opinion.{obj}"

    # Generic fallback
    words = t.split()[:4]
    if len(words) >= 2:
        return f"{claim_type}.{'_'.join(words[:3])}"

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# CONFLICT DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def _is_contradiction(existing_value: str, new_value: str) -> bool:
    """Check if two values for the same key are contradictory."""
    ev = existing_value.lower().strip()
    nv = new_value.lower().strip()
    
    # Exact or near-exact match = not a contradiction
    if ev == nv:
        return False
    
    # Check for negation patterns
    negation_pairs = [
        ("love", "hate"), ("like", "dislike"), ("enjoy", "can't stand"),
        ("always", "never"), ("favorite", "least favorite"),
    ]
    for pos, neg in negation_pairs:
        if (pos in ev and neg in nv) or (neg in ev and pos in nv):
            return True

    # If both are short and completely different, could be an evolution
    if len(ev) < 50 and len(nv) < 50:
        # Check word overlap
        ev_words = set(ev.split())
        nv_words = set(nv.split())
        overlap = len(ev_words & nv_words)
        total = max(len(ev_words), len(nv_words))
        if total > 3 and overlap / total < 0.2:
            return True  # Very different content for same key

    return False


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def update_dossier_from_response(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    assistant_text: str,
    turn_id: str,
) -> dict[str, int]:
    """
    Post-response writer: extract self-claims and update self_memory.
    
    Uses LLM extraction when available, falls back to regex patterns.
    
    Returns: {"new": N, "reinforced": N, "conflicts": N}
    """
    if not sb or not assistant_text:
        return {"new": 0, "reinforced": 0, "conflicts": 0}

    # Try LLM-powered extraction first (more accurate for nuanced claims)
    claims: list[dict] = []
    try:
        from app.services.dossier.llm_generator import extract_self_claims_llm
        llm_claims = extract_self_claims_llm(assistant_text)
        if llm_claims:
            claims = llm_claims
            logger.debug("Self-claim extraction: LLM found %d claims", len(claims))
    except Exception as e:
        logger.debug("LLM self-claim extraction unavailable: %s", e)

    # Fallback to regex if LLM didn't produce results
    if not claims:
        regex_claims = extract_self_claims(assistant_text)
        claims = regex_claims
        if claims:
            logger.debug("Self-claim extraction: regex found %d claims", len(claims))

    if not claims:
        return {"new": 0, "reinforced": 0, "conflicts": 0}

    uid = str(user_id)
    gid = str(girlfriend_id)
    now = datetime.now(timezone.utc).isoformat()

    counts = {"new": 0, "reinforced": 0, "conflicts": 0}

    for claim in claims:
        key = claim["key"]
        value = claim["value"]

        try:
            # Check if key exists
            existing = sb.table("girlfriend_self_memory").select("*").eq(
                "user_id", uid
            ).eq("girlfriend_id", gid).eq("memory_key", key).limit(1).execute()

            if existing.data and len(existing.data) > 0:
                row = existing.data[0]
                old_value = row["memory_value"]

                # Check if immutable
                if row.get("is_immutable", False):
                    if _is_contradiction(old_value, value):
                        # Log conflict but don't change
                        sb.table("girlfriend_self_conflicts").insert({
                            "user_id": uid, "girlfriend_id": gid,
                            "memory_key": key,
                            "old_value": old_value, "new_value": value,
                            "status": "rejected",
                            "resolution_note": "immutable key cannot change",
                        }).execute()
                        counts["conflicts"] += 1
                    continue

                if _is_contradiction(old_value, value):
                    # Soft key contradiction — update but log conflict
                    sb.table("girlfriend_self_conflicts").insert({
                        "user_id": uid, "girlfriend_id": gid,
                        "memory_key": key,
                        "old_value": old_value, "new_value": value,
                        "status": "evolved",
                        "resolution_note": "soft key updated to newer value",
                    }).execute()

                    sb.table("girlfriend_self_memory").update({
                        "memory_value": value,
                        "last_seen_at": now,
                        "source_turn_id": turn_id,
                        "is_conflicted": True,
                        "conflict_group": key,
                    }).eq("id", row["id"]).execute()

                    counts["conflicts"] += 1
                else:
                    # Reinforce confidence
                    new_conf = min(100, row.get("confidence", 80) + 2)
                    sb.table("girlfriend_self_memory").update({
                        "confidence": new_conf,
                        "last_seen_at": now,
                    }).eq("id", row["id"]).execute()
                    counts["reinforced"] += 1
            else:
                # New self-fact
                sb.table("girlfriend_self_memory").insert({
                    "user_id": uid, "girlfriend_id": gid,
                    "memory_key": key,
                    "memory_value": value,
                    "confidence": 70,
                    "salience": 50,
                    "is_immutable": False,
                    "source_turn_id": turn_id,
                    "source": "conversation",
                }).execute()
                counts["new"] += 1

        except Exception as e:
            logger.warning("Self-memory update error for key %s: %s", key, e)

    return counts


def update_conversation_mode_state(
    sb: Any,
    user_id: UUID,
    girlfriend_id: UUID,
    assistant_text: str,
    intent_label: str,
    cadence_used: str,
    story_ids_used: list[str] | None = None,
) -> None:
    """Update the rolling conversation mode metrics after each turn."""
    if not sb:
        return

    uid = str(user_id)
    gid = str(girlfriend_id)

    try:
        existing = sb.table("conversation_mode_state").select("*").eq(
            "user_id", uid
        ).eq("girlfriend_id", gid).limit(1).execute()

        row = existing.data[0] if existing.data else {}

        # Update rolling metrics
        last_intents = (row.get("last_intents") or [])[-9:] + [intent_label]
        last_cadences = (row.get("last_cadences") or [])[-9:] + [cadence_used]

        # Count questions in the response
        sentences = re.split(r'[.!?]+', assistant_text)
        question_count = sum(1 for s in sentences if s.strip().endswith("?") or "?" in s)
        total_sentences = max(len([s for s in sentences if s.strip()]), 1)

        # Calculate rolling question ratio over last 10 entries
        consec_q = row.get("consecutive_questions", 0)
        ends_with_question = assistant_text.rstrip().endswith("?")
        if ends_with_question:
            consec_q += 1
        else:
            consec_q = 0

        # Question ratio: rolling average
        old_ratio = row.get("question_ratio_10", 0.0)
        turn_q_ratio = question_count / total_sentences
        new_ratio = old_ratio * 0.8 + turn_q_ratio * 0.2  # Exponential moving average

        # Self-disclosure detection
        self_claims = extract_self_claims(assistant_text)
        has_disclosure = len(self_claims) > 0
        old_disc_ratio = row.get("self_disclosure_ratio_10", 0.0)
        new_disc_ratio = old_disc_ratio * 0.8 + (1.0 if has_disclosure else 0.0) * 0.2

        # Story IDs used
        recent_stories = (row.get("story_ids_used_recently") or [])[-15:]
        if story_ids_used:
            recent_stories.extend(story_ids_used)
            recent_stories = recent_stories[-20:]

        # Generic phrase tracking (rolling).
        generic_phrases = (
            "that's a great question",
            "tell me more",
            "i'd love to hear more",
            "how can i help",
            "i'm here to help",
        )
        text_lower = assistant_text.lower()
        was_generic = any(p in text_lower for p in generic_phrases)
        old_generic = int(row.get("generic_response_count", 0) or 0)
        new_generic = max(0, old_generic - 1)
        if was_generic:
            new_generic = min(50, old_generic + 1)

        # Callback hit-rate proxy: did we use a story/memory callback this turn.
        old_callback = float(row.get("callback_hit_rate", 0.0) or 0.0)
        callback_hit = 1.0 if story_ids_used else 0.0
        new_callback = old_callback * 0.85 + callback_hit * 0.15

        payload = {
            "user_id": uid,
            "girlfriend_id": gid,
            "question_ratio_10": round(new_ratio, 3),
            "self_disclosure_ratio_10": round(new_disc_ratio, 3),
            "last_intents": last_intents,
            "last_cadences": last_cadences,
            "consecutive_questions": consec_q,
            "story_ids_used_recently": recent_stories,
            "generic_response_count": new_generic,
            "callback_hit_rate": round(new_callback, 3),
        }

        try:
            sb.table("conversation_mode_state").upsert(
                payload,
                on_conflict="user_id,girlfriend_id",
            ).execute()
        except Exception as e:
            # If DB schema is missing newer columns, retry without the unknown field(s)
            # so the rest of the mode-state tracking still works.
            msg = str(e)
            m = re.search(r"Could not find the '([^']+)' column", msg)
            if m:
                missing_col = m.group(1)
                if missing_col in payload:
                    payload.pop(missing_col, None)
                    sb.table("conversation_mode_state").upsert(
                        payload,
                        on_conflict="user_id,girlfriend_id",
                    ).execute()
                else:
                    raise
            else:
                raise

    except Exception as e:
        logger.warning("Conversation mode state update failed: %s", e)
