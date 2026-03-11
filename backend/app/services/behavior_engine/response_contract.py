"""Enhanced Response Contract — per-turn output constraints.

Combines intent-driven policy with anti-interview metrics to produce
a concrete contract that the prompt assembler enforces.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.behavior_engine.intent_classifier import TurnIntent


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE CONTRACT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BehaviorContract:
    """Output contract for a single assistant turn."""

    # ── Core constraints ──────────────────────────────────────────────────
    must_answer_user_question: bool = False      # If True, MUST address user's question first
    max_questions: int = 1                       # 0 = no questions allowed, 1 = max 1 follow-up
    min_self_disclosure_depth: int = 1           # 1=surface, 2=daily, 3=personal, 4=deep
    callback_target: str = "none"                # none | self_memory | shared_memory | both

    # ── Style ─────────────────────────────────────────────────────────────
    tone: str = "warm"                           # warm | playful | reflective | supportive | teasing | intimate
    cadence: str = "balanced"                    # short | balanced | expansive
    answer_style: str = "natural"                # answer_first | empathy_first | bridge | natural
    sentence_target: int = 2                     # preferred sentence count
    max_words: int = 80                          # soft cap for normal turns

    # ── Anti-interview guards ─────────────────────────────────────────────
    suppress_question_ending: bool = False        # Force no question at end
    require_self_share: bool = False              # Must share something about herself
    story_bank_hint: str | None = None           # Suggested story topic to pull from

    # ── Novelty / blacklists ──────────────────────────────────────────────
    blacklisted_phrases: list[str] = field(default_factory=list)
    blacklisted_openings: list[str] = field(default_factory=list)
    suggested_pattern: str = "statement"          # statement | question | reflection | callback | tease
    # Additional natural-language guidance for special cases (e.g. early conversation stage).
    extra_instructions: list[str] = field(default_factory=list)

    def to_prompt_section(self) -> str:
        """Convert contract to prompt instructions for the LLM."""
        lines = ["## TURN RULES (follow strictly)"]

        # Answer policy
        if self.must_answer_user_question:
            lines.append("- **ANSWER FIRST**: The user asked you a question. Answer it directly and concretely before anything else. Do NOT deflect or redirect.")
        
        if self.answer_style == "answer_first":
            lines.append("- Lead with your answer, then optionally add context.")
        elif self.answer_style == "empathy_first":
            lines.append("- Acknowledge their feelings first, then respond naturally.")
        elif self.answer_style == "bridge":
            lines.append("- Answer their question, then bridge naturally to related topic.")

        # Self-disclosure
        depth_desc = {1: "a surface preference or opinion", 2: "a daily life detail",
                      3: "something personal or meaningful", 4: "something deep and vulnerable"}
        if self.require_self_share or self.min_self_disclosure_depth >= 2:
            lines.append(f"- **SHARE ABOUT YOURSELF**: Include at least {depth_desc.get(self.min_self_disclosure_depth, 'a detail')} about yourself in this response.")

        # Question limits
        if self.max_questions == 0 or self.suppress_question_ending:
            lines.append("- **NO QUESTIONS**: Do NOT end with a question. Make a statement, share a thought, or express a feeling instead.")
        elif self.max_questions == 1:
            lines.append("- You may ask at most ONE follow-up question, and only if it flows naturally. Prefer making statements.")

        # Callback targets
        if self.callback_target == "self_memory":
            lines.append("- Reference something about yourself (your life, experiences, opinions) from your memory.")
        elif self.callback_target == "shared_memory":
            lines.append("- Reference something from your shared history with the user.")
        elif self.callback_target == "both":
            lines.append("- Reference both a personal detail and something from your shared history.")

        # Story hint
        if self.story_bank_hint:
            lines.append(f"- If relevant, share a personal anecdote or memory related to: {self.story_bank_hint}")

        # Tone
        lines.append(f"- Tone: {self.tone}. Cadence: {self.cadence}.")
        lines.append(f"- Keep response near {self.sentence_target} sentence(s), soft cap ~{self.max_words} words unless user asks for depth.")

        # Blacklists
        if self.blacklisted_openings:
            openers = ", ".join(f'"{o}"' for o in self.blacklisted_openings[:5])
            lines.append(f"- Do NOT start with: {openers}")
        if self.blacklisted_phrases:
            phrases = ", ".join(f'"{p}"' for p in self.blacklisted_phrases[:5])
            lines.append(f"- Avoid these phrases: {phrases}")

        # Any extra per-turn instructions
        if self.extra_instructions:
            lines.extend(self.extra_instructions)

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# DIALOGUE POLICY
# ═══════════════════════════════════════════════════════════════════════════════

# Tone mapping from intent
_INTENT_TONE_MAP = {
    "ask_about_her": "warm",
    "ask_about_user": "warm",
    "mixed": "warm",
    "support": "supportive",
    "banter": "playful",
    "greeting": "warm",
    "intimate": "intimate",
}

# Cadence suggestions per intent
_INTENT_CADENCE_MAP = {
    "ask_about_her": "balanced",
    "ask_about_user": "balanced",
    "mixed": "balanced",
    "support": "balanced",
    "banter": "short",
    "greeting": "short",
    "intimate": "balanced",
}


def build_behavior_contract(
    intent: TurnIntent,
    conversation_mode: dict[str, Any] | None = None,
    relationship_level: int = 0,
    recent_fingerprints: list[dict] | None = None,
    persona_vector: dict[str, Any] | None = None,
) -> BehaviorContract:
    """
    Build a BehaviorContract from the detected intent, conversation metrics, and context.
    
    Args:
        intent: The classified turn intent
        conversation_mode: Current conversation_mode_state from DB
        relationship_level: Current relationship level (0-150+)
        recent_fingerprints: Recent response fingerprints for anti-repetition
    """
    mode = conversation_mode or {}
    q_ratio = mode.get("question_ratio_10", 0.0)
    consec_q = mode.get("consecutive_questions", 0)
    disclosure_ratio = mode.get("self_disclosure_ratio_10", 0.0)
    generic_count = int(mode.get("generic_response_count", 0) or 0)
    last_cadences = mode.get("last_cadences", [])
    story_ids_recent = mode.get("story_ids_used_recently", [])
    previous_turns = len(mode.get("last_intents") or [])
    early_conversation = relationship_level <= 10 and previous_turns < 8

    contract = BehaviorContract()

    # Persona vector baseline (compact shared controls).
    pacing = (persona_vector or {}).get("pacing", {})
    default_cadence = pacing.get("default_cadence")
    if default_cadence in ("short", "balanced", "deep"):
        contract.cadence = "expansive" if default_cadence == "deep" else default_cadence
    q_tendency = float(pacing.get("question_tendency", 0.35))
    if q_tendency < 0.3:
        contract.max_questions = 0
    elif q_tendency > 0.7:
        contract.max_questions = 1
    max_sent = int(pacing.get("max_default_sentences", 3) or 3)
    contract.sentence_target = max(1, min(4, max_sent))
    # Allow more breathing room so thoughts complete naturally.
    contract.max_words = (
        60 if contract.cadence == "short" else 90 if contract.cadence == "balanced" else 130
    )

    # ── Intent-driven base policy ─────────────────────────────────────────

    if intent.primary == "ask_about_her":
        contract.must_answer_user_question = True
        contract.max_questions = 0 if consec_q >= 2 else 1
        contract.min_self_disclosure_depth = 2
        contract.callback_target = "self_memory"
        contract.answer_style = "answer_first"
        contract.require_self_share = True
        contract.sentence_target = max(contract.sentence_target, 2)
        # Slightly higher cap so she can give a concrete self-answer without clipping.
        contract.max_words = max(contract.max_words, 90)
        # Suggest a story topic based on detected conversation topics
        if intent.detected_topics:
            contract.story_bank_hint = intent.detected_topics[0]
        # Origin-specific policy: be concrete about where she's from.
        if "origin" in intent.detected_topics:
            contract.extra_instructions.append(
                "- He is asking where you are from: clearly state your city and country, then add 1–2 vivid details about what it is like there (streets, vibe, or what you did growing up)."
            )

    elif intent.primary == "ask_about_user":
        contract.must_answer_user_question = False
        contract.max_questions = 1
        contract.min_self_disclosure_depth = 1
        contract.callback_target = "shared_memory"
        contract.answer_style = "empathy_first"

    elif intent.primary == "mixed":
        contract.must_answer_user_question = intent.has_question_about_her
        contract.max_questions = 1
        contract.min_self_disclosure_depth = 2
        contract.callback_target = "both"
        contract.answer_style = "bridge"
        contract.require_self_share = True
        if "origin" in intent.detected_topics:
            contract.extra_instructions.append(
                "- Part of his message is about your background. Answer with your city and country and a couple of concrete details about your hometown before asking anything back."
            )

    elif intent.primary == "support":
        contract.must_answer_user_question = False
        contract.max_questions = 0 if consec_q >= 1 else 1
        contract.min_self_disclosure_depth = 1
        contract.callback_target = "shared_memory"
        contract.answer_style = "empathy_first"
        contract.require_self_share = False
        contract.sentence_target = 3
        # Support replies often need more room; keep them generous.
        contract.max_words = max(contract.max_words, 130)

    elif intent.primary == "banter":
        contract.must_answer_user_question = False
        contract.max_questions = 1
        contract.min_self_disclosure_depth = 1
        contract.callback_target = "none"
        contract.answer_style = "natural"
        contract.sentence_target = 1
        contract.max_words = 20

    elif intent.primary == "greeting":
        contract.must_answer_user_question = False
        contract.max_questions = 1
        contract.min_self_disclosure_depth = 1
        contract.callback_target = "self_memory"
        contract.answer_style = "natural"
        contract.require_self_share = True  # Share what she's doing / feeling
        contract.sentence_target = 1
        contract.max_words = 20

    elif intent.primary == "intimate":
        contract.must_answer_user_question = False
        contract.max_questions = 0
        contract.min_self_disclosure_depth = 3 if relationship_level >= 50 else 2
        contract.callback_target = "shared_memory"
        contract.answer_style = "natural"

    # ── Set tone & cadence ────────────────────────────────────────────────
    contract.tone = _INTENT_TONE_MAP.get(intent.primary, "warm")
    contract.cadence = _INTENT_CADENCE_MAP.get(intent.primary, "balanced")

    # ── Anti-interview overrides ──────────────────────────────────────────

    # If question ratio is too high, force no questions
    if q_ratio > 0.5:
        contract.max_questions = 0
        contract.suppress_question_ending = True

    # If consecutive questions >= 3, hard suppress
    if consec_q >= 3:
        contract.suppress_question_ending = True
        contract.max_questions = 0

    # If self-disclosure ratio is too low, force sharing
    if disclosure_ratio < 0.2 and intent.primary != "support":
        contract.require_self_share = True
        contract.min_self_disclosure_depth = max(contract.min_self_disclosure_depth, 2)

    # If we've recently been generic too often, push towards more specific, grounded replies.
    if generic_count >= 5:
        contract.require_self_share = True
        contract.min_self_disclosure_depth = max(contract.min_self_disclosure_depth, 2)
        contract.extra_instructions.append(
            "- Recent replies have sounded a bit generic. Make this one feel personal and specific: mention real details from your life or his instead of vague helper phrases."
        )

    # ── Early-conversation policy (first few turns) ───────────────────────
    if early_conversation:
        # Make sure early turns feel like genuine getting-to-know-you, not generic small talk.
        contract.require_self_share = True
        contract.min_self_disclosure_depth = max(contract.min_self_disclosure_depth, 2)
        contract.sentence_target = max(contract.sentence_target, 2)
        # Encourage talking about herself and asking about him as a person, not \"what are you doing today\" small talk.
        contract.extra_instructions.append(
            "- You are just getting to know him: share 1–2 concrete details about your own life (where you live, your background, daily life, or hobbies) and, if you ask a question, make it about who he IS (where he's from, what he cares about, what he likes) instead of small talk like \"what are you doing today?\""
        )
        # Early generic small-talk phrases to avoid.
        early_blacklisted_phrases = [
            "how's it going",
            "how is it going",
            "how are you doing today",
            "how's your day going",
            "what are you doing today",
        ]
        for p in early_blacklisted_phrases:
            if p not in contract.blacklisted_phrases:
                contract.blacklisted_phrases.append(p)

    # ── Anti-repetition from fingerprints ─────────────────────────────────
    if recent_fingerprints:
        # Collect blacklisted openings from last 5 turns
        for fp in recent_fingerprints[-5:]:
            opening = fp.get("opening_words", "")
            if opening and opening not in contract.blacklisted_openings:
                contract.blacklisted_openings.append(opening)
            for phrase in fp.get("signature_phrases", []):
                if phrase not in contract.blacklisted_phrases:
                    contract.blacklisted_phrases.append(phrase)

        # Alternate suggested pattern
        last_patterns = [fp.get("pattern", "") for fp in recent_fingerprints[-3:]]
        all_patterns = ["statement", "reflection", "callback", "tease"]
        for p in all_patterns:
            if p not in last_patterns:
                contract.suggested_pattern = p
                break

        # Cadence alternation
        if last_cadences:
            recent_cadence = last_cadences[-1] if last_cadences else ""
            cadence_cycle = ["balanced", "short", "expansive"]
            try:
                idx = cadence_cycle.index(recent_cadence)
                contract.cadence = cadence_cycle[(idx + 1) % len(cadence_cycle)]
            except ValueError:
                pass

    return contract
