import os
from pathlib import Path

from .config import Settings, get_settings
from .cors import setup_cors
from .supabase_client import get_supabase, is_supabase_configured


def _env_candidate_paths() -> list[Path]:
    """All possible locations for backend/.env (order matters)."""
    # __file__ is backend/app/core/__init__.py -> parents[2] = backend
    backend_dir = Path(__file__).resolve().parents[2]
    return [
        backend_dir / ".env",
        Path.cwd() / ".env",
        Path.cwd() / "backend" / ".env",
    ]


def _read_api_key_from_file(env_path: Path) -> str:
    try:
        raw = env_path.read_bytes()
        text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        for line in text.split("\n"):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if s.startswith("API_KEY="):
                value = s.split("=", 1)[1].strip()
                if " #" in value:
                    value = value.split(" #", 1)[0].strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                value = value.strip()
                if value and len(value) > 20:
                    return value
    except Exception:
        pass
    return ""


def get_api_key() -> str:
    """Return API_KEY from backend/.env or env. Tries multiple file locations then env."""
    # 1. Try reading API_KEY directly from each candidate .env file (no dependency on cwd)
    for env_path in _env_candidate_paths():
        if env_path.exists():
            key = _read_api_key_from_file(env_path)
            if key:
                return key
    # 2. Force-load dotenv from backend/.env into os.environ then check again
    backend_env = Path(__file__).resolve().parents[2] / ".env"
    if backend_env.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(backend_env, override=True)
        except Exception:
            pass
    key = os.environ.get("API_KEY") or (get_settings().api_key or "")
    if isinstance(key, str):
        key = key.strip()
    return key if key else ""
