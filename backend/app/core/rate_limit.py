"""In-memory rate limiter: 30 requests/minute per key (token or IP)."""
import time
from collections import defaultdict

# key -> list of request timestamps (we prune older than 1 min)
_buckets: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_PER_MINUTE = 30
WINDOW_SECONDS = 60


def _prune(bucket: list[float]) -> None:
    now = time.monotonic()
    cutoff = now - WINDOW_SECONDS
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)


def check_rate_limit(key: str) -> tuple[bool, int]:
    """
    Returns (allowed, retry_after_seconds).
    If not allowed, retry_after_seconds is seconds until a slot frees up.
    """
    now = time.monotonic()
    bucket = _buckets[key]
    _prune(bucket)
    if len(bucket) >= RATE_LIMIT_PER_MINUTE:
        # Oldest request in window will expire in this many seconds
        retry_after = max(1, int(bucket[0] + WINDOW_SECONDS - now))
        return False, retry_after
    bucket.append(now)
    return True, 0
