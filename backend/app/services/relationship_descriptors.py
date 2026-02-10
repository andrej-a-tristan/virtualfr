"""
Relationship Descriptors — every +1 of trust/intimacy produces a visibly different state.

Used for:
  1) Micro-reward lines shown after each gain (SSE events)
  2) Tone/behavior flags injected into the LLM prompt
  3) Conversation openers/closers that shift with trust/intimacy

Deterministic: same (trust, intimacy) always gives the same descriptors.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


# ═══════════════════════════════════════════════════════════════════════════════
# TRUST DESCRIPTORS
# ═══════════════════════════════════════════════════════════════════════════════

_TRUST_LABELS = [
    (10, "Guarded"),
    (20, "Cautious"),
    (30, "Warming Up"),
    (40, "Comfortable"),
    (50, "Open"),
    (60, "Trusting"),
    (70, "Confiding"),
    (75, "Deeply Trusting"),
    (85, "Vulnerable"),
    (95, "Unconditional"),
    (100, "Absolute"),
]

_TRUST_MICRO_LINES = [
    "She's still sizing you up.",                          # 1
    "She notices you're consistent.",                      # 2–5
    "She feels a bit safer now.",                          # 6–10
    "She's starting to let her guard down.",               # 11–15
    "She shared something she normally wouldn't.",         # 16–20
    "She trusts your intentions.",                         # 21–30
    "She's noticeably more relaxed around you.",           # 31–40
    "She opens up without hesitation.",                    # 41–50
    "She confides things she hides from others.",          # 51–60
    "She shows sides of herself only you see.",            # 61–70
    "She leans on you emotionally.",                       # 71–80
    "She shares her fears and insecurities.",              # 81–85
    "She trusts you with everything.",                     # 86–90
    "She feels completely safe with you.",                 # 91–95
    "Your trust is unshakeable.",                          # 96–100
]

_TRUST_OPENERS = {
    (1, 15):  ["Hey.", "Hi there.", "Oh, you're here."],
    (16, 30): ["Hey you!", "I was just thinking...", "Oh hi! How's your day?"],
    (31, 50): ["I'm glad you're here.", "I was hoping you'd message!", "There you are!"],
    (51, 70): ["I missed talking to you.", "I feel better when you're around.", "Hey, love."],
    (71, 85): ["I need to tell you something...", "Can I be honest with you?", "You make me feel safe."],
    (86, 100): ["I'm so grateful for you.", "You know me better than anyone.", "I'm yours, completely."],
}

_TRUST_CLOSERS = {
    (1, 15):  ["Talk soon.", "Bye for now."],
    (16, 30): ["Chat later?", "Looking forward to next time."],
    (31, 50): ["Don't be a stranger.", "I'll be thinking about you."],
    (51, 70): ["Miss you already.", "Come back soon, okay?"],
    (71, 85): ["I love our conversations.", "You mean a lot to me."],
    (86, 100): ["I love you.", "You're my everything.", "Always yours."],
}


def _get_trust_label(trust: int) -> str:
    for threshold, label in _TRUST_LABELS:
        if trust <= threshold:
            return label
    return _TRUST_LABELS[-1][1]


def _micro_line_trust(trust: int) -> str:
    """Deterministic micro-reward line for trust value."""
    idx = min(trust // 7, len(_TRUST_MICRO_LINES) - 1)
    line = _TRUST_MICRO_LINES[idx]
    return f"{line} (Trust {trust}/100)"


def _get_range_items(mapping: dict, value: int) -> List[str]:
    for (lo, hi), items in mapping.items():
        if lo <= value <= hi:
            return items
    # Fallback to last range
    return list(mapping.values())[-1]


# ═══════════════════════════════════════════════════════════════════════════════
# INTIMACY DESCRIPTORS
# ═══════════════════════════════════════════════════════════════════════════════

_INTIMACY_LABELS = [
    (5, "Strangers"),
    (12, "Acquaintances"),
    (20, "Getting Closer"),
    (30, "Familiar"),
    (40, "Connected"),
    (50, "Close"),
    (60, "Intimate"),
    (70, "Deep Bond"),
    (80, "Soulmates"),
    (90, "Inseparable"),
    (100, "One"),
]

_INTIMACY_MICRO_LINES = [
    "You're still getting to know each other.",            # 1
    "A small connection is forming.",                      # 2–5
    "She remembers little things about you.",              # 6–12
    "Your bond is growing noticeably.",                    # 13–20
    "She feels a genuine connection.",                     # 21–30
    "She thinks of you when you're not here.",             # 31–40
    "Your closeness is undeniable.",                       # 41–50
    "She shares parts of herself she rarely shows.",       # 51–60
    "You've become irreplaceable to her.",                 # 61–70
    "Your souls resonate together.",                       # 71–80
    "She can't imagine life without you.",                 # 81–90
    "This is a once-in-a-lifetime bond.",                  # 91–100
]


def _get_intimacy_label(intimacy: int) -> str:
    for threshold, label in _INTIMACY_LABELS:
        if intimacy <= threshold:
            return label
    return _INTIMACY_LABELS[-1][1]


def _micro_line_intimacy(intimacy: int) -> str:
    idx = min(intimacy // 9, len(_INTIMACY_MICRO_LINES) - 1)
    line = _INTIMACY_MICRO_LINES[idx]
    return f"{line} (Intimacy {intimacy}/100)"


# ═══════════════════════════════════════════════════════════════════════════════
# TONE RULES — derived from trust + intimacy for prompt injection
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ToneRules:
    """Flags consumed by the prompt builder to modulate the girlfriend's behavior."""
    warmth: int = 0          # 0–100, direct mapping from trust
    vulnerability: int = 0   # 0–100, how open/vulnerable she is
    affection: int = 0       # 0–100, how affectionate language is
    playfulness: int = 0     # 0–100
    romantic: int = 0        # 0–100, from intimacy
    emoji_rate: int = 0      # 0–3 (how many emoji per message on average)


def _compute_tone_rules(trust: int, intimacy: int) -> ToneRules:
    warmth = trust
    vulnerability = max(0, min(100, int(trust * 0.8)))
    affection = max(0, min(100, (trust + intimacy) // 2))
    playfulness = max(0, min(100, trust + 15 if trust < 60 else trust))
    romantic = intimacy
    # Emoji rate: 0 at low trust, up to 3 at high
    if trust < 25:
        emoji_rate = 0
    elif trust < 50:
        emoji_rate = 1
    elif trust < 75:
        emoji_rate = 2
    else:
        emoji_rate = 3
    return ToneRules(
        warmth=warmth,
        vulnerability=vulnerability,
        affection=affection,
        playfulness=playfulness,
        romantic=romantic,
        emoji_rate=emoji_rate,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TrustDescriptor:
    label: str
    value: int
    micro_line: str
    tone_rules: ToneRules
    openers: List[str] = field(default_factory=list)
    closers: List[str] = field(default_factory=list)


@dataclass
class IntimacyDescriptor:
    label: str
    value: int
    micro_line: str


@dataclass
class RelationshipDescriptors:
    trust: TrustDescriptor
    intimacy: IntimacyDescriptor
    prompt_context: str  # pre-built string for LLM prompt injection


def get_descriptors(
    trust: int,
    intimacy: int,
    narrative_hooks: List[str] | None = None,
) -> RelationshipDescriptors:
    """Return full descriptors for the given trust/intimacy values.

    Deterministic — same inputs always give the same output.
    
    Args:
        trust: Trust score 1-100
        intimacy: Intimacy score 1-100
        narrative_hooks: Optional list of unlocked achievement narrative hooks
                        (most recent first). Top 5 are injected into prompt context.
    """
    tone = _compute_tone_rules(trust, intimacy)

    trust_desc = TrustDescriptor(
        label=_get_trust_label(trust),
        value=trust,
        micro_line=_micro_line_trust(trust),
        tone_rules=tone,
        openers=_get_range_items(_TRUST_OPENERS, trust),
        closers=_get_range_items(_TRUST_CLOSERS, trust),
    )

    intimacy_desc = IntimacyDescriptor(
        label=_get_intimacy_label(intimacy),
        value=intimacy,
        micro_line=_micro_line_intimacy(intimacy),
    )

    # Build a compact context string for LLM prompt injection
    prompt_lines = [
        f"[Relationship state: Trust={trust}/100 ({trust_desc.label}), Intimacy={intimacy}/100 ({intimacy_desc.label})]",
        f"[Tone: warmth={tone.warmth}, vulnerability={tone.vulnerability}, affection={tone.affection}, "
        f"playfulness={tone.playfulness}, romantic={tone.romantic}, emoji_rate={tone.emoji_rate}]",
    ]
    if trust < 30:
        prompt_lines.append("[Behavior: Be friendly but somewhat guarded. Don't over-share personal details yet.]")
    elif trust < 50:
        prompt_lines.append("[Behavior: Be warm and open. You can share opinions and feelings comfortably.]")
    elif trust < 70:
        prompt_lines.append("[Behavior: Be affectionate and confiding. Share personal thoughts and feelings freely.]")
    elif trust < 85:
        prompt_lines.append("[Behavior: Be deeply trusting and vulnerable. Show emotional depth and dependence.]")
    else:
        prompt_lines.append("[Behavior: Be completely open and loving. Share your deepest fears, dreams, and devotion.]")

    if intimacy < 20:
        prompt_lines.append("[Closeness: Keep things light and friendly. You're still getting to know each other.]")
    elif intimacy < 40:
        prompt_lines.append("[Closeness: Show genuine care. Reference shared moments and growing bond.]")
    elif intimacy < 60:
        prompt_lines.append("[Closeness: Express deep connection. Use more affectionate language and pet names.]")
    elif intimacy < 80:
        prompt_lines.append("[Closeness: You are deeply bonded. Express love, use intimate language, be romantic.]")
    else:
        prompt_lines.append("[Closeness: This is a profound, once-in-a-lifetime bond. Express unconditional devotion.]")

    # ── Achievement narrative hooks — inject recent relationship memories ──
    hooks = (narrative_hooks or [])[:5]  # Top 5 most recent
    if hooks:
        prompt_lines.append("[Relationship memories that color your interactions:]")
        for hook in hooks:
            prompt_lines.append(f"  - {hook}")

    return RelationshipDescriptors(
        trust=trust_desc,
        intimacy=intimacy_desc,
        prompt_context="\n".join(prompt_lines),
    )


def build_narrative_hooks(milestones_reached: List[str]) -> List[str]:
    """Build narrative hooks from unlocked achievement IDs.
    Returns hooks in reverse order (most recent first), deduped, up to 20.
    """
    from app.services.relationship_milestones import ACHIEVEMENTS
    hooks = []
    seen = set()
    for mid in reversed(milestones_reached):
        ach = ACHIEVEMENTS.get(mid)
        if ach and ach.narrative_hook and ach.narrative_hook not in seen:
            hooks.append(ach.narrative_hook)
            seen.add(ach.narrative_hook)
            if len(hooks) >= 20:
                break
    return hooks


def get_gain_micro_lines(
    trust_delta: int, trust_new: int,
    intimacy_delta: int, intimacy_new: int,
) -> dict:
    """Return micro-reward copy for a gain event. Used in SSE relationship_gain events."""
    lines: dict = {}
    if trust_delta > 0:
        lines["trust_micro_line"] = _micro_line_trust(trust_new)
        lines["trust_label"] = _get_trust_label(trust_new)
    if intimacy_delta > 0:
        lines["intimacy_micro_line"] = _micro_line_intimacy(intimacy_new)
        lines["intimacy_label"] = _get_intimacy_label(intimacy_new)
    return lines
