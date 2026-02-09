"""Application configuration loaded from environment."""
import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App settings from env vars."""

    host: str = "0.0.0.0"
    port: int = 8000
    env: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    # Supabase (optional; leave empty to use in-memory store)
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # API key for external services (e.g. OpenAI); optional
    api_key: str = ""

    # Chat gateway
    chat_api_key: str = "dev-key"
    stream_timeout_seconds: int = 60
    upstream_token_timeout_seconds: int = 15
    use_mock_model: bool = True
    mock_model_base_url: str = "http://127.0.0.1:8000"

    # Internal LLM (OpenAI-compatible); gateway calls this (default: same host = mock on main app)
    internal_llm_base_url: str = "http://127.0.0.1:8000"
    internal_llm_api_key: str = ""
    internal_llm_path: str = "/v1/chat/completions"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""
    stripe_price_free: str = ""       # price ID for Free tier (optional, not used by Stripe)
    stripe_price_plus: str = ""      # price ID for Plus tier
    stripe_price_premium: str = ""   # price ID for Premium tier
    stripe_success_url: str = "http://localhost:5173/app/chat?gift_success=1"
    stripe_cancel_url: str = "http://localhost:5173/app/chat?gift_cancel=1"

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def frontend_dist_path(self) -> Path:
        """Path to frontend build (parent of backend = monorepo root)."""
        return Path(__file__).resolve().parents[3] / "frontend" / "dist"

    class Config:
        env_file = ".env"
        extra = "ignore"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
