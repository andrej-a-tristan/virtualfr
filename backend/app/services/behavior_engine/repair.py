"""Hard response repair utilities for behavior contract enforcement."""
from __future__ import annotations

import re
from typing import Any


_AI_PATTERNS = [
    r"\bi('?m| am) (an? )?(ai|assistant|language model|chatbot|bot)\b",
    r"\bi('?m| am) not (an? )?(ai|assistant|language model|chatbot|bot)\b",
    r"\bas an ai\b",
    r"\bi (don't|do not) (have|feel|experience)\b.{0,30}\b(feelings|emotions|body|life)\b",
    r"\bi('?m| am) here to help\b",
]


def _clean_whitespace(text: str) -> str:
    out = re.sub(r"\s+", " ", (text or "")).strip()
    out = re.sub(r"\b(No|Yes),\s*;", r"\1,", out, flags=re.IGNORECASE)
    out = re.sub(r"\s+([,;:.!?])", r"\1", out)
    out = re.sub(r"([,;:.!?])\1+", r"\1", out)
    return out


def _strip_ai_identity(text: str) -> str:
    out = text or ""
    for pat in _AI_PATTERNS:
        out = re.sub(pat, "", out, flags=re.IGNORECASE)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out


def _limit_questions(text: str, max_questions: int, suppress_end_question: bool) -> str:
    if not text:
        return text
    if max_questions < 0:
        max_questions = 0
    q_seen = 0
    chars: list[str] = []
    for ch in text:
        if ch == "?":
            if q_seen < max_questions:
                chars.append("?")
            else:
                chars.append(".")
            q_seen += 1
        else:
            chars.append(ch)
    out = "".join(chars)
    if suppress_end_question:
        out = out.rstrip()
        if out.endswith("?"):
            out = out[:-1] + "."
    return out


def _trim_words(text: str, max_words: int) -> str:
    """Trim to a soft word cap without obviously clipping mid-thought."""
    if not text:
        return text
    try:
        max_words_int = int(max_words)
    except Exception:
        max_words_int = 60
    if max_words_int <= 0:
        return ""

    words = text.split()
    if len(words) <= max_words_int:
        return text

    # Start with a hard cut, then walk back from conjunctions / dangling fragments.
    trimmed_words = words[:max_words_int]
    bad_endings = {
        "and",
        "but",
        "or",
        "so",
        "because",
        "when",
        "while",
        "if",
        "though",
        "although",
        "since",
        # Common pronoun + aux fragments that sound clipped when alone.
        "you're",
        "youre",
        "i'm",
        "im",
        "we're",
        "were",
        "they're",
        "theyre",
        "he's",
        "shes",
        "he",
        "she",
        "you",
        "i",
        "they",
        "we",
        "that",
        "which",
        "who",
        "whom",
        "whose",
    }

    # Avoid ending on a明显 dangling connector; walk back a few tokens if needed.
    max_backtrack = 8
    backtracked = 0
    while (
        len(trimmed_words) > 5
        and backtracked < max_backtrack
        and trimmed_words[-1].rstrip(".,;:!?").lower() in bad_endings
    ):
        trimmed_words.pop()
        backtracked += 1

    if not trimmed_words:
        trimmed_words = words[:max_words_int]

    trimmed = " ".join(trimmed_words).rstrip(".,;:!?")
    return trimmed + "."


def _ensure_self_answer(text: str, fallback_self_fact: str | None = None) -> str:
    if re.search(r"\bi\b", text, flags=re.IGNORECASE):
        return text
    if fallback_self_fact:
        return f"For me, {fallback_self_fact}. {text}".strip()
    return f"For me, it feels personal and real. {text}".strip()


def apply_contract_hard_limits(
    response_text: str,
    contract: Any | None,
    user_asked_about_her: bool = False,
    fallback_self_fact: str | None = None,
) -> str:
    """Deterministic hard limits after generation.

    Design goal:
    - Let the model produce a naturally sized, flowing message guided by the
      behavior contract (sentence_target, tone, etc.).
    - Use this function only as a *safety net* (strip AI identity, cap
      pathological question spam, trim only if the reply is extremely long),
      not as a routine word-by-word cutter.
    """
    out = _clean_whitespace(response_text)
    if not out:
        return out

    max_questions = 1
    suppress_end_question = False
    max_words = 60

    if contract is not None:
        try:
            max_questions = int(getattr(contract, "max_questions", 1))
        except Exception:
            pass
        suppress_end_question = bool(getattr(contract, "suppress_question_ending", False))
        try:
            max_words = int(getattr(contract, "max_words", 60))
        except Exception:
            pass
    # Global hard ceiling from architecture: never exceed one follow-up question.
    max_questions = max(0, min(1, max_questions))

    out = _strip_ai_identity(out)
    out = _limit_questions(out, max_questions=max_questions, suppress_end_question=suppress_end_question)

    # Only trim if the model went way over the intended length (e.g. long ramble).
    # Normal replies are left untouched so they feel natural and conversational.
    try:
        word_limit = int(max_words)
    except Exception:
        word_limit = 60
    words = out.split()
    if len(words) > word_limit * 2:
        out = _trim_words(out, max_words=word_limit * 2)
    if user_asked_about_her:
        out = _ensure_self_answer(out, fallback_self_fact=fallback_self_fact)
    return _clean_whitespace(out)

