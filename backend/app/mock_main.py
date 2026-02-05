"""
Standalone entrypoint for the internal LLM mock server (OpenAI-compatible).
Run on port 8000 for a single-process dev backend (chat + mock LLM):

  uvicorn app.mock_main:app --reload --port 8000

Provides:
  POST /v1/chat/stream              (chat gateway; uses in-process mock when use_mock_model=True)
  GET  /mock-model/stream?text=...   (legacy)
  POST /v1/chat/completions          (OpenAI-like stream or JSON)
"""
from fastapi import FastAPI

from app.core import setup_cors
from app.routers import chat as chat_gateway
from app.routers import mock_model

app = FastAPI(title="Internal LLM Mock", version="1.0.0")
setup_cors(app)

# Chat gateway so POST /v1/chat/stream exists (avoids 404 when only this app is run)
app.include_router(chat_gateway.router, prefix="/v1")
app.include_router(mock_model.router)
app.include_router(mock_model.router_completions)
