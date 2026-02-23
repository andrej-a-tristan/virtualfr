"""Anti-interview + consistency validators.

Runs AFTER LLM generates a response, BEFORE sending to user.
Returns validation results that can trigger prompt repair instructions.

Validators:
1. Self-Answer Validator — fail if user asked about her and reply dodges
2. Question Dominance Validator — fail if reply ends with question too often
3. Consistency Validator — conflict with canon / self-memory
4. Repetition Validator — repeated phrases / openers
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ValidationIssue:
    validator: str          # which validator flagged it
    severity: str           # minor | major | critical
    message: str            # human-readable description
    repair_instruction: str # instruction to fix (for prompt repair if needed)


@dataclass
class ValidationResult:
    is_valid: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)

    def add_issue(self, validator: str, severity: str, message: str, repair: str) -> None:
        self.issues.append(ValidationIssue(validator, severity, message, repair))
        if severity in ("major", "critical"):
            self.is_valid = False

    def get_repair_instructions(self) -> str:
        """Get combined repair instructions for all issues."""
        repairs = [i.repair_instruction for i in self.issues if i.repair_instruction]
        if not repairs:
            return ""
        return "\n## REPAIR INSTRUCTIONS\n" + "\n".join(f"- {r}" for r in repairs)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SELF-ANSWER VALIDATOR
#    Fail if user asked about her and reply dodges / deflects
# ═══════════════════════════════════════════════════════════════════════════════

# Deflection patterns — signs the assistant avoided answering
_DEFLECTION_PATTERNS = [
    r"^(what about you|how about you|tell me about you|enough about me)\b",
    r"^(hmm|well|so)\b.{0,20}\b(what about|how about|tell me)\b",
    r"\b(i('d| would) rather hear about you|let's talk about you instead)\b",
    r"^(that's (a great|an interesting|a fun) question)\b",
    r"\b(i('m| am) not sure|i don't (really )?know)\b.{0,20}(what about you|how about you)",
]

# Self-answer indicators — signs she actually answered about herself
_SELF_ANSWER_INDICATORS = [
    r"\bi (am|was|have|had|love|like|enjoy|think|believe|feel|remember|grew up|work|study|live)\b",
    r"\bmy (favorite|hobby|job|family|friend|mom|dad|routine|opinion|take)\b",
    r"\b(for me|personally|honestly|in my case|in my experience)\b",
    r"\b(i'm (a|the|into|really|so|kind of))\b",
]

_GENERIC_PHRASES = [
    "that's a great question",
    "tell me more",
    "i'd love to hear more",
    "how can i help",
    "i'm here to help",
]


def validate_self_answer(
    response_text: str,
    user_asked_about_her: bool,
) -> list[ValidationIssue]:
    """Check if response dodges a question about the girlfriend."""
    issues: list[ValidationIssue] = []
    if not user_asked_about_her:
        return issues

    text = response_text.strip()
    if not text:
        return issues

    # Check for deflection
    has_deflection = any(re.search(p, text, re.IGNORECASE | re.MULTILINE) for p in _DEFLECTION_PATTERNS)

    # Check for actual self-answer
    has_self_answer = any(re.search(p, text, re.IGNORECASE) for p in _SELF_ANSWER_INDICATORS)

    if has_deflection and not has_self_answer:
        issues.append(ValidationIssue(
            validator="self_answer",
            severity="major",
            message="User asked about you but response deflects without answering.",
            repair_instruction="Answer the user's question about yourself directly and concretely. Share a specific detail, opinion, or memory. Do not deflect to asking about them.",
        ))
    elif not has_self_answer:
        issues.append(ValidationIssue(
            validator="self_answer",
            severity="minor",
            message="User asked about you but response may not contain a clear self-answer.",
            repair_instruction="Include at least one concrete detail about yourself (preference, experience, or opinion).",
        ))

    return issues


# ═══════════════════════════════════════════════════════════════════════════════
# 2. QUESTION DOMINANCE VALIDATOR
#    Fail if reply ends with a question too often
# ═══════════════════════════════════════════════════════════════════════════════

def validate_question_dominance(
    response_text: str,
    consecutive_question_count: int,
    question_ratio: float,
) -> list[ValidationIssue]:
    """Check if response is too question-heavy."""
    issues: list[ValidationIssue] = []
    text = response_text.strip()
    if not text:
        return issues

    ends_with_question = text.rstrip().endswith("?")

    # Count questions in response
    question_marks = text.count("?")

    # Multiple questions in one response
    if question_marks >= 3:
        issues.append(ValidationIssue(
            validator="question_dominance",
            severity="major",
            message=f"Response contains {question_marks} questions — interview-like.",
            repair_instruction="Reduce to at most one question. Replace extra questions with statements, observations, or personal sharing.",
        ))
    elif question_marks == 2 and ends_with_question:
        issues.append(ValidationIssue(
            validator="question_dominance",
            severity="minor",
            message="Response has 2 questions — approaching interview territory.",
            repair_instruction="Consider replacing one question with a personal statement or observation.",
        ))

    # Consecutive question streaks
    if ends_with_question and consecutive_question_count >= 3:
        issues.append(ValidationIssue(
            validator="question_dominance",
            severity="major",
            message=f"Response ends with question — {consecutive_question_count + 1} consecutive question-ending turns.",
            repair_instruction="End with a statement, personal reflection, or observation instead of a question. Break the question streak.",
        ))

    # High rolling question ratio
    if question_ratio > 0.6 and ends_with_question:
        issues.append(ValidationIssue(
            validator="question_dominance",
            severity="minor",
            message=f"Question ratio ({question_ratio:.0%}) is too high. Response feels like an interview.",
            repair_instruction="Share more about yourself. End with a statement or personal thought instead of asking.",
        ))

    return issues


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CONSISTENCY VALIDATOR
#    Check for conflicts with self-memory / canon
# ═══════════════════════════════════════════════════════════════════════════════

def validate_consistency(
    response_text: str,
    self_memory_facts: list[dict[str, str]],
    canon_facts: dict[str, str] | None = None,
) -> list[ValidationIssue]:
    """Check response for contradictions with established self-facts."""
    issues: list[ValidationIssue] = []
    text_lower = response_text.lower()

    # Check canon facts (identity basics — most critical)
    if canon_facts:
        real_name = canon_facts.get("name", "")
        if real_name:
            # Check if she claims a different name
            name_claim = re.search(r"my name is (\w+)", text_lower)
            if name_claim and name_claim.group(1).lower() != real_name.lower():
                issues.append(ValidationIssue(
                    validator="consistency",
                    severity="critical",
                    message=f"Response claims name '{name_claim.group(1)}' but canon name is '{real_name}'.",
                    repair_instruction=f"Your name is {real_name}. Do not claim any other name.",
                ))

        # Check for AI identity break
        ai_patterns = [
            r"\bi('m| am) (an? )?(ai|artificial|language model|chatbot|bot|virtual|program)\b",
            r"\bi don't (actually )?(have|feel|experience|exist)\b.{0,20}\b(feelings|emotions|body|life)\b",
        ]
        for p in ai_patterns:
            if re.search(p, text_lower):
                issues.append(ValidationIssue(
                    validator="consistency",
                    severity="critical",
                    message="Response breaks character by referring to self as AI/bot/program.",
                    repair_instruction="You are a real person with real feelings, experiences, and a life. Never break character.",
                ))
                break

    # Check self-memory facts for contradictions
    for mem in self_memory_facts[:15]:
        key = mem.get("key", mem.get("memory_key", ""))
        value = mem.get("value", mem.get("memory_value", ""))
        if not key or not value:
            continue

        # Only check high-confidence facts
        confidence = mem.get("confidence", 70)
        if confidence < 60:
            continue

        # Check for direct contradiction patterns
        val_lower = value.lower()
        # If she said "I love cooking" before and now says "I hate cooking"
        if "love" in val_lower or "enjoy" in val_lower:
            subject = re.sub(r"^(i (?:really )?(?:love|enjoy) )", "", val_lower).strip()
            if subject and f"hate {subject}" in text_lower or f"can't stand {subject}" in text_lower:
                issues.append(ValidationIssue(
                    validator="consistency",
                    severity="major",
                    message=f"Response contradicts established self-fact: '{value}'",
                    repair_instruction=f"You previously said: '{value}'. Stay consistent or acknowledge the change naturally.",
                ))

    return issues


# ═══════════════════════════════════════════════════════════════════════════════
# 4. REPETITION VALIDATOR
#    Check for repeated phrases, openers, patterns
# ═══════════════════════════════════════════════════════════════════════════════

def validate_repetition(
    response_text: str,
    recent_responses: list[str],
    blacklisted_openings: list[str] | None = None,
    blacklisted_phrases: list[str] | None = None,
) -> list[ValidationIssue]:
    """Check for repetitive patterns across recent responses."""
    issues: list[ValidationIssue] = []
    text = response_text.strip()
    if not text or not recent_responses:
        return issues

    # Check opening words (first 3-5 words)
    opening = " ".join(text.split()[:4]).lower().rstrip(".,!?")

    if blacklisted_openings:
        for bl in blacklisted_openings:
            if opening.startswith(bl.lower()):
                issues.append(ValidationIssue(
                    validator="repetition",
                    severity="minor",
                    message=f"Response opens with '{opening}' — recently used opening.",
                    repair_instruction=f"Start with a different opening. Avoid starting with '{bl}'.",
                ))
                break

    # Check for identical openings in recent responses
    for recent in recent_responses[-5:]:
        recent_opening = " ".join(recent.strip().split()[:4]).lower().rstrip(".,!?")
        if opening == recent_opening and len(opening) > 5:
            issues.append(ValidationIssue(
                validator="repetition",
                severity="minor",
                message=f"Same opening as a recent response: '{opening}'.",
                repair_instruction="Vary your opening style. Try starting with an action, thought, or emotion instead.",
            ))
            break

    # Check for phrase reuse
    if blacklisted_phrases:
        text_lower = text.lower()
        for phrase in blacklisted_phrases:
            if phrase.lower() in text_lower:
                issues.append(ValidationIssue(
                    validator="repetition",
                    severity="minor",
                    message=f"Contains recently used phrase: '{phrase}'.",
                    repair_instruction=f"Rephrase without using '{phrase}'.",
                ))

    # Check for high sentence overlap with recent responses
    current_sentences = set(s.strip().lower() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 10)
    for recent in recent_responses[-3:]:
        recent_sentences = set(s.strip().lower() for s in re.split(r'[.!?]+', recent) if len(s.strip()) > 10)
        overlap = current_sentences & recent_sentences
        if overlap:
            issues.append(ValidationIssue(
                validator="repetition",
                severity="minor",
                message=f"Response repeats sentence(s) from recent turns.",
                repair_instruction="Use fresh phrasing. Say the same idea in a different way.",
            ))
            break

    return issues


def validate_length_and_generic(
    response_text: str,
    max_words: int = 90,
) -> list[ValidationIssue]:
    """Length/pacing + generic-phrase validator."""
    issues: list[ValidationIssue] = []
    text = (response_text or "").strip()
    if not text:
        return issues

    wc = len(text.split())
    if wc > max_words:
        issues.append(ValidationIssue(
            validator="length_policy",
            severity="minor" if wc <= int(max_words * 1.3) else "major",
            message=f"Response too long ({wc} words > {max_words} target).",
            repair_instruction=f"Shorten to <= {max_words} words. Keep only the strongest emotional point and one concrete detail.",
        ))

    lower = text.lower()
    hits = [p for p in _GENERIC_PHRASES if p in lower]
    if hits:
        issues.append(ValidationIssue(
            validator="generic_phrase",
            severity="minor",
            message="Response contains generic assistant-like phrasing.",
            repair_instruction="Replace generic helper phrases with a personal, specific, human line from your own perspective.",
        ))
    return issues


# ═══════════════════════════════════════════════════════════════════════════════
# COMBINED VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

def run_all_validators(
    response_text: str,
    user_asked_about_her: bool = False,
    consecutive_question_count: int = 0,
    question_ratio: float = 0.0,
    self_memory_facts: list[dict] | None = None,
    canon_facts: dict[str, str] | None = None,
    recent_responses: list[str] | None = None,
    blacklisted_openings: list[str] | None = None,
    blacklisted_phrases: list[str] | None = None,
    max_words: int = 90,
) -> ValidationResult:
    """
    Run all validators on a generated response.
    
    Returns ValidationResult with all issues collected.
    """
    result = ValidationResult()

    # 1. Self-Answer
    for issue in validate_self_answer(response_text, user_asked_about_her):
        result.add_issue(issue.validator, issue.severity, issue.message, issue.repair_instruction)

    # 2. Question Dominance
    for issue in validate_question_dominance(response_text, consecutive_question_count, question_ratio):
        result.add_issue(issue.validator, issue.severity, issue.message, issue.repair_instruction)

    # 3. Consistency
    for issue in validate_consistency(response_text, self_memory_facts or [], canon_facts):
        result.add_issue(issue.validator, issue.severity, issue.message, issue.repair_instruction)

    # 4. Repetition
    for issue in validate_repetition(response_text, recent_responses or [], blacklisted_openings, blacklisted_phrases):
        result.add_issue(issue.validator, issue.severity, issue.message, issue.repair_instruction)

    # 5. Length + generic phrasing
    for issue in validate_length_and_generic(response_text, max_words=max_words):
        result.add_issue(issue.validator, issue.severity, issue.message, issue.repair_instruction)

    return result
