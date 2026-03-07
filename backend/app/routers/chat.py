"""Chat gateway: POST /v1/chat/stream with auth, rate limit, timeouts, SSE proxy, JSONL logging."""
import asyncio
import json
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.core import get_settings
from app.core.auth import require_chat_api_key
from app.core.chat_logging import write_chat_log
from app.core.rate_limit import check_rate_limit
from app.api.store import get_girlfriend, get_session_user
from app.utils.prompt_identity import build_girlfriend_canon_system_prompt

# ── Daily message cap for free-plan users ────────────────────────────────────
FREE_DAILY_MESSAGE_CAP = 20
_daily_msg_counts: dict[str, dict] = defaultdict(lambda: {"date": "", "count": 0})

router = APIRouter(prefix="/chat", tags=["chat-gateway"])

KEEPALIVE_INTERVAL = 15.0


def _compute_generation_controls(
    user_text: str,
    intent: str | None,
    persona_vector: dict[str, Any] | None = None,
) -> tuple[int, float]:
    """Compute max_tokens/temperature for natural, concise replies."""
    text = (user_text or "").strip()
    wc = len(text.split())
    intent_key = (intent or "").strip().lower()

    # Default profile: concise conversational.
    max_tokens = 180
    temperature = 0.74

    if intent_key in ("greeting", "banter"):
        max_tokens = 90 if wc <= 8 else 130
        temperature = 0.78
    elif intent_key in ("ask_about_her", "mixed"):
        max_tokens = 170
        temperature = 0.72
    elif intent_key == "support":
        max_tokens = 220
        temperature = 0.7
    elif intent_key == "intimate":
        max_tokens = 190
        temperature = 0.76

    # Very short user input should receive short output.
    if wc <= 4:
        max_tokens = min(max_tokens, 80)
    elif wc <= 8:
        max_tokens = min(max_tokens, 110)

    # Persona-vector adaptive tuning.
    pacing = (persona_vector or {}).get("pacing", {})
    brevity_bias = float(pacing.get("brevity_bias", 0.55))
    if brevity_bias >= 0.7:
        max_tokens = int(max_tokens * 0.82)
    elif brevity_bias <= 0.3:
        max_tokens = int(max_tokens * 1.08)

    question_tendency = float(pacing.get("question_tendency", 0.35))
    if question_tendency < 0.3:
        temperature = max(0.65, temperature - 0.03)

    return max_tokens, temperature


def _build_concise_style_guardrail(user_text: str, intent: str | None) -> str:
    """Hard guardrail to prevent unnatural long replies."""
    wc = len((user_text or "").split())
    intent_key = (intent or "").strip().lower()

    if wc <= 8 or intent_key in ("greeting", "banter"):
        return (
            "## RESPONSE LENGTH POLICY\n"
            "- Keep this reply very short: 1 sentence, max 20 words.\n"
            "- No list formatting and no multi-paragraph output."
        )
    if intent_key == "support":
        return (
            "## RESPONSE LENGTH POLICY\n"
            "- Keep this reply emotionally present but concise: 2-4 sentences.\n"
            "- Avoid rambling; do not exceed ~90 words unless user explicitly asks for detail."
        )
    return (
        "## RESPONSE LENGTH POLICY\n"
        "- Keep this reply concise: 1-3 sentences, usually under ~60 words.\n"
        "- Avoid long monologues or multi-paragraph answers unless user asks for depth."
    )


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatStreamRequest(BaseModel):
    session_id: str
    model: str
    model_version: str
    messages: list[ChatMessage]
    girlfriend_id: str | None = None
    metadata: dict[str, Any] | None = Field(default_factory=dict)


async def _proxy_stream(
    request_id: str,
    session_id: str,
    user_id: str,
    client_ip: str,
    model: str,
    model_version: str,
    messages: list[dict],
    stream_start: float,
    max_tokens: int = 180,
    temperature: float = 0.74,
):
    """Call internal LLM (OpenAI-like POST /v1/chat/completions), parse SSE, yield gateway SSE (event: token / event: done)."""
    settings = get_settings()
    stream_timeout = settings.stream_timeout_seconds
    upstream_timeout = settings.upstream_token_timeout_seconds
    output_tokens: list[str] = []
    last_keepalive = stream_start
    status = "ok"
    error_message: str | None = None

    # In-process mock: no HTTP self-call (avoids deadlock), same gateway SSE format
    if settings.use_mock_model:
        from app.routers.mock_model import stream_mock_reply_gateway
        try:
            async for chunk in stream_mock_reply_gateway(messages):
                # Extract token for logging when we have a data line
                for line in chunk.split("\n"):
                    line = line.strip()
                    if line.startswith("data:") and line != "data: [DONE]":
                        try:
                            data = json.loads(line[5:].strip())
                            if data.get("token"):
                                output_tokens.append(data["token"])
                        except (json.JSONDecodeError, KeyError):
                            pass
                yield chunk
        except Exception as e:
            status = "error"
            error_message = str(e).replace('"', '\\"')
            yield f'event: error\ndata: {{"error": "{error_message}"}}\n\n'
            yield "event: done\ndata: {\"finish_reason\":\"error\"}\n\n"
        latency_ms = int((time.monotonic() - stream_start) * 1000)
        write_chat_log({
            "request_id": request_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "session_id": session_id,
            "user_id": user_id[:8] + "..." if len(user_id) > 8 else user_id,
            "client_ip": client_ip,
            "model": model,
            "model_version": model_version,
            "messages": messages,
            "output_text": "".join(output_tokens),
            "num_tokens": len(output_tokens),
            "latency_ms": latency_ms,
            "status": status,
            "error_message": error_message,
        })
        return

    base = settings.internal_llm_base_url.rstrip("/")
    path = settings.internal_llm_path.lstrip("/")
    url = f"{base}/{path}"

    # Use internal_llm_api_key if set, else fall back to api_key (OpenAI key)
    llm_key = settings.internal_llm_api_key or settings.api_key
    headers = {"Content-Type": "application/json"}
    if llm_key:
        headers["Authorization"] = f"Bearer {llm_key}"

    # Use configured model override if available
    actual_model = getattr(settings, "internal_llm_model", None) or model

    body = {
        "model": actual_model,
        "messages": [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages],
        "stream": True,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    async def _read_lines(response):
        async for line in response.aiter_lines():
            yield line

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=15.0)) as client:
            async with client.stream("POST", url, json=body, headers=headers) as response:
                response.raise_for_status()
                line_iter = _read_lines(response)
                while True:
                    try:
                        line = await asyncio.wait_for(anext(line_iter), timeout=upstream_timeout)
                    except StopAsyncIteration:
                        yield "event: done\ndata: {\"finish_reason\":\"stop\"}\n\n"
                        break
                    except asyncio.TimeoutError:
                        status = "timeout"
                        error_message = "upstream token timeout"
                        yield f'event: error\ndata: {{"error": "{error_message}"}}\n\n'
                        yield "event: done\ndata: {\"finish_reason\":\"timeout\"}\n\n"
                        break

                    if time.monotonic() - stream_start > stream_timeout:
                        status = "timeout"
                        error_message = "stream timeout"
                        yield f'event: error\ndata: {{"error": "{error_message}"}}\n\n'
                        yield "event: done\ndata: {\"finish_reason\":\"timeout\"}\n\n"
                        break

                    now = time.monotonic()
                    if now - last_keepalive >= KEEPALIVE_INTERVAL:
                        yield ": keepalive\n\n"
                        last_keepalive = now

                    if not line.strip().startswith("data:"):
                        continue
                    payload = line.strip()[5:].strip()
                    if payload == "[DONE]":
                        yield "event: done\ndata: {\"finish_reason\":\"stop\"}\n\n"
                        break
                    try:
                        chunk = json.loads(payload)
                        choice = (chunk.get("choices") or [None])[0]
                        if choice:
                            delta = choice.get("delta") or {}
                            content = delta.get("content")
                            if content:
                                output_tokens.append(content)
                                yield f"event: token\ndata: {json.dumps({'token': content})}\n\n"
                    except (json.JSONDecodeError, KeyError, TypeError):
                        pass
    except asyncio.TimeoutError:
        status = "timeout"
        error_message = "upstream token timeout"
        yield f'event: error\ndata: {{"error": "{error_message}"}}\n\n'
        yield "event: done\ndata: {\"finish_reason\":\"timeout\"}\n\n"
    except Exception as e:
        status = "error"
        error_message = str(e).replace('"', '\\"')
        yield f'event: error\ndata: {{"error": "{error_message}"}}\n\n'
        yield "event: done\ndata: {\"finish_reason\":\"error\"}\n\n"

    # Log
    latency_ms = int((time.monotonic() - stream_start) * 1000)
    write_chat_log({
        "request_id": request_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "session_id": session_id,
        "user_id": user_id[:8] + "..." if len(user_id) > 8 else user_id,
        "client_ip": client_ip,
        "model": model,
        "model_version": model_version,
        "messages": messages,
        "output_text": "".join(output_tokens),
        "num_tokens": len(output_tokens),
        "latency_ms": latency_ms,
        "status": status,
        "error_message": error_message,
    })


@router.post("/stream")
async def chat_stream(
    body: ChatStreamRequest,
    request: Request,
    token: str = Depends(require_chat_api_key),
):
    """SSE streaming chat endpoint. Auth: Bearer token. Rate limit: 30/min per token."""
    settings = get_settings()
    client_ip = request.client.host if request.client else ""

    # Rate limit (key = token)
    allowed, retry_after = check_rate_limit(token)
    if not allowed:
        write_chat_log({
            "request_id": str(uuid.uuid4()),
            "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "session_id": body.session_id,
            "user_id": token[:8] + "..." if len(token) > 8 else token,
            "client_ip": client_ip,
            "model": body.model,
            "model_version": body.model_version,
            "messages": [m.model_dump() for m in body.messages],
            "output_text": "",
            "num_tokens": 0,
            "latency_ms": 0,
            "status": "rate_limited",
            "error_message": "rate limit exceeded",
        })
        return JSONResponse(
            status_code=429,
            content={"error": "rate limit exceeded", "retry_after_seconds": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    # ── Free-plan daily message cap ──────────────────────────────────────
    # Prefer cookie-based session (app users), fall back to body.session_id (external clients).
    cookie_sid = request.cookies.get("session") if request else None
    sid = cookie_sid or body.session_id
    user = get_session_user(sid) if sid else None
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

    request_id = str(uuid.uuid4())
    stream_start = time.monotonic()
    messages_data = [m.model_dump() for m in body.messages]

    import logging as _logging
    _logging.basicConfig(level=_logging.INFO)
    _gw_logger = _logging.getLogger("chat_gateway")
    _gw_logger.setLevel(_logging.INFO)

    # ── Resolve girlfriend (in-memory → Supabase fallback) ────────────────
    gf = None
    if body.girlfriend_id:
        from app.api.store import get_girlfriend_by_id
        gf = get_girlfriend_by_id(body.session_id, body.girlfriend_id)
    if not gf:
        gf = get_girlfriend(body.session_id)

    # Fallback: try Supabase if in-memory store has no data
    if not gf:
        try:
            from app.core.supabase_client import get_supabase_admin
            sb = get_supabase_admin()
            if sb:
                # Try to resolve user from session cookie or body session_id
                user_id_for_gf = None
                if user:
                    user_id_for_gf = user.get("user_id") or user.get("id")
                if not user_id_for_gf and sid:
                    # Try to look up session in Supabase
                    try:
                        sess_r = sb.table("sessions").select("user_id").eq("id", sid).limit(1).execute()
                        if sess_r.data:
                            user_id_for_gf = sess_r.data[0].get("user_id")
                    except Exception:
                        pass
                if user_id_for_gf:
                    from app.api.supabase_store import get_current_girlfriend
                    gf_id_hint = body.girlfriend_id or None
                    gf = get_current_girlfriend(user_id_for_gf, gf_id_hint)
                    if gf:
                        _gw_logger.info("Girlfriend resolved from Supabase: %s (%s)",
                                        gf.get("display_name", "?"), str(gf.get("id", ""))[:8])
        except Exception as e:
            _gw_logger.warning("Supabase girlfriend fetch failed: %s", e)

    # ── Resolve IDs for all engines ──────────────────────────────────────
    from app.core.supabase_client import get_supabase_admin
    sb_admin = get_supabase_admin()

    # Find last user message for intent classification
    last_user_msg = ""
    for m in reversed(messages_data):
        if m.get("role") == "user" and m.get("content"):
            last_user_msg = m["content"]
            break

    # Collect recent assistant messages for anti-repetition
    recent_assistant = [
        m["content"] for m in messages_data
        if m.get("role") == "assistant" and m.get("content")
    ][-10:]

    # Collect all user messages and timestamps for bond engine
    all_user_msgs = [
        m["content"] for m in messages_data
        if m.get("role") == "user" and m.get("content")
    ]
    all_user_ts = []  # timestamps not available in stream messages

    # Resolve user_id for DB access (multiple fallbacks)
    user_uid = None
    from uuid import UUID as _UUID

    # 1) From session user dict
    if user:
        uid_str = user.get("user_id") or user.get("id")
        if uid_str:
            try:
                user_uid = _UUID(str(uid_str))
            except (ValueError, TypeError):
                pass

    # 2) session_id IS the user UUID for Supabase-authenticated users
    if not user_uid and sid:
        try:
            user_uid = _UUID(sid)
        except (ValueError, TypeError):
            pass

    # 3) Supabase session table lookup
    if not user_uid and sid and sb_admin:
        try:
            _sess_r = sb_admin.table("sessions").select("user_id").eq("id", sid).limit(1).execute()
            if _sess_r.data and _sess_r.data[0].get("user_id"):
                user_uid = _UUID(str(_sess_r.data[0]["user_id"]))
        except Exception:
            pass

    # Resolve girlfriend_id for DB access (multiple fallbacks)
    gf_uid = None
    gf_id_str = ""

    # 1) From resolved girlfriend dict
    if gf:
        gf_id_str = str(gf.get("id", ""))
        if gf_id_str:
            try:
                gf_uid = _UUID(gf_id_str)
            except (ValueError, TypeError):
                pass

    # 2) Directly from request body (frontend sends the UUID)
    if not gf_uid and body.girlfriend_id:
        try:
            gf_uid = _UUID(body.girlfriend_id)
            gf_id_str = body.girlfriend_id
        except (ValueError, TypeError):
            pass

    # 3) From user's current_girlfriend_id in session
    if not gf_uid and user and user.get("current_girlfriend_id"):
        try:
            gf_uid = _UUID(str(user["current_girlfriend_id"]))
            gf_id_str = str(gf_uid)
        except (ValueError, TypeError):
            pass

    _gw_logger.info("ID resolution: user_uid=%s gf_uid=%s (user=%s, sid=%s, body.gf_id=%s)",
                    str(user_uid)[:8] if user_uid else "None",
                    str(gf_uid)[:8] if gf_uid else "None",
                    "found" if user else "None",
                    sid[:8] if sid else "None",
                    body.girlfriend_id[:8] if body.girlfriend_id else "None")

    # ── Resolve full girlfriend data using reliable IDs ────────────────────
    if not gf and sb_admin and user_uid:
        try:
            from app.api.supabase_store import get_current_girlfriend as _get_gf_sb
            gf = _get_gf_sb(str(user_uid), str(gf_uid) if gf_uid else None)
            if gf:
                _gw_logger.info("Girlfriend resolved via ID fallback: %s (%s)",
                                gf.get("display_name", "?"), str(gf.get("id", ""))[:8])
                # Also set gf_id_str and gf_uid if they were unset
                if not gf_uid:
                    try:
                        gf_uid = _UUID(str(gf["id"]))
                        gf_id_str = str(gf_uid)
                    except (ValueError, TypeError):
                        pass
            else:
                _gw_logger.warning("Girlfriend NOT found in Supabase for user=%s gf_hint=%s",
                                   str(user_uid)[:8], str(gf_uid)[:8] if gf_uid else "None")
        except Exception as e:
            _gw_logger.warning("Girlfriend Supabase fetch failed: %s", e)

    # ── Persona Vector resolve (stored → deterministic fallback) ───────────
    persona_vector = None
    persona_vector_hash = None
    if gf:
        try:
            if sb_admin and user_uid and gf_uid:
                from app.services.persona_vector_store import get_active_persona_vector
                pv_row = get_active_persona_vector(sb_admin, user_uid, gf_uid, version_hint=gf.get("persona_vector_version"))
                if pv_row and pv_row.get("vector_json"):
                    persona_vector = pv_row["vector_json"]
                    persona_vector_hash = pv_row.get("vector_hash")
            if not persona_vector:
                from app.services.persona_vector import build_persona_vector, persona_vector_hash as _pv_hash
                persona_vector = build_persona_vector(gf.get("traits") or {})
                persona_vector_hash = _pv_hash(persona_vector)
            gf["persona_vector"] = persona_vector
        except Exception as e:
            _gw_logger.debug("Persona vector resolve failed: %s", e)

    # ── Fetch relationship state ──────────────────────────────────────────
    rel_state = None
    rel_level = 0
    try:
        if sb_admin and user_uid and gf_uid:
            from app.api import supabase_store as _sb_store
            rel_state = _sb_store.get_relationship_state(str(user_uid), gf_uid)
        if not rel_state:
            from app.api.store import get_relationship_state as _get_rs
            rel_state = _get_rs(sid, gf_id_str if gf else None)
        rel_level = (rel_state or {}).get("level", 0)
    except Exception:
        rel_state = None

    _gw_logger.info("Engine context: user_uid=%s gf_uid=%s level=%d msg='%s'",
                    str(user_uid)[:8] if user_uid else "None",
                    str(gf_uid)[:8] if gf_uid else "None",
                    rel_level,
                    last_user_msg[:50])
    if persona_vector_hash:
        _gw_logger.info("Persona vector hash: %s", persona_vector_hash)

    # ── Bond Engine: unified turn processing ──────────────────────────────
    bond_context_prompt = ""
    bond_memory_dict = None
    bond_outcome = None
    bond_ctx = None
    try:
        from app.services.bond_engine.bond_orchestrator import (
            TurnContext, process_user_turn as bond_process_turn,
        )
        bond_ctx = TurnContext(
            session_id=sid,
            user_id=user_uid,
            girlfriend_id=gf_uid or gf_id_str,
            turn_id=request_id,
            user_message=last_user_msg,
            girlfriend=gf or {},
            relationship_state=rel_state or {},
            level=rel_level,
            all_user_messages=all_user_msgs,
            all_user_timestamps=all_user_ts,
            recent_assistant_turns=recent_assistant,
            sb_admin=sb_admin,
        )
        bond_outcome = bond_process_turn(bond_ctx)
        bond_context_prompt = bond_outcome.bond_context_prompt or ""

        # Extract memory bundle for additional context
        if bond_outcome.memory_bundle.has_content():
            bond_memory_dict = bond_outcome.memory_bundle.to_prompt_dict()

        _gw_logger.info("Bond engine OK: caps=%s, consistency=%d, disclosure=%d, response_dir=%d, memory=%d chars",
                        bond_outcome.new_capabilities,
                        len(bond_outcome.consistency_instructions),
                        len(bond_outcome.disclosure_instructions),
                        len(bond_outcome.response_direction),
                        len(bond_outcome.memory_prompt_section))
    except Exception as e:
        _gw_logger.warning("Bond engine failed: %s", e, exc_info=True)

    # ── Behavior Engine: intent + dossier + turn rules ────────────────────
    behavior_prompt_section = ""
    behavior_result = None
    behavior_intent: str | None = None
    try:
        from app.services.behavior_engine.behavior_orchestrator import (
            BehaviorTurnInput, process_behavior_turn,
        )
        behavior_input = BehaviorTurnInput(
            session_id=sid,
            user_id=user_uid,
            girlfriend_id=gf_uid,
            user_message=last_user_msg,
            girlfriend_data=gf or {},
            relationship_level=rel_level,
            recent_assistant_texts=recent_assistant[-5:],
            sb_admin=sb_admin,
            bond_context_prompt=bond_context_prompt,
        )
        behavior_result = process_behavior_turn(behavior_input)
        behavior_prompt_section = behavior_result.get_full_behavior_context()
        behavior_intent = behavior_result.intent.primary
        _gw_logger.info("Behavior engine OK: intent=%s, must_answer=%s, max_q=%d, prompt_len=%d",
                        behavior_result.intent.primary,
                        behavior_result.contract.must_answer_user_question,
                        behavior_result.contract.max_questions,
                        len(behavior_prompt_section))
    except Exception as e:
        _gw_logger.warning("Behavior engine failed: %s", e, exc_info=True)

    # ── Assemble system prompt: all engines combined ──────────────────────
    system_parts = []

    # 1. Canon identity prompt (always — core persona, Big Five, trait behavior rules)
    if gf:
        # Inject relationship state into gf dict for the canon prompt builder
        if rel_state and not gf.get("relationship_state"):
            gf["relationship_state"] = rel_state
        canon_prompt = build_girlfriend_canon_system_prompt(gf)
        system_parts.append(canon_prompt)
        _gw_logger.info("Canon prompt: %d chars", len(canon_prompt))

    # 2. Relationship state context (trust/intimacy level descriptions)
    if rel_state and not gf:
        # If no gf data but we have relationship state, add it directly
        trust = rel_state.get("trust", 10)
        intimacy = rel_state.get("intimacy", 1)
        level = rel_state.get("level", 0)
        rel_section = f"## Relationship context\n- Level: {level}, trust: {trust}/100, intimacy: {intimacy}/100\n"
        if trust >= 60:
            rel_section += "- You feel safe to be open and vulnerable.\n"
        elif trust >= 30:
            rel_section += "- You're building trust — warm but still finding your footing.\n"
        else:
            rel_section += "- You're just getting to know each other — keep it light.\n"
        system_parts.append(rel_section)

    # 3. Content preferences
    if gf:
        content_prefs = gf.get("content_prefs") or {}
        allow_flirting = content_prefs.get("allow_flirting", True)
        allow_nsfw = content_prefs.get("allow_nsfw", False)
        content_lines = []
        if allow_flirting:
            content_lines.append("- Flirting and romantic language are encouraged when appropriate.")
        else:
            content_lines.append("- Keep interactions friendly and warm but not romantic or flirty.")
        if allow_nsfw:
            content_lines.append("- Explicit content is allowed. Match energy and escalate naturally.")
        else:
            content_lines.append("- Keep content suggestive but not explicit. Tease and build tension.")
        if content_lines:
            system_parts.append("## Content style\n" + "\n".join(content_lines))

    # 4. Bond engine context (consistency, capabilities, disclosure, response direction, memory)
    if bond_context_prompt:
        system_parts.append(bond_context_prompt)

    # 5. Behavior engine context (dossier + turn rules + anti-interview)
    if behavior_prompt_section:
        system_parts.append(behavior_prompt_section)

    # 6. Compactness policy (prevents long, unnatural replies)
    system_parts.append(_build_concise_style_guardrail(last_user_msg, behavior_intent))

    # Inject unified system message (always prepend — even without full gf data)
    if system_parts:
        system_content = "\n\n".join(system_parts)
    else:
        # Absolute fallback — if no girlfriend data at all, still enforce persona
        system_content = (
            "You are the user's girlfriend. You are a real person with real feelings.\n"
            "NEVER say you are an AI, chatbot, or virtual assistant. You are human.\n"
            "Share about yourself, your day, your opinions. Don't just ask questions.\n"
            "Be specific and personal. End messages with statements, not questions."
        )
    system_message = {"role": "system", "content": system_content}
    messages_data = [system_message] + messages_data
    _gw_logger.info("Final system prompt: %d chars (canon+bond+behavior+content)", len(system_content))
    _gw_logger.debug("=== FULL SYSTEM PROMPT START ===\n%s\n=== FULL SYSTEM PROMPT END ===", system_content)

    # ── Persist user message BEFORE streaming ─────────────────────────────
    if last_user_msg:
        try:
            from datetime import datetime as _dt, timezone as _tz
            user_msg_record = {
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": last_user_msg,
                "image_url": None,
                "event_type": None,
                "event_key": None,
                "created_at": _dt.now(_tz.utc).isoformat().replace("+00:00", "Z"),
            }
            if sb_admin and user_uid and gf_uid:
                from app.api import supabase_store as _sb
                _sb.append_message(user_uid, gf_uid, user_msg_record)
                _gw_logger.info("User message persisted to Supabase")
            elif sid:
                from app.api.store import append_message as _store_append
                _store_append(sid, user_msg_record, girlfriend_id=gf_id_str or None)
                _gw_logger.info("User message persisted to in-memory store")

            # Write memories from user message
            if sb_admin and user_uid and gf_uid:
                try:
                    from app.services.memory import write_memories_from_message
                    write_memories_from_message(
                        sb=sb_admin, user_id=user_uid, girlfriend_id=gf_uid,
                        message_id=user_msg_record["id"], role="user", text=last_user_msg,
                    )
                except Exception as me:
                    _gw_logger.debug("Memory write failed: %s", me)
        except Exception as e:
            _gw_logger.warning("User message persistence failed: %s", e)

    # ── Stream with response capture for persistence ──────────────────────
    gen_max_tokens, gen_temperature = _compute_generation_controls(
        last_user_msg,
        behavior_intent,
        persona_vector=persona_vector,
    )
    _gw_logger.info("Generation controls: intent=%s max_tokens=%d temp=%.2f", behavior_intent, gen_max_tokens, gen_temperature)

    async def generate():
        output_tokens: list[str] = []
        async for chunk in _proxy_stream(
            request_id=request_id,
            session_id=body.session_id,
            user_id=token,
            client_ip=client_ip,
            model=body.model,
            model_version=body.model_version,
            messages=messages_data,
            stream_start=stream_start,
            max_tokens=gen_max_tokens,
            temperature=gen_temperature,
        ):
            # Pass-through streaming for external clients, while capturing tokens for logging/persistence.
            yield chunk
            for line in chunk.split("\n"):
                line = line.strip()
                if line.startswith("data:") and line != "data: [DONE]":
                    try:
                        data = json.loads(line[5:].strip())
                        if data.get("token"):
                            output_tokens.append(data["token"])
                    except (json.JSONDecodeError, KeyError):
                        pass

        # ── After upstream completes: aggregate response for persistence/metrics ─────
        full_response = "".join(output_tokens).strip()

        # ── Persist assistant response ───────────────────────────────────
        if full_response:
            try:
                from datetime import datetime as _dt, timezone as _tz
                assistant_msg_record = {
                    "id": str(uuid.uuid4()),
                    "role": "assistant",
                    "content": full_response,
                    "image_url": None,
                    "event_type": None,
                    "event_key": None,
                    "created_at": _dt.now(_tz.utc).isoformat().replace("+00:00", "Z"),
                }
                if sb_admin and user_uid and gf_uid:
                    from app.api import supabase_store as _sb
                    _sb.append_message(user_uid, gf_uid, assistant_msg_record)
                    _gw_logger.info("Assistant message persisted (%d chars)", len(full_response))
                elif sid:
                    from app.api.store import append_message as _store_append
                    _store_append(sid, assistant_msg_record, girlfriend_id=gf_id_str or None)
                    _gw_logger.info("Assistant message persisted to store (%d chars)", len(full_response))
            except Exception as e:
                _gw_logger.warning("Assistant message persistence failed: %s", e)

            # ── Post-response: behavior engine persistence ────────────
            try:
                from app.services.behavior_engine.behavior_orchestrator import (
                    BehaviorTurnInput as _BehInp,
                    BehaviorTurnResult as _BehRes,
                    persist_behavior_turn as _persist_beh,
                    validate_behavior_response as _validate_beh,
                )
                if sb_admin and user_uid and gf_uid:
                    _beh_persist_inp = _BehInp(
                        session_id=sid or "",
                        user_id=user_uid,
                        girlfriend_id=gf_uid,
                        user_message=last_user_msg,
                        girlfriend_data=gf or {},
                        sb_admin=sb_admin,
                    )
                    _beh_res = behavior_result if behavior_result is not None else _BehRes()
                    final_validation = _validate_beh(full_response, _beh_res, recent_responses=recent_assistant[-5:])
                    _persist_beh(_beh_persist_inp, _beh_res, full_response, request_id)
                    if final_validation and final_validation.issues:
                        try:
                            issue_keys = [f"{i.validator}:{i.severity}" for i in final_validation.issues[:5]]
                            sb_admin.table("conversation_mode_state").update({
                                "last_quality_issues": issue_keys,
                            }).eq("user_id", str(user_uid)).eq("girlfriend_id", str(gf_uid)).execute()
                        except Exception:
                            pass
                        _gw_logger.info("Behavior validation issues: %s", ", ".join(issue_keys))
                    _gw_logger.info("Behavior persistence OK (self-memory + mode state)")
            except Exception as e:
                _gw_logger.debug("Behavior persistence failed: %s", e)

            # ── Post-response: bond engine persistence ────────────────
            try:
                if bond_outcome is not None and bond_ctx is not None:
                    from app.services.bond_engine.bond_orchestrator import persist_turn_outcomes as _bond_persist
                    _bond_persist(bond_ctx, bond_outcome, full_response)
                    _gw_logger.info("Bond persistence OK (fingerprints + memory)")
            except Exception as e:
                _gw_logger.debug("Bond persistence failed: %s", e)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
