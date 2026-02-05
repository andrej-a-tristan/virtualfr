# Companion — Monorepo

Production-quality monorepo: **FastAPI** backend + **React (Vite)** frontend. Dark-first, premium UI with mock APIs and SSE chat streaming.

## Structure

- **`/backend`** — FastAPI app: JSON APIs under `/api/*`, optional static frontend at `/` in production.
- **`/frontend`** — Vite + React + TypeScript, TailwindCSS, shadcn/ui, React Router, TanStack Query, Zustand, Zod.

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** and npm

## Development (local)

Run backend and frontend in two terminals.

### Terminal 1 — Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend: **http://localhost:8000**  
API docs: **http://localhost:8000/docs**

### Terminal 2 — Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: **http://localhost:5173**  
Vite proxies `/api` to `http://localhost:8000`, so the app talks to the backend with cookies.

## Production (serve built frontend from FastAPI)

1. Build the frontend:

```bash
cd frontend
npm install
npm run build
```

2. Run FastAPI in production mode (so it serves `frontend/dist` at `/`):

```bash
cd backend
source .venv/bin/activate
export ENV=production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- **App:** http://localhost:8000  
- **APIs:** http://localhost:8000/api/*  
- **Docs:** http://localhost:8000/docs  

CORS and static serving are driven by `backend/app/core/config.py` (e.g. `ENV`, `CORS_ORIGINS`). Copy `backend/.env.example` to `backend/.env` and adjust if needed.

**Supabase and API key:** To connect the backend to Supabase (project URL + anon key) and set an API key for external services (e.g. OpenAI), see **[backend/docs/SETUP_SUPABASE.md](backend/docs/SETUP_SUPABASE.md)**. Put all secrets in `backend/.env`; never commit real keys.

## Scripts summary

| Task              | Command                          |
|-------------------|----------------------------------|
| Frontend dev      | `cd frontend && npm run dev`     |
| Frontend build    | `cd frontend && npm run build`   |
| Backend dev       | `cd backend && uvicorn app.main:app --reload --port 8000` |
| Backend prod      | `ENV=production uvicorn app.main:app --host 0.0.0.0 --port 8000` (after building frontend) |

## Features

- **Auth:** Mock signup/login/logout with session cookie; no database.
- **Age gate:** Checkbox "I am 18+", POST `/api/me/age-gate`; then redirect: no girlfriend → `/onboarding/traits`, else → `/app/chat`.
- **Onboarding (Design Your Girlfriend):**
  - **`/onboarding/traits`** — Single-screen wizard with 6 relationship-style questions (Emotional style, Attachment, Reaction to absence, Communication style, Relationship pace, Cultural personality). Two-column layout on desktop (wizard left, sticky live preview right); mobile stacked. Display name input (default "My Girl"). CTA "Create Her" → POST `/api/girlfriends` with `{ displayName, traits }` → `/onboarding/preview`.
  - **`/onboarding/preview`** — Final persona summary (vibe paragraph + "How she'll treat you" bullets). Copy: "She'll open up more as you get closer." CTA "Start Chat" → `/app/chat`.
  - Traits and display name are persisted in Zustand + localStorage so refresh doesn't lose progress.
- **Chat:** History + relationship state; POST `/api/chat/send` returns SSE stream (token → message → done); frontend uses `useSSEChat` and streaming UI.
- **Gallery:** Mock images; request image job; view in grid + modal.
- **Billing:** Plan and caps from `/api/billing/status`; checkout URL from `/api/billing/checkout`.
- **Safety:** Report via `/api/moderation/report`; content preferences in Settings.

All state is in-memory keyed by session cookie. Ready to swap in a real DB and auth when you extend.

## Testing the onboarding flow

1. Run backend and frontend (see Development above).
2. Open http://localhost:5173 → Sign up or Log in (any email/password; mock auth).
3. **Age gate:** Check "I am 18+", click Continue → you are sent to `/onboarding/traits` (no girlfriend yet).
4. **Traits:** Answer all 6 questions, optionally set her name. Click "Create Her" → `/onboarding/preview`.
5. **Preview:** Read the summary, click "Start Chat" → `/app/chat`.
6. Next time you pass the age gate with an existing girlfriend, you go straight to `/app/chat`.

---

## Chat gateway (v1) — SSE streaming

The backend exposes a **chat gateway** at `POST /v1/chat/stream` with Bearer auth, rate limiting, timeouts, and JSONL logging. The gateway calls an **internal OpenAI-compatible** endpoint (`POST {INTERNAL_LLM_BASE_URL}/v1/chat/completions`), so you can run a mock now and swap in vLLM (or any OpenAI-compatible server) later with no frontend changes.

### Run gateway + internal mock (two terminals)

**Terminal 1 — Internal LLM mock (port 8001)**

```bash
cd backend
uvicorn app.mock_main:app --reload --port 8001
```

**Terminal 2 — Gateway (port 8000)**

```bash
cd backend
export CHAT_API_KEY=dev-key
export INTERNAL_LLM_BASE_URL=http://127.0.0.1:8001
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Test

```bash
curl -N -X POST http://localhost:8000/v1/chat/stream \
  -H "Authorization: Bearer dev-key" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"abc","model":"mock-1","model_version":"2026-02-03","messages":[{"role":"user","content":"Hi"}]}'
```

Use `-N` to disable buffering. You should see `event: token` with `data: {"token":"..."}` and finally `event: done`. The mock responds with "Mock reply: Hi" (or the last user message).

You can later **replace the internal mock with vLLM** (or any server that exposes `POST /v1/chat/completions` with OpenAI-style streaming); set `INTERNAL_LLM_BASE_URL` to that server and optionally `INTERNAL_LLM_API_KEY`.

### Env (optional)

| Env | Default | Description |
|-----|---------|-------------|
| `CHAT_API_KEY` | `dev-key` | Bearer token required by clients |
| `INTERNAL_LLM_BASE_URL` | `http://127.0.0.1:8001` | Base URL of internal LLM (OpenAI-compatible) |
| `INTERNAL_LLM_API_KEY` | *(empty)* | If set, gateway sends `Authorization: Bearer <key>` to internal LLM |
| `STREAM_TIMEOUT_SECONDS` | `60` | Hard limit for the whole stream |
| `UPSTREAM_TOKEN_TIMEOUT_SECONDS` | `15` | Timeout waiting for next token from internal LLM |

### Logs

Each request is logged as one JSON line in **`backend/logs/chat.jsonl`**. Fields: `request_id`, `timestamp_utc`, `session_id`, `user_id`, `client_ip`, `model`, `model_version`, `messages`, `output_text`, `num_tokens`, `latency_ms`, `status`, `error_message`.

---

## Step C: CPU-only inference container

You can run a **CPU-only** inference server (vLLM) locally in Docker. It serves the OpenAI-compatible endpoint:

- `POST /v1/chat/completions`

Then point the gateway (`:8000`) at it via `INTERNAL_LLM_BASE_URL`.

### 1) Build + run the vLLM CPU container (port 8001)

From `virtualfr/backend/`:

```bash
docker build -t virtualfr-vllm-cpu -f inference/Dockerfile .
docker run --rm -p 8001:8000 \
  -e MODEL=Qwen/Qwen2.5-0.5B-Instruct \
  -e VLLM_API_KEY=token-abc123 \
  virtualfr-vllm-cpu
```

CPU inference is slow; a small model is recommended. See `backend/inference/README.md` for details.

### 2) Run the gateway (port 8000) pointed at the container

```bash
cd backend
export CHAT_API_KEY=dev-key
export INTERNAL_LLM_BASE_URL=http://127.0.0.1:8001
export INTERNAL_LLM_API_KEY=token-abc123
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3) Run tests against `/v1/chat/completions`

```bash
cd backend
export INTERNAL_LLM_BASE_URL=http://127.0.0.1:8001
export INTERNAL_LLM_API_KEY=token-abc123
pytest -q
```

If the internal server isn't running, the tests will skip with a message telling you what to start.
