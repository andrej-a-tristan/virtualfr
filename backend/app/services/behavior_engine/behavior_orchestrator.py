"""Behavior Orchestrator — unified pipeline for natural, non-robotic chat.

Single entry point for ALL chat endpoints. Combines:
  1. Bond Engine (memory, disclosure, capabilities)
  2. Intent Classifier + Dialogue Policy
  3. Dossier Retriever (self-knowledge)
  4. Response Contract (per-turn constraints)
  5. Validators (post-generation checks)

Returns a BehaviorTurnResult containing everything needed for prompt assembly
and post-generation validation.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

from app.services.behavior_engine.intent_classifier import TurnIntent, classify_turn_intent
from app.services.behavior_engine.response_contract import BehaviorContract, build_behavior_contract
from app.services.behavior_engine.validators import ValidationResult, run_all_validators
from app.services.dossier.retriever import DossierContext, build_dossier_context, get_conversation_mode_state
from app.services.dossier.self_memory import update_dossier_from_response, update_conversation_mode_state

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# INPUT / OUTPUT TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BehaviorTurnInput:
    """Everything needed for a behavior-aware turn."""
    session_id: str
    user_id: UUID | str | None
    girlfriend_id: UUID | str | None
    user_message: str
    girlfriend_data: dict                     # Full girlfriend dict (traits, identity, canon)
    relationship_level: int = 0
    recent_assistant_texts: list[str] = field(default_factory=list)  # Last 5-10 assistant messages
    sb_admin: Any = None                      # Supabase admin client

    # Optional: pre-computed bond engine result (if bond engine already ran)
    bond_context_prompt: str | None = None
    bond_memory_prompt: str | None = None


@dataclass
class BehaviorTurnResult:
    """Output of the behavior orchestrator — everything for prompt assembly."""
    # Core outputs
    intent: TurnIntent = field(default_factory=lambda: TurnIntent(
        primary="banter", confidence=0.3, has_question_about_her=False,
        has_user_disclosure=False, has_emotional_need=False))
    contract: BehaviorContract = field(default_factory=BehaviorContract)
    dossier: DossierContext = field(default_factory=DossierContext)

    # Prompt sections
    behavior_prompt: str = ""                 # Combined behavior instructions for LLM
    dossier_prompt: str = ""                  # Girl self-knowledge section
    turn_rules_prompt: str = ""               # Turn-specific rules

    # For post-generation
    conversation_mode: dict = field(default_factory=dict)
    canon_facts: dict = field(default_factory=dict)
    self_memory_facts: list[dict] = field(default_factory=list)

    def get_full_behavior_context(self) -> str:
        """Get the complete behavior context to inject into system prompt."""
        sections = []
        if self.dossier_prompt:
            sections.append(self.dossier_prompt)
        if self.turn_rules_prompt:
            sections.append(self.turn_rules_prompt)
        return "\n\n".join(sections)


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def process_behavior_turn(inp: BehaviorTurnInput) -> BehaviorTurnResult:
    """
    Main pipeline: process a user turn through the full behavior engine.
    
    Steps:
    1. Classify turn intent
    2. Fetch conversation mode state
    3. Build behavior contract (intent + anti-interview metrics)
    4. Fetch dossier context (self-knowledge for prompt)
    5. Assemble prompt sections
    6. Return BehaviorTurnResult
    """
    result = BehaviorTurnResult()
    sb = inp.sb_admin

    uid = _to_uuid(inp.user_id)
    gid = _to_uuid(inp.girlfriend_id)
    gf = inp.girlfriend_data or {}

    # ── Step 1: Classify intent ───────────────────────────────────────────
    result.intent = classify_turn_intent(inp.user_message)
    logger.debug("Intent: %s (conf=%.2f, q_about_her=%s)",
                 result.intent.primary, result.intent.confidence, result.intent.has_question_about_her)

    # ── Step 2: Fetch conversation mode state ─────────────────────────────
    conv_mode: dict = {}
    recent_fps: list[dict] = []
    if sb and uid and gid:
        conv_mode = get_conversation_mode_state(sb, uid, gid)
        # Fetch recent fingerprints for anti-repetition
        try:
            fp_result = sb.table("response_fingerprints").select("fingerprint").eq(
                "user_id", str(uid)
            ).eq("girlfriend_id", str(gid)).order(
                "created_at", desc=True
            ).limit(5).execute()
            recent_fps = [r["fingerprint"] for r in (fp_result.data or [])]
        except Exception:
            pass
    result.conversation_mode = conv_mode

    # ── Step 3: Build behavior contract ───────────────────────────────────
    result.contract = build_behavior_contract(
        intent=result.intent,
        conversation_mode=conv_mode,
        relationship_level=inp.relationship_level,
        recent_fingerprints=recent_fps,
    )

    # ── Step 4: Fetch dossier context ─────────────────────────────────────
    if sb and uid and gid:
        result.dossier = build_dossier_context(
            sb=sb,
            user_id=uid,
            girlfriend_id=gid,
            intent_topics=result.intent.detected_topics,
            relationship_level=inp.relationship_level,
            requires_self_answer=result.intent.requires_self_answer(),
        )
    else:
        # Fallback: build minimal dossier from girlfriend data
        result.dossier = _build_fallback_dossier(gf)

    # ── Step 5: Build canon facts for post-generation validation ──────────
    identity = gf.get("identity") or {}
    identity_canon = gf.get("identity_canon") or {}
    result.canon_facts = {
        "name": gf.get("display_name") or gf.get("name") or identity.get("name", ""),
        "origin": identity.get("origin_vibe", ""),
        "job": identity.get("job_vibe", ""),
    }
    # Store self-memory facts for post-validation
    if result.dossier.self_facts:
        result.self_memory_facts = [{"key": f.split(":")[0].strip(), "value": f} for f in result.dossier.self_facts]

    # ── Step 6: Assemble prompt sections ──────────────────────────────────
    result.dossier_prompt = result.dossier.to_prompt_section() if result.dossier.has_content() else ""
    result.turn_rules_prompt = result.contract.to_prompt_section()

    result.behavior_prompt = result.get_full_behavior_context()

    return result


def validate_behavior_response(
    response_text: str,
    result: BehaviorTurnResult,
    recent_responses: list[str] | None = None,
) -> ValidationResult:
    """
    Post-generation validation: run all validators on the LLM output.
    """
    return run_all_validators(
        response_text=response_text,
        user_asked_about_her=result.intent.requires_self_answer(),
        consecutive_question_count=result.conversation_mode.get("consecutive_questions", 0),
        question_ratio=result.conversation_mode.get("question_ratio_10", 0.0),
        self_memory_facts=result.self_memory_facts,
        canon_facts=result.canon_facts,
        recent_responses=recent_responses,
        blacklisted_openings=result.contract.blacklisted_openings,
        blacklisted_phrases=result.contract.blacklisted_phrases,
    )


def persist_behavior_turn(
    inp: BehaviorTurnInput,
    result: BehaviorTurnResult,
    response_text: str,
    turn_id: str,
) -> dict:
    """
    Post-generation persistence: update self-memory, conversation mode, etc.
    """
    sb = inp.sb_admin
    uid = _to_uuid(inp.user_id)
    gid = _to_uuid(inp.girlfriend_id)

    output = {"self_memory": {}, "mode_updated": False}

    if not sb or not uid or not gid:
        return output

    # 1. Extract self-claims from response and update self_memory
    self_mem_result = update_dossier_from_response(
        sb=sb, user_id=uid, girlfriend_id=gid,
        assistant_text=response_text, turn_id=turn_id,
    )
    output["self_memory"] = self_mem_result

    # 2. Update conversation mode state
    story_ids = [s["id"] for s in result.dossier.available_stories if "id" in s] if result.dossier.available_stories else []
    update_conversation_mode_state(
        sb=sb, user_id=uid, girlfriend_id=gid,
        assistant_text=response_text,
        intent_label=result.intent.primary,
        cadence_used=result.contract.cadence,
        story_ids_used=story_ids,
    )
    output["mode_updated"] = True

    return output


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _to_uuid(val: Any) -> UUID | None:
    if val is None:
        return None
    if isinstance(val, UUID):
        return val
    try:
        s = str(val)
        if len(s) == 36 and s.count("-") == 4:
            return UUID(s)
    except (ValueError, TypeError):
        pass
    return None


def _build_fallback_dossier(gf: dict) -> DossierContext:
    """Build minimal dossier from girlfriend dict when DB is unavailable."""
    ctx = DossierContext()
    identity = gf.get("identity") or {}
    identity_canon = gf.get("identity_canon") or {}
    traits = gf.get("traits") or {}

    # Voice style from communication style
    comm = traits.get("communication_style", "Soft")
    ctx.voice_style = {"Soft": "gentle", "Direct": "direct", "Teasing": "playful"}.get(comm, "warm")

    # Life facts from identity
    if identity.get("job_vibe"):
        ctx.life_facts.append(f"Works in: {identity['job_vibe']}")
    if identity.get("origin_vibe"):
        ctx.life_facts.append(f"Background: {identity['origin_vibe']}")
    for hobby in (identity.get("hobbies") or []):
        ctx.life_facts.append(f"Enjoys: {hobby}")

    # Self facts from canon
    if identity_canon.get("backstory"):
        ctx.self_facts.append(f"backstory: {identity_canon['backstory'][:200]}")
    if identity_canon.get("daily_routine"):
        ctx.self_facts.append(f"routine: {identity_canon['daily_routine'][:200]}")
    favorites = identity_canon.get("favorites") or {}
    for k, v in list(favorites.items())[:3]:
        ctx.self_facts.append(f"favorite {k}: {v}")

    return ctx
