"""Image / gallery Pydantic schemas."""
from typing import Literal
from pydantic import BaseModel


class ImageRequestResponse(BaseModel):
    job_id: str


class ImageJobResponse(BaseModel):
    status: Literal["pending", "processing", "done", "failed"]
    image_url: str | None = None


class GalleryItem(BaseModel):
    id: str
    url: str
    created_at: str
    caption: str | None = None
