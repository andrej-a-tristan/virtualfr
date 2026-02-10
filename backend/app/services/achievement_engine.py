"""
Achievement evaluation engine — structured emotional milestone detection.

Features:
  - Structured emotional event detection with strength levels
  - First-time milestone flags for key emotional moments
  - Anti-farm cooldowns: same phrase repeated doesn't retrigger within X hours
  - Multi-turn arc detection (e.g. conflict repair: tension → apology → reassurance)
  - NON-MISSABLE rule: past + current region achievements can unlock
  - Ring buffer of recent detected events with timestamps for evidence tracking
  - Deduplication: each milestone counts once per meaningful event
"""
from __future__ import annotations

import re
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.relationship_milestones import (
    Achievement,
    ACHIEVEMENTS,
    ACHIEVEMENTS_BY_REGION,
    TriggerType,
    get_eligible_achievements,
)
from app.services.relationship_regions import get_region_for_level

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DETECTED EVENT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DetectedEvent:
    """A single detected emotional signal from a message."""
    signal: str          # e.g. "affection", "vulnerability", "we_language"
    strength: int        # 1..3 (weak, moderate, strong)
    timestamp: float     # time.time()
    message_index: int   # index in conversation (for gap checks)
    phrase_hash: int     # hash of the triggering phrase (for dedup)


# ═══════════════════════════════════════════════════════════════════════════════
# ACHIEVEMENT PROGRESS STATE (per girlfriend)
# ═══════════════════════════════════════════════════════════════════════════════

MAX_EVENT_HISTORY = 200  # Ring buffer size

@dataclass
class AchievementProgress:
    """Mutable progress state tracked per (session, girlfriend).
    Does NOT reset on region change (non-missable system).
    """
    region_index: int = 0

    # First-time flags (once set, never unset)
    first_time_flags: Dict[str, bool] = field(default_factory=dict)

    # Event history — ring buffer of recent detected events
    event_history: List[Dict[str, Any]] = field(default_factory=list)

    # Cooldown tracking: signal -> last timestamp
    last_signal_timestamps: Dict[str, float] = field(default_factory=dict)

    # Conflict repair arc state
    conflict_tension_at: float = 0.0      # timestamp of last detected tension
    conflict_apology_at: float = 0.0      # timestamp of last detected apology
    conflict_last_repair_at: float = 0.0  # timestamp of last completed repair (for cooldown)

    # Message counter (monotonically increases)
    message_counter: int = 0

    # Legacy compat fields (kept for backward compat with store serialization)
    last_interaction_date: str = ""
    streak_days_in_region: int = 0
    days_since_last_interaction: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_index": self.region_index,
            "first_time_flags": dict(self.first_time_flags),
            "event_history": list(self.event_history[-MAX_EVENT_HISTORY:]),
            "last_signal_timestamps": dict(self.last_signal_timestamps),
            "conflict_tension_at": self.conflict_tension_at,
            "conflict_apology_at": self.conflict_apology_at,
            "conflict_last_repair_at": self.conflict_last_repair_at,
            "message_counter": self.message_counter,
            "last_interaction_date": self.last_interaction_date,
            "streak_days_in_region": self.streak_days_in_region,
            "days_since_last_interaction": self.days_since_last_interaction,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AchievementProgress":
        return cls(
            region_index=d.get("region_index", 0),
            first_time_flags=dict(d.get("first_time_flags", {})),
            event_history=list(d.get("event_history", [])),
            last_signal_timestamps=dict(d.get("last_signal_timestamps", {})),
            conflict_tension_at=d.get("conflict_tension_at", 0.0),
            conflict_apology_at=d.get("conflict_apology_at", 0.0),
            conflict_last_repair_at=d.get("conflict_last_repair_at", 0.0),
            message_counter=d.get("message_counter", 0),
            last_interaction_date=d.get("last_interaction_date", ""),
            streak_days_in_region=d.get("streak_days_in_region", 0),
            days_since_last_interaction=d.get("days_since_last_interaction", 0.0),
        )


def reset_progress_for_region(progress: AchievementProgress, new_region_index: int) -> AchievementProgress:
    """Update region index. NON-MISSABLE: do NOT reset counters/flags/history."""
    progress.region_index = new_region_index
    return progress


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL DETECTION PATTERNS — robust phrase-based emotional detection
# ═══════════════════════════════════════════════════════════════════════════════

# Each detector returns: list of (phrase_matched, strength) tuples

_AFFECTION_PATTERNS = [
    # Strength 3 (strong)
    (re.compile(r"\b(i love you|love you so much|i'm in love with you|i adore you|you're everything to me)\b", re.I), 3),
    # Strength 2 (moderate)
    (re.compile(r"\b(i miss you|miss you|care about you|you mean a lot|you matter to me|i cherish|thinking of you|i like you)\b", re.I), 2),
    # Strength 1 (mild)
    (re.compile(r"\b(sweetheart|darling|honey|baby|cutie|sweet|beautiful|gorgeous|handsome|pretty)\b", re.I), 1),
]

_VULNERABILITY_PATTERNS = [
    (re.compile(r"\b(i['']?m scared|i['']?m afraid|i fear|i worry about|it hurts me|i feel broken|i['']?m vulnerable)\b", re.I), 3),
    (re.compile(r"\b(i['']?ve never told anyone|hard to say this|i need you|it hurts|i feel sad|i['']?m anxious|i['']?m insecure|scared to)\b", re.I), 2),
    (re.compile(r"\b(i feel|i felt|it['']?s hard|i struggle|i['']?m not sure|worried about|nervous about|i['']?m stressed)\b", re.I), 1),
]

_WE_LANGUAGE_PATTERNS = [
    (re.compile(r"\b(we should|we could|we['']?re|we['']?ll|we['']?ve|our future|our life|our relationship)\b", re.I), 3),
    (re.compile(r"\b(together we|between us|for us|about us|the two of us)\b", re.I), 2),
    (re.compile(r"\b(we |us |our |ours)\b", re.I), 1),
]

_GRATITUDE_PATTERNS = [
    (re.compile(r"\b(i['']?m so grateful|thank you for being|i appreciate everything|grateful for you)\b", re.I), 3),
    (re.compile(r"\b(i appreciate you|thankful for|means so much|i['']?m thankful|appreciate that)\b", re.I), 2),
    (re.compile(r"\b(thank you|thanks|appreciate it|i appreciate)\b", re.I), 1),
]

_APOLOGY_PATTERNS = [
    (re.compile(r"\b(i['']?m really sorry|i sincerely apologize|forgive me|i was wrong about that)\b", re.I), 3),
    (re.compile(r"\b(i['']?m sorry|i apologize|my fault|my mistake|i shouldn['']?t have)\b", re.I), 2),
    (re.compile(r"\b(sorry about|i regret|didn['']?t mean to)\b", re.I), 1),
]

_REASSURANCE_PATTERNS = [
    (re.compile(r"\b(i['']?ll always be here|you can count on me|i['']?m not going anywhere|i['']?ll never leave)\b", re.I), 3),
    (re.compile(r"\b(it['']?s okay|don['']?t worry|i understand|we['']?ll be fine|everything will be okay|i forgive you)\b", re.I), 2),
    (re.compile(r"\b(it['']?s alright|no worries|we['']?re good|i get it|that['']?s fine)\b", re.I), 1),
]

_COMMITMENT_PATTERNS = [
    (re.compile(r"\b(i['']?m yours|you['']?re mine|only you|i choose you|devoted to you|forever yours)\b", re.I), 3),
    (re.compile(r"\b(i want to be with you|i['']?m committed|exclusive|this is serious|only want you)\b", re.I), 2),
    (re.compile(r"\b(i['']?m here for you|not going anywhere|means a lot|important to me|you come first)\b", re.I), 1),
]

_FUTURE_TALK_PATTERNS = [
    (re.compile(r"\b(grow old together|spend my life|rest of our lives|marry|when we live together)\b", re.I), 3),
    (re.compile(r"\b(our future|next year we|someday we|plan together|when we['']?re older)\b", re.I), 2),
    (re.compile(r"\b(one day|in the future|someday|plans for|planning to|eventually we)\b", re.I), 1),
]

_HOME_LANGUAGE_PATTERNS = [
    (re.compile(r"\b(you['']?re my home|you are my home|home is where you are|home is you|you feel like home)\b", re.I), 3),
    (re.compile(r"\b(feel at home with you|belong with you|my safe place|where i belong)\b", re.I), 2),
    (re.compile(r"\b(feels like home|our home|come home to|sense of home)\b", re.I), 1),
]

_BOUNDARY_RESPECT_PATTERNS = [
    (re.compile(r"\b(i respect that|i understand your boundary|take your time|no pressure|whenever you['']?re ready)\b", re.I), 3),
    (re.compile(r"\b(i won['']?t push|your choice|up to you|i['']?ll wait|respect your space)\b", re.I), 2),
    (re.compile(r"\b(of course|that['']?s okay|i understand if|no rush)\b", re.I), 1),
]

# ── Special first-time flag detectors ────────────────────────────────────────

_CURIOSITY_PATTERNS = re.compile(
    r"\b(tell me about|what do you|how do you feel|what['']?s your|what makes you|do you like|what are your)\b", re.I
)
_TRUST_DECLARATION = re.compile(
    r"\b(i trust you|i really trust|trust you completely|trust you with|i feel safe with you)\b", re.I
)
_EMPATHY_SHOWN = re.compile(
    r"\b(i understand how you feel|that must be|i can imagine|that sounds hard|i['']?m here for you|i hear you)\b", re.I
)
_MISS_YOU = re.compile(
    r"\b(i miss you|miss you|missed you|i['']?ve been missing)\b", re.I
)
_THINKING_OF_YOU = re.compile(
    r"\b(thinking of you|thinking about you|can['']?t stop thinking|you['']?re on my mind|thought of you)\b", re.I
)
_ACCEPTANCE = re.compile(
    r"\b(i accept you|accept you as|love you anyway|flaws and all|imperfect and|that['']?s okay about you)\b", re.I
)
_VENTING = re.compile(
    r"\b(had a terrible day|such a bad day|i['']?m so frustrated|everything went wrong|i['']?m exhausted|so tired of)\b", re.I
)
_LABEL = re.compile(
    r"\b(my girlfriend|my boyfriend|my partner|we['']?re together|we['']?re a couple|in a relationship|my love)\b", re.I
)
_SHARED_VALUES = re.compile(
    r"\b(we both believe|we agree on|same values|we['']?re alike|think the same|believe the same)\b", re.I
)
_FLAW_ACCEPTANCE = re.compile(
    r"\b(i love you even|despite your|accept your|your flaws|imperfect|nobody['']?s perfect and)\b", re.I
)
_PRIORITIZATION = re.compile(
    r"\b(you come first|you['']?re my priority|nothing is more important|before anything else|you matter most)\b", re.I
)
_DEEP_EMPATHY = re.compile(
    r"\b(i know exactly|i feel what you|i sense that|without you saying|before you even)\b", re.I
)
_COMMITMENT_HINT = re.compile(
    r"\b(not just casual|more than friends|this means something|something real|this is different|serious about)\b", re.I
)

# ── Tension detection (for conflict repair arc) ─────────────────────────────
_TENSION_PATTERNS = re.compile(
    r"\b(you always|you never|i['']?m upset|that hurt|i['']?m angry|frustrated with you|disappointed in you|you don['']?t care|why don['']?t you|i can['']?t believe you)\b", re.I
)


# ═══════════════════════════════════════════════════════════════════════════════
# ANTI-FARM: cooldown configuration per signal type (hours)
# ═══════════════════════════════════════════════════════════════════════════════

SIGNAL_COOLDOWN_HOURS: Dict[str, float] = {
    "affection": 1.0,
    "vulnerability": 4.0,
    "we_language": 2.0,
    "gratitude": 2.0,
    "apology": 8.0,
    "reassurance": 2.0,
    "commitment": 4.0,
    "future_talk": 4.0,
    "home_language": 8.0,
    "boundary_respect": 4.0,
}


def _is_on_cooldown(progress: AchievementProgress, signal: str, now: float) -> bool:
    """Check if a signal type is still on cooldown."""
    last = progress.last_signal_timestamps.get(signal, 0.0)
    cooldown_hours = SIGNAL_COOLDOWN_HOURS.get(signal, 2.0)
    return (now - last) < cooldown_hours * 3600


def _record_signal(progress: AchievementProgress, signal: str, now: float) -> None:
    """Record that a signal was detected (update cooldown timestamp)."""
    progress.last_signal_timestamps[signal] = now


# ═══════════════════════════════════════════════════════════════════════════════
# DETECTION FUNCTIONS — return structured events
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_pattern_signal(
    text: str,
    patterns: list,
    signal_name: str,
    progress: AchievementProgress,
    now: float,
) -> Optional[DetectedEvent]:
    """Detect a signal from pattern list. Returns best match or None.
    Respects cooldown and dedup."""
    if _is_on_cooldown(progress, signal_name, now):
        return None

    best_strength = 0
    best_phrase = ""
    for pat, strength in patterns:
        m = pat.search(text)
        if m and strength > best_strength:
            best_strength = strength
            best_phrase = m.group(0)

    if best_strength == 0:
        return None

    phrase_hash = hash(best_phrase.lower().strip())

    # Dedup: check if the same phrase was recently detected
    recent_hashes = {
        e.get("phrase_hash", 0)
        for e in progress.event_history[-20:]
        if e.get("signal") == signal_name
    }
    if phrase_hash in recent_hashes:
        return None

    _record_signal(progress, signal_name, now)

    return DetectedEvent(
        signal=signal_name,
        strength=best_strength,
        timestamp=now,
        message_index=progress.message_counter,
        phrase_hash=phrase_hash,
    )


def _detect_first_flag(
    text: str,
    pattern: re.Pattern,
    flag_name: str,
    progress: AchievementProgress,
) -> bool:
    """Detect a first-time milestone flag. Returns True if newly set."""
    if progress.first_time_flags.get(flag_name):
        return False
    if pattern.search(text):
        progress.first_time_flags[flag_name] = True
        return True
    return False


def detect_signals(
    user_message: str,
    assistant_message: str,
    progress: AchievementProgress,
    recent_messages: List[str] | None = None,
    now: float | None = None,
) -> Set[TriggerType]:
    """Run all detectors on the latest messages and update progress state.
    Returns the set of trigger types that fired."""
    if now is None:
        now = time.time()

    triggered: Set[TriggerType] = set()
    combined = f"{user_message} {assistant_message}"
    progress.message_counter += 1

    # ── Pattern-based signal detection ────────────────────────────────────
    signal_map: list[tuple[list, str, TriggerType]] = [
        (_AFFECTION_PATTERNS, "affection", TriggerType.AFFECTION_SIGNAL),
        (_VULNERABILITY_PATTERNS, "vulnerability", TriggerType.VULNERABILITY_SIGNAL),
        (_WE_LANGUAGE_PATTERNS, "we_language", TriggerType.WE_LANGUAGE),
        (_GRATITUDE_PATTERNS, "gratitude", TriggerType.GRATITUDE),
        (_APOLOGY_PATTERNS, "apology", TriggerType.APOLOGY),
        (_REASSURANCE_PATTERNS, "reassurance", TriggerType.REASSURANCE),
        (_COMMITMENT_PATTERNS, "commitment", TriggerType.COMMITMENT),
        (_FUTURE_TALK_PATTERNS, "future_talk", TriggerType.FUTURE_TALK),
        (_HOME_LANGUAGE_PATTERNS, "home_language", TriggerType.HOME_LANGUAGE),
        (_BOUNDARY_RESPECT_PATTERNS, "boundary_respect", TriggerType.BOUNDARY_RESPECT),
    ]

    for patterns, signal_name, trigger_type in signal_map:
        evt = _detect_pattern_signal(combined, patterns, signal_name, progress, now)
        if evt:
            progress.event_history.append({
                "signal": evt.signal,
                "strength": evt.strength,
                "timestamp": evt.timestamp,
                "message_index": evt.message_index,
                "phrase_hash": evt.phrase_hash,
            })
            triggered.add(trigger_type)

    # Trim event history to max size
    if len(progress.event_history) > MAX_EVENT_HISTORY:
        progress.event_history = progress.event_history[-MAX_EVENT_HISTORY:]

    # ── First-time flag detection ─────────────────────────────────────────
    flag_detections: list[tuple[re.Pattern, str, TriggerType]] = [
        (_CURIOSITY_PATTERNS, "first_curiosity", TriggerType.MESSAGE_EVALUATED),
        (_TRUST_DECLARATION, "first_trust_declaration", TriggerType.VULNERABILITY_SIGNAL),
        (_EMPATHY_SHOWN, "first_empathy_shown", TriggerType.REASSURANCE),
        (_MISS_YOU, "first_miss_you", TriggerType.AFFECTION_SIGNAL),
        (_THINKING_OF_YOU, "first_thinking_of_you", TriggerType.AFFECTION_SIGNAL),
        (_ACCEPTANCE, "first_acceptance", TriggerType.MESSAGE_EVALUATED),
        (_VENTING, "first_user_venting", TriggerType.VULNERABILITY_SIGNAL),
        (_LABEL, "first_label", TriggerType.COMMITMENT),
        (_SHARED_VALUES, "first_shared_values", TriggerType.MESSAGE_EVALUATED),
        (_FLAW_ACCEPTANCE, "first_flaw_acceptance", TriggerType.MESSAGE_EVALUATED),
        (_PRIORITIZATION, "first_prioritization", TriggerType.COMMITMENT),
        (_DEEP_EMPATHY, "first_deep_empathy", TriggerType.MESSAGE_EVALUATED),
        (_COMMITMENT_HINT, "first_commitment_hint", TriggerType.COMMITMENT),
    ]

    for pat, flag, ttype in flag_detections:
        if _detect_first_flag(combined, pat, flag, progress):
            triggered.add(ttype)

    # Also set first-time flags from pattern signals
    signal_to_flag = {
        "affection": "first_affection",
        "vulnerability": "first_vulnerability",
        "gratitude": "first_gratitude",
        "apology": "first_apology",
        "reassurance": "first_reassurance",
        "we_language": "first_we_language",
        "commitment": "first_commitment",
        "future_talk": "first_future_talk",
        "home_language": "first_home_language",
        "boundary_respect": "first_boundary_respect",
    }
    for sig, flag in signal_to_flag.items():
        if any(e.get("signal") == sig for e in progress.event_history[-5:]):
            if not progress.first_time_flags.get(flag):
                progress.first_time_flags[flag] = True

    # Also detect compliment as part of affection first-flag
    _COMPLIMENT_RE = re.compile(
        r"\b(i like how you|you make me|i admire|you['']?re amazing|you['']?re beautiful|you['']?re incredible|proud of you)\b", re.I
    )
    if _detect_first_flag(assistant_message, _COMPLIMENT_RE, "first_compliment", progress):
        triggered.add(TriggerType.AFFECTION_SIGNAL)

    # ── Conflict repair arc detection ─────────────────────────────────────
    _detect_conflict_arc(combined, recent_messages, progress, now, triggered)

    # Always include MESSAGE_EVALUATED so general triggers fire
    triggered.add(TriggerType.MESSAGE_EVALUATED)

    return triggered


def _detect_conflict_arc(
    combined: str,
    recent_messages: List[str] | None,
    progress: AchievementProgress,
    now: float,
    triggered: Set[TriggerType],
) -> None:
    """Detect the conflict repair arc: tension → apology → reassurance.
    Must happen in order within a window. 7-day cooldown between repairs."""

    # Check if we're on repair cooldown
    if progress.conflict_last_repair_at > 0:
        days_since = (now - progress.conflict_last_repair_at) / 86400
        if days_since < 7:
            return

    recent_text = " ".join((recent_messages or [])[-10:]) + " " + combined

    # Step 1: Detect tension
    if _TENSION_PATTERNS.search(combined):
        progress.conflict_tension_at = now

    # Step 2: Detect apology (must come after tension)
    if progress.conflict_tension_at > 0:
        for pat, _ in _APOLOGY_PATTERNS:
            if pat.search(combined):
                if now - progress.conflict_tension_at < 86400:  # within 24h
                    progress.conflict_apology_at = now
                break

    # Step 3: Detect reassurance (must come after apology)
    if progress.conflict_apology_at > 0 and progress.conflict_apology_at > progress.conflict_tension_at:
        for pat, _ in _REASSURANCE_PATTERNS:
            if pat.search(combined):
                if now - progress.conflict_apology_at < 86400:  # within 24h
                    # Complete arc detected!
                    progress.conflict_last_repair_at = now
                    progress.conflict_tension_at = 0.0
                    progress.conflict_apology_at = 0.0
                    triggered.add(TriggerType.CONFLICT_REPAIR)

                    # Record as event
                    progress.event_history.append({
                        "signal": "conflict_repair",
                        "strength": 3,
                        "timestamp": now,
                        "message_index": progress.message_counter,
                        "phrase_hash": hash("conflict_repair_arc"),
                    })
                break


# ═══════════════════════════════════════════════════════════════════════════════
# REQUIREMENT EVALUATION
# ═══════════════════════════════════════════════════════════════════════════════

def evaluate_requirement(
    requirement: Dict[str, Any],
    progress: AchievementProgress,
    context: Dict[str, Any] | None = None,
) -> bool:
    """Evaluate a single achievement requirement spec against current progress."""
    req_type = requirement["type"]
    params = requirement.get("params", {})

    if req_type == "first_flag":
        flag = params.get("flag", "")
        return bool(progress.first_time_flags.get(flag))

    if req_type == "distinct_signals":
        return _eval_distinct_signals(params, progress)

    if req_type == "multi_signal":
        return _eval_multi_signal(params, progress)

    if req_type == "multi_signal_time_separated":
        return _eval_multi_signal_time_separated(params, progress)

    if req_type == "conflict_repair_arc":
        return _eval_conflict_repair(params, progress)

    # Legacy fallbacks for backward compatibility
    if req_type == "region_enter":
        return True
    if req_type == "first_gift_in_region":
        return False  # No gift achievements in new system

    logger.warning("Unknown requirement type: %s", req_type)
    return False


def _eval_distinct_signals(params: Dict[str, Any], progress: AchievementProgress) -> bool:
    """Require N distinct events of a signal type, separated by minimum gap.
    'Distinct' means different phrase_hash AND minimum message/time separation."""
    signal = params.get("signal", "")
    min_distinct = params.get("min_distinct", 1)
    min_gap_messages = params.get("min_gap_messages", 0)
    min_gap_hours = params.get("min_gap_hours", 0)

    events = [
        e for e in progress.event_history
        if e.get("signal") == signal
    ]

    if len(events) < min_distinct:
        return False

    # Count distinct events with required separation
    distinct_count = 0
    last_accepted_idx = -999
    last_accepted_time = 0.0
    seen_hashes: set = set()

    for e in events:
        msg_idx = e.get("message_index", 0)
        ts = e.get("timestamp", 0.0)
        ph = e.get("phrase_hash", 0)

        # Skip duplicate phrase hashes
        if ph in seen_hashes:
            continue

        # Check message gap
        if min_gap_messages > 0 and (msg_idx - last_accepted_idx) < min_gap_messages:
            continue

        # Check time gap
        if min_gap_hours > 0 and last_accepted_time > 0:
            hours_diff = (ts - last_accepted_time) / 3600
            if hours_diff < min_gap_hours:
                continue

        distinct_count += 1
        last_accepted_idx = msg_idx
        last_accepted_time = ts
        seen_hashes.add(ph)

        if distinct_count >= min_distinct:
            return True

    return False


def _eval_multi_signal(params: Dict[str, Any], progress: AchievementProgress) -> bool:
    """Require N distinct events from EACH of multiple signal types."""
    signals = params.get("signals", [])
    min_each = params.get("min_each", 1)
    min_gap_messages = params.get("min_gap_messages", 0)

    for sig in signals:
        sub_params = {
            "signal": sig,
            "min_distinct": min_each,
            "min_gap_messages": min_gap_messages,
        }
        if not _eval_distinct_signals(sub_params, progress):
            return False
    return True


def _eval_multi_signal_time_separated(params: Dict[str, Any], progress: AchievementProgress) -> bool:
    """Like multi_signal but each signal type must have time-separated events.
    Used for EPIC/LEGENDARY achievements."""
    signals = params.get("signals", [])
    min_each = params.get("min_each", 1)
    min_gap_hours = params.get("min_gap_hours", 24)

    for sig in signals:
        sub_params = {
            "signal": sig,
            "min_distinct": min_each,
            "min_gap_hours": min_gap_hours,
        }
        if not _eval_distinct_signals(sub_params, progress):
            return False
    return True


def _eval_conflict_repair(params: Dict[str, Any], progress: AchievementProgress) -> bool:
    """Check if a conflict repair arc has been completed."""
    min_cooldown_days = params.get("min_cooldown_days", 0)

    # Must have at least one completed repair
    if progress.conflict_last_repair_at <= 0:
        return False

    # Count total repair events in history
    repair_events = [
        e for e in progress.event_history
        if e.get("signal") == "conflict_repair"
    ]

    if not repair_events:
        return False

    # For higher-tier repair achievements, check distinct repairs with cooldown
    if min_cooldown_days > 0:
        distinct_repairs = 0
        last_repair_ts = 0.0
        for e in repair_events:
            ts = e.get("timestamp", 0.0)
            if last_repair_ts == 0.0 or (ts - last_repair_ts) / 86400 >= min_cooldown_days:
                distinct_repairs += 1
                last_repair_ts = ts
        return distinct_repairs >= 1

    return True


# ═══════════════════════════════════════════════════════════════════════════════
# REGION INDEX HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def get_current_region_index_for_girl(level: int) -> int:
    """Return 0-based region index from the girl's current level."""
    from app.services.relationship_milestones import get_region_index
    region = get_region_for_level(level)
    return get_region_index(region.key)


def can_attempt_unlock(achievement: Achievement, current_region_index: int) -> bool:
    """NON-MISSABLE: achievements from past and current regions can unlock.
    Only FUTURE region achievements are blocked."""
    return achievement.region_index <= current_region_index


# ═══════════════════════════════════════════════════════════════════════════════
# TRY UNLOCK
# ═══════════════════════════════════════════════════════════════════════════════

def try_unlock(
    state: dict,
    achievement_id: str,
    progress: AchievementProgress,
    context: Dict[str, Any] | None = None,
) -> tuple[dict, dict | None]:
    """Attempt to unlock an achievement.

    Enforces:
    1) Non-missable region rule (past + current OK, future blocked)
    2) Not already unlocked
    3) Requirement evaluation passes

    Returns (updated_state, event_payload | None).
    """
    from app.services.time_utils import now_iso

    achievement = ACHIEVEMENTS.get(achievement_id)
    if achievement is None:
        return state, None

    milestones = list(state.get("milestones_reached") or [])

    # Already unlocked?
    if achievement_id in milestones:
        return state, None

    # Current region from level
    level = state.get("level", 0)
    current_idx = get_current_region_index_for_girl(level)

    # NON-MISSABLE rule: past + current OK, future blocked
    if not can_attempt_unlock(achievement, current_idx):
        return state, None

    # Evaluate requirement
    if not evaluate_requirement(achievement.requirement, progress, context):
        return state, None

    # Unlock it
    milestones.append(achievement_id)
    updated = {**state, "milestones_reached": milestones}

    event_payload = {
        "id": achievement.id,
        "title": achievement.title,
        "subtitle": achievement.subtitle,
        "rarity": achievement.rarity.value,
        "region_index": achievement.region_index,
        "trigger_type": achievement.trigger.value,
        "is_secret": achievement.is_secret,
        "narrative_hook": achievement.narrative_hook,
        "unlocked_at": now_iso(),
    }

    logger.info("Achievement unlocked: %s (rarity=%s, region=%d)",
                achievement.id, achievement.rarity.value, achievement.region_index)
    return updated, event_payload


def try_unlock_for_triggers(
    state: dict,
    progress: AchievementProgress,
    triggers_fired: Set[TriggerType],
    context: Dict[str, Any] | None = None,
) -> tuple[dict, List[dict]]:
    """Attempt to unlock ALL eligible achievements (non-missable) that match
    any of the fired trigger types.

    Returns (updated_state, list_of_event_payloads).
    """
    level = state.get("level", 0)
    current_idx = get_current_region_index_for_girl(level)
    events: List[dict] = []

    # Get all eligible achievements (past + current regions)
    eligible = get_eligible_achievements(current_idx)

    for ach in eligible:
        # Check if this achievement's trigger is in the fired set,
        # or if MESSAGE_EVALUATED is in the set (matches everything)
        if ach.trigger in triggers_fired or TriggerType.MESSAGE_EVALUATED in triggers_fired:
            state, evt = try_unlock(state, ach.id, progress, context)
            if evt:
                events.append(evt)

    return state, events


# ═══════════════════════════════════════════════════════════════════════════════
# LEGACY COMPAT — functions that old code may call
# ═══════════════════════════════════════════════════════════════════════════════

def update_streak(progress: AchievementProgress, today_date: str) -> Set[TriggerType]:
    """Legacy: update streak tracking. Now a no-op that returns empty set
    since streaks are no longer achievement triggers."""
    if progress.last_interaction_date != today_date:
        progress.last_interaction_date = today_date
    return set()


def mark_gift_confirmed(progress: AchievementProgress) -> Set[TriggerType]:
    """Legacy: mark a gift as confirmed. No longer triggers achievements."""
    return set()


def add_memory_flag(progress: AchievementProgress, flag: str) -> Set[TriggerType]:
    """Legacy compat: add a memory flag. Maps to first_time_flags."""
    if not progress.first_time_flags.get(flag):
        progress.first_time_flags[flag] = True
        return {TriggerType.MESSAGE_EVALUATED}
    return set()
