"""CORS configuration for FastAPI."""
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings


def setup_cors(app):
    """Add CORS middleware with origins from config."""
    settings = get_settings()
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
