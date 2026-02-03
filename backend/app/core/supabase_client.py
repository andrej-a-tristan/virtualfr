"""
Supabase client for FastAPI. Uses env vars SUPABASE_URL and SUPABASE_ANON_KEY.
Returns None if not configured (app can fall back to in-memory store).
"""
from typing import TYPE_CHECKING

from app.core.config import get_settings

if TYPE_CHECKING:
    from supabase import Client

_supabase: "Client | None" = None


def get_supabase() -> "Client | None":
    """Return Supabase client if SUPABASE_URL and SUPABASE_ANON_KEY are set, else None."""
    global _supabase
    if _supabase is not None:
        return _supabase
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        return None
    from supabase import create_client
    _supabase = create_client(settings.supabase_url, settings.supabase_anon_key)
    return _supabase


def is_supabase_configured() -> bool:
    """Return True if Supabase env vars are set."""
    settings = get_settings()
    return bool(settings.supabase_url and settings.supabase_anon_key)
