"""
Supabase client for FastAPI. Uses env vars SUPABASE_URL and SUPABASE_ANON_KEY.
Returns None if not configured (app can fall back to in-memory store).
"""
import logging
from typing import TYPE_CHECKING

from app.core.config import get_settings

if TYPE_CHECKING:
    from supabase import Client

logger = logging.getLogger(__name__)

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


def is_supabase_configured() -> bool:
    """Return True if Supabase env vars are set."""
    settings = get_settings()
    return bool(settings.supabase_url and settings.supabase_anon_key)


def get_supabase_admin() -> "Client | None":
    """Return Supabase admin client using SERVICE_ROLE_KEY (bypasses RLS).

    Falls back to anon-key client if service role key is not configured.
    """
    global _supabase_admin
    if _supabase_admin is not None:
        return _supabase_admin
    settings = get_settings()
    if not settings.supabase_url:
        return None

    from supabase import create_client

    # Prefer service role key for admin operations (bypasses RLS)
    service_key = getattr(settings, "supabase_service_role_key", None)
    if service_key:
        _supabase_admin = create_client(settings.supabase_url, service_key)
        logger.info("Supabase admin client initialized with service role key")
        return _supabase_admin

    # Fall back to anon key
    if settings.supabase_anon_key:
        _supabase_admin = create_client(settings.supabase_url, settings.supabase_anon_key)
        logger.warning("Supabase admin client using anon key (service role key not set)")
        return _supabase_admin

    return None
