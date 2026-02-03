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
