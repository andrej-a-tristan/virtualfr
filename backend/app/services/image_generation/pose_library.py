"""Pose reference selection for identity batches."""
from __future__ import annotations

import random
from pathlib import Path

from app.core.config import get_settings


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_available_pose_images() -> list[str]:
    settings = get_settings()
    configured = (settings.avatar_pose_images or "").strip()
    if configured:
        return [item.strip() for item in configured.split(",") if item.strip()]

    pose_dir = Path(settings.avatar_pose_dir)
    if not pose_dir.is_absolute():
        pose_dir = (_backend_root() / pose_dir).resolve()
    if not pose_dir.exists() or not pose_dir.is_dir():
        return []

    allowed = {".png", ".jpg", ".jpeg", ".webp"}
    return [str(path.as_posix()) for path in pose_dir.iterdir() if path.suffix.lower() in allowed]


def choose_pose_for_identity_batch(girlfriend_id: str | None = None) -> str:
    poses = get_available_pose_images()
    if not poses:
        return "poses/default_pose.png"
    return random.choice(poses)

