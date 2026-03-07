"""Utility helpers for serving deterministic local AI girlfriend images."""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path


def get_ai_images_dir() -> Path:
    # backend/app/utils/ai_images.py -> repo root is parents[3]
    return Path(__file__).resolve().parents[3] / "AI_gf_images"


@lru_cache(maxsize=1)
def _ai_image_filenames() -> tuple[str, ...]:
    image_dir = get_ai_images_dir()
    if not image_dir.exists():
        return ()
    exts = ("*.png", "*.jpg", "*.jpeg", "*.webp")
    files: list[str] = []
    for ext in exts:
        files.extend(p.name for p in image_dir.glob(ext))
    files.sort()
    return tuple(files)


def pick_ai_image_url(seed_key: str, fallback_url: str = "") -> str:
    """Pick a deterministic local image URL from AI_gf_images by seed."""
    names = _ai_image_filenames()
    if not names:
        return fallback_url
    digest = hashlib.sha256(seed_key.encode("utf-8")).hexdigest()
    idx = int(digest[:16], 16) % len(names)
    return f"/api/ai-gf/{names[idx]}"

