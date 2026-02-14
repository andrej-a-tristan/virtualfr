"""
Bond Orchestrator — single call per turn, orchestrates the entire bond brain.

Replaces fragmented heuristics (memory, progression, identity, initiation,
disclosure) with one coherent pipeline called from chat.py.

Pipeline steps per turn:
  1. ingest_user_turn — extract memories, detect episodes, update patterns
  2. update_state — update disclosure, reciprocity, detect new capabilities
  3. plan_response_contract — memory retrieval, consistency guard, response direction
  4. build_enhanced_prompt — compose system prompt with all bond context
  5. validate_consistency — post-generation consistency check
  6. persist_outcomes — save all state changes, record fingerprints
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from app.services.bond_engine.memory_fabric import (
    MemoryBundle,
    ingest_user_turn,
    build_prompt_memory_bundle,
    record_used_memories,
    get_unresolved_emotional_threads,
    get_pending_promises,
)
from app.services.bond_engine.consistency_guard import (
    PersonaKernel,
    PersonaGrowthState,
    ConsistencyResult,
    build_persona_kernel,
    build_growth_state,
    validate_consistency,
    build_consistency_system_instructions,
)
from app.services.bond_engine.depth_planner import (
    build_capability_prompt_section,
    detect_new_capability_unlocks,
    persist_capability_unlock,
)
from app.services.bond_engine.disclosure_planner import (
    DisclosureState,
    load_disclosure_state,
    save_disclosure_state,
    advance_disclosure,
    update_reciprocity,
    build_disclosure_prompt_section,
)
from app.services.bond_engine.response_director import (
    ResponseContract,
    plan_response_contract,
    compute_style_fingerprint,
)
from app.services.bond_engine.initiation_planner import (
    InitiationMessage,
    plan_initiation,
)

logger = logging.getLogger(__name__)


# ── Turn Context (input to orchestrator) ─────────────────────────────────────

@dataclass
class TurnContext:
    """All context needed for a single turn."""
    # Identifiers
    session_id: str
    user_id: str | UUID | None
    girlfriend_id: str | UUID | None
    turn_id: str  # unique message ID for this turn

    # User message
    user_message: str

    # Girlfriend data
    girlfriend: dict = field(default_factory=dict)

    # Current state
    relationship_state: dict = field(default_factory=dict)
    level: int = 0

    # Message history context
    all_user_messages: list[str] = field(default_factory=list)
    all_user_timestamps: list[str] = field(default_factory=list)
    recent_assistant_turns: list[str] = field(default_factory=list)

    # Supabase admin client (None for in-memory mode)
    sb_admin: Any = None


# ── Turn Outcome (output from orchestrator) ──────────────────────────────────

@dataclass
class TurnOutcome:
    """Results of bond orchestration for a single turn."""
    # Memory bundle for prompt injection
    memory_bundle: MemoryBundle = field(default_factory=MemoryBundle)

    # Enhanced prompt sections to inject
    consistency_instructions: str = ""
    capability_instructions: str = ""
    disclosure_instructions: str = ""
    response_direction: str = ""
    memory_prompt_section: str = ""

    # Full bond context section (all of the above combined)
    bond_context_prompt: str = ""

    # Ingestion results
    ingestion_result: dict = field(default_factory=dict)

    # New capability unlocks detected
    new_capabilities: list[str] = field(default_factory=list)

    # Response contract for novelty
    response_contract: Optional[ResponseContract] = None

    # Persona models
    persona_kernel: Optional[PersonaKernel] = None
    persona_growth: Optional[PersonaGrowthState] = None

    # Disclosure state
    disclosure_state: Optional[DisclosureState] = None


# ── Initiation Outcome ───────────────────────────────────────────────────────

@dataclass
class InitiationOutcome:
    """Results of initiation planning."""
    should_initiate: bool = False
    message: Optional[InitiationMessage] = None
    reason_type: str = ""
    reason_context: str = ""


# ── Main Orchestrator ────────────────────────────────────────────────────────

def process_user_turn(ctx: TurnContext) -> TurnOutcome:
    """Process a single user turn through the full bond engine pipeline.
    
    Called from chat.py after user message is saved, before prompt building.
    
    Steps:
      1. Ingest user turn (extract memories, patterns, episodes)
      2. Update state (disclosure, reciprocity, capabilities)
      3. Build response contract (novelty, cadence)
      4. Retrieve scored memory bundle
      5. Build enhanced prompt sections
      6. Return TurnOutcome with all context for prompt building
    """
    outcome = TurnOutcome()
    sb = ctx.sb_admin
    uid = UUID(str(ctx.user_id)) if ctx.user_id else None
    gfid = UUID(str(ctx.girlfriend_id)) if ctx.girlfriend_id else None
    now = datetime.now(timezone.utc)

    # ── 1. INGEST USER TURN ──────────────────────────────────────────────
    if sb and uid and gfid:
        try:
            outcome.ingestion_result = ingest_user_turn(
                sb=sb,
                user_id=uid,
                girlfriend_id=gfid,
                turn_id=ctx.turn_id,
                text=ctx.user_message,
                all_user_timestamps=ctx.all_user_timestamps,
                all_user_messages=ctx.all_user_messages,
            )
        except Exception as e:
            logger.warning("Bond ingestion failed: %s", e)

    # ── 2. UPDATE STATE ──────────────────────────────────────────────────
    # 2a. Build persona models
    try:
        outcome.persona_kernel = build_persona_kernel(ctx.girlfriend)
        disclosure_level = 0
        if sb and uid and gfid:
            disc_state = load_disclosure_state(sb, uid, gfid)
            disclosure_level = disc_state.current_level
        else:
            disc_state = DisclosureState()
        outcome.persona_growth = build_growth_state(ctx.relationship_state, disclosure_level)
        outcome.disclosure_state = disc_state
    except Exception as e:
        logger.warning("Persona build failed: %s", e)
        outcome.persona_kernel = None
        outcome.persona_growth = None
        outcome.disclosure_state = DisclosureState()

    # 2b. Update disclosure reciprocity
    try:
        user_emotional = bool(outcome.ingestion_result.get("emotions_detected"))
        disc_state = outcome.disclosure_state or DisclosureState()
        disc_state = update_reciprocity(disc_state, user_emotional)

        # Try to advance disclosure
        trust = ctx.relationship_state.get("trust", 10)
        disc_state, did_advance = advance_disclosure(disc_state, trust, now)
        if did_advance:
            logger.info("Disclosure advanced to level %d", disc_state.current_level)

        outcome.disclosure_state = disc_state

        # Persist
        if sb and uid and gfid:
            save_disclosure_state(sb, uid, gfid, disc_state)
    except Exception as e:
        logger.debug("Disclosure update failed: %s", e)

    # 2c. Detect new capability unlocks
    try:
        prev_level = ctx.relationship_state.get("prev_level", ctx.level)
        new_caps = detect_new_capability_unlocks(prev_level, ctx.level)
        outcome.new_capabilities = [c.key for c in new_caps]
        if sb and uid and gfid:
            for cap in new_caps:
                persist_capability_unlock(sb, uid, gfid, cap.key, ctx.level)
                logger.info("Capability unlocked: %s at level %d", cap.key, ctx.level)
    except Exception as e:
        logger.debug("Capability detection failed: %s", e)

    # ── 3. BUILD RESPONSE CONTRACT ───────────────────────────────────────
    try:
        user_emotions = outcome.ingestion_result.get("emotions_detected", [])
        user_emotion = user_emotions[0] if user_emotions else None
        emotional_style = (ctx.girlfriend.get("traits") or {}).get("emotional_style", "Caring")

        outcome.response_contract = plan_response_contract(
            recent_assistant_turns=ctx.recent_assistant_turns,
            emotional_style=emotional_style,
            user_emotion=user_emotion,
            has_memory_to_callback=True,  # will be updated after memory retrieval
            message_count_in_topic=0,  # simplified for now
        )
    except Exception as e:
        logger.debug("Response contract planning failed: %s", e)

    # ── 4. RETRIEVE SCORED MEMORY BUNDLE ─────────────────────────────────
    if sb and uid and gfid:
        try:
            outcome.memory_bundle = build_prompt_memory_bundle(
                sb=sb,
                user_id=uid,
                girlfriend_id=gfid,
                current_message=ctx.user_message,
            )
        except Exception as e:
            logger.warning("Memory bundle retrieval failed: %s", e)

    # ── 5. BUILD ENHANCED PROMPT SECTIONS ────────────────────────────────
    sections: list[str] = []

    # 5a. Consistency instructions
    if outcome.persona_kernel and outcome.persona_growth:
        try:
            outcome.consistency_instructions = build_consistency_system_instructions(
                outcome.persona_kernel, outcome.persona_growth
            )
            sections.append(outcome.consistency_instructions)
        except Exception as e:
            logger.debug("Consistency instructions build failed: %s", e)

    # 5b. Capability instructions
    try:
        outcome.capability_instructions = build_capability_prompt_section(ctx.level)
        sections.append(outcome.capability_instructions)
    except Exception as e:
        logger.debug("Capability instructions build failed: %s", e)

    # 5c. Disclosure instructions
    if outcome.disclosure_state:
        try:
            trust = ctx.relationship_state.get("trust", 10)
            outcome.disclosure_instructions = build_disclosure_prompt_section(
                outcome.disclosure_state, trust
            )
            sections.append(outcome.disclosure_instructions)
        except Exception as e:
            logger.debug("Disclosure instructions build failed: %s", e)

    # 5d. Response direction
    if outcome.response_contract:
        try:
            outcome.response_direction = outcome.response_contract.to_prompt_section()
            sections.append(outcome.response_direction)
        except Exception as e:
            logger.debug("Response direction build failed: %s", e)

    # 5e. Enhanced memory section
    if outcome.memory_bundle.has_content():
        try:
            bundle_dict = outcome.memory_bundle.to_prompt_dict()
            mem_lines: list[str] = []
            mem_lines.append("WHAT YOU KNOW (weave in naturally, don't list):")

            if bundle_dict.get("facts"):
                mem_lines.append("  Known facts (stable, high-confidence):")
                for f in bundle_dict["facts"][:4]:
                    mem_lines.append(f"    - {f}")

            if bundle_dict.get("emotions"):
                mem_lines.append("  Emotional continuity (open threads):")
                for e in bundle_dict["emotions"][:3]:
                    mem_lines.append(f"    - {e}")

            if bundle_dict.get("episodes"):
                mem_lines.append("  Shared episodes (callbacks to relationship history):")
                for ep in bundle_dict["episodes"][:2]:
                    mem_lines.append(f"    - {ep}")

            if bundle_dict.get("patterns"):
                mem_lines.append("  Communication patterns:")
                for p in bundle_dict["patterns"][:2]:
                    mem_lines.append(f"    - {p}")

            mem_lines.append("  Rules: max 1-2 callbacks per message, prefer unresolved emotional threads")

            outcome.memory_prompt_section = "\n".join(mem_lines)
            sections.append(outcome.memory_prompt_section)
        except Exception as e:
            logger.debug("Memory prompt section build failed: %s", e)

    # Combine all sections
    outcome.bond_context_prompt = "\n\n".join(s for s in sections if s)

    return outcome


def validate_response(
    response_text: str,
    outcome: TurnOutcome,
) -> ConsistencyResult:
    """Validate a generated response for consistency.
    
    Called between generation and SSE streaming.
    Returns ConsistencyResult with violations and repair instructions.
    """
    if not outcome.persona_kernel or not outcome.persona_growth:
        return ConsistencyResult(is_valid=True)

    return validate_consistency(
        response_text=response_text,
        kernel=outcome.persona_kernel,
        growth=outcome.persona_growth,
        recent_assistant_turns=None,  # already checked in response_director
    )


def persist_turn_outcomes(
    ctx: TurnContext,
    outcome: TurnOutcome,
    response_text: str,
) -> None:
    """Persist all turn outcomes: fingerprints, used memories, etc.
    
    Called after response is fully streamed.
    """
    sb = ctx.sb_admin
    uid = UUID(str(ctx.user_id)) if ctx.user_id else None
    gfid = UUID(str(ctx.girlfriend_id)) if ctx.girlfriend_id else None

    if not sb or not uid or not gfid:
        return

    # Record which memories were used (for diversity tracking)
    try:
        memory_ids = []
        for item in (outcome.memory_bundle.facts_top +
                     outcome.memory_bundle.emotions_top +
                     outcome.memory_bundle.episodes_top):
            mid = item.get("id")
            if mid:
                memory_ids.append(str(mid))

        fingerprint = compute_style_fingerprint(response_text)
        if outcome.response_contract:
            fingerprint["cadence"] = outcome.response_contract.suggested_cadence
            fingerprint["pattern"] = outcome.response_contract.suggested_pattern
            fingerprint["topic_action"] = outcome.response_contract.topic_action

        record_used_memories(
            sb=sb,
            user_id=uid,
            girlfriend_id=gfid,
            turn_id=ctx.turn_id,
            memory_ids_used=memory_ids,
            fingerprint=fingerprint,
        )
    except Exception as e:
        logger.debug("Persist turn outcomes failed: %s", e)


# ── Initiation Planning ─────────────────────────────────────────────────────

def plan_proactive_initiation(
    *,
    sb_admin: Any,
    user_id: str | UUID | None,
    girlfriend_id: str | UUID | None,
    girlfriend: dict,
    relationship_state: dict,
    last_message_from_her: bool,
    hours_inactive: float,
    current_hour: int,
    active_hours: list[int] | None = None,
) -> InitiationOutcome:
    """Plan a proactive initiation message using the bond engine.
    
    Called from chat.py app_open endpoint.
    Replaces the old should_initiate_conversation + get_initiation_message.
    """
    result = InitiationOutcome()
    sb = sb_admin
    uid = UUID(str(user_id)) if user_id else None
    gfid = UUID(str(girlfriend_id)) if girlfriend_id else None

    traits = girlfriend.get("traits") or {}
    attachment_style = traits.get("attachment_style", "Calm but caring")
    attachment_intensity = {
        "Very attached": "high",
        "Emotionally present": "medium",
        "Calm but caring": "low",
    }.get(attachment_style, "low")

    # Gather context for event-conditioned initiation
    unresolved_threads: list[dict] = []
    pending_events: list[dict] = []

    if sb and uid and gfid:
        try:
            unresolved_threads = get_unresolved_emotional_threads(sb, uid, gfid)
        except Exception:
            pass
        try:
            pending_events = get_pending_promises(sb, uid, gfid)
        except Exception:
            pass

    gf_name = girlfriend.get("display_name") or girlfriend.get("name") or "Companion"

    msg = plan_initiation(
        relationship_state=relationship_state,
        attachment_intensity=attachment_intensity,
        last_message_from_her=last_message_from_her,
        hours_inactive=hours_inactive,
        current_hour=current_hour,
        active_hours=active_hours,
        unresolved_threads=unresolved_threads,
        pending_events=pending_events,
        user_id=str(user_id or ""),
        girlfriend_id=str(girlfriend_id or ""),
        girlfriend_name=gf_name,
    )

    if msg:
        result.should_initiate = True
        result.message = msg
        result.reason_type = msg.reason.reason_type
        result.reason_context = msg.reason.context

    return result
