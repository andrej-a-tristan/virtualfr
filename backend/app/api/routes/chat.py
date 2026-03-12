"""Chat: history, state, send (SSE), app_open (initiation + jealousy).

This version includes full memory and personality integration with mock LLM responses.
To enable real AI, set API_KEY in .env or connect to the /v1/chat/stream gateway.
"""
import uuid as uuid_mod
from uuid import UUID
from datetime import datetime, timezone
from collections import defaultdict
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
import logging

# ── Daily message cap for free-plan users ────────────────────────────────────
FREE_DAILY_MESSAGE_CAP = 20
_daily_msg_counts: dict[str, dict] = defaultdict(lambda: {"date": "", "count": 0})

from app.schemas.chat import (
    SendMessageRequest,
    AppOpenRequest,
    ChatMessage,
    RelationshipState as RelationshipStateSchema,
)
from app.api.store import (
    get_session_user,
    get_girlfriend,
    get_relationship_state,
    set_relationship_state,
    get_messages,
    append_message as store_append_message,
    get_habit_profile,
    set_habit_profile,
    get_relationship_progress,
    set_relationship_progress,
    get_intimacy_state,
    set_intimacy_state,
    get_trust_intimacy_state,
    set_trust_intimacy_state,
)
from app.api.request_context import get_current_user
from app.core.supabase_client import get_supabase_admin
from app.api import supabase_store as sb
from app.utils.sse import sse_event
from app.services.relationship_state import (
    create_initial_relationship_state,
    register_interaction,
    apply_inactivity_decay,
    get_jealousy_reaction,
    check_for_milestone_event,
    append_milestone_reached,
)
from app.services.relationship_regions import get_region_for_level, clamp_level, REGIONS
from app.services.intimacy_service import award_region_milestone
from app.services.trust_intimacy_service import (
    apply_conversation_trust_gain,
    award_intimacy_region,
    award_trust_gift,
    award_intimacy_gift,
    apply_trust_decay,
    release_banked,
    get_trust_cap_for_region,
    get_intimacy_cap_for_region,
)
from app.services.relationship_descriptors import get_descriptors, get_gain_micro_lines, build_narrative_hooks
from app.services.relationship_milestones import get_region_index
from app.services.trust_intimacy_service import compute_quality_score
from app.services.achievement_engine import (
    AchievementProgress,
    detect_signals,
    update_streak,
    reset_progress_for_region,
    try_unlock_for_triggers,
    get_current_region_index_for_girl,
    TriggerType,
)
from app.api.store import get_achievement_progress, set_achievement_progress
from app.services.image_decision_engine import (
    decide_image_action,
    request_is_sensitive,
    should_send_blurred_surprise,
    _pick_blurred_url,
    FREE_PLAN_BLURRED_INTIMACY,
)
from app.services.relationship_progression import (
    award_progress,
    derive_trust,
    derive_intimacy,
    RelationshipProgressState,
)
from app.services.initiation_engine import should_initiate_conversation, get_initiation_message
from app.services.habits import build_habit_profile
from app.services.big_five import map_traits_to_big_five, big_five_to_description
from app.services.time_utils import hours_since, now_iso
from app.services.memory import build_memory_context, write_memories_from_message
from app.services.prompt_builder import build_system_prompt, build_input_from_dict
from app.services.prompt_context import get_prompt_context

# ── Bond Engine: unified orchestration layer ────────────────────────────────
from app.services.bond_engine.bond_orchestrator import (
    TurnContext,
    TurnOutcome,
    process_user_turn as bond_process_turn,
    validate_response as bond_validate_response,
    persist_turn_outcomes as bond_persist_outcomes,
    plan_proactive_initiation,
)

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

# Attachment style -> intensity for engine
ATTACHMENT_INTENSITY = {"Very attached": "high", "Emotionally present": "medium", "Calm but caring": "low"}
# Reaction to absence -> jealousy level
JEALOUSY_LEVEL = {"High": "high", "Medium": "medium", "Low": "low"}


def _compute_generation_controls(
    user_text: str,
    intent: str | None,
    persona_vector: dict | None = None,
) -> tuple[int, float]:
    """Compute max_tokens/temperature for concise, natural replies."""
    text = (user_text or "").strip()
    wc = len(text.split())
    intent_key = (intent or "").strip().lower()

    max_tokens = 170
    temperature = 0.74

    if intent_key in ("greeting", "banter"):
        max_tokens = 90 if wc <= 8 else 120
        temperature = 0.78
    elif intent_key in ("ask_about_her", "mixed"):
        max_tokens = 160
        temperature = 0.72
    elif intent_key == "support":
        max_tokens = 220
        temperature = 0.7
    elif intent_key == "intimate":
        max_tokens = 190
        temperature = 0.76

    if wc <= 4:
        max_tokens = min(max_tokens, 80)
    elif wc <= 8:
        max_tokens = min(max_tokens, 110)

    pacing = (persona_vector or {}).get("pacing", {})
    brevity_bias = float(pacing.get("brevity_bias", 0.55))
    if brevity_bias >= 0.7:
        max_tokens = int(max_tokens * 0.82)
    elif brevity_bias <= 0.3:
        max_tokens = int(max_tokens * 1.08)

    return max_tokens, temperature


def _build_concise_style_guardrail(user_text: str, intent: str | None) -> str:
    wc = len((user_text or "").split())
    intent_key = (intent or "").strip().lower()
    if wc <= 8 or intent_key in ("greeting", "banter"):
        return (
            "RESPONSE LENGTH POLICY:\n"
            "- Keep this reply to one sentence, max 20 words.\n"
            "- No long paragraph and no list formatting."
        )
    if intent_key == "support":
        return (
            "RESPONSE LENGTH POLICY:\n"
            "- Keep this supportive reply concise: 2-4 sentences.\n"
            "- Avoid rambling; cap around 90 words unless user asks for depth."
        )
    return (
        "RESPONSE LENGTH POLICY:\n"
        "- Keep this reply concise: 1-3 sentences, usually under 60 words.\n"
        "- Avoid monologues unless user explicitly asks for a long answer."
    )


def _state_to_schema(state: dict) -> RelationshipStateSchema:
    level = clamp_level(state.get("level", 0) if isinstance(state.get("level"), int) else 0)
    region = get_region_for_level(level)
    from app.services.relationship_milestones import get_region_index
    return RelationshipStateSchema(
        trust=state["trust"],
        intimacy=state["intimacy"],
        level=level,
        region_key=region.key,
        region_title=region.title,
        region_min_level=region.min_level,
        region_max_level=region.max_level,
        last_interaction_at=state.get("last_interaction_at"),
        milestones_reached=state.get("milestones_reached", []),
        current_region_index=get_region_index(region.key),
    )


def _progress_to_schema(prog: RelationshipProgressState, ti_state=None, milestones: list[str] | None = None) -> RelationshipStateSchema:
    """Build API schema from progression engine + unified trust/intimacy state."""
    level = clamp_level(prog.level)
    region = get_region_for_level(level)
    from app.services.relationship_milestones import get_region_index
    # Prefer unified trust/intimacy state if available, else derive from level
    if ti_state:
        trust = ti_state.trust
        intimacy = ti_state.intimacy
    else:
        trust = derive_trust(level)
        intimacy = derive_intimacy(level)
    schema = RelationshipStateSchema(
        trust=trust,
        intimacy=intimacy,
        level=level,
        region_key=region.key,
        region_title=region.title,
        region_min_level=region.min_level,
        region_max_level=region.max_level,
        last_interaction_at=prog.last_interaction_at.isoformat() if prog.last_interaction_at else None,
        milestones_reached=milestones or [],
        current_region_index=get_region_index(region.key),
    )
    # Add bank/cap fields when unified state is available
    if ti_state:
        schema.trust_visible = ti_state.trust_visible
        schema.trust_bank = ti_state.trust_bank
        schema.trust_cap = get_trust_cap_for_region(region.key)
        schema.intimacy_visible = ti_state.intimacy_visible
        schema.intimacy_bank = ti_state.intimacy_bank
        schema.intimacy_cap = get_intimacy_cap_for_region(region.key)
    return schema


def _msg_to_schema(m: dict) -> ChatMessage:
    return ChatMessage(
        id=m["id"],
        role=m["role"],
        content=m.get("content"),
        image_url=m.get("image_url"),
        event_type=m.get("event_type"),
        event_key=m.get("event_key"),
        created_at=m["created_at"],
    )


def _use_supabase(user_id) -> bool:
    """Check if we should use Supabase (admin client available and user_id is UUID)."""
    if not get_supabase_admin() or not user_id:
        return False
    try:
        UUID(str(user_id))
        return True
    except (ValueError, TypeError):
        return False


@router.get("/history")
def chat_history(request: Request, girlfriend_id: str | None = None):
    sid, user, user_id, gf_id = get_current_user(request)
    if not sid or not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    # Use explicit girlfriend_id from query param, fall back to session's current
    resolved_gf_id = girlfriend_id or gf_id
    use_sb = _use_supabase(user_id)
    if use_sb and user_id:
        gf = sb.get_current_girlfriend(user_id, resolved_gf_id)
        if gf:
            messages = sb.get_messages(user_id, UUID(str(gf["id"])))
        else:
            messages = []
    else:
        # Pass explicit girlfriend_id so messages are per-girl
        messages = get_messages(sid, resolved_gf_id)
    return {"messages": [_msg_to_schema(m) for m in messages]}


@router.get("/state")
def chat_state(request: Request, girlfriend_id: str | None = None):
    sid, user, user_id, gf_id = get_current_user(request)
    if not sid or not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    # Use explicit girlfriend_id from query param, fall back to session's current
    resolved_gf_id = girlfriend_id or gf_id
    use_sb = _use_supabase(user_id)
    if use_sb and user_id:
        # Supabase path: still uses the old relationship_state dict
        gf = sb.get_current_girlfriend(user_id, resolved_gf_id)
        if gf:
            gf_uuid = UUID(str(gf["id"]))
            state = sb.get_relationship_state(user_id, gf_uuid)
            if not state:
                state = create_initial_relationship_state()
                sb.upsert_relationship_state(user_id, gf_uuid, state)
        else:
            state = create_initial_relationship_state()
        return _state_to_schema(state)
    else:
        # In-memory path: use the progression engine + unified trust/intimacy
        prog = get_relationship_progress(sid, resolved_gf_id)
        ti_state = get_trust_intimacy_state(sid, resolved_gf_id)
        rs = get_relationship_state(sid, girlfriend_id=resolved_gf_id) or {}
        return _progress_to_schema(prog, ti_state=ti_state, milestones=rs.get("milestones_reached", []))


def _affection_heuristic(text: str) -> bool:
    t = (text or "").lower()
    return any(x in t for x in ["miss", "love", "❤", "heart", "hug", "care"])


def _emotional_disclosure_heuristic(text: str) -> bool:
    t = (text or "").lower()
    return any(x in t for x in ["feel", "felt", "worried", "sad", "happy", "excited", "nervous"])


def _generate_mock_response(system_prompt: str, traits: dict, relationship_state: dict, memory_context, last_user_message: str) -> str:
    """Generate a personality-aware mock response using the system prompt context.
    
    Uses trust/intimacy descriptors to modulate tone and language.
    When a real LLM is connected, the system_prompt is sent as the system message.
    """
    trust = relationship_state.get("trust", 20) if relationship_state else 20
    intimacy = relationship_state.get("intimacy", 1) if relationship_state else 1

    # Get descriptors for current trust/intimacy
    descs = get_descriptors(trust, intimacy)
    tone = descs.trust.tone_rules

    # Get personality traits
    emotional_style = traits.get("emotional_style", "Caring")

    # Base responses modulated by trust level
    if trust < 25:
        base_responses = [
            "Hey. How are you doing?",
            "Oh, hi. What's up?",
            "That's interesting.",
        ]
    elif trust < 45:
        base_responses = [
            "That's so sweet of you to say! I appreciate it.",
            "I've been thinking about things... Tell me about your day.",
            "I really enjoy talking to you!",
        ]
    elif trust < 65:
        base_responses = [
            "I'm so glad you're here. I was hoping you'd message!",
            "You always know how to make me feel better.",
            "I feel like I can really be myself around you.",
        ]
    elif trust < 85:
        base_responses = [
            "I missed you so much. You mean everything to me.",
            "I feel so safe when we talk. Can I tell you something?",
            "You're the one person I trust with everything.",
        ]
    else:
        base_responses = [
            "I love you. I can't imagine my life without you.",
            "You know me better than anyone. I'm completely yours.",
            "Every moment with you feels perfect.",
        ]

    # Emotional style modifier
    style_modifiers = {
        "Playful": " 😊",
        "Caring": " 💕",
        "Reserved": "",
        "Protective": " 💪",
    }
    suffix = style_modifiers.get(emotional_style, "")

    # Add emoji based on tone rules
    if tone.emoji_rate >= 2 and not suffix:
        suffix = " ❤️"

    # Add memory context if available
    prefix = ""
    if memory_context and hasattr(memory_context, 'facts') and memory_context.facts:
        if any("name" in f.lower() for f in memory_context.facts):
            prefix = "I remember you telling me about yourself. "

    # Deterministic selection
    import random
    random.seed(hash(last_user_message))
    response = random.choice(base_responses)

    # Use descriptor openers at higher trust
    if trust >= 40 and descs.trust.openers:
        opener = random.choice(descs.trust.openers)
        if opener not in response:
            response = f"{opener} {response}"

    return prefix + response + suffix


def _stream_response_and_save(
    sid,
    user_id,
    gf_id,
    milestone_message,
    messages_for_context,
    gf_display_name,
    traits,
    relationship_state=None,
    habit_profile=None,
    memory_context=None,
    girlfriend_id=None,
    image_decision_event=None,
    blurred_surprise_event=None,
    relationship_gain_events=None,
    achievement_events=None,
    intimacy_unlock_events=None,
    intimacy_photo_events=None,
    system_prompt=None,
    bond_outcome=None,
    bond_turn_ctx=None,
    behavior_result=None,
    max_tokens: int = 170,
    temperature: float = 0.74,
):
    """Stream response and save assistant message. Yields SSE events.
    
    Main-branch behavior: use the personality-aware mock response generator only.
    The real LLM integration (Runpod or OpenAI) is handled via the /v1/chat/stream
    gateway in app.routers.chat, not from this endpoint.
    """
    # Get the last user message for context
    last_user_msg = ""
    for m in reversed(messages_for_context):
        if m.get("role") == "user" and m.get("content"):
            last_user_msg = m["content"]
            break

    response_text = ""

    # Main branch: always use the mock, personality-aware response generator.
    # All real LLM calls (Runpod, OpenAI, etc.) are confined to the chat gateway.
    response_text = _generate_mock_response(
        system_prompt or "",
        traits,
        relationship_state,
        memory_context,
        last_user_msg,
    )

    # ── Hard quality enforcement before token emission ────────────────────
    validation = None
    _beh_res = behavior_result
    try:
        from app.services.behavior_engine.behavior_orchestrator import (
            BehaviorTurnResult,
            validate_behavior_response,
        )
        if _beh_res is None:
            _beh_res = BehaviorTurnResult()
        validation = validate_behavior_response(
            response_text,
            _beh_res,
            recent_responses=[
                m.get("content", "") for m in (messages_for_context or [])[-6:]
                if m.get("role") == "assistant" and m.get("content")
            ],
        )
    except Exception as e:
        logger.debug("Behavior validation unavailable: %s", e)

    try:
        from app.services.behavior_engine.repair import apply_contract_hard_limits
        fallback_fact = None
        if _beh_res is not None and getattr(_beh_res, "dossier", None) and getattr(_beh_res.dossier, "self_facts", None):
            fallback_fact = str(_beh_res.dossier.self_facts[0]).split(":", 1)[-1].strip()
        user_asked_about_her = False
        if _beh_res is not None and getattr(_beh_res, "intent", None):
            user_asked_about_her = bool(_beh_res.intent.requires_self_answer())
        contract = _beh_res.contract if _beh_res is not None else None
        response_text = apply_contract_hard_limits(
            response_text,
            contract,
            user_asked_about_her=user_asked_about_her,
            fallback_self_fact=fallback_fact,
        )
    except Exception as e:
        logger.warning("Hard response repair failed: %s", e)

    for t in response_text.split():
        yield sse_event({"type": "token", "token": t + " "})
    
    # Send milestone message if any
    if milestone_message:
        milestone_msg = {
            "id": str(uuid_mod.uuid4()),
            "role": "assistant",
            "content": milestone_message,
            "image_url": None,
            "event_type": "milestone",
            "event_key": "milestone",
            "created_at": now_iso(),
        }
        if user_id and gf_id:
            sb.append_message(user_id, gf_id, milestone_msg)
        else:
            store_append_message(sid, milestone_msg, girlfriend_id=girlfriend_id)
        yield sse_event({"type": "message", "message": milestone_msg})
    
    # Save and send the response message
    msg = {
        "id": str(uuid_mod.uuid4()),
        "role": "assistant",
        "content": response_text,
        "image_url": None,
        "event_type": None,
        "event_key": None,
        "created_at": now_iso(),
    }
    if user_id and gf_id:
        sb.append_message(user_id, gf_id, msg)
    else:
        store_append_message(sid, msg, girlfriend_id=girlfriend_id)
    yield sse_event({"type": "message", "message": msg})

    # Emit image decision event if sensitive content was detected
    if image_decision_event:
        decision_msg = {
            "id": str(uuid_mod.uuid4()),
            "role": "assistant",
            "content": image_decision_event.get("ui_copy", ""),
            "image_url": None,
            "event_type": "image_decision",
            "event_key": image_decision_event.get("reason", ""),
            "created_at": now_iso(),
        }
        if user_id and gf_id:
            sb.append_message(user_id, gf_id, decision_msg)
        else:
            store_append_message(sid, decision_msg, girlfriend_id=girlfriend_id)
        yield sse_event({
            "type": "image_decision",
            "message": decision_msg,
            "decision": image_decision_event,
        })

    # Emit relationship gain events (trust/intimacy changes)
    if relationship_gain_events:
        for gain_evt in relationship_gain_events:
            # Persist as a chat message so gains survive refresh, including full gain payload
            gain_msg = {
                "id": str(uuid_mod.uuid4()),
                "role": "assistant",
                "content": "",
                "image_url": None,
                "event_type": "relationship_gain",
                "event_key": gain_evt.get("reason", "conversation"),
                "created_at": now_iso(),
                "gain_data": gain_evt,
            }
            if user_id and gf_id:
                sb.append_message(user_id, gf_id, gain_msg)
            else:
                store_append_message(sid, gain_msg, girlfriend_id=girlfriend_id)

            yield sse_event({
                "type": "relationship_gain",
                "gain": gain_evt,
            })

    # Emit achievement unlock events
    if achievement_events:
        for ach_evt in achievement_events:
            # Persist as a chat message card with full achievement payload
            ach_msg = {
                "id": str(uuid_mod.uuid4()),
                "role": "assistant",
                "content": "",
                "image_url": None,
                "event_type": "relationship_achievement",
                "event_key": ach_evt.get("id", ""),
                "created_at": now_iso(),
                "achievement": ach_evt,
            }
            if user_id and gf_id:
                sb.append_message(user_id, gf_id, ach_msg)
            else:
                store_append_message(sid, ach_msg, girlfriend_id=girlfriend_id)

            yield sse_event({
                "type": "relationship_achievement",
                "achievement": ach_evt,
            })

    # Emit intimacy achievement unlock events
    if intimacy_unlock_events:
        for iu_evt in intimacy_unlock_events:
            # Persist as a simple assistant bubble describing the unlock, including achievement payload
            ia_msg = {
                "id": str(uuid_mod.uuid4()),
                "role": "assistant",
                "content": f"{iu_evt.get('icon', '🔥')} **{iu_evt.get('title', 'Achievement')}** unlocked — {iu_evt.get('subtitle', '')}",
                "image_url": None,
                "event_type": "intimacy_achievement",
                "event_key": iu_evt.get("id", ""),
                "created_at": now_iso(),
                "achievement": iu_evt,
            }
            if user_id and gf_id:
                sb.append_message(user_id, gf_id, ia_msg)
            else:
                store_append_message(sid, ia_msg, girlfriend_id=girlfriend_id)

            yield sse_event({
                "type": "intimacy_achievement",
                "achievement": iu_evt,
            })

    # Emit intimacy photo ready events
    if intimacy_photo_events:
        for ip_evt in intimacy_photo_events:
            # Also append as a chat message with image and structured photo payload
            photo_msg = {
                "id": str(uuid_mod.uuid4()),
                "role": "assistant",
                "content": f"{ip_evt.get('icon', '🔥')} *{ip_evt.get('title', 'Achievement')}* — unlocked",
                "image_url": ip_evt.get("image_url"),
                "event_type": "intimacy_photo_ready",
                "event_key": ip_evt.get("id", ""),
                "created_at": now_iso(),
                "photo": ip_evt,
            }
            if user_id and gf_id:
                sb.append_message(user_id, gf_id, photo_msg)
            else:
                store_append_message(sid, photo_msg, girlfriend_id=girlfriend_id)
            yield sse_event({
                "type": "intimacy_photo_ready",
                "photo": ip_evt,
                "message": photo_msg,
            })

    # Emit blurred surprise (proactive, when free user crosses intimacy threshold)
    if blurred_surprise_event:
        yield sse_event({
            "type": "blurred_preview",
            "message": blurred_surprise_event,
        })

    # ── Bond Engine: persist turn outcomes (fingerprints, used memories) ──
    if bond_outcome and bond_turn_ctx and response_text:
        try:
            bond_persist_outcomes(bond_turn_ctx, bond_outcome, response_text)
        except Exception as e:
            logger.debug("Bond outcome persistence failed: %s", e)

    # ── Behavior Engine: persist self-memory + conversation mode ─────────
    if response_text and girlfriend_id:
        try:
            from app.services.behavior_engine.behavior_orchestrator import (
                BehaviorTurnInput, BehaviorTurnResult, persist_behavior_turn, validate_behavior_response,
            )
            from app.core.supabase_client import get_supabase_admin as _get_sb
            sb_persist = _get_sb()
            if sb_persist:
                _beh_inp = BehaviorTurnInput(
                    session_id=sid or "",
                    user_id=user_id,
                    girlfriend_id=girlfriend_id,
                    user_message="",
                    girlfriend_data={},
                    sb_admin=sb_persist,
                )
                _beh_result = behavior_result if behavior_result is not None else BehaviorTurnResult()
                validation = validate_behavior_response(
                    response_text,
                    _beh_result,
                    recent_responses=[
                        m.get("content", "") for m in (messages_for_context or [])[-6:]
                        if m.get("role") == "assistant" and m.get("content")
                    ],
                )
                persist_behavior_turn(_beh_inp, _beh_result, response_text, str(uuid_mod.uuid4()))
                if validation and validation.issues:
                    issue_keys = [f"{i.validator}:{i.severity}" for i in validation.issues[:5]]
                    sb_persist.table("conversation_mode_state").update({
                        "last_quality_issues": issue_keys,
                    }).eq("user_id", str(user_id)).eq("girlfriend_id", str(gf_id)).execute()
        except Exception as e:
            logger.debug("Behavior persistence failed: %s", e)

    # ── Bond Engine: emit new capability unlock events ───────────────────
    if bond_outcome and bond_outcome.new_capabilities:
        for cap_key in bond_outcome.new_capabilities:
            yield sse_event({
                "type": "capability_unlocked",
                "capability": cap_key,
            })

    yield sse_event({"type": "done"})


@router.post("/send")
def send_message(request: Request, body: SendMessageRequest):
    sid, user, user_id, gf_id = get_current_user(request)
    if not sid or not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    # ── Free-plan daily message cap ──────────────────────────────────────
    user_plan = (user or {}).get("plan", "free")
    if user_plan == "free":
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tracker = _daily_msg_counts[sid]
        if tracker["date"] != today_str:
            tracker["date"] = today_str
            tracker["count"] = 0
        if tracker["count"] >= FREE_DAILY_MESSAGE_CAP:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "daily_limit_reached",
                    "message": f"You've used all {FREE_DAILY_MESSAGE_CAP} free messages today. Upgrade to Plus for unlimited messaging!",
                    "messages_sent": tracker["count"],
                    "message_cap": FREE_DAILY_MESSAGE_CAP,
                },
            )
        tracker["count"] += 1

    # Resolve the girlfriend_id from the request body (preferred) or session's current
    explicit_gf_id = body.girlfriend_id or gf_id or None

    use_sb = get_supabase_admin() and user_id is not None
    if use_sb and user_id:
        gf = sb.get_current_girlfriend(user_id, explicit_gf_id)
        if gf:
            gf_uuid = UUID(str(gf["id"]))
            if not gf_id or str(gf_id) != str(gf["id"]):
                from app.api.store import set_session_girlfriend_id
                set_session_girlfriend_id(sid, str(gf["id"]))
        else:
            gf_uuid = None
    else:
        # Use explicit girlfriend_id if provided, otherwise fall back to current
        if explicit_gf_id:
            from app.api.store import get_girlfriend_by_id
            gf = get_girlfriend_by_id(sid, explicit_gf_id)
        else:
            gf = get_girlfriend(sid)
        gf_uuid = None
    if not gf:
        return JSONResponse(status_code=400, content={"error": "no_girlfriend"})

    # Persona vector (stored active vector → deterministic fallback).
    persona_vector = None
    try:
        if use_sb and user_id and gf_uuid:
            from app.services.persona_vector_store import get_active_persona_vector
            pv_row = get_active_persona_vector(
                get_supabase_admin(),
                user_id,
                gf_uuid,
                version_hint=gf.get("persona_vector_version"),
            )
            if pv_row and pv_row.get("vector_json"):
                persona_vector = pv_row["vector_json"]
        if not persona_vector:
            from app.services.persona_vector import build_persona_vector
            persona_vector = build_persona_vector(gf.get("traits") or {})
        gf["persona_vector"] = persona_vector
    except Exception:
        persona_vector = None

    # Use the resolved girlfriend's id for all per-girl storage
    resolved_gf_id = explicit_gf_id or gf.get("id")

    # Save user message
    user_msg = {
        "id": str(uuid_mod.uuid4()),
        "role": "user",
        "content": body.message,
        "image_url": None,
        "event_type": None,
        "event_key": None,
        "created_at": now_iso(),
    }
    if use_sb and user_id and gf_uuid:
        sb.append_message(user_id, gf_uuid, user_msg)
        messages = sb.get_messages(user_id, gf_uuid)
    else:
        store_append_message(sid, user_msg, girlfriend_id=resolved_gf_id)
        messages = get_messages(sid, girlfriend_id=resolved_gf_id)
    
    # Build habit profile
    user_timestamps = [m["created_at"] for m in messages if m["role"] == "user"]
    habit = build_habit_profile(user_timestamps)
    
    # Compute and store Big Five scores from girlfriend traits
    traits_dict = gf.get("traits") or {}
    if traits_dict and isinstance(traits_dict, dict):
        big_five_scores = map_traits_to_big_five(traits_dict)
        habit["big_five"] = big_five_scores
    if use_sb and user_id and gf_uuid:
        sb.upsert_habit_profile(user_id, gf_uuid, habit)
    else:
        set_habit_profile(sid, habit, girlfriend_id=resolved_gf_id)

    # ── Progression engine (in-memory path) ────────────────────────────────
    from datetime import datetime as dt_cls, timezone as tz
    progression_now = dt_cls.now(tz.utc)

    if not (use_sb and user_id and gf_uuid):
        # In-memory: drive relationship via the progression engine
        prog = get_relationship_progress(sid, girlfriend_id=resolved_gf_id)
        prev_level = prog.level
        prog, _award_result = award_progress(prog, body.message, progression_now)
        set_relationship_progress(sid, prog, girlfriend_id=resolved_gf_id)

        # Derive a relationship state dict from progression for milestone checks etc.
        region = get_region_for_level(prog.level)
        state = {
            "trust": derive_trust(prog.level),
            "intimacy": derive_intimacy(prog.level),
            "level": prog.level,
            "region_key": region.key,
            "last_interaction_at": prog.last_interaction_at.isoformat() if prog.last_interaction_at else None,
            "milestones_reached": [],
        }
        # Carry over existing milestones from stored relationship_state
        old_rs = get_relationship_state(sid, girlfriend_id=resolved_gf_id) or {}
        state["milestones_reached"] = old_rs.get("milestones_reached", [])

        prev_state = {**state, "level": prev_level, "region_key": get_region_for_level(prev_level).key}
        set_relationship_state(sid, state, girlfriend_id=resolved_gf_id)
    else:
        # Supabase path: keep legacy register_interaction flow
        state = sb.get_relationship_state(user_id, gf_uuid)
        if not state:
            state = create_initial_relationship_state()
            sb.upsert_relationship_state(user_id, gf_uuid, state)
        prev_state = dict(state)
        state = register_interaction(
            state,
            emotional_disclosure=_emotional_disclosure_heuristic(body.message),
            affection=_affection_heuristic(body.message),
        )
        sb.upsert_relationship_state(user_id, gf_uuid, state)

    # ── Trust/Intimacy gain tracking ─────────────────────────────────────────
    gain_events = []  # list of dicts for SSE relationship_gain events
    ti_state = get_trust_intimacy_state(sid, girlfriend_id=resolved_gf_id)
    current_region_key = state.get("region_key") or get_region_for_level(state.get("level", 0)).key

    # 1) Conversation trust gain (slow, quality-gated, cooldowned) — bank-first
    try:
        ti_state, trust_result = apply_conversation_trust_gain(
            ti_state, body.message, progression_now,
            region_key=current_region_key,
        )
        if trust_result.delta > 0:
            micro = get_gain_micro_lines(trust_result.delta, ti_state.trust, 0, ti_state.intimacy)
            gain_events.append({
                "trust_delta": trust_result.delta,
                "trust_new": ti_state.trust,
                "intimacy_delta": 0,
                "intimacy_new": ti_state.intimacy,
                "reason": "conversation",
                # Bank/release breakdown
                "trust_banked_delta": trust_result.banked_delta,
                "trust_released_delta": trust_result.released_delta,
                "trust_visible_new": trust_result.visible_new,
                "trust_bank_new": trust_result.bank_new,
                "trust_cap": trust_result.cap,
                "intimacy_banked_delta": 0,
                "intimacy_released_delta": 0,
                "intimacy_visible_new": ti_state.intimacy_visible,
                "intimacy_bank_new": ti_state.intimacy_bank,
                "intimacy_cap": get_intimacy_cap_for_region(current_region_key),
                **micro,
            })
    except Exception as e:
        logger.warning("Conversation trust gain failed: %s", e)

    # Check for milestone
    milestone_result = check_for_milestone_event(prev_state, state)
    milestone_message = None
    if milestone_result:
        region_key, milestone_message = milestone_result
        state = append_milestone_reached(state, region_key)
        if use_sb and user_id and gf_uuid:
            sb.upsert_relationship_state(user_id, gf_uuid, state)
        else:
            set_relationship_state(sid, state, girlfriend_id=resolved_gf_id)

        # ── Intimacy: award region milestone (legacy IntimacyState) ───────
        try:
            region_index = next(
                (i for i, r in enumerate(REGIONS) if r.key == region_key), 0
            )
            int_state = get_intimacy_state(sid, girlfriend_id=resolved_gf_id)
            prev_intimacy = int_state.intimacy_index
            int_state, _int_result = award_region_milestone(
                int_state, region_key, region_index, progression_now
            )
            set_intimacy_state(sid, int_state, girlfriend_id=resolved_gf_id)
            logger.info("Intimacy region award (legacy): %s", _int_result.reason)
        except Exception as e:
            logger.warning("Intimacy region award (legacy) failed: %s", e)

        # ── Intimacy: award region milestone (new unified state) ──────────
        try:
            region_index = next(
                (i for i, r in enumerate(REGIONS) if r.key == region_key), 0
            )
            ti_state, intimacy_result = award_intimacy_region(
                ti_state, region_key, region_index, progression_now
            )

            # Also release any previously banked values under the new higher cap
            release_banked(ti_state, region_key)
            # Update current_region_key for subsequent calls
            current_region_key = region_key

            if intimacy_result.delta > 0:
                micro = get_gain_micro_lines(0, ti_state.trust, intimacy_result.delta, ti_state.intimacy)
                gain_events.append({
                    "trust_delta": 0,
                    "trust_new": ti_state.trust,
                    "intimacy_delta": intimacy_result.delta,
                    "intimacy_new": ti_state.intimacy,
                    "reason": "region",
                    # Bank/release breakdown
                    "trust_banked_delta": 0,
                    "trust_released_delta": 0,
                    "trust_visible_new": ti_state.trust_visible,
                    "trust_bank_new": ti_state.trust_bank,
                    "trust_cap": get_trust_cap_for_region(current_region_key),
                    "intimacy_banked_delta": intimacy_result.banked_delta,
                    "intimacy_released_delta": intimacy_result.released_delta,
                    "intimacy_visible_new": intimacy_result.visible_new,
                    "intimacy_bank_new": intimacy_result.bank_new,
                    "intimacy_cap": intimacy_result.cap,
                    **micro,
                })
            logger.info("Intimacy region award (unified): %s", intimacy_result.reason)
        except Exception as e:
            logger.warning("Intimacy region award (unified) failed: %s", e)

        # Check if the free user just crossed the blurred preview threshold
        try:
            user_plan = (user or {}).get("plan", "free")
            content_prefs = gf.get("content_prefs") or {}
            # Use visible intimacy for blurred surprise check
            if (
                should_send_blurred_surprise(
                    ti_state.intimacy_visible,
                    user_plan,
                    bool((user or {}).get("age_gate_passed")),
                    bool(content_prefs.get("wants_spicy_photos")),
                )
            ):
                blurred_surprise_msg = {
                    "id": str(uuid_mod.uuid4()),
                    "role": "assistant",
                    "content": "I took something just for you... \U0001f60f",
                    "image_url": None,
                    "event_type": "blurred_preview",
                    "event_key": "free_plan_upgrade",
                    "created_at": now_iso(),
                    "blurred_image_url": _pick_blurred_url(resolved_gf_id or ""),
                }
                store_append_message(sid, blurred_surprise_msg, girlfriend_id=resolved_gf_id)
        except Exception as e:
            logger.warning("Blurred surprise check failed: %s", e)

    # Persist unified trust/intimacy state
    set_trust_intimacy_state(sid, ti_state, girlfriend_id=resolved_gf_id)

    # Also sync trust/intimacy into the relationship state dict for API consumers
    state["trust"] = ti_state.trust
    state["intimacy"] = ti_state.intimacy
    if not (use_sb and user_id and gf_uuid):
        set_relationship_state(sid, state, girlfriend_id=resolved_gf_id)

    # ── Achievement milestone triggers (emotional detection engine) ────────────
    achievement_events = []
    try:
        ach_progress = get_achievement_progress(sid, girlfriend_id=resolved_gf_id)
        cur_region_idx = get_current_region_index_for_girl(state.get("level", 0))

        # Update region index (non-missable: no counter reset)
        if ach_progress.region_index != cur_region_idx:
            ach_progress = reset_progress_for_region(ach_progress, cur_region_idx)

        # Build recent messages context for arc detection
        recent_msgs = get_messages(sid, girlfriend_id=resolved_gf_id)
        last_assistant = ""
        recent_texts = []
        for m in (recent_msgs or [])[-10:]:
            recent_texts.append(m.get("content", ""))
            if m.get("role") == "assistant":
                last_assistant = m.get("content", "")

        # Run emotional signal detection on user + assistant messages
        all_triggers = detect_signals(
            body.message, last_assistant, ach_progress, recent_texts
        )

        # Try unlock ALL eligible achievements (non-missable: past + current regions)
        if all_triggers:
            state, new_events = try_unlock_for_triggers(
                state, ach_progress, all_triggers
            )
            achievement_events.extend(new_events)

        # Persist achievement progress
        set_achievement_progress(sid, ach_progress, girlfriend_id=resolved_gf_id)

        # Persist state if any achievements unlocked
        if achievement_events:
            if use_sb and user_id and gf_uuid:
                sb.upsert_relationship_state(user_id, gf_uuid, state)
            else:
                set_relationship_state(sid, state, girlfriend_id=resolved_gf_id)
    except Exception as e:
        logger.warning("Achievement trigger check failed: %s", e)

    # ── Intimacy achievement triggers (keyword-based photo rewards) ─────────
    intimacy_unlock_events = []
    intimacy_photo_events = []
    try:
        from app.services.intimacy_achievement_engine import evaluate_intimacy_achievements
        cur_region_idx_ia = get_current_region_index_for_girl(state.get("level", 0))
        ia_unlocks, ia_photos = evaluate_intimacy_achievements(
            session_id=sid,
            girlfriend_id=resolved_gf_id or "",
            user_message=body.message,
            current_region_index=cur_region_idx_ia,
            intimacy_visible=ti_state.intimacy_visible if ti_state else 1,
            age_gate_passed=bool((user or {}).get("age_gate_passed")),
        )
        intimacy_unlock_events.extend(ia_unlocks)
        intimacy_photo_events.extend(ia_photos)
    except Exception as e:
        logger.warning("Intimacy achievement check failed: %s", e)

    # Collect blurred surprise (set above if threshold was crossed)
    blurred_surprise = locals().get("blurred_surprise_msg")

    traits_payload = gf.get("traits") or {}
    habit = sb.get_habit_profile(user_id, gf_uuid) if (use_sb and user_id and gf_uuid) else get_habit_profile(sid, girlfriend_id=resolved_gf_id)
    
    # ── Bond Engine: unified turn processing ─────────────────────────────────
    bond_outcome: TurnOutcome | None = None
    bond_context_prompt: str | None = None
    try:
        # Gather recent assistant turns for response director
        recent_assistant_texts = [
            m.get("content", "") for m in (messages or [])[-10:]
            if m.get("role") == "assistant" and m.get("content")
        ]
        # Gather all user timestamps and messages for pattern memory
        all_user_ts = [m.get("created_at", "") for m in (messages or []) if m.get("role") == "user"]
        all_user_msgs = [m.get("content", "") for m in (messages or []) if m.get("role") == "user" and m.get("content")]

        bond_ctx = TurnContext(
            session_id=sid,
            user_id=user_id,
            girlfriend_id=gf_uuid or resolved_gf_id,
            turn_id=user_msg["id"],
            user_message=body.message,
            girlfriend=gf,
            relationship_state=state,
            level=state.get("level", 0) if isinstance(state, dict) else 0,
            all_user_messages=all_user_msgs,
            all_user_timestamps=all_user_ts,
            recent_assistant_turns=recent_assistant_texts,
            sb_admin=get_supabase_admin() if use_sb else None,
        )
        bond_outcome = bond_process_turn(bond_ctx)
        bond_context_prompt = bond_outcome.bond_context_prompt or None

        # Log bond engine results
        if bond_outcome.ingestion_result:
            ir = bond_outcome.ingestion_result
            logger.info(
                "Bond Engine: facts=%d emotions=%s episodes=%d conflicts=%d caps=%s",
                ir.get("facts_extracted", 0),
                ir.get("emotions_detected", []),
                ir.get("episodes_created", 0),
                ir.get("conflicts_found", 0),
                bond_outcome.new_capabilities,
            )
    except Exception as e:
        logger.warning("Bond engine processing failed (non-blocking): %s", e)

    # Build memory context for personalized responses (legacy, used alongside bond engine)
    memory_ctx = None
    if use_sb and user_id and gf_uuid:
        try:
            memory_ctx = build_memory_context(
                sb=get_supabase_admin(),
                user_id=user_id,
                girlfriend_id=gf_uuid,
                max_facts=8,
                max_emotions=5,
                habit_profile=habit
            )
        except Exception as e:
            logger.warning("Memory context build failed: %s", e)

    # If bond engine produced a memory bundle, use it for prompt memories
    bond_memories_dict = None
    if bond_outcome and bond_outcome.memory_bundle.has_content():
        bond_memories_dict = bond_outcome.memory_bundle.to_prompt_dict()
    
    # ── Build system prompt ─────────────────────────────────────────────────
    system_prompt = None
    behavior_intent: str | None = None
    behavior_result = None
    try:
        prompt_ctx = get_prompt_context(
            sb_admin=get_supabase_admin() if use_sb else None,
            user_id=user_id if use_sb else None,
            girlfriend_id=gf_uuid if use_sb else None,
            session_id=sid if not use_sb else None,
            girlfriend_id_str=resolved_gf_id if not use_sb else None,
            girlfriend=gf,
            relationship_state=state,
            habit_profile=habit,
            memory_context=memory_ctx,
        )
        # Override memories with bond engine's scored bundle if available
        if bond_memories_dict:
            prompt_ctx["memories_dict"] = bond_memories_dict
        # Inject bond context (consistency, capabilities, disclosure, response direction)
        if bond_context_prompt:
            prompt_ctx["bond_context"] = bond_context_prompt

        # ── Behavior Engine: intent + dossier + turn rules ────────────────
        behavior_context = ""
        try:
            from app.services.behavior_engine.behavior_orchestrator import (
                BehaviorTurnInput, process_behavior_turn,
            )
            behavior_input = BehaviorTurnInput(
                session_id=sid,
                user_id=user_id,
                girlfriend_id=gf_uuid or resolved_gf_id,
                user_message=body.message,
                girlfriend_data=gf,
                relationship_level=state.get("level", 0) if isinstance(state, dict) else 0,
                recent_assistant_texts=[
                    m.get("content", "") for m in (messages or [])[-10:]
                    if m.get("role") == "assistant" and m.get("content")
                ],
                sb_admin=get_supabase_admin() if use_sb else None,
                bond_context_prompt=bond_context_prompt,
            )
            behavior_result = process_behavior_turn(behavior_input)
            behavior_context = behavior_result.get_full_behavior_context()
            behavior_intent = behavior_result.intent.primary
            if behavior_context:
                # Append behavior context after bond context
                existing_bond = prompt_ctx.get("bond_context", "")
                prompt_ctx["bond_context"] = (existing_bond + "\n\n" + behavior_context).strip()
            logger.info("Behavior Engine: intent=%s, must_answer=%s, max_q=%d, tone=%s",
                        behavior_result.intent.primary,
                        behavior_result.contract.must_answer_user_question,
                        behavior_result.contract.max_questions,
                        behavior_result.contract.tone)
        except Exception as e:
            logger.warning("Behavior engine failed (non-blocking): %s", e)

        # Always add concise reply guardrail to reduce unnatural long outputs.
        length_guardrail = _build_concise_style_guardrail(body.message, behavior_intent)
        existing_bond = prompt_ctx.get("bond_context", "")
        prompt_ctx["bond_context"] = (existing_bond + "\n\n" + length_guardrail).strip()

        prompt_input = build_input_from_dict(**prompt_ctx)
        system_prompt = build_system_prompt(prompt_input)
    except Exception as e:
        logger.warning("System prompt build failed: %s", e)

    # ── Image decision check (sensitive content gating) ─────────────────────
    image_decision_event = None
    if request_is_sensitive(body.message):
        try:
            content_prefs = gf.get("content_prefs") or {}
            user_plan = (user or {}).get("plan", "free")
            # Use VISIBLE intimacy only (banked does NOT count for gates)
            img_decision = decide_image_action(
                text=body.message,
                age_gate_passed=bool((user or {}).get("age_gate_passed")),
                wants_spicy=bool(content_prefs.get("wants_spicy_photos")),
                girlfriend_traits=traits_payload,
                has_quota=True,
                explicit_ask=False,
                user_plan=user_plan,
                girlfriend_id=resolved_gf_id or "",
                intimacy_visible=ti_state.intimacy_visible,
            )
            if img_decision.action != "generate":
                image_decision_event = {
                    "action": img_decision.action,
                    "reason": img_decision.reason,
                    "ui_copy": img_decision.ui_copy,
                    "suggested_prompts": img_decision.suggested_prompts,
                    "required_intimacy": img_decision.required_intimacy,
                    "current_intimacy": img_decision.current_intimacy,
                    "blurred_image_url": img_decision.blurred_image_url,
                }
        except Exception as e:
            logger.warning("Image decision check failed: %s", e)

    # ── Progression evaluation (event-driven architecture) ───────────────────
    try:
        from app.services import progression_service as prog_svc
        from app.services import message_composer, delivery_service, experiment_service, telemetry_service

        _user_id_str = str(user_id) if user_id else (user or {}).get("user_id", (user or {}).get("id", ""))
        _gf_id_str = str(gf_uuid) if gf_uuid else resolved_gf_id or ""

        if _user_id_str and _gf_id_str:
            # Extract quality signals from the user message
            recent_count = len([m for m in messages[-10:] if m.get("role") == "user"])
            signals = prog_svc.extract_quality_signals(body.message, recent_message_count=recent_count)
            quality = prog_svc.compute_quality_score(signals)

            # Log session quality
            telemetry_service.update_session_quality(_user_id_str, _gf_id_str, quality.total, signals.model_dump())

            # Detect progression events from before/after state change
            old_level = prev_state.get("level", 0) if prev_state else 0
            new_level = state.get("level", 0) if isinstance(state, dict) else 0
            old_trust_vis = prev_state.get("trust_visible", 20) if prev_state else 20
            new_trust_vis = ti_state.trust_visible if hasattr(ti_state, "trust_visible") else (ti_state.get("trust_visible", 20) if isinstance(ti_state, dict) else 20)
            old_streak_val = 0
            # `prog` only exists in the in-memory progression path; for Supabase users
            # we still want progression events to work without crashing.
            try:
                _prog_any = get_relationship_progress(sid, girlfriend_id=resolved_gf_id)
                if isinstance(_prog_any, dict):
                    new_streak_val = int(_prog_any.get("streak_days", 0) or 0)
                else:
                    new_streak_val = int(getattr(_prog_any, "streak_days", 0) or 0)
            except Exception:
                new_streak_val = 0
            ach_state = get_achievement_progress(sid, girlfriend_id=resolved_gf_id)
            old_mc = (ach_state.get("message_counter", 0) if isinstance(ach_state, dict) else getattr(ach_state, "message_counter", 0)) - 1
            new_mc = old_mc + 1
            existing_milestones = state.get("milestones_reached", []) if isinstance(state, dict) else []

            prog_events = prog_svc.detect_progression_events(
                user_id=_user_id_str,
                girlfriend_id=_gf_id_str,
                quality_score=quality.total,
                old_level=old_level,
                new_level=new_level,
                old_trust=old_trust_vis,
                new_trust=new_trust_vis,
                old_streak=old_streak_val,
                new_streak=new_streak_val,
                old_message_count=old_mc,
                new_message_count=new_mc,
                reached_milestones=existing_milestones,
            )

            # Compose and queue milestone messages
            if prog_events:
                gf_name_str = gf.get("display_name") or gf.get("name") or "her"
                gf_traits = gf.get("traits") or {}
                tone = experiment_service.resolve_tone_from_traits(gf_traits)
                for evt in prog_events:
                    msg = message_composer.compose_milestone_message(
                        evt, girlfriend_name=gf_name_str, tone=tone,
                    )
                    if msg:
                        delivery_service.queue_message(_user_id_str, _gf_id_str, msg)
                    telemetry_service.log_progression_event(
                        _user_id_str, _gf_id_str, evt.event_type, evt.payload, quality.total
                    )
                logger.info(f"Progression: {len(prog_events)} events, queued messages for user {_user_id_str[:8]}")
    except Exception as e:
        logger.warning("Progression evaluation failed (non-blocking): %s", e)

    # ── Optional debug: include prompt hash in response headers ─────────────
    extra_headers: dict[str, str] = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    if request.headers.get("X-Debug-Prompt") == "1" and system_prompt:
        import hashlib
        prompt_hash = hashlib.sha256(system_prompt.encode()).hexdigest()[:16]
        extra_headers["X-Prompt-Hash"] = prompt_hash
    gen_max_tokens, gen_temperature = _compute_generation_controls(
        body.message,
        behavior_intent,
        persona_vector=persona_vector,
    )

    return StreamingResponse(
        _stream_response_and_save(
            sid, user_id, gf_uuid, milestone_message, messages,
            gf.get("display_name") or gf.get("name", "Companion"),
            traits_payload, relationship_state=state, habit_profile=habit, memory_context=memory_ctx,
            girlfriend_id=resolved_gf_id,
            image_decision_event=image_decision_event,
            blurred_surprise_event=blurred_surprise,
            relationship_gain_events=gain_events if gain_events else None,
            achievement_events=achievement_events if achievement_events else None,
            intimacy_unlock_events=intimacy_unlock_events if intimacy_unlock_events else None,
            intimacy_photo_events=intimacy_photo_events if intimacy_photo_events else None,
            system_prompt=system_prompt,
            bond_outcome=bond_outcome,
            bond_turn_ctx=bond_ctx if bond_outcome else None,
            behavior_result=behavior_result,
            max_tokens=gen_max_tokens,
            temperature=gen_temperature,
        ),
        media_type="text/event-stream",
        headers=extra_headers,
    )


@router.post("/app_open")
def app_open(request: Request, body: AppOpenRequest):
    sid, user, user_id, gf_id = get_current_user(request)
    if not sid or not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    # Use body.girlfriend_id or session's current
    resolved_gf_id = body.girlfriend_id or gf_id
    use_sb = get_supabase_admin() and user_id is not None
    if use_sb and user_id:
        gf = sb.get_current_girlfriend(user_id, resolved_gf_id)
        if gf:
            gf_uuid = UUID(str(gf["id"]))
            if not gf_id or str(gf_id) != str(gf["id"]):
                from app.api.store import set_session_girlfriend_id
                set_session_girlfriend_id(sid, str(gf["id"]))
        else:
            gf_uuid = None
    else:
        if resolved_gf_id:
            from app.api.store import get_girlfriend_by_id as _get_gf_by_id
            gf = _get_gf_by_id(sid, resolved_gf_id) or get_girlfriend(sid)
        else:
            gf = get_girlfriend(sid)
        gf_uuid = None
    if not gf or gf.get("id") != body.girlfriend_id:
        return JSONResponse(status_code=400, content={"error": "girlfriend_mismatch"})
    if use_sb and user_id and gf_uuid:
        state = sb.get_relationship_state(user_id, gf_uuid)
        if not state:
            state = create_initial_relationship_state()
            sb.upsert_relationship_state(user_id, gf_uuid, state)
    else:
        state = get_relationship_state(sid)
        if not state:
            state = create_initial_relationship_state()
            set_relationship_state(sid, state)

    hours_inactive = hours_since(state.get("last_interaction_at"))
    traits = gf.get("traits") or {}
    attachment_style = traits.get("attachment_style", "Calm but caring")
    reaction_absence = traits.get("reaction_to_absence", "Low")
    attachment_intensity = ATTACHMENT_INTENSITY.get(attachment_style, "low")
    jealousy_level = JEALOUSY_LEVEL.get(reaction_absence, "Low")

    state = apply_inactivity_decay(state, hours_inactive, attachment_intensity)
    if use_sb and user_id and gf_uuid:
        sb.upsert_relationship_state(user_id, gf_uuid, state)
    else:
        set_relationship_state(sid, state)

    messages_out: list[dict] = []
    from datetime import datetime, timezone
    current_hour = datetime.now(timezone.utc).hour
    if use_sb and user_id and gf_uuid:
        habit = sb.get_habit_profile(user_id, gf_uuid)
        stored = sb.get_messages(user_id, gf_uuid)
    else:
        habit = get_habit_profile(sid)
        stored = get_messages(sid)
    preferred_hours = habit.get("preferred_hours") or [] if habit else []
    typical_gap = habit.get("typical_gap_hours") if habit else None

    last_from_her = False
    if stored:
        last = stored[-1]
        last_from_her = last.get("role") == "assistant"

    region_key = state.get("region_key") or get_region_for_level(state.get("level", 0)).key
    jealousy_text = get_jealousy_reaction(region_key, jealousy_level, hours_inactive)
    if jealousy_text:
        msg = {
            "id": str(uuid_mod.uuid4()),
            "role": "assistant",
            "content": jealousy_text,
            "image_url": None,
            "event_type": None,
            "event_key": None,
            "created_at": now_iso(),
        }
        if use_sb and user_id and gf_uuid:
            sb.append_message(user_id, gf_uuid, msg)
        else:
            store_append_message(sid, msg)
        messages_out.append(msg)
        state["last_interaction_at"] = now_iso()
        if use_sb and user_id and gf_uuid:
            sb.upsert_relationship_state(user_id, gf_uuid, state)
        else:
            set_relationship_state(sid, state)

    if not jealousy_text:
        # ── Bond Engine: event-conditioned initiation ────────────────────
        init_result = plan_proactive_initiation(
            sb_admin=get_supabase_admin() if use_sb else None,
            user_id=user_id,
            girlfriend_id=gf_uuid or body.girlfriend_id,
            girlfriend=gf,
            relationship_state=state,
            last_message_from_her=last_from_her,
            hours_inactive=hours_inactive,
            current_hour=current_hour,
            active_hours=preferred_hours if preferred_hours else None,
        )

        if init_result.should_initiate and init_result.message:
            init_text = init_result.message.text
            msg = {
                "id": str(uuid_mod.uuid4()),
                "role": "assistant",
                "content": init_text,
                "image_url": None,
                "event_type": "initiation",
                "event_key": init_result.reason_type,
                "created_at": now_iso(),
            }
            if use_sb and user_id and gf_uuid:
                sb.append_message(user_id, gf_uuid, msg)
            else:
                store_append_message(sid, msg)
            messages_out.append(msg)
            state["last_interaction_at"] = now_iso()
            if use_sb and user_id and gf_uuid:
                sb.upsert_relationship_state(user_id, gf_uuid, state)
            else:
                set_relationship_state(sid, state)
            logger.info("Bond initiation: type=%s reason=%s", init_result.reason_type, init_result.reason_context)
        else:
            # Fallback to legacy initiation if bond engine didn't trigger
            should_init = should_initiate_conversation(
                state,
                attachment_intensity,
                last_from_her,
                hours_inactive,
                current_hour,
                preferred_hours=preferred_hours if preferred_hours else None,
                typical_gap_hours=typical_gap,
                user_id=user.get("id"),
                girlfriend_id=body.girlfriend_id,
            )
            if should_init:
                init_text = get_initiation_message(region_key, attachment_intensity)
                msg = {
                    "id": str(uuid_mod.uuid4()),
                    "role": "assistant",
                    "content": init_text,
                    "image_url": None,
                    "event_type": None,
                    "event_key": None,
                    "created_at": now_iso(),
                }
                if use_sb and user_id and gf_uuid:
                    sb.append_message(user_id, gf_uuid, msg)
                else:
                    store_append_message(sid, msg)
                messages_out.append(msg)
                state["last_interaction_at"] = now_iso()
                if use_sb and user_id and gf_uuid:
                    sb.upsert_relationship_state(user_id, gf_uuid, state)
                else:
                    set_relationship_state(sid, state)

    return {
        "messages": [_msg_to_schema(m) for m in messages_out],
        "relationshipState": _state_to_schema(state),
    }
