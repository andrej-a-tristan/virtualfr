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
- **Age gate:** Checkbox “I am 18+”, POST `/api/me/age-gate`; then redirect: no girlfriend → `/onboarding/traits`, else → `/app/chat`.
- **Onboarding (Design Your Girlfriend):**
  - **`/onboarding/traits`** — Single-screen wizard with 6 relationship-style questions (Emotional style, Attachment, Reaction to absence, Communication style, Relationship pace, Cultural personality). Two-column layout on desktop (wizard left, sticky live preview right); mobile stacked. Display name input (default “My Girl”). CTA “Create Her” → POST `/api/girlfriends` with `{ displayName, traits }` → `/onboarding/preview`.
  - **`/onboarding/preview`** — Final persona summary (vibe paragraph + “How she’ll treat you” bullets). Copy: “She’ll open up more as you get closer.” CTA “Start Chat” → `/app/chat`.
  - Traits and display name are persisted in Zustand + localStorage so refresh doesn’t lose progress.
- **Chat:** History + relationship state; POST `/api/chat/send` returns SSE stream (token → message → done); frontend uses `useSSEChat` and streaming UI.
- **Gallery:** Mock images; request image job; view in grid + modal.
- **Billing:** Plan and caps from `/api/billing/status`; checkout URL from `/api/billing/checkout`.
- **Safety:** Report via `/api/moderation/report`; content preferences in Settings.

All state is in-memory keyed by session cookie. Ready to swap in a real DB and auth when you extend.

## Testing the onboarding flow

1. Run backend and frontend (see Development above).
2. Open http://localhost:5173 → Sign up or Log in (any email/password; mock auth).
3. **Age gate:** Check “I am 18+”, click Continue → you are sent to `/onboarding/traits` (no girlfriend yet).
4. **Traits:** Answer all 6 questions, optionally set her name. Click “Create Her” → `/onboarding/preview`.
5. **Preview:** Read the summary, click “Start Chat” → `/app/chat`.
6. Next time you pass the age gate with an existing girlfriend, you go straight to `/app/chat`.
