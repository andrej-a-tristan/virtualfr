"""
FastAPI app: APIs under /api, optional static frontend at / in production.
"""
from pathlib import Path

# Load .env before any app code that reads config (so API_KEY is available under uvicorn --reload)
# __file__ is backend/app/main.py -> parents[0]=app, parents[1]=backend
_backend_dir = Path(__file__).resolve().parents[1]
_env_file = _backend_dir / ".env"
if _env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_file, override=True)

# Force-reset the settings singleton so it picks up the .env we just loaded
import app.core.config as _cfg
_cfg._settings = None

import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse

from app.core import get_settings, setup_cors
from app.api.routes import (
    auth,
    billing,
    chat,
    dossier,
    gifts,
    girlfriends,
    health,
    images,
    intimacy_achievements,
    leaks,
    me,
    memory,
    moderation,
    onboarding,
    payments,
    profile,
    progression,
    prompt,
    relationship,
)
from app.routers import chat as chat_gateway
from app.routers import mock_model

app = FastAPI(title="Companion API", version="1.0.0")
setup_cors(app)
logger = logging.getLogger(__name__)


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    """Log and return 500 with message for debugging."""
    logger.exception("Unhandled error: %s", exc)
    err_msg = str(exc)
    return JSONResponse(
        status_code=500,
        content={"error": err_msg or "Internal server error"},
    )


@app.on_event("startup")
def _log_api_key_status():
    from app.core import get_api_key
    from app.core.config import get_settings
    import logging
    log = logging.getLogger("uvicorn.error")
    key = get_api_key()
    if key:
        log.info("API_KEY loaded (OpenAI enabled)")
    else:
        log.warning("API_KEY not set: add API_KEY=sk-... to backend/.env for AI chat")
    # Log Stripe config status
    s = get_settings()
    if s.stripe_secret_key and not s.stripe_secret_key.endswith("REPLACE_ME"):
        log.info("STRIPE_SECRET_KEY loaded: %s...%s", s.stripe_secret_key[:12], s.stripe_secret_key[-4:])
    else:
        log.warning("STRIPE_SECRET_KEY not configured or still placeholder!")


@app.post("/api/dev/reset")
def dev_reset(request: Request):
    """DEV ONLY: Wipe all in-memory state and clear session cookie so user starts fresh."""
    from app.api.store import (
        _sessions, _all_girlfriends, _relationship_state, _messages,
        _habit_profile, _gallery, _relationship_progress, _intimacy_state,
        _trust_intimacy_state, _achievement_progress,
        _intimacy_ach_unlocked, _intimacy_ach_last_award, _intimacy_ach_photos,
        _intimacy_ach_pending_photos, _intimacy_ach_phrase_log,
    )
    for store in [
        _sessions, _all_girlfriends, _relationship_state, _messages,
        _habit_profile, _gallery, _relationship_progress, _intimacy_state,
        _trust_intimacy_state, _achievement_progress,
        _intimacy_ach_unlocked, _intimacy_ach_last_award, _intimacy_ach_photos,
        _intimacy_ach_pending_photos, _intimacy_ach_phrase_log,
    ]:
        store.clear()
    resp = JSONResponse(content={"ok": True, "message": "All state wiped. Reload the page."})
    resp.delete_cookie("session")
    return resp


@app.get("/", response_class=HTMLResponse)
def root():
    """Help users find the app. The actual UI runs on the frontend dev server."""
    return """
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"><title>Companion API</title></head>
    <body style="font-family:sans-serif;max-width:480px;margin:60px auto;padding:20px;">
    <h1>Companion API</h1>
    <p>This is the <strong>backend</strong>. There is no app UI here.</p>
    <p>To use the app, open the <strong>frontend</strong> in your browser:</p>
    <p><a href="http://localhost:5173">http://localhost:5173</a></p>
    <p>If that port is in use, try <a href="http://localhost:5174">5174</a> or <a href="http://localhost:5175">5175</a>.</p>
    <p><a href="/docs">API docs (Swagger)</a></p>
    </body></html>
    """


# Mount API routers under /api
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(me.router, prefix="/api")
app.include_router(girlfriends.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(gifts.router, prefix="/api")
app.include_router(moderation.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(onboarding.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(progression.router, prefix="/api")
app.include_router(prompt.router, prefix="/api")
app.include_router(dossier.router, prefix="/api")
app.include_router(relationship.router, prefix="/api")
app.include_router(intimacy_achievements.router, prefix="/api")
app.include_router(leaks.router, prefix="/api")
app.include_router(payments.router, prefix="/api")

# Chat gateway: /v1/chat/stream and /api/chat/stream (same handler; /api works with proxy)
app.include_router(chat_gateway.router, prefix="/v1")
app.include_router(chat_gateway.router, prefix="/api")
app.include_router(mock_model.router)
app.include_router(mock_model.router_completions)

# In production, serve built frontend: static files from dist, SPA fallback to index.html
settings = get_settings()
dist = settings.frontend_dist_path
if settings.is_production and dist.exists():
    app.mount("/assets", StaticFiles(directory=str(dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if not full_path:
            return FileResponse(dist / "index.html")
        file_path = (dist / full_path).resolve()
        dist_resolved = dist.resolve()
        if file_path.is_file() and str(file_path).startswith(str(dist_resolved)):
            return FileResponse(file_path)
        return FileResponse(dist / "index.html")
