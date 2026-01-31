"""Image request, job status, gallery."""
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.schemas.image import ImageRequestResponse, ImageJobResponse, GalleryItem
from app.api.store import get_session_user

router = APIRouter(prefix="/images", tags=["images"])

# In-memory job store: job_id -> {status, image_url}
_jobs: dict[str, dict] = {}


def _session_id(request: Request) -> str | None:
    return request.cookies.get("session")


def _mock_gallery():
    return [
        {"id": "img1", "url": "https://picsum.photos/400/400?random=1", "created_at": "2025-01-01T12:00:00Z", "caption": "Sunset"},
        {"id": "img2", "url": "https://picsum.photos/400/400?random=2", "created_at": "2025-01-02T12:00:00Z", "caption": None},
        {"id": "img3", "url": "https://picsum.photos/400/400?random=3", "created_at": "2025-01-03T12:00:00Z", "caption": "Beach"},
    ]


@router.post("/request")
def request_image(request: Request):
    sid = _session_id(request)
    if not sid or not get_session_user(sid):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "done", "image_url": "https://picsum.photos/400/400"}
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
def gallery(request: Request):
    sid = _session_id(request)
    if not sid or not get_session_user(sid):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    items = _mock_gallery()
    return {"items": [GalleryItem(**i) for i in items]}
