"""Time utilities: hours since, etc."""
from datetime import datetime, timezone
from typing import Optional


def hours_since(iso_timestamp: Optional[str]) -> float:
    """Return hours since the given ISO timestamp, or 0 if None/invalid."""
    if not iso_timestamp:
        return 0.0
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - dt
        return max(0.0, delta.total_seconds() / 3600.0)
    except (ValueError, TypeError):
        return 0.0


def now_iso() -> str:
    """Current time in ISO format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
