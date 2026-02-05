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

import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.core import get_settings, setup_cors
from app.api.routes import health, auth, me, girlfriends, chat, images, billing, moderation, check, memory

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
    key = get_api_key()
    if key:
        import logging
        logging.getLogger("uvicorn.error").info("API_KEY loaded (OpenAI enabled)")
    else:
        import logging
        logging.getLogger("uvicorn.error").warning("API_KEY not set: add API_KEY=sk-... to backend/.env for AI chat")

# Mount API routers under /api
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(me.router, prefix="/api")
app.include_router(girlfriends.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(moderation.router, prefix="/api")
app.include_router(check.router, prefix="/api")
app.include_router(memory.router, prefix="/api")

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
