"""Heuristic scoring for identity candidates (pluggable placeholder)."""
from __future__ import annotations

import random
from typing import Any

from app.schemas.image_generation import IdentityCandidateScore


def score_candidate(
    *,
    candidate_index: int,
    seed: int,
    pose_image: str,
    candidate_output: dict[str, Any] | None,
) -> IdentityCandidateScore:
    candidate_output = candidate_output or {}
    rejection_reasons: list[str] = []
    if not candidate_output.get("image_url"):
        rejection_reasons.append("missing output")
    if candidate_output.get("face_too_small"):
        rejection_reasons.append("face too small")
    if candidate_output.get("zoomed_out"):
        rejection_reasons.append("image too zoomed out")
    if candidate_output.get("anatomy_issue"):
        rejection_reasons.append("obvious anatomy issue")
    if candidate_output.get("framing_unusable"):
        rejection_reasons.append("unusable framing")

    rng = random.Random(seed)
    face_score = float(candidate_output.get("face_score_hint", 0.65 + rng.random() * 0.3))
    anatomy_score = float(candidate_output.get("anatomy_score_hint", 0.60 + rng.random() * 0.35))
    attribute_match_score = float(candidate_output.get("attribute_match_hint", 0.60 + rng.random() * 0.35))
    aesthetic_score = float(candidate_output.get("quality_hint", 0.65 + rng.random() * 0.3))
    reference_usefulness_score = float(candidate_output.get("reference_usefulness_hint", 0.55 + rng.random() * 0.35))

    if candidate_output.get("width") in (None, 0) or candidate_output.get("height") in (None, 0):
        rejection_reasons.append("unusable framing")
        face_score *= 0.5
        anatomy_score *= 0.5
        attribute_match_score *= 0.5
        aesthetic_score *= 0.5

    total_score = (
        0.35 * face_score
        + 0.25 * anatomy_score
        + 0.20 * attribute_match_score
        + 0.15 * aesthetic_score
        + 0.05 * reference_usefulness_score
    )
    return IdentityCandidateScore(
        candidate_index=candidate_index,
        seed=seed,
        pose_image=pose_image,
        face_score=round(face_score, 4),
        anatomy_score=round(anatomy_score, 4),
        attribute_match_score=round(attribute_match_score, 4),
        aesthetic_score=round(aesthetic_score, 4),
        reference_usefulness_score=round(reference_usefulness_score, 4),
        total_score=round(total_score, 4),
        rejected=len(rejection_reasons) > 0,
        rejection_reasons=rejection_reasons,
    )


def choose_best_candidate(scores: list[IdentityCandidateScore]) -> tuple[IdentityCandidateScore, bool]:
    non_rejected = [item for item in scores if not item.rejected]
    if non_rejected:
        winner = max(non_rejected, key=lambda item: item.total_score)
        return winner, False
    winner = max(scores, key=lambda item: item.total_score)
    return winner, True

