"""Chat: history, state, send (SSE stream)."""
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from app.schemas.chat import SendMessageRequest, ChatMessage, RelationshipState
from app.api.store import get_session_user, get_girlfriend
from app.utils.sse import sse_event

router = APIRouter(prefix="/chat", tags=["chat"])


def _session_id(request: Request) -> str | None:
    return request.cookies.get("session")


# Deterministic mock history
def _mock_history():
    return [
        {"id": "m1", "role": "user", "content": "Hey, how are you?", "image_url": None, "event_type": None, "created_at": "2025-01-01T12:00:00Z"},
        {"id": "m2", "role": "assistant", "content": "I'm doing great! Thanks for asking. How about you?", "image_url": None, "event_type": None, "created_at": "2025-01-01T12:00:01Z"},
        {"id": "m3", "role": "assistant", "content": None, "image_url": "https://picsum.photos/400/400", "event_type": None, "created_at": "2025-01-01T12:05:00Z"},
        {"id": "m4", "role": "assistant", "content": "We just reached a new level! 💕", "image_url": None, "event_type": "milestone", "created_at": "2025-01-01T12:10:00Z"},
    ]


@router.get("/history")
def chat_history(request: Request):
    sid = _session_id(request)
    if not sid or not get_session_user(sid):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    messages = _mock_history()
    return {"messages": [ChatMessage(**m) for m in messages]}


@router.get("/state")
def chat_state(request: Request):
    sid = _session_id(request)
    if not sid or not get_session_user(sid):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    return RelationshipState(
        trust=72,
        intimacy=65,
        level=3,
        last_interaction_at="2025-01-01T12:10:00Z",
    )


def _stream_tokens():
    """Yield SSE events: token, token, ..., message, done."""
    tokens = ["I ", "had ", "a ", "great ", "day! ", "How ", "was ", "yours?"]
    for t in tokens:
        yield sse_event({"type": "token", "token": t})
    msg = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": "".join(tokens),
        "image_url": None,
        "event_type": None,
        "created_at": "2025-01-31T12:00:00Z",
    }
    yield sse_event({"type": "message", "message": msg})
    yield sse_event({"type": "done"})


@router.post("/send")
def send_message(request: Request, body: SendMessageRequest):
    sid = _session_id(request)
    if not sid or not get_session_user(sid):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    return StreamingResponse(
        _stream_tokens(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
