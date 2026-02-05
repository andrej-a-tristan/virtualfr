"""Mock model server: GET /mock-model/stream?text=... (legacy) and POST /v1/chat/completions (OpenAI-like)."""
import asyncio
import json
from urllib.parse import unquote
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/mock-model", tags=["mock-model"])

# OpenAI-compatible completions (mount at "" so path is /v1/chat/completions)
router_completions = APIRouter(prefix="/v1/chat", tags=["openai-compat"])

CHUNK_DELAY = 0.05
MOCK_ID = "chatcmpl-mock"


class OpenAIMessage(BaseModel):
    role: str
    content: str


class OpenAICompletionsRequest(BaseModel):
    model: str = "mock"
    messages: list[OpenAIMessage] = Field(default_factory=list)
    stream: bool = True


def _text_from_messages(messages: list[dict[str, Any]]) -> str:
    """Join user message contents; use for mock reply."""
    parts = [m["content"] for m in messages if m.get("role") == "user" and m.get("content")]
    return " ".join(parts).strip() or "Hello"


async def stream_mock_reply_gateway(messages: list[dict[str, Any]]):
    """Yield gateway-format SSE (event: token / event: done) for use by chat gateway in-process."""
    text = _text_from_messages(messages)
    reply = f"Mock reply: {text}" if text else "Mock reply: Hello"
    async for event in _stream_tokens(reply):
        yield event


async def _stream_openai_chunks(text: str):
    """Yield OpenAI-style SSE lines: data: {chunk} then data: [DONE]."""
    if not text.strip():
        text = " "
    chunks = []
    for word in text.split():
        for i in range(0, len(word), 2):
            chunks.append(word[i : i + 2])
        chunks.append(" ")
    if chunks and chunks[-1] == " ":
        chunks.pop()
    for token in chunks:
        chunk = {
            "id": MOCK_ID,
            "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": {"content": token}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        await asyncio.sleep(CHUNK_DELAY)
    yield "data: [DONE]\n\n"


async def _stream_tokens(text: str):
    """Yield SSE events: token events then done (legacy format)."""
    if not text.strip():
        chunks = [" "]
    else:
        chunks = []
        for word in text.split():
            for i in range(0, len(word), 2):
                chunks.append(word[i : i + 2])
            chunks.append(" ")
        if chunks and chunks[-1] == " ":
            chunks.pop()
    for token in chunks:
        yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
        await asyncio.sleep(CHUNK_DELAY)
    yield "event: done\ndata: {\"finish_reason\":\"stop\"}\n\n"


@router.get("/stream")
async def mock_stream(text: str = Query(..., description="Text to stream as tokens")):
    """Stream the given text as SSE token events (legacy; backward compatible)."""
    decoded = unquote(text) if text else ""
    return StreamingResponse(
        _stream_tokens(decoded),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router_completions.post("/completions")
async def openai_completions(body: OpenAICompletionsRequest):
    """OpenAI-like chat completions: stream=true returns SSE; stream=false returns JSON."""
    user_text = _text_from_messages([m.model_dump() for m in body.messages])
    reply = f"Mock reply: {user_text}" if user_text else "Mock reply: Hello"

    if body.stream:
        return StreamingResponse(
            _stream_openai_chunks(reply),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    return {
        "id": MOCK_ID,
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": reply},
                "finish_reason": "stop",
            }
        ],
    }
