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

## Scripts summary

| Task              | Command                          |
|-------------------|----------------------------------|
| Frontend dev      | `cd frontend && npm run dev`     |
| Frontend build    | `cd frontend && npm run build`   |
| Backend dev       | `cd backend && uvicorn app.main:app --reload --port 8000` |
| Backend prod      | `ENV=production uvicorn app.main:app --host 0.0.0.0 --port 8000` (after building frontend) |

## Features

- **Auth:** Mock signup/login/logout with session cookie; no database.
- **Age gate:** POST `/api/me/age-gate`; guarded routes redirect as needed.
- **Onboarding:** 6 traits (emotional style, attachment, jealousy, tone, intimacy pace, cultural personality); create girlfriend; preview then go to chat.
- **Chat:** History + relationship state; POST `/api/chat/send` returns SSE stream (token → message → done); frontend uses `useSSEChat` and streaming UI.
- **Gallery:** Mock images; request image job; view in grid + modal.
- **Billing:** Plan and caps from `/api/billing/status`; checkout URL from `/api/billing/checkout`.
- **Safety:** Report via `/api/moderation/report`; content preferences in Settings.

All state is in-memory keyed by session cookie. Ready to swap in a real DB and auth when you extend.
