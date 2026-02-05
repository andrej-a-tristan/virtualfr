"""JSONL logging for chat gateway (logs/chat.jsonl)."""
import json
import os
from pathlib import Path
from typing import Any

# Ensure logs dir exists
_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
_LOG_FILE = _LOG_DIR / "chat.jsonl"


def _ensure_log_dir() -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


def write_chat_log(record: dict[str, Any]) -> None:
    """Append one JSON line to logs/chat.jsonl. Best-effort; swallows errors."""
    try:
        _ensure_log_dir()
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass
