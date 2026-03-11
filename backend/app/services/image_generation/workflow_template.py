"""Workflow A template loading and runtime patching."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings


WORKFLOW_A_DEFAULTS = {
    "checkpoint": "realvisxlV50_v50Bakedvae.safetensors",
    "width": 896,
    "height": 1152,
    "batch_size": 1,
    "steps": 30,
    "cfg": 5.5,
    "sampler": "dpmpp_2m_sde",
    "scheduler": "karras",
    "controlnet_model": "controlnet-openpose-sdxl.safetensors",
}


def _workflow_template_path() -> Path:
    settings = get_settings()
    configured = (settings.avatar_workflow_template_path or "").strip()
    if configured:
        path = Path(configured)
        if path.is_absolute():
            return path
        return (Path(__file__).resolve().parents[3] / path).resolve()
    return Path(__file__).resolve().parent / "workflow_configs" / "FINAL_AVATAR_WF_APP_READY.json"


def load_workflow_template() -> dict[str, Any]:
    template_path = _workflow_template_path()
    with template_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _replace_tokens(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {k: _replace_tokens(v, replacements) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace_tokens(v, replacements) for v in value]
    if isinstance(value, str):
        out = value
        for key, replacement in replacements.items():
            out = out.replace(key, replacement)
        return out
    return value


def patch_workflow_for_candidate(
    base_workflow: dict[str, Any],
    *,
    positive_prompt: str,
    negative_prompt: str,
    pose_image: str,
    output_prefix: str,
    seed: int,
    checkpoint_name: str = WORKFLOW_A_DEFAULTS["checkpoint"],
    controlnet_model: str = WORKFLOW_A_DEFAULTS["controlnet_model"],
    width: int = WORKFLOW_A_DEFAULTS["width"],
    height: int = WORKFLOW_A_DEFAULTS["height"],
    batch_size: int = WORKFLOW_A_DEFAULTS["batch_size"],
    steps: int = WORKFLOW_A_DEFAULTS["steps"],
    cfg: float = WORKFLOW_A_DEFAULTS["cfg"],
    sampler: str = WORKFLOW_A_DEFAULTS["sampler"],
    scheduler: str = WORKFLOW_A_DEFAULTS["scheduler"],
) -> dict[str, Any]:
    workflow = copy.deepcopy(base_workflow)
    replacements = {
        "__CHECKPOINT_NAME__": checkpoint_name,
        "__POSITIVE_PROMPT__": positive_prompt,
        "__NEGATIVE_PROMPT__": negative_prompt,
        "__POSE_IMAGE__": pose_image,
        "__CONTROLNET_MODEL__": controlnet_model,
        "__OUTPUT_PREFIX__candidate": output_prefix,
        "__OUTPUT_PREFIX__": output_prefix,
    }
    workflow = _replace_tokens(workflow, replacements)

    nodes = workflow.get("nodes", {})
    if isinstance(nodes, dict):
        node_iter = nodes.values()
    elif isinstance(nodes, list):
        node_iter = nodes
    else:
        node_iter = []

    for node in node_iter:
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            continue
        if "width" in inputs:
            inputs["width"] = width
        if "height" in inputs:
            inputs["height"] = height
        if "batch_size" in inputs:
            inputs["batch_size"] = batch_size
        if "seed" in inputs:
            inputs["seed"] = seed
        if "steps" in inputs:
            inputs["steps"] = steps
        if "cfg" in inputs:
            inputs["cfg"] = cfg
        if "sampler_name" in inputs:
            inputs["sampler_name"] = sampler
        if "sampler" in inputs:
            inputs["sampler"] = sampler
        if "scheduler" in inputs:
            inputs["scheduler"] = scheduler
        if "ckpt_name" in inputs:
            inputs["ckpt_name"] = checkpoint_name
        if "control_net_name" in inputs:
            inputs["control_net_name"] = controlnet_model
    return workflow

