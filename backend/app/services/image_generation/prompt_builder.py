"""Prompt builder for identity creation workflow."""
from __future__ import annotations

import random

from app.schemas.image_generation import IdentityAppearance, IdentityPersona


BACKGROUND_PROMPTS = [
    "softly blurred european street background",
    "warm cafe terrace background",
    "sunlit park background",
    "modern apartment interior background",
    "luxury hotel lobby background",
]

NEGATIVE_PROMPT = (
    "full body, knees visible, wide shot, long shot, too much background, "
    "anime, cartoon, cgi, plastic skin, asymmetrical eyes, deformed face, "
    "bad anatomy, extra limbs, extra fingers, twisted torso, blurry, text, watermark, logo"
)


def choose_background_for_batch() -> str:
    return random.choice(BACKGROUND_PROMPTS)


def build_workflow_a_prompts(
    appearance: IdentityAppearance,
    persona: IdentityPersona,
    background_prompt: str | None = None,
) -> tuple[str, str]:
    traits = ", ".join([t for t in persona.traits if t]) or "balanced personality"
    hobbies = ", ".join([h for h in persona.hobbies if h]) or "mixed interests"
    job_vibe = persona.job_vibe or "modern"
    origin_vibe = persona.origin_vibe or "urban european"
    bg = background_prompt or choose_background_for_batch()

    positive_prompt = (
        "photorealistic portrait of a young adult woman, medium shot framed from the hips up, "
        "visible from hips to head, subject filling most of the frame, natural body proportions, "
        "relaxed standing pose, facing camera, soft natural lighting on face, shallow depth of field, "
        "attractive blurred background, professional portrait photography, DSLR photo, 85mm lens, "
        "realistic skin texture, high detail, "
        f"{appearance.age_band} {appearance.ethnicity} woman, "
        f"{appearance.appearance_vibe} vibe, "
        f"{appearance.body_type or 'natural'} build, "
        f"{appearance.breast_size or 'medium'} breasts, "
        f"{appearance.butt_size or 'medium'} butt, "
        f"{appearance.hair_color} {appearance.hair_style} hair, "
        f"{appearance.eye_color} eyes, "
        "distinct facial identity, natural asymmetry, unique cheekbone structure, realistic nose bridge, natural lip shape, "
        f"personality impression: {traits}, "
        f"lifestyle impression: {job_vibe}, {hobbies}, {origin_vibe}, "
        f"background: {bg}"
    )
    return positive_prompt, NEGATIVE_PROMPT

