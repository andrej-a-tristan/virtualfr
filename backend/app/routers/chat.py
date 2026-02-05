"""Chat gateway: POST /v1/chat/stream with auth, rate limit, timeouts, SSE proxy, JSONL logging."""
import asyncio
import json
import time
import uuid
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
from app.api.store import get_girlfriend
from app.utils.prompt_identity import build_girlfriend_canon_system_prompt

router = APIRouter(prefix="/chat", tags=["chat-gateway"])

KEEPALIVE_INTERVAL = 15.0


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatStreamRequest(BaseModel):
    session_id: str
    model: str
    model_version: str
    messages: list[ChatMessage]
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

    headers = {"Content-Type": "application/json"}
    if settings.internal_llm_api_key:
        headers["Authorization"] = f"Bearer {settings.internal_llm_api_key}"

    body = {
        "model": model,
        "messages": [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages],
        "stream": True,
    }

    async def _read_lines(response):
        async for line in response.aiter_lines():
            yield line

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(upstream_timeout)) as client:
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

    request_id = str(uuid.uuid4())
    stream_start = time.monotonic()
    messages_data = [m.model_dump() for m in body.messages]

    # Inject girlfriend canon system prompt if available
    gf = get_girlfriend(body.session_id)
    if gf and (gf.get("identity") or gf.get("identity_canon")):
        canon_prompt = build_girlfriend_canon_system_prompt(gf)
        canon_message = {"role": "system", "content": canon_prompt}
        # Prepend canon system message (keep any existing messages after)
        messages_data = [canon_message] + messages_data

    async def generate():
        async for chunk in _proxy_stream(
            request_id=request_id,
            session_id=body.session_id,
            user_id=token,
            client_ip=client_ip,
            model=body.model,
            model_version=body.model_version,
            messages=messages_data,
            stream_start=stream_start,
        ):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
