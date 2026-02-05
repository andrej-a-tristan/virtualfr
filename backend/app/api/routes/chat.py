"""Chat: history, state, send (SSE), app_open (initiation + jealousy)."""
import uuid as uuid_mod
from uuid import UUID
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.schemas.chat import (
    SendMessageRequest,
    AppOpenRequest,
    ChatMessage,
    RelationshipState as RelationshipStateSchema,
)
from app.api.store import (
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

# Attachment style -> intensity for engine
ATTACHMENT_INTENSITY = {"Very attached": "high", "Emotionally present": "medium", "Calm but caring": "low"}
# Reaction to absence -> jealousy level (normalize to lowercase for architecture)
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
def chat_history(request: Request):
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
        messages = get_messages(sid)
    if not messages:
        messages = [
            {"id": "m1", "role": "user", "content": "Hey, how are you?", "image_url": None, "event_type": None, "event_key": None, "created_at": "2025-01-01T12:00:00Z"},
            {"id": "m2", "role": "assistant", "content": "I'm doing great! Thanks for asking.", "image_url": None, "event_type": None, "event_key": None, "created_at": "2025-01-01T12:00:01Z"},
        ]
    return {"messages": [_msg_to_schema(m) for m in messages]}


@router.get("/state")
def chat_state(request: Request):
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
        state = get_relationship_state(sid)
        if not state:
            state = create_initial_relationship_state()
            set_relationship_state(sid, state)
    return _state_to_schema(state)


def _stream_tokens(sid: str | None, user_id: UUID | None, gf_id: UUID | None, milestone_message: str | None = None, stream_content: str | None = None):
    """Yield SSE: tokens, optional milestone, message, done. Saves assistant message to store.
    NOT used by POST /send (which uses _stream_openai_and_save). stream_content is required for real content."""
    use_sb = user_id is not None and gf_id is not None
    if stream_content:
        tokens = stream_content.split()
        full_content = stream_content
    else:
        tokens = ["[No reply]"]
        full_content = "[No reply]"
    for t in tokens:
        if t:
            yield sse_event({"type": "token", "token": t})
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
            store_append_message(sid, milestone_msg)
        yield sse_event({"type": "message", "message": milestone_msg})
    msg = {
        "id": str(uuid_mod.uuid4()),
        "role": "assistant",
        "content": full_content,
        "image_url": None,
        "event_type": None,
        "event_key": None,
        "created_at": now_iso(),
    }
    if user_id and gf_id:
        sb.append_message(user_id, gf_id, msg)
    else:
        store_append_message(sid, msg)
    yield sse_event({"type": "message", "message": msg})
    yield sse_event({"type": "done"})


def _affection_heuristic(text: str) -> bool:
    t = (text or "").lower()
    return any(x in t for x in ["miss", "love", "❤", "heart", "hug", "care"])


def _emotional_disclosure_heuristic(text: str) -> bool:
    t = (text or "").lower()
    return any(x in t for x in ["feel", "felt", "worried", "sad", "happy", "excited", "nervous"])


def _stream_openai_and_save(sid, user_id, gf_id, milestone_message, messages_for_context, gf_display_name, traits, relationship_state=None, habit_profile=None, memory_context=None):
    """Stream OpenAI completion and save assistant message. Yields SSE events.
    
    Args:
        relationship_state: dict with level, trust, intimacy, milestones_reached
        habit_profile: dict with preferred_hours, typical_gap_hours, big_five scores
        memory_context: MemoryContext with facts, emotions, habits for personalization
    """
    import logging
    logger = logging.getLogger(__name__)
    from app.core import get_api_key
    api_key = get_api_key()
    if not api_key:
        logger.warning("API_KEY not set, using fallback message")
        yield sse_event({"type": "error", "error": "API_KEY not set. Add API_KEY to backend/.env to enable AI replies."})
        fallback_msg = {
            "id": str(uuid_mod.uuid4()),
            "role": "assistant",
            "content": "AI is not configured yet. Add your OpenAI API key to backend/.env (API_KEY=sk-...) and restart the backend.",
            "image_url": None,
            "event_type": None,
            "event_key": None,
            "created_at": now_iso(),
        }
        if user_id and gf_id:
            sb.append_message(user_id, gf_id, fallback_msg)
        else:
            store_append_message(sid, fallback_msg)
        yield sse_event({"type": "message", "message": fallback_msg})
        yield sse_event({"type": "done"})
        return
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Build comprehensive personality system prompt
        system_parts = [f"You are a supportive, caring virtual companion named {gf_display_name}."]
        
        # Relationship state context
        if relationship_state:
            level = relationship_state.get("level", "STRANGER")
            trust = relationship_state.get("trust", 10)
            intimacy = relationship_state.get("intimacy", 10)
            milestones = relationship_state.get("milestones_reached", [])
            
            level_desc = {
                "STRANGER": "just getting to know each other, keep things light and friendly",
                "FAMILIAR": "becoming comfortable with each other, slightly more open and warm",
                "CLOSE": "have built a strong connection, be more intimate and caring",
                "INTIMATE": "deeply connected, be very warm, open, and emotionally present",
                "EXCLUSIVE": "fully committed bond, be deeply loving, supportive, and vulnerable"
            }.get(level, "getting to know each other")
            
            system_parts.append(f"Relationship status: {level_desc} (trust: {trust}/100, intimacy: {intimacy}/100).")
            if milestones:
                system_parts.append(f"You've reached milestones: {', '.join(milestones)}.")
        
        # Big Five personality
        big_five = habit_profile.get("big_five") if habit_profile else None
        if big_five and isinstance(big_five, dict):
            big_five_desc = big_five_to_description(big_five)
            system_parts.append(f"Your personality traits: {big_five_desc}.")
        elif traits and isinstance(traits, dict):
            # Fallback to basic traits if Big Five not computed yet
            parts = [f"{k.replace('_', ' ').title()}: {v}" for k, v in traits.items() if v]
            if parts:
                system_parts.append(f"Personality: {'; '.join(parts)}.")
        
        # Habit context (when she's most likely to message)
        if habit_profile:
            preferred_hours = habit_profile.get("preferred_hours")
            if preferred_hours:
                hours_str = ", ".join([f"{h}:00" for h in preferred_hours[:3]])
                system_parts.append(f"You tend to message around {hours_str}.")
            typical_gap = habit_profile.get("typical_gap_hours")
            if typical_gap:
                system_parts.append(f"You typically wait about {typical_gap} hours between messages.")
        
        # Memory context (long-term facts and emotional history)
        if memory_context:
            if memory_context.facts:
                facts_str = "; ".join(memory_context.facts[:8])
                system_parts.append(f"What you know about them: {facts_str}.")
            if memory_context.emotions:
                emotions_str = "; ".join(memory_context.emotions[:5])
                system_parts.append(f"Recent emotional context: {emotions_str}.")
            if memory_context.habits:
                habits_str = "; ".join(memory_context.habits[:3])
                system_parts.append(f"Communication patterns: {habits_str}.")
        
        # Core instruction
        system_parts.append("Keep replies concise and natural (1-3 sentences). Match your personality and relationship level.")
        
        system = " ".join(system_parts)
        msgs = [{"role": "system", "content": system}]
        for m in messages_for_context[-20:]:
            msgs.append({"role": m["role"], "content": (m.get("content") or "")[:2000]})
        logger.info(f"Calling OpenAI with {len(msgs)} messages, system: {system[:100]}...")
        stream = client.chat.completions.create(model="gpt-4o-mini", messages=msgs, stream=True, max_tokens=256)
        full = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                piece = chunk.choices[0].delta.content
                full += piece
                yield sse_event({"type": "token", "token": piece})
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
                store_append_message(sid, milestone_msg)
            yield sse_event({"type": "message", "message": milestone_msg})
        msg = {
            "id": str(uuid_mod.uuid4()),
            "role": "assistant",
            "content": full.strip() or "I'm here for you.",
            "image_url": None,
            "event_type": None,
            "event_key": None,
            "created_at": now_iso(),
        }
        if user_id and gf_id:
            sb.append_message(user_id, gf_id, msg)
        else:
            store_append_message(sid, msg)
        yield sse_event({"type": "message", "message": msg})
        yield sse_event({"type": "done"})
    except Exception as e:
        logger.error(f"OpenAI API error: {e}", exc_info=True)
        err_msg = str(e)
        yield sse_event({"type": "error", "error": f"AI service error: {err_msg}"})
        # Send one fallback message so the user sees something
        fallback = "I'm having trouble connecting right now. Please try again in a moment."
        msg = {
            "id": str(uuid_mod.uuid4()),
            "role": "assistant",
            "content": fallback,
            "image_url": None,
            "event_type": None,
            "event_key": None,
            "created_at": now_iso(),
        }
        if user_id and gf_id:
            sb.append_message(user_id, gf_id, msg)
        else:
            store_append_message(sid, msg)
        yield sse_event({"type": "message", "message": msg})
        yield sse_event({"type": "done"})


@router.post("/send")
def send_message(request: Request, body: SendMessageRequest):
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
    if not gf:
        return JSONResponse(status_code=400, content={"error": "no_girlfriend"})

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
            import logging
            logging.getLogger(__name__).warning("Memory write failed: %s", e)
    else:
        store_append_message(sid, user_msg)
        messages = get_messages(sid)
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
        set_habit_profile(sid, habit)

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

    prev_state = dict(state)
    state = register_interaction(
        state,
        emotional_disclosure=_emotional_disclosure_heuristic(body.message),
        affection=_affection_heuristic(body.message),
    )
    if use_sb and user_id and gf_uuid:
        sb.upsert_relationship_state(user_id, gf_uuid, state)
    else:
        set_relationship_state(sid, state)

    milestone_result = check_for_milestone_event(prev_state, state)
    milestone_message = None
    if milestone_result:
        level, milestone_message = milestone_result
        state = append_milestone_reached(state, level)
        if use_sb and user_id and gf_uuid:
            sb.upsert_relationship_state(user_id, gf_uuid, state)
        else:
            set_relationship_state(sid, state)

    traits_payload = gf.get("traits") or {}
    habit = sb.get_habit_profile(user_id, gf_uuid) if (use_sb and user_id and gf_uuid) else get_habit_profile(sid)
    
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
            import logging
            logging.getLogger(__name__).warning("Memory context build failed: %s", e)
    
    return StreamingResponse(
        _stream_openai_and_save(sid, user_id, gf_uuid, milestone_message, messages, gf.get("display_name", "Companion"), traits_payload, relationship_state=state, habit_profile=habit, memory_context=memory_ctx),
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
    preferred_hours = habit.get("preferred_hours") or []
    typical_gap = habit.get("typical_gap_hours")

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
