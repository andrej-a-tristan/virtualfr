"""Moderation: report."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/moderation", tags=["moderation"])


def _session_id(request: Request) -> str | None:
    return request.cookies.get("session")


@router.post("/report")
def report(request: Request):
    sid = _session_id(request)
    if not sid:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    return {"ok": True}
