"""Schemas for onboarding identity image generation."""
from typing import Any, Literal

from pydantic import BaseModel, Field


class IdentityAppearance(BaseModel):
    age_band: str
    ethnicity: str
    appearance_vibe: str
    body_type: str | None = None
    breast_size: str | None = None
    butt_size: str | None = None
    hair_color: str
    hair_style: str
    eye_color: str


class IdentityPersona(BaseModel):
    display_name: str
    traits: list[str]
    job_vibe: str | None = None
    hobbies: list[str]
    origin_vibe: str | None = None


class IdentityPreferences(BaseModel):
    spicy_photos_opt_in: bool


class IdentityGenerationConfig(BaseModel):
    workflow_type: Literal["identity_creation"] = "identity_creation"
    workflow_version: str = "workflow_a_v1"
    candidate_count: int = 4


class IdentityGenerationRequest(BaseModel):
    girlfriend_id: str
    user_id: str | None = None
    appearance: IdentityAppearance
    persona: IdentityPersona
    preferences: IdentityPreferences
    generation: IdentityGenerationConfig = Field(default_factory=IdentityGenerationConfig)


class IdentityCandidateScore(BaseModel):
    candidate_index: int
    seed: int
    pose_image: str
    face_score: float
    anatomy_score: float
    attribute_match_score: float
    aesthetic_score: float
    reference_usefulness_score: float
    total_score: float
    rejected: bool
    rejection_reasons: list[str] = Field(default_factory=list)


class IdentityPackage(BaseModel):
    main_avatar_url: str | None
    face_ref_primary_url: str | None = None
    face_ref_secondary_url: str | None = None
    upper_body_ref_url: str | None = None
    body_ref_url: str | None = None
    candidate_urls: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IdentityGenerationResponse(BaseModel):
    job_id: str
    girlfriend_id: str
    status: str
    identity_package: IdentityPackage | None = None
