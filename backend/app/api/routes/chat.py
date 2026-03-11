"""Chat: history, state, send (SSE), app_open (initiation + jealousy).

This version includes full memory and personality integration with OpenAI streaming.
Uses the /v1/chat/stream gateway or direct OpenAI API when API_KEY is set.
Falls back to mock responses if no API key is configured.
"""
import uuid as uuid_mod
from uuid import UUID
from datetime import datetime, timezone
from collections import defaultdict
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
import logging
import httpx

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
from app.core import get_settings
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
    if not messages:
        messages = [
            {"id": "m1", "role": "user", "content": "Hey, how are you?", "image_url": None, "event_type": None, "event_key": None, "created_at": "2025-01-01T12:00:00Z"},
            {"id": "m2", "role": "assistant", "content": "I'm doing great! Thanks for asking.", "image_url": None, "event_type": None, "event_key": None, "created_at": "2025-01-01T12:00:01Z"},
        ]
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


def _fetch_runpod_vllm_response(llm_messages: list[dict]) -> str:
    """Call RunPod vLLM chat completions endpoint and return assistant text."""
    settings = get_settings()
    base_url = (settings.runpod_vllm_base_url or "").rstrip("/")
    model = settings.runpod_vllm_model
    if not base_url:
        raise RuntimeError("RUNPOD_VLLM_BASE_URL is not configured")
    if not model:
        raise RuntimeError("RUNPOD_VLLM_MODEL is not configured")

    url = f"{base_url}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.runpod_vllm_api_key:
        headers["Authorization"] = f"Bearer {settings.runpod_vllm_api_key}"

    payload = {
        "model": model,
        "messages": llm_messages,
        "stream": False,
    }

    timeout = httpx.Timeout(
        float(settings.runpod_vllm_timeout_seconds),
        connect=min(30.0, float(settings.runpod_vllm_timeout_seconds)),
    )
    def _messages_to_prompt(messages: list[dict]) -> str:
        prompt_lines: list[str] = []
        for m in messages:
            role = (m.get("role") or "user").strip().lower()
            content = str(m.get("content") or "").strip()
            if not content:
                continue
            if role == "system":
                prompt_lines.append(f"System: {content}")
            elif role == "assistant":
                prompt_lines.append(f"Assistant: {content}")
            else:
                prompt_lines.append(f"User: {content}")
        prompt_lines.append("Assistant:")
        return "\n\n".join(prompt_lines)

    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=payload, headers=headers)
        if response.status_code == 400:
            # Some vLLM deployments require /v1/completions for base models without chat template.
            response_text = response.text or ""
            if "chat template" in response_text.lower():
                fallback_url = f"{base_url}/v1/completions"
                fallback_payload = {
                    "model": model,
                    "prompt": _messages_to_prompt(llm_messages),
                    "stream": False,
                    "max_tokens": 400,
                    "temperature": 0.85,
                }
                logger.warning("RunPod chat/completions unavailable; falling back to /v1/completions")
                fallback_resp = client.post(fallback_url, json=fallback_payload, headers=headers)
                fallback_resp.raise_for_status()
                fallback_data = fallback_resp.json()
                raw_text = ((fallback_data.get("choices") or [{}])[0]).get("text", "")
                if not isinstance(raw_text, str) or not raw_text.strip():
                    raise ValueError("Invalid RunPod completions response: missing choices[0].text")
                # Trim model continuation if it starts generating the next user turn.
                cleaned = raw_text.split("\nUser:", 1)[0].strip()
                return cleaned or raw_text.strip()
        response.raise_for_status()
        data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except (TypeError, KeyError, IndexError) as exc:
        raise ValueError("Invalid RunPod vLLM response shape: missing choices[0].message.content") from exc
    if not isinstance(content, str):
        raise ValueError("Invalid RunPod vLLM response shape: content is not a string")
    return content


def _stream_response_and_save(sid, user_id, gf_id, milestone_message, messages_for_context, gf_display_name, traits, relationship_state=None, habit_profile=None, memory_context=None, girlfriend_id=None, image_decision_event=None, blurred_surprise_event=None, relationship_gain_events=None, achievement_events=None, intimacy_unlock_events=None, intimacy_photo_events=None, system_prompt=None, bond_outcome=None, bond_turn_ctx=None):
    """Stream response and save assistant message. Yields SSE events.
    
    Uses OpenAI ChatGPT API for real streaming responses when API_KEY is set.
    Falls back to mock responses if API_KEY is unavailable.
    The system_prompt contains the full personality, memory, bond engine context.
    """
    # Get the last user message for context
    last_user_msg = ""
    for m in reversed(messages_for_context):
        if m.get("role") == "user" and m.get("content"):
            last_user_msg = m["content"]
            break

    # Build messages list for LLM
    llm_messages = []
    if system_prompt:
        llm_messages.append({"role": "system", "content": system_prompt})
    # Add short-term context (last 20 messages)
    for m in messages_for_context[-20:]:
        llm_messages.append({"role": m["role"], "content": (m.get("content") or "")[:2000]})
    logger.debug("LLM message count: %d (system prompt: %d chars)", len(llm_messages), len(system_prompt or ""))

    response_text = ""
    try:
        response_text = _fetch_runpod_vllm_response(llm_messages).strip()
        if not response_text:
            raise ValueError("RunPod vLLM returned empty assistant content")
        for t in response_text.split():
            yield sse_event({"type": "token", "token": t + " "})
        logger.info("RunPod vLLM response: %d chars", len(response_text))
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        details = (e.response.text[:500] if e.response is not None else str(e)) if hasattr(e, "response") else str(e)
        logger.error("RunPod vLLM HTTP error (%s): %s", status, details)
        yield sse_event({"type": "error", "error": f"RunPod chat request failed with status {status}."})
        yield sse_event({"type": "done"})
        return
    except httpx.RequestError as e:
        logger.error("RunPod vLLM unreachable: %s", e)
        yield sse_event({"type": "error", "error": "RunPod chat service is unreachable. Please try again."})
        yield sse_event({"type": "done"})
        return
    except ValueError as e:
        logger.error("RunPod vLLM invalid response: %s", e)
        yield sse_event({"type": "error", "error": "RunPod chat returned an invalid response format."})
        yield sse_event({"type": "done"})
        return
    except Exception as e:
        logger.error("RunPod vLLM unexpected error: %s", e)
        yield sse_event({"type": "error", "error": "Unexpected RunPod chat error."})
        yield sse_event({"type": "done"})
        return
    
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
        "content": response_text.strip() if response_text else "I'm here for you.",
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
            yield sse_event({
                "type": "relationship_gain",
                "gain": gain_evt,
            })

    # Emit achievement unlock events
    if achievement_events:
        for ach_evt in achievement_events:
            yield sse_event({
                "type": "relationship_achievement",
                "achievement": ach_evt,
            })

    # Emit intimacy achievement unlock events
    if intimacy_unlock_events:
        for iu_evt in intimacy_unlock_events:
            yield sse_event({
                "type": "intimacy_achievement",
                "achievement": iu_evt,
            })

    # Emit intimacy photo ready events
    if intimacy_photo_events:
        for ip_evt in intimacy_photo_events:
            photo_msg = {
                "id": str(uuid_mod.uuid4()),
                "role": "assistant",
                "content": f"{ip_evt.get('icon', '🔥')} *{ip_evt.get('title', 'Achievement')}* — unlocked",
                "image_url": ip_evt.get("image_url"),
                "event_type": "intimacy_photo_ready",
                "event_key": ip_evt.get("id", ""),
                "created_at": now_iso(),
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
                BehaviorTurnInput, persist_behavior_turn, process_behavior_turn,
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
                # Build a minimal result for persistence (we just need intent and contract)
                from app.services.behavior_engine.intent_classifier import TurnIntent
                from app.services.behavior_engine.response_contract import BehaviorContract
                from app.services.behavior_engine.behavior_orchestrator import BehaviorTurnResult
                from app.services.dossier.retriever import DossierContext
                _beh_result = BehaviorTurnResult()
                persist_behavior_turn(_beh_inp, _beh_result, response_text, str(uuid_mod.uuid4()))
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
        if explicit_gf_id:
            from app.api.store import get_girlfriend_by_id
            gf = get_girlfriend_by_id(sid, explicit_gf_id)
        else:
            gf = get_girlfriend(sid)
        gf_uuid = None
    if not gf:
        return JSONResponse(status_code=400, content={"error": "no_girlfriend"})

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
        try:
            write_memories_from_message(
                sb=get_supabase_admin(),
                user_id=user_id,
                girlfriend_id=gf_uuid,
                message_id=user_msg["id"],
                role="user",
                text=body.message
            )
        except Exception as e:
            logger.warning("Memory write failed: %s", e)
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
        prog = get_relationship_progress(sid, girlfriend_id=resolved_gf_id)
        prev_level = prog.level
        prog, _award_result = award_progress(prog, body.message, progression_now)
        set_relationship_progress(sid, prog, girlfriend_id=resolved_gf_id)

        region = get_region_for_level(prog.level)
        state = {
            "trust": derive_trust(prog.level),
            "intimacy": derive_intimacy(prog.level),
            "level": prog.level,
            "region_key": region.key,
            "last_interaction_at": prog.last_interaction_at.isoformat() if prog.last_interaction_at else None,
            "milestones_reached": [],
        }
        old_rs = get_relationship_state(sid, girlfriend_id=resolved_gf_id) or {}
        state["milestones_reached"] = old_rs.get("milestones_reached", [])

        prev_state = {**state, "level": prev_level, "region_key": get_region_for_level(prev_level).key}
        set_relationship_state(sid, state, girlfriend_id=resolved_gf_id)
    else:
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
    gain_events = []
    ti_state = get_trust_intimacy_state(sid, girlfriend_id=resolved_gf_id)
    current_region_key = state.get("region_key") or get_region_for_level(state.get("level", 0)).key

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
            release_banked(ti_state, region_key)
            current_region_key = region_key

            if intimacy_result.delta > 0:
                micro = get_gain_micro_lines(0, ti_state.trust, intimacy_result.delta, ti_state.intimacy)
                gain_events.append({
                    "trust_delta": 0,
                    "trust_new": ti_state.trust,
                    "intimacy_delta": intimacy_result.delta,
                    "intimacy_new": ti_state.intimacy,
                    "reason": "region",
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

        if ach_progress.region_index != cur_region_idx:
            ach_progress = reset_progress_for_region(ach_progress, cur_region_idx)

        recent_msgs = get_messages(sid, girlfriend_id=resolved_gf_id)
        last_assistant = ""
        recent_texts = []
        for m in (recent_msgs or [])[-10:]:
            recent_texts.append(m.get("content", ""))
            if m.get("role") == "assistant":
                last_assistant = m.get("content", "")

        all_triggers = detect_signals(
            body.message, last_assistant, ach_progress, recent_texts
        )

        if all_triggers:
            state, new_events = try_unlock_for_triggers(
                state, ach_progress, all_triggers
            )
            achievement_events.extend(new_events)

        set_achievement_progress(sid, ach_progress, girlfriend_id=resolved_gf_id)

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
            new_streak_val = prog.streak_days if hasattr(prog, "streak_days") else 0
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
