"""Chat: history, state, send (SSE), app_open (initiation + jealousy).

This version includes full memory and personality integration with mock LLM responses.
To enable real AI, set API_KEY in .env or connect to the /v1/chat/stream gateway.
"""
import uuid as uuid_mod
from uuid import UUID
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
import logging

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
from app.services.initiation_engine import should_initiate_conversation, get_initiation_message
from app.services.habits import build_habit_profile
from app.services.big_five import map_traits_to_big_five, big_five_to_description
from app.services.time_utils import hours_since, now_iso
from app.services.memory import build_memory_context, write_memories_from_message

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

# Attachment style -> intensity for engine
ATTACHMENT_INTENSITY = {"Very attached": "high", "Emotionally present": "medium", "Calm but caring": "low"}
# Reaction to absence -> jealousy level
JEALOUSY_LEVEL = {"High": "high", "Medium": "medium", "Low": "low"}


def _state_to_schema(state: dict) -> RelationshipStateSchema:
    return RelationshipStateSchema(
        trust=state["trust"],
        intimacy=state["intimacy"],
        level=state["level"],
        last_interaction_at=state.get("last_interaction_at"),
        milestones_reached=state.get("milestones_reached") or [],
    )


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
    use_sb = _use_supabase(user_id)
    if use_sb and user_id:
        gf = sb.get_current_girlfriend(user_id)
        if gf:
            messages = sb.get_messages(user_id, UUID(str(gf["id"])))
        else:
            messages = []
    else:
        # Pass explicit girlfriend_id so messages are per-girl
        messages = get_messages(sid, girlfriend_id)
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
    use_sb = _use_supabase(user_id)
    if use_sb and user_id:
        gf = sb.get_current_girlfriend(user_id)
        if gf:
            gf_uuid = UUID(str(gf["id"]))
            state = sb.get_relationship_state(user_id, gf_uuid)
            if not state:
                state = create_initial_relationship_state()
                sb.upsert_relationship_state(user_id, gf_uuid, state)
        else:
            state = create_initial_relationship_state()
    else:
        state = get_relationship_state(sid, girlfriend_id)
        if not state:
            state = create_initial_relationship_state()
            set_relationship_state(sid, state, girlfriend_id)
    return _state_to_schema(state)


def _affection_heuristic(text: str) -> bool:
    t = (text or "").lower()
    return any(x in t for x in ["miss", "love", "❤", "heart", "hug", "care"])


def _emotional_disclosure_heuristic(text: str) -> bool:
    t = (text or "").lower()
    return any(x in t for x in ["feel", "felt", "worried", "sad", "happy", "excited", "nervous"])


def _generate_mock_response(gf_display_name: str, traits: dict, relationship_state: dict, memory_context, last_user_message: str) -> str:
    """Generate a personality-aware mock response based on traits and memory."""
    level = relationship_state.get("level", "STRANGER") if relationship_state else "STRANGER"
    
    # Get personality traits
    emotional_style = traits.get("emotional_style", "Caring")
    communication_style = traits.get("communication_style", "Soft")
    
    # Base responses by emotional style
    responses = {
        "Caring": [
            "I'm here for you, always. How are you feeling today?",
            "That's so sweet of you to say! I really appreciate you.",
            "I've been thinking about you. Tell me more about your day.",
        ],
        "Playful": [
            "Haha, you always know how to make me smile!",
            "Oh really? Tell me more, I'm intrigued!",
            "You're such a tease! But I love it.",
        ],
        "Reserved": [
            "I understand. Thank you for sharing that with me.",
            "That's interesting. I appreciate you telling me.",
            "I'm listening. Take your time.",
        ],
        "Protective": [
            "I've got your back, don't worry about a thing.",
            "Let me take care of that for you.",
            "You know I'm always looking out for you.",
        ],
    }
    
    # Select response based on emotional style
    style_responses = responses.get(emotional_style, responses["Caring"])
    
    # Add memory context if available
    prefix = ""
    if memory_context and memory_context.facts:
        # Reference something we know about the user
        if any("name" in f.lower() for f in memory_context.facts):
            prefix = "I remember you telling me about yourself. "
    
    # Adjust based on relationship level
    import random
    random.seed(hash(last_user_message))  # Deterministic based on message
    response = random.choice(style_responses)
    
    if level in ["INTIMATE", "EXCLUSIVE"]:
        response = f"💕 {response}"
    
    return prefix + response


def _stream_response_and_save(sid, user_id, gf_id, milestone_message, messages_for_context, gf_display_name, traits, relationship_state=None, habit_profile=None, memory_context=None, girlfriend_id=None):
    """Stream mock response and save assistant message. Yields SSE events.
    
    This function includes full personality and memory context for future LLM integration.
    Currently returns personality-aware mock responses.
    """
    # Get the last user message for context
    last_user_msg = ""
    for m in reversed(messages_for_context):
        if m.get("role") == "user" and m.get("content"):
            last_user_msg = m["content"]
            break
    
    # Generate personality-aware mock response
    response_text = _generate_mock_response(
        gf_display_name, 
        traits, 
        relationship_state, 
        memory_context, 
        last_user_msg
    )
    
    # Stream tokens
    tokens = response_text.split()
    for t in tokens:
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
    yield sse_event({"type": "done"})


@router.post("/send")
def send_message(request: Request, body: SendMessageRequest):
    sid, user, user_id, gf_id = get_current_user(request)
    if not sid or not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    # Resolve the girlfriend_id from the request body (preferred) or session
    explicit_gf_id = body.girlfriend_id or None

    use_sb = get_supabase_admin() and user_id is not None
    if use_sb and user_id:
        gf = sb.get_current_girlfriend(user_id)
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
        # Write memories from user message
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

    # Get/update relationship state
    if use_sb and user_id and gf_uuid:
        state = sb.get_relationship_state(user_id, gf_uuid)
        if not state:
            state = create_initial_relationship_state()
            sb.upsert_relationship_state(user_id, gf_uuid, state)
    else:
        state = get_relationship_state(sid, girlfriend_id=resolved_gf_id)
        if not state:
            state = create_initial_relationship_state()
            set_relationship_state(sid, state, girlfriend_id=resolved_gf_id)

    prev_state = dict(state)
    state = register_interaction(
        state,
        emotional_disclosure=_emotional_disclosure_heuristic(body.message),
        affection=_affection_heuristic(body.message),
    )
    if use_sb and user_id and gf_uuid:
        sb.upsert_relationship_state(user_id, gf_uuid, state)
    else:
        set_relationship_state(sid, state, girlfriend_id=resolved_gf_id)

    # Check for milestone
    milestone_result = check_for_milestone_event(prev_state, state)
    milestone_message = None
    if milestone_result:
        level, milestone_message = milestone_result
        state = append_milestone_reached(state, level)
        if use_sb and user_id and gf_uuid:
            sb.upsert_relationship_state(user_id, gf_uuid, state)
        else:
            set_relationship_state(sid, state, girlfriend_id=resolved_gf_id)

    traits_payload = gf.get("traits") or {}
    habit = sb.get_habit_profile(user_id, gf_uuid) if (use_sb and user_id and gf_uuid) else get_habit_profile(sid, girlfriend_id=resolved_gf_id)
    
    # Build memory context for personalized responses
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
    
    return StreamingResponse(
        _stream_response_and_save(
            sid, user_id, gf_uuid, milestone_message, messages,
            gf.get("display_name") or gf.get("name", "Companion"),
            traits_payload, relationship_state=state, habit_profile=habit, memory_context=memory_ctx,
            girlfriend_id=resolved_gf_id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/app_open")
def app_open(request: Request, body: AppOpenRequest):
    sid, user, user_id, gf_id = get_current_user(request)
    if not sid or not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    use_sb = get_supabase_admin() and user_id is not None
    if use_sb and user_id:
        gf = sb.get_current_girlfriend(user_id)
        if gf:
            gf_uuid = UUID(str(gf["id"]))
            if not gf_id or str(gf_id) != str(gf["id"]):
                from app.api.store import set_session_girlfriend_id
                set_session_girlfriend_id(sid, str(gf["id"]))
        else:
            gf_uuid = None
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

    jealousy_text = get_jealousy_reaction(state["level"], jealousy_level, hours_inactive)
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
            init_text = get_initiation_message(state["level"], attachment_intensity)
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
