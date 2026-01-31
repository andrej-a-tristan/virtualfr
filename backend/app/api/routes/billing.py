"""Billing status and checkout."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/billing", tags=["billing"])


def _session_id(request: Request) -> str | None:
    return request.cookies.get("session")


@router.get("/status")
def billing_status(request: Request):
    sid = _session_id(request)
    if not sid:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    return {
        "plan": "free",
        "message_cap": 50,
        "image_cap": 5,
    }


@router.post("/checkout")
def checkout(request: Request):
    sid = _session_id(request)
    if not sid:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    return {"checkout_url": "https://example.com/checkout"}
