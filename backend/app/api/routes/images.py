"""Image request, job status, gallery — all per-girlfriend."""
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.schemas.image import ImageRequestResponse, ImageJobResponse, GalleryItem
from app.api.store import (
    get_session_user,
    get_girlfriend,
    get_gallery,
    add_gallery_item,
)

router = APIRouter(prefix="/images", tags=["images"])

# In-memory job store: job_id -> {status, image_url, session_id, girlfriend_id}
_jobs: dict[str, dict] = {}


def _session_id(request: Request) -> str | None:
    return request.cookies.get("session")


def _mock_gallery_for_girlfriend(girlfriend_id: str) -> list[dict]:
    """Generate unique mock gallery items seeded by the girlfriend id."""
    seed = girlfriend_id.replace("gf-", "")
    return [
        {
            "id": f"img-{seed}-1",
            "url": f"https://picsum.photos/seed/{seed}a/400/400",
            "created_at": "2025-01-01T12:00:00Z",
            "caption": "First photo together",
        },
        {
            "id": f"img-{seed}-2",
            "url": f"https://picsum.photos/seed/{seed}b/400/400",
            "created_at": "2025-01-02T12:00:00Z",
            "caption": None,
        },
        {
            "id": f"img-{seed}-3",
            "url": f"https://picsum.photos/seed/{seed}c/400/400",
            "created_at": "2025-01-03T12:00:00Z",
            "caption": "A special moment",
        },
    ]


class ImageRequestBody(BaseModel):
    girlfriend_id: str | None = None


@router.post("/request")
def request_image(request: Request, body: ImageRequestBody | None = None):
    sid = _session_id(request)
    if not sid or not get_session_user(sid):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    # Resolve girlfriend_id
    gf_id = (body.girlfriend_id if body else None) or None
    if not gf_id:
        gf = get_girlfriend(sid)
        gf_id = gf["id"] if gf else None

    job_id = str(uuid.uuid4())
    image_url = f"https://picsum.photos/seed/{job_id[:8]}/400/400"
    _jobs[job_id] = {
        "status": "done",
        "image_url": image_url,
        "session_id": sid,
        "girlfriend_id": gf_id,
    }

    # Also add to the girlfriend's gallery
    if gf_id:
        from datetime import datetime, timezone
        add_gallery_item(sid, {
            "id": f"img-{job_id[:8]}",
            "url": image_url,
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "caption": None,
        }, girlfriend_id=gf_id)

    return ImageRequestResponse(job_id=job_id)


@router.get("/jobs/{job_id}")
def get_job(job_id: str, request: Request):
    sid = _session_id(request)
    if not sid or not get_session_user(sid):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    job = _jobs.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "job_not_found"})
    return ImageJobResponse(status=job["status"], image_url=job.get("image_url"))


@router.get("/gallery")
def gallery(request: Request, girlfriend_id: str | None = None):
    """Return gallery items for a specific girlfriend. Falls back to current girlfriend."""
    sid = _session_id(request)
    if not sid or not get_session_user(sid):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    # Resolve girlfriend_id
    if not girlfriend_id:
        gf = get_girlfriend(sid)
        girlfriend_id = gf["id"] if gf else None

    if not girlfriend_id:
        return {"items": []}

    # Get stored gallery items for this girl
    items = get_gallery(sid, girlfriend_id)

    # If no items stored yet, seed with mock data unique to this girl
    if not items:
        items = _mock_gallery_for_girlfriend(girlfriend_id)

    return {"items": [GalleryItem(**i) for i in items]}
