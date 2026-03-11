"""Provider adapters for workflow execution."""
from __future__ import annotations

import hashlib
import json
import random
from typing import Any, Protocol

import httpx

from app.core.config import get_settings
from app.utils.ai_images import pick_ai_image_url


class GeneratorAdapter(Protocol):
    def generate_workflow(self, workflow: dict, *, girlfriend_id: str, candidate_index: int) -> dict:
        ...

    def healthcheck(self) -> dict:
        ...


class MockGeneratorAdapter:
    """Local deterministic adapter used for dev before RunPod integration."""

    def generate_workflow(self, workflow: dict, *, girlfriend_id: str, candidate_index: int) -> dict:
        workflow_str = json.dumps(workflow, sort_keys=True)
        token = hashlib.sha256(f"{girlfriend_id}:{candidate_index}:{workflow_str}".encode("utf-8")).hexdigest()
        seed_int = int(token[:8], 16)
        rng = random.Random(seed_int)
        image_url = pick_ai_image_url(
            f"identity:{girlfriend_id}:{candidate_index}:{token[:8]}",
            fallback_url=f"https://picsum.photos/seed/{token[:8]}/896/1152",
        )
        return {
            "image_url": image_url,
            "width": 896,
            "height": 1152,
            "has_face": rng.random() > 0.05,
            "framing_ok": rng.random() > 0.08,
            "anatomy_ok": rng.random() > 0.06,
            "quality_hint": 0.75 + (rng.random() * 0.2),
            "provider": "mock",
        }

    def healthcheck(self) -> dict:
        return {"provider": "mock", "ok": True}


class RunPodServerlessAdapter:
    """RunPod adapter skeleton; response parsing is intentionally conservative."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def generate_workflow(self, workflow: dict, *, girlfriend_id: str, candidate_index: int) -> dict:
        if not self._settings.runpod_serverless_url or not self._settings.runpod_api_key:
            raise RuntimeError("RunPod adapter is not configured")
        headers = {
            "Authorization": f"Bearer {self._settings.runpod_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": {
                "workflow_json": workflow,
                "job_type": "identity_creation_candidate",
                "girlfriend_id": girlfriend_id,
                "candidate_index": candidate_index,
            }
        }
        with httpx.Client(timeout=self._settings.runpod_timeout_seconds) as client:
            response = client.post(self._settings.runpod_serverless_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        # TODO: replace with finalized RunPod response mapping.
        output = data.get("output") if isinstance(data, dict) else None
        image_url = output.get("image_url") if isinstance(output, dict) else None
        return {
            "image_url": image_url,
            "provider": "runpod",
            "raw_response": data,
        }

    def healthcheck(self) -> dict:
        return {
            "provider": "runpod",
            "ok": bool(self._settings.runpod_serverless_url and self._settings.runpod_api_key),
        }


def get_generator_adapter() -> GeneratorAdapter:
    provider = (get_settings().image_provider or "mock").strip().lower()
    if provider == "runpod":
        return RunPodServerlessAdapter()
    return MockGeneratorAdapter()

