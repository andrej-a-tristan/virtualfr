# VirtualFR / Companion — Project Index

Up-to-date index of the **virtualfr** repository structure, APIs, and key files.

---

## Project Overview

**Stack:** FastAPI (Python) backend + React (Vite, TypeScript) frontend. Dark-first UI. Mock APIs, SSE chat, in-memory session store.

**Structure:**
- `backend/` — FastAPI app, JSON APIs under `/api/*`
- `frontend/` — Vite + React + TypeScript, TailwindCSS, shadcn/ui, React Router, TanStack Query, Zustand, Zod

**Features:** Auth (signup/login), age gate, onboarding (traits → appearance → preferences → **identity** → generating → preview), girlfriend creation with single portrait + identity (name, job vibe, hobbies, origin vibe) + **identity canon** (backstory, daily_routine, favorites, memory_seeds — deterministically generated), prompt images per question/option (picsum placeholders), chat with SSE streaming, relationship state (trust, intimacy, level), gallery, billing, safety/moderation. **Chat gateway:** `POST /api/chat/stream` proxies to an **internal OpenAI-compatible** `POST /v1/chat/completions` service (mock or vLLM). **Step C:** CPU-only vLLM container in `backend/inference/`; pytest tests in `backend/tests/` hit `/v1/chat/completions`.

---

## File Tree

```
virtualfr/
├── .gitignore
├── README.md
├── GEMINI_INDEX.md          # Legacy full index for Gemini
├── PROJECT_INDEX.md         # This file
├── onboarding_questions.md.txt
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── inference/           # Step C: CPU-only vLLM container
│   │   ├── Dockerfile      # vllm-cpu image; serves /v1/chat/completions on :8000
│   │   └── README.md       # Build, run, point gateway at container
│   ├── tests/
│   │   ├── test_openai_contract.py  # POST /v1/chat/completions (stream=false, stream=true)
│   │   └── test_identity_canon.py   # Identity canon generation tests
│   └── app/
│       ├── main.py
│       ├── mock_main.py        # Internal LLM mock server entrypoint (run on :8001)
│       ├── core/             # config.py, cors.py, auth.py, rate_limit.py, chat_logging.py
│       ├── api/
│       │   ├── store.py      # In-memory sessions + girlfriends
│       │   └── routes/       # health, auth, me, girlfriends, chat, images, billing, moderation, onboarding
│       ├── routers/         # Chat gateway + mock model
│       │   ├── chat.py      # POST /v1/chat/stream (auth, rate limit, SSE proxy, logging)
│       │   └── mock_model.py # POST /v1/chat/completions (OpenAI-like), plus legacy GET /mock-model/stream
│       ├── schemas/          # auth, chat, girlfriend, image, relationship
│       └── utils/            # sse.py, identity_canon.py
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
        ├── routes/           # router.tsx, guards.tsx
        ├── lib/
        │   ├── api/          # client.ts, endpoints.ts, types.ts, zod.ts
        │   ├── constants/    # identity.ts (job vibes, hobbies, city vibes, safe names)
        │   ├── hooks/        # useAuth.ts, useSSEChat.ts
        │   ├── store/        # useAppStore.ts, useChatStore.ts
        │   └── utils.ts
        ├── pages/
        │   # Public
        │   ├── Landing.tsx
        │   ├── Login.tsx
        │   ├── Signup.tsx
        │   # Onboarding (RequireAuth + RequireAgeGate)
        │   ├── OnboardingTraits.tsx
        │   ├── OnboardingAppearance.tsx
        │   ├── OnboardingPreferences.tsx
        │   ├── OnboardingIdentity.tsx   # Name, job vibe, hobbies (3), origin vibe
        │   ├── OnboardingGenerating.tsx
        │   ├── PersonaPreview.tsx    # RequireGirlfriend
        │   # Guarded
        │   ├── AgeGate.tsx
        │   ├── Chat.tsx
        │   ├── Gallery.tsx
        │   ├── Profile.tsx
        │   ├── Settings.tsx
        │   ├── Billing.tsx
        │   ├── Safety.tsx
        └── components/
            ├── chat/         # ChatHeader, Composer, MessageList, RelationshipMeter, etc.
            ├── gallery/      # GalleryGrid, ImageViewerModal
            ├── layout/       # AppShell, SideNav, TopNav, Footer, MobileNav
            ├── onboarding/   # TraitSelector, PersonaPreviewCard, TraitCard, ProgressStepper
            ├── safety/       # ContentPreferences, ReportDialog
            └── ui/           # shadcn: button, card, dialog, input, tabs, etc.
```

---

## Backend API Summary

| Prefix | Route | Method | Description |
|--------|--------|--------|-------------|
| `/api` | `/health` | GET | Health check |
| `/api/auth` | `/signup`, `/login`, `/logout` | POST | Auth (session cookie `session`) |
| `/api/me` | `` | GET | Current user (id, email, age_gate_passed, has_girlfriend) |
| `/api/me` | `/age-gate` | POST | Set age_gate_passed |
| `/api/girlfriends` | `` | POST | Create girlfriend from traits (legacy) |
| `/api/girlfriends` | `/current` | GET | Get current girlfriend |
| `/api/onboarding` | `/prompt-images` | GET | Map of prompt keys → image URLs (question + per-option) |
| `/api/onboarding` | `/complete` | POST | Complete onboarding; body: traits + appearance_prefs + content_prefs + identity; generates identity_canon; returns girlfriend with identity + identity_canon |
| `/api/chat` | `/history` | GET | Chat messages |
| `/api/chat` | `/state` | GET | RelationshipState (trust, intimacy, level, last_interaction_at) |
| `/api/chat` | `/send` | POST | Send message (SSE stream) |
| `/api/images` | `/request`, `/jobs/{id}`, `/gallery` | POST/GET | Image request, job status, gallery |
| `/api/billing` | `/status`, `/checkout` | GET/POST | Plan, caps, checkout URL |
| `/api/moderation` | `/report` | POST | Report |
| `/api/chat` | `/stream` | POST | Chat gateway: SSE stream; Bearer auth; rate limit 30/min; timeouts; JSONL logging |
| `/v1/chat` | `/stream` | POST | Chat gateway (alias): same as `/api/chat/stream` |
| — | `/v1/chat/completions` | POST | Internal LLM contract (OpenAI-like). Served by `app.mock_main` (dev) or vLLM container (Step C). |
| — | `/mock-model/stream` | GET | Legacy mock SSE stream `?text=...` (backward compatible; not used by gateway) |

**Root:** `GET /` returns a small HTML page directing users to the frontend (e.g. localhost:5173) and linking to `/docs`.

---

## Key Schemas (Backend)

- **auth:** SignupRequest, LoginRequest, UserResponse
- **chat:** ChatMessage, SendMessageRequest, **RelationshipState** (trust, intimacy, level, last_interaction_at)
- **girlfriend:** TraitsPayload, AppearancePrefsPayload, ContentPrefsPayload, IdentityPayload (girlfriend_name, job_vibe, hobbies[], origin_vibe), **IdentityCanon** (backstory, daily_routine, favorites{music_vibe, comfort_food, weekend_idea}, memory_seeds[]), OnboardingCompletePayload, GirlfriendResponse (id, name, avatar_url, traits, appearance_prefs, content_prefs, identity, **identity_canon**, created_at)
- **image:** ImageRequestResponse, ImageJobResponse, GalleryItem

---

## Frontend Routes (React Router)

| Path | Guards | Page |
|------|--------|------|
| `/` | — | Landing |
| `/login`, `/signup` | — | Login, Signup |
| `/age-gate` | RequireAuth | AgeGate |
| `/onboarding/traits` | RequireAuth, RequireAgeGate | OnboardingTraits |
| `/onboarding/appearance` | RequireAuth, RequireAgeGate | OnboardingAppearance |
| `/onboarding/preferences` | RequireAuth, RequireAgeGate | OnboardingPreferences |
| `/onboarding/identity` | RequireAuth, RequireAgeGate | OnboardingIdentity (name, job vibe, hobbies, origin vibe) |
| `/onboarding/generating` | RequireAuth, RequireAgeGate | OnboardingGenerating |
| `/onboarding/preview` | RequireAuth, RequireAgeGate, RequireGirlfriend | PersonaPreview |
| `/app/*` | RequireAuth, RequireAgeGate, RequireGirlfriend | AppShell → Chat, Gallery, Profile, Settings, Billing, Safety |

---

## Chat gateway

- **Auth:** `Authorization: Bearer <token>`; token must equal `CHAT_API_KEY` (default `dev-key`). 401 if missing/invalid.
- **Rate limit:** 30 requests/minute per token (in-memory); 429 + `Retry-After` when exceeded.
- **Timeouts:** Overall stream `STREAM_TIMEOUT_SECONDS` (default 60); upstream token wait `UPSTREAM_TOKEN_TIMEOUT_SECONDS` (default 15). On timeout: SSE `event: error` then `event: done`.
- **Logging:** One JSON line per request in `backend/logs/chat.jsonl`: request_id, timestamp_utc, session_id, user_id, client_ip, model, model_version, messages, output_text, num_tokens, latency_ms, status (ok \| error \| timeout \| rate_limited), error_message.
- **Internal contract:** Gateway calls `POST {INTERNAL_LLM_BASE_URL}/v1/chat/completions` (OpenAI streaming style) and **translates** OpenAI `data:` chunks into the app’s SSE contract (`event: token` / `event: done`). Keepalive comments every 15s.
- **Internal auth (optional):** If `INTERNAL_LLM_API_KEY` is set, gateway sends `Authorization: Bearer <key>` to the internal LLM.

---

## Step C: CPU-only inference container + tests

- **`backend/inference/`:** Dockerfile builds a CPU-only vLLM image (base `python:3.12-slim`, `vllm-cpu`, default model `Qwen/Qwen2.5-0.5B-Instruct`). Container runs `vllm serve $MODEL --host 0.0.0.0 --port 8000 --api-key $VLLM_API_KEY` and exposes `POST /v1/chat/completions`. See `backend/inference/README.md` for build/run and how to set `INTERNAL_LLM_BASE_URL` / `INTERNAL_LLM_API_KEY`.
- **`backend/tests/test_openai_contract.py`:** Pytest tests that call `POST {INTERNAL_LLM_BASE_URL}/v1/chat/completions` (default `http://127.0.0.1:8001`). One test uses `stream: false` and asserts 200 and `choices[0].message.content`; one uses `stream: true` and asserts at least one `data: ` line and stream end with `data: [DONE]`. If the server is unreachable, tests skip with a message. Run: `cd backend && export INTERNAL_LLM_BASE_URL=... INTERNAL_LLM_API_KEY=... && pytest -q`.

---

## Identity Canon Generation

When onboarding completes (`POST /api/onboarding/complete`), the backend generates an **identity canon** deterministically from the identity anchors (name, job_vibe, hobbies, origin_vibe) using a seeded random generator.

- **Seed:** `int(sha256(girlfriend_id)[:8], 16)` — ensures consistent output for the same girlfriend.
- **Generator:** `backend/app/utils/identity_canon.py` → `generate_identity_canon()`
- **Output fields:**
  - `backstory` — 2 paragraphs separated by `\n\n`, templated by job_vibe, weaves in hobbies and origin
  - `daily_routine` — templated by job_vibe, includes 1–2 hobbies
  - `favorites` — `{music_vibe, comfort_food, weekend_idea}`; biased by job/hobbies/origin (e.g., nightlife → electronic, beach-town → beach weekend ideas)
  - `memory_seeds` — 3–6 "cute facts" using templates like "I learned {hobby} from someone I admire"
- **Note:** Values and boundaries are **not** included in identity canon; they are handled by the personality engine elsewhere.
- **Tests:** `backend/tests/test_identity_canon.py` (10 tests: determinism, field presence, no values/boundaries, etc.)

---

## Relationship State

Used for chat/companion UX (e.g. RelationshipMeter). Fetched via `GET /api/chat/state`.

- **trust** (number)
- **intimacy** (number)
- **level** (number)
- **last_interaction_at** (string | null)

Currently mocked in `backend/app/api/routes/chat.py` (e.g. trust=72, intimacy=65, level=3).

---

## Store (Zustand)

**useAppStore:** user, girlfriend, onboardingTraits, onboardingAppearance, onboardingContentPrefs, onboardingIdentity; setUser, setGirlfriend, setOnboardingTraits, setOnboardingAppearance, setOnboardingContentPrefs, setGirlfriendName, setJobVibe, toggleHobby, setOriginVibe, clearOnboarding, reset.

**useChatStore:** messages, streamingContent, isStreaming, appendMessage, setStreamingContent, setMessages.

---

## How to Run

- **Internal mock LLM (dev):** `cd backend` then `uvicorn app.mock_main:app --reload --port 8001`
- **vLLM CPU container (Step C):** From `backend/`: `docker build -t virtualfr-vllm-cpu -f inference/Dockerfile .` then `docker run --rm -p 8001:8000 -e MODEL=Qwen/Qwen2.5-0.5B-Instruct -e VLLM_API_KEY=token-abc123 virtualfr-vllm-cpu`
- **Gateway backend:** `cd backend` then `export CHAT_API_KEY=dev-key INTERNAL_LLM_BASE_URL=http://127.0.0.1:8001` (and `INTERNAL_LLM_API_KEY=token-abc123` if using vLLM), then `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- **Frontend:** `cd frontend` then `npm run dev` → e.g. http://localhost:5173
- Open the frontend URL in a browser; API is at http://localhost:8000 (proxy in dev via Vite).
- **Chat gateway test:** `curl -N -X POST http://localhost:8000/api/chat/stream -H "Authorization: Bearer dev-key" -H "Content-Type: application/json" -d '{"session_id":"abc","model":"mock-1","model_version":"2026-02-03","messages":[{"role":"user","content":"Hi"}]}'`
- **OpenAI contract tests:** `cd backend` then `export INTERNAL_LLM_BASE_URL=http://127.0.0.1:8001 INTERNAL_LLM_API_KEY=token-abc123` (if needed) and `pytest -q`

---

*Generated for the virtualfr / Companion repo. Update when adding or changing major features.*
