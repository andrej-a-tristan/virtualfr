"""Image request, job status, gallery — all per-girlfriend."""
import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.schemas.image import ImageRequestResponse, ImageJobResponse, GalleryItem
from app.api.store import (
    get_session_user,
    get_girlfriend,
    get_gallery,
    add_gallery_item,
    get_intimacy_state,
    create_image_job,
    get_image_job,
)
from app.services.image_decision_engine import decide_image_action
from app.utils.ai_images import pick_ai_image_url

router = APIRouter(prefix="/images", tags=["images"])
logger = logging.getLogger(__name__)


def _session_id(request: Request) -> str | None:
    return request.cookies.get("session")


def _mock_gallery_for_girlfriend(girlfriend_id: str) -> list[dict]:
    """Generate unique mock gallery items seeded by the girlfriend id."""
    seed = girlfriend_id.replace("gf-", "")
    return [
        {
            "id": f"img-{seed}-1",
            "url": pick_ai_image_url(f"gallery:{seed}:a", fallback_url=f"https://picsum.photos/seed/{seed}a/400/400"),
            "created_at": "2025-01-01T12:00:00Z",
            "caption": "First photo together",
        },
        {
            "id": f"img-{seed}-2",
            "url": pick_ai_image_url(f"gallery:{seed}:b", fallback_url=f"https://picsum.photos/seed/{seed}b/400/400"),
            "created_at": "2025-01-02T12:00:00Z",
            "caption": None,
        },
        {
            "id": f"img-{seed}-3",
            "url": pick_ai_image_url(f"gallery:{seed}:c", fallback_url=f"https://picsum.photos/seed/{seed}c/400/400"),
            "created_at": "2025-01-03T12:00:00Z",
            "caption": "A special moment",
        },
    ]


class ImageRequestBody(BaseModel):
    girlfriend_id: str | None = None
    prompt: str = ""  # optional text describing desired image


@router.post("/request")
def request_image(request: Request, body: ImageRequestBody | None = None):
    sid = _session_id(request)
    user = get_session_user(sid) if sid else None
    if not sid or not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    # Resolve girlfriend_id
    gf_id = (body.girlfriend_id if body else None) or None
    gf = get_girlfriend(sid)
    if not gf_id:
        gf_id = gf["id"] if gf else None

    # ── Image decision engine gate ────────────────────────────────────────
    prompt_text = (body.prompt if body else "") or ""
    if prompt_text and gf:
        int_state = get_intimacy_state(sid, girlfriend_id=gf_id)
        traits = gf.get("traits") or {}
        content_prefs = gf.get("content_prefs") or {}
        user_plan = (user or {}).get("plan", "free")
        decision = decide_image_action(
            text=prompt_text,
            age_gate_passed=bool(user.get("age_gate_passed")),
            wants_spicy=bool(content_prefs.get("wants_spicy_photos")),
            intimacy_state=int_state,
            girlfriend_traits=traits,
            has_quota=True,  # TODO: wire real quota check
            explicit_ask=True,
            user_plan=user_plan,
            girlfriend_id=gf_id or "",
        )
        if decision.action != "generate":
            return JSONResponse(
                status_code=200,
                content={
                    "action": decision.action,
                    "reason": decision.reason,
                    "ui_copy": decision.ui_copy,
                    "suggested_prompts": decision.suggested_prompts,
                    "required_intimacy": decision.required_intimacy,
                    "current_intimacy": decision.current_intimacy,
                    "blurred_image_url": decision.blurred_image_url,
                },
            )

    image_url = pick_ai_image_url(
        f"request:{gf_id or 'nogf'}:{prompt_text[:24]}",
        fallback_url=f"https://picsum.photos/seed/{(gf_id or 'nogf')[:8]}/400/400",
    )
    row = create_image_job(
        sid,
        girlfriend_id=gf_id or "",
        status="completed",
        job_type="image_request",
        image_url=image_url,
        request_prompt=prompt_text or None,
        progress_message="Image generated",
    )
    job_id = row["id"]

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
    user = get_session_user(sid) if sid else None
    if not sid or not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    gf_id = (user or {}).get("current_girlfriend_id")
    job = get_image_job(sid, girlfriend_id=gf_id, job_id=job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "job_not_found"})
    return ImageJobResponse(
        status=job["status"],
        type=job.get("type"),
        girlfriend_id=job.get("girlfriend_id"),
        progress_message=job.get("progress_message"),
        image_url=job.get("image_url"),
        identity_package=job.get("identity_package"),
        error=job.get("error"),
    )


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
