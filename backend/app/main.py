"""
FastAPI app: APIs under /api, optional static frontend at / in production.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from app.core import get_settings, setup_cors
from app.api.routes import (
    auth,
    billing,
    chat,
    girlfriends,
    health,
    images,
    me,
    moderation,
    onboarding,
)
from app.routers import chat as chat_gateway
from app.routers import mock_model

app = FastAPI(title="Companion API", version="1.0.0")
setup_cors(app)


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
app.include_router(moderation.router, prefix="/api")
app.include_router(onboarding.router, prefix="/api")

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
