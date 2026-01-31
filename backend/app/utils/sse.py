"""SSE (Server-Sent Events) helpers."""
import json
from typing import Any


def sse_event(data: dict[str, Any]) -> str:
    """Format a single SSE event line: data: {json}\\n\\n"""
    return f"data: {json.dumps(data)}\n\n"
