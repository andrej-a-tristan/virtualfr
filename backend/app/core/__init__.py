from .config import Settings, get_settings
from .cors import setup_cors
from .supabase_client import get_supabase, is_supabase_configured


def get_api_key() -> str:
    """Return API_KEY from settings (for external services). Use only server-side."""
    return get_settings().api_key
