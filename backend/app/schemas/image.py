"""Image / gallery Pydantic schemas."""
from typing import Literal
from pydantic import BaseModel

from app.schemas.image_generation import IdentityPackage


class ImageRequestResponse(BaseModel):
    job_id: str


class ImageJobResponse(BaseModel):
    status: Literal["pending", "running", "processing", "completed", "done", "failed"]
    type: str | None = None
    girlfriend_id: str | None = None
    progress_message: str | None = None
    image_url: str | None = None
    identity_package: IdentityPackage | None = None
    error: str | None = None


class GalleryItem(BaseModel):
    id: str
    url: str
    created_at: str
    caption: str | None = None
