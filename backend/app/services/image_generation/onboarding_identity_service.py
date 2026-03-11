"""Orchestration entrypoint for onboarding identity package generation."""
from __future__ import annotations

import random

from app.api.store import apply_identity_package_to_girlfriend
from app.schemas.image_generation import (
    IdentityGenerationRequest,
    IdentityGenerationResponse,
    IdentityPackage,
)
from app.services.image_generation.generator_adapter import get_generator_adapter
from app.services.image_generation.pose_library import choose_pose_for_identity_batch
from app.services.image_generation.prompt_builder import (
    build_workflow_a_prompts,
    choose_background_for_batch,
)
from app.services.image_generation.scoring import choose_best_candidate, score_candidate
from app.services.image_generation.workflow_template import (
    WORKFLOW_A_DEFAULTS,
    load_workflow_template,
    patch_workflow_for_candidate,
)


def generate_initial_identity_package(
    request: IdentityGenerationRequest,
    session_id: str | None = None,
) -> IdentityGenerationResponse:
    candidate_count = max(1, int(request.generation.candidate_count or 4))
    selected_pose_image = choose_pose_for_identity_batch(request.girlfriend_id)
    selected_background_prompt = choose_background_for_batch()
    positive_prompt, negative_prompt = build_workflow_a_prompts(
        request.appearance,
        request.persona,
        background_prompt=selected_background_prompt,
    )

    base_seed = random.randint(1, 2_147_483_000)
    seeds = [base_seed + i for i in range(candidate_count)]
    base_workflow = load_workflow_template()
    adapter = get_generator_adapter()

    candidate_urls: list[str] = []
    candidate_scores = []
    for candidate_index, seed in enumerate(seeds):
        output_prefix = f"generated/girls/{request.girlfriend_id}/identity/candidate_{candidate_index}_"
        workflow = patch_workflow_for_candidate(
            base_workflow,
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            pose_image=selected_pose_image,
            output_prefix=output_prefix,
            seed=seed,
            checkpoint_name=WORKFLOW_A_DEFAULTS["checkpoint"],
            controlnet_model=WORKFLOW_A_DEFAULTS["controlnet_model"],
            width=WORKFLOW_A_DEFAULTS["width"],
            height=WORKFLOW_A_DEFAULTS["height"],
            batch_size=WORKFLOW_A_DEFAULTS["batch_size"],
            steps=WORKFLOW_A_DEFAULTS["steps"],
            cfg=WORKFLOW_A_DEFAULTS["cfg"],
            sampler=WORKFLOW_A_DEFAULTS["sampler"],
            scheduler=WORKFLOW_A_DEFAULTS["scheduler"],
        )
        output = adapter.generate_workflow(
            workflow,
            girlfriend_id=request.girlfriend_id,
            candidate_index=candidate_index,
        )
        candidate_urls.append(output.get("image_url"))
        candidate_scores.append(
            score_candidate(
                candidate_index=candidate_index,
                seed=seed,
                pose_image=selected_pose_image,
                candidate_output=output,
            )
        )

    winner, all_candidates_rejected = choose_best_candidate(candidate_scores)
    main_avatar_url = candidate_urls[winner.candidate_index] if candidate_urls else None
    metadata = {
        "identity_package_version": "identity_pack_v1",
        "workflow_version": request.generation.workflow_version,
        "selected_candidate_index": winner.candidate_index,
        "selected_seed": winner.seed,
        "selected_pose_image": selected_pose_image,
        "selected_background_prompt": selected_background_prompt,
        "candidate_scores": [score.model_dump() for score in candidate_scores],
        "candidate_count": candidate_count,
        "all_candidates_rejected": all_candidates_rejected,
        # TODO: replace heuristic scoring with true CV-based scoring.
        # TODO: generate face refs in Workflow B.
        # TODO: generate body refs in Workflow C.
    }
    identity_package = IdentityPackage(
        main_avatar_url=main_avatar_url,
        face_ref_primary_url=None,
        face_ref_secondary_url=None,
        upper_body_ref_url=None,
        body_ref_url=None,
        candidate_urls=[url for url in candidate_urls if url],
        metadata=metadata,
    )

    if session_id:
        apply_identity_package_to_girlfriend(
            session_id=session_id,
            girlfriend_id=request.girlfriend_id,
            identity_package=identity_package.model_dump(),
        )

    return IdentityGenerationResponse(
        job_id="",
        girlfriend_id=request.girlfriend_id,
        status="completed",
        identity_package=identity_package,
    )

