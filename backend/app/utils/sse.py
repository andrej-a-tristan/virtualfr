"""SSE (Server-Sent Events) helpers."""
import json
from typing import Any


def sse_event(data: dict[str, Any]) -> str:
    """Format a single SSE event with proper 'event:' line when type is present.

    Produces standard SSE format:
        event: <type>
        data: <json>

    The frontend SSE parser expects 'event: token' / 'event: done' lines.
    """
    event_type = data.get("type", "")
    json_str = json.dumps(data)
    if event_type:
        return f"event: {event_type}\ndata: {json_str}\n\n"
    return f"data: {json_str}\n\n"
