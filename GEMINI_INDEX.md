# VirtualFR / Companion — Full Project Index for Google Gemini

This document contains the complete source code of the **virtualfr** repository. Use it to give Gemini full context when asking questions about the codebase.

---

## Project Overview

**Stack:** FastAPI (Python) backend + React (Vite, TypeScript) frontend. Dark-first, premium UI. Mock APIs, SSE chat streaming, in-memory session store.

**Structure:**
- `backend/` — FastAPI app, JSON APIs under `/api/*`
- `frontend/` — Vite + React + TypeScript, TailwindCSS, shadcn/ui, React Router, TanStack Query, Zustand, Zod

**Features:** Auth (signup/login), age gate, 6-trait onboarding, girlfriend creation, chat with SSE streaming, gallery, billing, safety/moderation.

---

## File Tree

```
virtualfr/
├── .gitignore
├── README.md
├── onboarding_questions.md.txt
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── core/ (config, cors)
│       ├── api/ (store, routes: health, auth, me, girlfriends, chat, images, billing, moderation)
│       ├── schemas/ (auth, chat, girlfriend, image, relationship)
│       └── utils/ (sse)
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.ts
    ├── postcss.config.js
    ├── tsconfig.json
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── styles/globals.css
        ├── routes/ (router, guards)
        ├── lib/ (api, hooks, store, utils)
        ├── pages/ (Landing, Login, Signup, AgeGate, OnboardingTraits, PersonaPreview, Chat, Gallery, Profile, Settings, Billing, Safety)
        └── components/ (chat, gallery, layout, onboarding, safety, ui)
```

---

## Source Files

### .gitignore
```gitignore
# Dependencies
node_modules/
__pycache__/
*.py[cod]
*$py.class
.Python
venv/
.venv/
env/
.env
!.env.example

# Build
frontend/dist/
*.tsbuildinfo
frontend/vite.config.d.ts
frontend/vite.config.js
*.egg-info/
.eggs/
dist/
build/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
npm-debug.log*

# Test / coverage
.coverage
htmlcov/
.pytest_cache/
*.cover
```

---

### README.md
See project root README for full content (setup, scripts, features).

---

### onboarding_questions.md.txt
Contains 6 trait questions with answer options: Emotional Style, Attachment Style, Jealousy, Communication Tone, Intimacy Pace, Cultural Personality.

---

### backend/.env.example
```env
HOST=0.0.0.0
PORT=8000
ENV=development
CORS_ORIGINS=http://localhost:5173
```

---

### backend/requirements.txt
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic[email]>=2.5.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0
```

---

### backend/app/main.py
```python
"""
FastAPI app: APIs under /api, optional static frontend at / in production.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core import get_settings, setup_cors
from app.api.routes import health, auth, me, girlfriends, chat, images, billing, moderation

app = FastAPI(title="Companion API", version="1.0.0")
setup_cors(app)

# Mount API routers under /api
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(me.router, prefix="/api")
app.include_router(girlfriends.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(moderation.router, prefix="/api")

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
```

---

### backend/app/core/config.py
```python
"""Application configuration loaded from environment."""
import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App settings from env vars."""

    host: str = "0.0.0.0"
    port: int = 8000
    env: str = "development"
    cors_origins: str = "http://localhost:5173"

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def frontend_dist_path(self) -> Path:
        """Path to frontend build (parent of backend = monorepo root)."""
        return Path(__file__).resolve().parents[3] / "frontend" / "dist"

    class Config:
        env_file = ".env"
        extra = "ignore"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

---

### backend/app/core/cors.py
```python
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
```

---

### backend/app/api/store.py
```python
"""In-memory session store keyed by cookie value. No DB."""
from typing import Any

# session_id -> user dict (id, email, display_name, age_gate_passed, girlfriend_id, etc.)
_sessions: dict[str, dict[str, Any]] = {}
# girlfriend data per session
_girlfriends: dict[str, dict[str, Any]] = {}


def get_session_user(session_id: str) -> dict[str, Any] | None:
    return _sessions.get(session_id)


def set_session_user(session_id: str, data: dict[str, Any]) -> None:
    existing = _sessions.get(session_id) or {}
    _sessions[session_id] = {**existing, **data}


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
    _girlfriends.pop(session_id, None)


def get_girlfriend(session_id: str) -> dict[str, Any] | None:
    return _girlfriends.get(session_id)


def set_girlfriend(session_id: str, data: dict[str, Any]) -> None:
    _girlfriends[session_id] = data
```

---

### backend/app/api/routes/health.py
```python
"""Health check endpoint."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"ok": True}
```

---

### backend/app/api/routes/auth.py
```python
"""Auth endpoints: signup, login, logout (mock session cookie)."""
from fastapi import APIRouter, Response
from app.schemas.auth import SignupRequest, LoginRequest, UserResponse
from app.api.store import get_session_user, set_session_user, clear_session

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE = "session"
SESSION_VALUE = "demo"


@router.post("/signup")
def signup(body: SignupRequest, response: Response):
    """Mock signup: set session cookie."""
    user_id = f"user-{body.email.split('@')[0]}"
    set_session_user(SESSION_VALUE, {"id": user_id, "email": body.email, "display_name": body.display_name})
    response.set_cookie(
        key=SESSION_COOKIE,
        value=SESSION_VALUE,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
    )
    return {"ok": True, "user": UserResponse(id=user_id, email=body.email, display_name=body.display_name, age_gate_passed=False, has_girlfriend=False)}


@router.post("/login")
def login(body: LoginRequest, response: Response):
    """Mock login: set session cookie."""
    user_id = f"user-{body.email.split('@')[0]}"
    set_session_user(SESSION_VALUE, {"id": user_id, "email": body.email, "display_name": None})
    response.set_cookie(
        key=SESSION_COOKIE,
        value=SESSION_VALUE,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
    )
    return {"ok": True, "user": UserResponse(id=user_id, email=body.email, display_name=None, age_gate_passed=False, has_girlfriend=False)}


@router.post("/logout")
def logout(response: Response):
    """Clear session cookie."""
    clear_session(SESSION_VALUE)
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}
```

---

### backend/app/api/routes/me.py
```python
"""Current user and age-gate endpoints."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.schemas.auth import UserResponse
from app.api.store import get_session_user, set_session_user, get_girlfriend

def _age_gate(user): return user.get("age_gate_passed", False)

router = APIRouter(prefix="/me", tags=["me"])


def _session_id(request: Request) -> str | None:
    return request.cookies.get("session")


@router.get("")
def me(request: Request):
    """Return current user + flags (age_gate_passed, has_girlfriend)."""
    sid = _session_id(request)
    if not sid:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    user = get_session_user(sid)
    if not user:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    has_gf = bool(get_girlfriend(sid))
    age_gate = _age_gate(user)
    return UserResponse(
        id=user["id"],
        email=user["email"],
        display_name=user.get("display_name"),
        age_gate_passed=age_gate,
        has_girlfriend=has_gf,
    )


@router.post("/age-gate")
def age_gate(request: Request):
    """Set age_gate_passed=True for current session."""
    sid = _session_id(request)
    if not sid:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    set_session_user(sid, {"age_gate_passed": True})
    return {"ok": True}
```

---

### backend/app/api/routes/girlfriends.py
```python
"""Girlfriend CRUD (create, get current) with mock storage."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.schemas.girlfriend import TraitsPayload, GirlfriendResponse
from app.api.store import get_session_user, get_girlfriend, set_girlfriend

router = APIRouter(prefix="/girlfriends", tags=["girlfriends"])


def _session_id(request: Request) -> str | None:
    return request.cookies.get("session")


@router.post("")
def create_girlfriend(request: Request, body: TraitsPayload):
    """Create current girlfriend from traits payload."""
    sid = _session_id(request)
    if not sid or not get_session_user(sid):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    traits = body.model_dump()
    gf = {
        "id": "gf-1",
        "name": "Luna",
        "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=luna",
        "traits": traits,
        "created_at": "2025-01-01T00:00:00Z",
    }
    set_girlfriend(sid, gf)
    return GirlfriendResponse(**gf)


@router.get("/current")
def get_current_girlfriend(request: Request):
    """Return current girlfriend or 404."""
    sid = _session_id(request)
    if not sid or not get_session_user(sid):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    gf = get_girlfriend(sid)
    if not gf:
        return JSONResponse(status_code=404, content={"error": "no_girlfriend"})
    return GirlfriendResponse(**gf)
```

---

### backend/app/api/routes/chat.py
```python
"""Chat: history, state, send (SSE stream)."""
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from app.schemas.chat import SendMessageRequest, ChatMessage, RelationshipState
from app.api.store import get_session_user, get_girlfriend
from app.utils.sse import sse_event

router = APIRouter(prefix="/chat", tags=["chat"])


def _session_id(request: Request) -> str | None:
    return request.cookies.get("session")


# Deterministic mock history
def _mock_history():
    return [
        {"id": "m1", "role": "user", "content": "Hey, how are you?", "image_url": None, "event_type": None, "created_at": "2025-01-01T12:00:00Z"},
        {"id": "m2", "role": "assistant", "content": "I'm doing great! Thanks for asking. How about you?", "image_url": None, "event_type": None, "created_at": "2025-01-01T12:00:01Z"},
        {"id": "m3", "role": "assistant", "content": None, "image_url": "https://picsum.photos/400/400", "event_type": None, "created_at": "2025-01-01T12:05:00Z"},
        {"id": "m4", "role": "assistant", "content": "We just reached a new level! 💕", "image_url": None, "event_type": "milestone", "created_at": "2025-01-01T12:10:00Z"},
    ]


@router.get("/history")
def chat_history(request: Request):
    sid = _session_id(request)
    if not sid or not get_session_user(sid):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    messages = _mock_history()
    return {"messages": [ChatMessage(**m) for m in messages]}


@router.get("/state")
def chat_state(request: Request):
    sid = _session_id(request)
    if not sid or not get_session_user(sid):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    return RelationshipState(
        trust=72,
        intimacy=65,
        level=3,
        last_interaction_at="2025-01-01T12:10:00Z",
    )


def _stream_tokens():
    """Yield SSE events: token, token, ..., message, done."""
    tokens = ["I ", "had ", "a ", "great ", "day! ", "How ", "was ", "yours?"]
    for t in tokens:
        yield sse_event({"type": "token", "token": t})
    msg = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": "".join(tokens),
        "image_url": None,
        "event_type": None,
        "created_at": "2025-01-31T12:00:00Z",
    }
    yield sse_event({"type": "message", "message": msg})
    yield sse_event({"type": "done"})


@router.post("/send")
def send_message(request: Request, body: SendMessageRequest):
    sid = _session_id(request)
    if not sid or not get_session_user(sid):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    return StreamingResponse(
        _stream_tokens(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

---

### backend/app/schemas/girlfriend.py
```python
"""Girlfriend / persona Pydantic schemas."""
from pydantic import BaseModel


class TraitsPayload(BaseModel):
    emotional_style: str
    attachment_style: str
    jealousy_level: str
    communication_tone: str
    intimacy_pace: str
    cultural_personality: str


class GirlfriendResponse(BaseModel):
    id: str
    name: str
    avatar_url: str | None = None
    traits: dict
    created_at: str
```

---

### backend/app/api/routes/images.py
```python
"""Image request, job status, gallery."""
# POST /images/request, GET /images/jobs/{job_id}, GET /images/gallery
# Mock jobs and gallery items
```

### backend/app/api/routes/billing.py
```python
"""Billing status and checkout."""
# GET /billing/status -> plan, message_cap, image_cap
# POST /billing/checkout -> checkout_url
```

### backend/app/api/routes/moderation.py
```python
"""Moderation: report."""
# POST /moderation/report
```

### backend/app/schemas/auth.py
```python
class SignupRequest(BaseModel): email, password, display_name
class LoginRequest(BaseModel): email, password
class UserResponse(BaseModel): id, email, display_name, age_gate_passed, has_girlfriend
```

### backend/app/schemas/chat.py
```python
class ChatMessage(BaseModel): id, role, content, image_url, event_type, created_at
class SendMessageRequest(BaseModel): message, girlfriend_id
class RelationshipState(BaseModel): trust, intimacy, level, last_interaction_at
```

### backend/app/schemas/image.py
```python
class ImageRequestResponse(BaseModel): job_id
class ImageJobResponse(BaseModel): status, image_url
class GalleryItem(BaseModel): id, url, created_at, caption
```

### backend/app/utils/sse.py
```python
def sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"
```

---

## Frontend (full source for key files)

### frontend/package.json
```json
{
  "name": "companion-frontend",
  "scripts": { "dev": "vite", "build": "tsc -b && vite build" },
  "dependencies": ["react", "react-router-dom", "@tanstack/react-query", "zustand", "zod", "react-hook-form", "@hookform/resolvers", "@radix-ui/*", "tailwindcss", "lucide-react", ...]
}
```

### frontend/vite.config.ts
```typescript
// Proxy /api -> http://localhost:8000, alias @ -> ./src
```

### frontend/src/routes/router.tsx
```typescript
// Routes: / (Landing), /login, /signup, /age-gate (RequireAuth), /onboarding/traits (RequireAuth+AgeGate), /onboarding/preview (RequireAuth+AgeGate+Girlfriend), /app (AppShell with RequireAuth+AgeGate+Girlfriend) -> chat, gallery, profile, settings, billing, safety
```

### frontend/src/routes/guards.tsx
```typescript
// RequireAuth: redirect to /login if !isAuthenticated
// RequireAgeGate: redirect to /age-gate if !user?.age_gate_passed
// RequireGirlfriend: redirect to /onboarding/traits if !user?.has_girlfriend
```

### frontend/src/lib/api/client.ts
```typescript
const BASE = "/api"
export async function apiFetch<T>(path, init?): Promise<T>  // credentials: include
export async function apiPost<T>(path, body?): Promise<T>
export async function apiGet<T>(path): Promise<T>
```

### frontend/src/lib/api/endpoints.ts
```typescript
// signup, login, logout | getMe, postAgeGate | createGirlfriend, getCurrentGirlfriend | getChatHistory, getChatState, getChatSendStreamUrl | requestImage, getImageJob, getGallery | getBillingStatus, checkout | report
```

### frontend/src/lib/api/types.ts
```typescript
// User, Traits, Girlfriend, ChatMessage, RelationshipState, ImageJob, GalleryItem, BillingStatus
```

### frontend/src/lib/api/zod.ts
```typescript
// signupSchema, loginSchema, traitsSchema (Zod validation)
```

### frontend/src/lib/hooks/useAuth.ts
```typescript
// useQuery(["me"], getMe), useMutation(logout), returns { user, isLoading, isAuthenticated, logout }
```

### frontend/src/lib/hooks/useSSEChat.ts
```typescript
// sendChatMessage: POST /api/chat/send, parse SSE (token -> message -> done), appendMessage to store
```

### frontend/src/lib/store/useAppStore.ts
```typescript
// Zustand: user, girlfriend, setUser, setGirlfriend, reset
```

### frontend/src/lib/store/useChatStore.ts
```typescript
// Zustand: messages, streamingContent, isStreaming, appendMessage, setStreamingContent, setMessages
```

### frontend/src/pages/OnboardingTraits.tsx
- 6 trait selectors (emotional_style, attachment_style, jealousy_level, communication_tone, intimacy_pace, cultural_personality)
- TRAIT_OPTIONS and TRAIT_LABELS, createGirlfriend on submit, navigate to /onboarding/preview

### frontend/src/pages/Chat.tsx
- getChatHistory -> setMessages, ChatHeader + MessageList + Composer

### frontend/src/components/chat/Composer.tsx
- useSSEChat().sendMessage, append user message, PaywallInlineCard for free plan

### frontend/src/components/onboarding/TraitSelector.tsx
- Grid of TraitOption cards, onClick -> onChange(traitKey, value)

**All other pages and components** follow the same patterns: TanStack Query for data, Zustand for shared state, shadcn/ui for UI, Tailwind for styling.

---

## How to Use This Index with Gemini

1. **Copy this entire file** (or the sections you need) into your Gemini prompt.
2. **Or** upload `GEMINI_INDEX.md` when Gemini supports file upload.
3. **Or** paste individual file blocks when asking about specific features.

Example prompt: *"Here is my full project index [paste GEMINI_INDEX.md]. I want to add [feature X]. Which files should I modify and how?"*

---

*Generated for the virtualfr / Companion monorepo. Update this index when adding significant new files.*
