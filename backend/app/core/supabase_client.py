"""
Supabase client for FastAPI. Uses env vars SUPABASE_URL and SUPABASE_ANON_KEY (and optionally SUPABASE_SERVICE_ROLE_KEY).
Returns None if not configured (app can fall back to in-memory store).
"""
from typing import TYPE_CHECKING

from app.core.config import get_settings

if TYPE_CHECKING:
    from supabase import Client

_supabase: "Client | None" = None
_supabase_admin: "Client | None" = None


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


def get_supabase_admin() -> "Client | None":
    """Return Supabase client with service role key (for auth admin + DB). Use server-side only."""
    global _supabase_admin
    if _supabase_admin is not None:
        return _supabase_admin
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    from supabase import create_client
    _supabase_admin = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _supabase_admin


def is_supabase_configured() -> bool:
    """Return True if Supabase env vars are set."""
    settings = get_settings()
    return bool(settings.supabase_url and settings.supabase_anon_key)
