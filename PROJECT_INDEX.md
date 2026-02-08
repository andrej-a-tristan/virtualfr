# VirtualFR — Project Index

> AI companion web app: FastAPI backend + React/Vite frontend.

---

## File Tree

```
virtualfr/
├── .gitignore
├── README.md
├── PROJECT_INDEX.md
├── onboarding_questions.md.txt
│
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── supabase_schema.sql
│   ├── docs/
│   │   ├── BIG_FIVE_MIGRATION.md
│   │   └── SETUP_SUPABASE.md
│   ├── inference/
│   │   ├── Dockerfile
│   │   └── README.md
│   ├── scripts/
│   │   ├── check_api_key.py
│   │   └── check_config.py
│   ├── tests/
│   │   ├── test_chat_canon_injection.py
│   │   ├── test_identity_canon.py
│   │   └── test_openai_contract.py
│   ├── logs/
│   │   └── chat.jsonl
│   └── app/
│       ├── main.py
│       ├── mock_main.py
│       ├── core/
│       │   ├── config.py          — Settings (env vars, CORS, LLM URL, etc.)
│       │   ├── cors.py            — CORS middleware setup
│       │   ├── auth.py            — Auth helpers
│       │   ├── rate_limit.py      — Rate limiting
│       │   ├── chat_logging.py    — JSONL chat logger
│       │   └── supabase_client.py — Supabase client init
│       ├── api/
│       │   ├── store.py           — In-memory session/girlfriend store
│       │   ├── supabase_store.py  — Supabase-backed store
│       │   ├── request_context.py — Request context helpers
│       │   └── routes/
│       │       ├── auth.py        — Signup, login, logout
│       │       ├── billing.py     — Plan status, checkout
│       │       ├── chat.py        — Chat history, state, send, app_open
│       │       ├── girlfriends.py — Create/get girlfriend
│       │       ├── health.py      — Health check
│       │       ├── images.py      — Image jobs, gallery
│       │       ├── me.py          — Current user, age gate
│       │       ├── memory.py      — Memory summary/items/stats
│       │       ├── moderation.py  — Content reports
│       │       └── onboarding.py  — Prompt images, complete onboarding
│       ├── routers/
│       │   ├── chat.py            — Chat gateway (SSE proxy + canon injection)
│       │   └── mock_model.py      — Internal mock LLM (/v1/chat/completions)
│       ├── schemas/
│       │   ├── auth.py            — SignupRequest, LoginRequest, UserResponse
│       │   ├── chat.py            — ChatMessage, SendMessageRequest, RelationshipState
│       │   ├── girlfriend.py      — TraitsPayload, AppearancePrefs, IdentityCanon, etc.
│       │   ├── image.py           — ImageJobResponse, GalleryItem
│       │   └── relationship.py    — Relationship schemas
│       ├── services/
│       │   ├── big_five.py             — Trait → Big Five mapping
│       │   ├── big_five_modulation.py  — Big Five → behavior modulation
│       │   ├── trait_behavior_rules.py — Trait → BehaviorProfile
│       │   ├── relationship_state.py   — Trust/intimacy/level tracking, decay, milestones
│       │   ├── memory.py               — Factual & emotional memory extraction/context
│       │   ├── habits.py               — User habit profiling
│       │   ├── initiation_engine.py    — Girlfriend-initiated messages
│       │   └── time_utils.py           — Time helpers
│       └── utils/
│           ├── identity_canon.py  — Deterministic identity canon generation
│           ├── prompt_identity.py — Builds canon system prompt for LLM injection
│           ├── moderation.py      — Content moderation
│           └── sse.py             — SSE event formatter
│
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.ts
    ├── tsconfig.json
    ├── public/assets/
    │   └── companion-avatar.png
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── styles/globals.css        — Theme (dark, pink primary)
        ├── routes/
        │   ├── router.tsx             — All routes
        │   └── guards.tsx             — RequireAuth, RequireAgeGate, RequireGirlfriend
        ├── lib/
        │   ├── api/
        │   │   ├── client.ts          — Axios/fetch wrapper
        │   │   ├── endpoints.ts       — All API call functions
        │   │   ├── types.ts           — TypeScript types
        │   │   └── zod.ts             — Zod schemas for forms
        │   ├── constants/identity.ts  — Job vibes, hobbies, city vibes, name validation
        │   ├── engines/               — Frontend personality/memory/relationship engines
        │   ├── hooks/
        │   │   ├── useAuth.ts         — Auth hook (react-query + store)
        │   │   └── useSSEChat.ts      — SSE chat streaming hook
        │   ├── store/
        │   │   ├── useAppStore.ts     — Main Zustand store (user, girlfriend, onboarding)
        │   │   └── useChatStore.ts    — Chat Zustand store (messages, streaming)
        │   └── utils.ts               — cn() utility
        ├── pages/
        │   ├── Landing.tsx            — Auto-login, redirect to onboarding or chat
        │   ├── Login.tsx              — Email/password login
        │   ├── Signup.tsx             — Email/password signup
        │   ├── AgeGate.tsx            — 18+ confirmation
        │   ├── OnboardingAppearance.tsx — Vibe selection (first onboarding page)
        │   ├── appearance/
        │   │   ├── AppearanceAge.tsx          — Age range selection
        │   │   ├── AppearanceEthnicity.tsx    — Ethnicity selection
        │   │   ├── AppearanceBodyDetails.tsx  — Body type + breast + butt (combined)
        │   │   └── AppearanceHairEyes.tsx     — Hair color + hair style + eyes (combined)
        │   ├── OnboardingTraits.tsx      — 6 personality trait questions
        │   ├── OnboardingPreferences.tsx — Spicy photos + age confirmation
        │   ├── OnboardingIdentity.tsx    — Name, job vibe, hobbies, origin
        │   ├── OnboardingGenerating.tsx  — Calls completeOnboarding, shows spinner
        │   ├── GirlfriendReveal.tsx      — Blurred photo + signup form
        │   ├── SubscriptionPlan.tsx      — 3-tier subscription paywall
        │   ├── PersonaPreview.tsx        — Final persona summary
        │   ├── Chat.tsx                  — Main chat interface
        │   ├── Gallery.tsx               — Photo gallery
        │   ├── Profile.tsx               — Girlfriend profile
        │   ├── Settings.tsx              — User settings
        │   ├── Billing.tsx               — Billing/plans
        │   └── Safety.tsx                — Safety/moderation
        └── components/
            ├── onboarding/
            │   ├── AppearanceStepPage.tsx   — Reusable appearance step wrapper
            │   ├── OnboardingSignIn.tsx     — Persistent "Sign in" button (fixed, top-right)
            │   ├── PersonaPreviewCard.tsx   — Companion preview card
            │   ├── ProgressStepper.tsx      — Step progress indicator
            │   ├── TraitCard.tsx            — Single trait option card
            │   └── TraitSelector.tsx        — Trait question + options
            ├── chat/
            │   ├── ChatHeader.tsx           — Header with avatar + name
            │   ├── Composer.tsx             — Message input
            │   ├── MessageBubble.tsx        — Message bubble with avatar
            │   ├── MessageList.tsx          — Scrollable message list
            │   ├── ImageMessage.tsx         — Image message display
            │   ├── PaywallInlineCard.tsx    — In-chat paywall card
            │   ├── RelationshipMeter.tsx    — Trust/intimacy meter
            │   └── TypingIndicator.tsx      — Typing animation
            ├── gallery/
            │   ├── GalleryGrid.tsx          — Image grid layout
            │   └── ImageViewerModal.tsx     — Fullscreen image viewer
            ├── layout/
            │   ├── AppShell.tsx             — App shell with side/top nav
            │   ├── SideNav.tsx              — Desktop sidebar
            │   ├── TopNav.tsx               — Top navigation bar
            │   ├── MobileNav.tsx            — Mobile bottom nav
            │   └── Footer.tsx               — Footer
            ├── safety/
            │   ├── ContentPreferences.tsx   — Content pref toggles
            │   └── ReportDialog.tsx         — Report content dialog
            └── ui/                          — shadcn/ui primitives
```

---

## Backend API Summary

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/auth/signup` | Create account (mock session cookie) |
| `POST` | `/api/auth/login` | Login (mock session cookie) |
| `POST` | `/api/auth/logout` | Logout (clear cookie) |
| `GET` | `/api/me` | Current user + flags |
| `POST` | `/api/me/age-gate` | Set `age_gate_passed = true` |
| `POST` | `/api/girlfriends` | Create girlfriend (legacy) |
| `GET` | `/api/girlfriends/current` | Get current girlfriend |
| `GET` | `/api/onboarding/prompt-images` | Prompt key → image URL map |
| `POST` | `/api/onboarding/complete` | Complete onboarding; generates identity canon |
| `GET` | `/api/chat/history` | Chat message history |
| `GET` | `/api/chat/state` | Relationship state (trust, intimacy, level) |
| `POST` | `/api/chat/send` | Send message (SSE) |
| `POST` | `/api/chat/app_open` | App open event (initiation + jealousy) |
| `POST` | `/api/chat/stream` | Chat gateway: SSE proxy + canon injection |
| `GET` | `/api/memory/summary` | Memory context (facts, emotions, habits) |
| `GET` | `/api/memory/items` | Raw memory items |
| `GET` | `/api/memory/stats` | Memory statistics |
| `POST` | `/api/images/request` | Request AI image job |
| `GET` | `/api/images/jobs/{id}` | Image job status |
| `GET` | `/api/images/gallery` | Gallery items |
| `GET` | `/api/billing/status` | Plan + caps |
| `POST` | `/api/billing/checkout` | Checkout URL |
| `POST` | `/api/moderation/report` | Report content |
| `POST` | `/v1/chat/completions` | Internal mock LLM (OpenAI contract) |

---

## Onboarding Flow

```
Landing (auto-login)
  ↓
Appearance: Vibe → Age → Ethnicity → Body (type + breast + butt) → Hair & Eyes (color + style + eyes)
  ↓
Traits (6 personality questions)
  ↓
Preferences (spicy photos + age check if yes)
  ↓
Identity (name, job vibe, hobbies, origin)
  ↓
Generating (POST /api/onboarding/complete)
  ↓
Reveal (blurred photo + signup form)
  ↓
Subscribe (Free / Plus / Premium tiers)
  ↓
Chat
```

**Sign in** button is visible on every onboarding page (top-right, fixed) so returning users can skip to login.

---

## Subscription Tiers

| Tier | Price | Tagline | Features |
|------|-------|---------|----------|
| **Free** | €0.00/mo | "Meet [name] and chat to her" | Reveal photo, Unlimited messaging |
| **Plus** | €14.99/mo | "Your sweetheart" | Everything in Free, Voice messages, 30 photos/month, Nude photos |
| **Premium** | €29.99/mo | "Exclusive relationship" | Everything in Plus, 80 photos/month, More intimate moments, More nude photos |

---

## Key Schemas

### Backend (`schemas/girlfriend.py`)

- **TraitsPayload**: `emotional_style`, `attachment_style`, `reaction_to_absence`, `communication_style`, `relationship_pace`, `cultural_personality`
- **AppearancePrefsPayload**: `vibe`, `age_range`, `ethnicity`, `breast_size`, `butt_size`, `hair_color`, `hair_style`, `eye_color`, `body_type`
- **ContentPrefsPayload**: `wants_spicy_photos`
- **IdentityPayload**: `girlfriend_name`, `job_vibe`, `hobbies`, `origin_vibe`
- **IdentityCanon**: `backstory`, `daily_routine`, `favorites` (music_vibe, comfort_food, weekend_idea), `memory_seeds`

### Frontend (`lib/api/types.ts`)

- **User**: `id`, `email`, `display_name`, `age_gate_passed`, `has_girlfriend`
- **Girlfriend**: `id`, `display_name`, `name`, `avatar_url`, `traits`, `appearance_prefs`, `content_prefs`, `identity`, `identity_canon`
- **ChatMessage**: `id`, `role`, `content`, `image_url`, `event_type`
- **RelationshipState**: `trust`, `intimacy`, `level`, `milestones_reached`
- **BigFive**: `openness`, `conscientiousness`, `extraversion`, `agreeableness`, `neuroticism` (0–100)

---

## Zustand Stores

### `useAppStore` (persisted to localStorage)

- `user`, `girlfriend` — current session
- `onboardingDraft` — legacy trait draft
- `onboardingTraits`, `onboardingAppearance`, `onboardingContentPrefs`, `onboardingIdentity` — extended onboarding state (all persisted)
- `clearOnboarding()` — resets all onboarding state

### `useChatStore`

- `messages`, `streamingContent`, `isStreaming`

---

## Identity Canon Generation

Deterministic, seeded from `girlfriend_name + job_vibe + hobbies + origin_vibe`.

Generates:
- **Backstory** — 2-paragraph character backstory
- **Daily routine** — typical day description
- **Favorites** — music_vibe, comfort_food, weekend_idea
- **Memory seeds** — 3–6 conversation starters

Canon is injected as a system message into every LLM chat request via `build_girlfriend_canon_system_prompt()`.

---

## Personality Engine

- **Trait → Big Five mapping** (`services/big_five.py`)
- **Big Five → behavior modulation** (`services/big_five_modulation.py`)
- **Trait → BehaviorProfile** (`services/trait_behavior_rules.py`)
- **Relationship tracking** — trust/intimacy/level with decay and milestones
- **Memory system** — factual + emotional memory extraction and context building
- **Habit profiling** — preferred hours, typical message gaps
- **Initiation engine** — girlfriend-initiated messages based on relationship state

---

## Configuration

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_MOCK_MODEL` | `true` | Use internal mock LLM |
| `INTERNAL_LLM_BASE_URL` | `http://127.0.0.1:8000` | LLM endpoint |
| `INTERNAL_LLM_PATH` | `/v1/chat/completions` | LLM path |
| `INTERNAL_LLM_API_KEY` | — | Optional LLM auth |
| `API_KEY` | — | External API key |
| `CHAT_API_KEY` | `dev-key` | Chat gateway auth |
| `SUPABASE_URL` | — | Supabase URL (optional) |
| `SUPABASE_ANON_KEY` | — | Supabase key (optional) |

### Frontend (`vite.config.ts`)

- Dev server: `http://localhost:5173`
- API proxy: `/api` → `http://localhost:8000`
- Path alias: `@` → `./src`

---

## How to Run

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in browser.

---

## Tests

```bash
cd backend
pytest tests/ -v
```

- **test_identity_canon.py** — 10 tests: determinism, field validation, edge cases
- **test_chat_canon_injection.py** — 4 tests: injection with/without girlfriend, message preservation
- **test_openai_contract.py** — 2 tests: LLM stream/non-stream contract
