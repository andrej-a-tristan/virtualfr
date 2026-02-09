# VirtualFR — Project Index

> AI companion web app: FastAPI backend + React/Vite frontend.
> Multi-girlfriend support with per-girl chat, gallery, relationship state, and gifting.

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
│       │   ├── config.py          — Settings (env vars, CORS, LLM URL, Stripe, etc.)
│       │   ├── cors.py            — CORS middleware setup
│       │   ├── auth.py            — Auth helpers
│       │   ├── rate_limit.py      — Rate limiting
│       │   ├── chat_logging.py    — JSONL chat logger
│       │   └── supabase_client.py — Supabase client init
│       ├── api/
│       │   ├── store.py           — In-memory session store (multi-girl: messages, gallery, relationship, habits per girlfriend)
│       │   ├── supabase_store.py  — Supabase-backed store
│       │   ├── request_context.py — Request context helpers
│       │   └── routes/
│       │       ├── auth.py        — Signup, login (preserves session data), logout
│       │       ├── billing.py     — Plan status, setup-intent, subscribe, cancel, payment-method, Stripe webhook
│       │       ├── chat.py        — Chat history, state, send (SSE), app_open — all per-girlfriend
│       │       ├── gifts.py       — Gift catalog, checkout (inline Stripe), confirm, history — per-girlfriend
│       │       ├── girlfriends.py — List, create, switch, get current — multi-girl CRUD with plan limits
│       │       ├── health.py      — Health check
│       │       ├── images.py      — Image jobs, gallery — per-girlfriend
│       │       ├── me.py          — Current user, age gate
│       │       ├── memory.py      — Memory summary/items/stats
│       │       ├── moderation.py  — Content reports
│       │       └── onboarding.py  — Prompt images, complete onboarding (first girl)
│       ├── routers/
│       │   ├── chat.py            — Chat gateway (SSE proxy + canon injection, accepts girlfriend_id)
│       │   └── mock_model.py      — Internal mock LLM (/v1/chat/completions)
│       ├── schemas/
│       │   ├── auth.py            — SignupRequest, LoginRequest, UserResponse
│       │   ├── chat.py            — ChatMessage, SendMessageRequest (with girlfriend_id), RelationshipState
│       │   ├── gift.py            — GiftDefinition, GiftCheckoutRequest/Response, GiftHistoryItem
│       │   ├── girlfriend.py      — TraitsPayload, AppearancePrefs, IdentityCanon, GirlfriendListResponse, OnboardingCompletePayload
│       │   ├── image.py           — ImageJobResponse, GalleryItem
│       │   ├── payment_method.py  — PaymentMethodResponse
│       │   └── relationship.py    — Relationship schemas
│       ├── services/
│       │   ├── big_five.py             — Trait → Big Five mapping
│       │   ├── big_five_modulation.py  — Big Five → behavior modulation
│       │   ├── big_five_mapping.json   — Big Five mapping data
│       │   ├── trait_behavior_rules.py — Trait → BehaviorProfile
│       │   ├── gifting.py              — Gift catalog, effects, checkout, webhook handling
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
        │   │   ├── endpoints.ts       — All API call functions (multi-girl, gifts, billing, gallery)
        │   │   ├── types.ts           — TypeScript types (Girlfriend, GirlfriendListResponse, gifts, billing, memory, Big Five)
        │   │   └── zod.ts             — Zod schemas for forms
        │   ├── constants/identity.ts  — Job vibes, hobbies, city vibes, name validation
        │   ├── engines/               — Frontend personality/memory/relationship engines
        │   │   ├── big_five_modulation.ts
        │   │   ├── habits.ts
        │   │   ├── index.ts
        │   │   ├── initiation_engine.ts
        │   │   ├── memory.ts
        │   │   ├── relationship_state.ts
        │   │   └── trait_behavior_rules.ts
        │   ├── hooks/
        │   │   ├── useAuth.ts         — Auth hook (react-query + store)
        │   │   └── useSSEChat.ts      — SSE chat streaming hook (sends girlfriend_id)
        │   ├── onboarding/
        │   │   └── vibe.ts            — Vibe helpers
        │   ├── store/
        │   │   ├── useAppStore.ts     — Main Zustand store (user, girlfriends[], currentGirlfriendId, onboarding, persisted)
        │   │   └── useChatStore.ts    — Chat Zustand store (messages, streaming)
        │   └── utils.ts               — cn() utility
        ├── pages/
        │   ├── Landing.tsx            — Auto-login, redirect to onboarding or chat
        │   ├── Login.tsx              — Email/password login (smart redirect based on user state)
        │   ├── Signup.tsx             — Email/password signup
        │   ├── AgeGate.tsx            — 18+ confirmation
        │   ├── OnboardingAppearance.tsx — Vibe selection (first onboarding page)
        │   ├── appearance/
        │   │   ├── AppearanceAge.tsx          — Age range selection
        │   │   ├── AppearanceEthnicity.tsx    — Ethnicity selection
        │   │   ├── AppearanceBodyDetails.tsx  — Body type + breast + butt (combined)
        │   │   ├── AppearanceHairEyes.tsx     — Hair color + hair style + eyes (combined)
        │   │   ├── AppearanceBody.tsx         — (legacy) Body type
        │   │   ├── AppearanceBreast.tsx       — (legacy) Breast size
        │   │   ├── AppearanceButt.tsx         — (legacy) Butt size
        │   │   ├── AppearanceEyes.tsx         — (legacy) Eye color
        │   │   ├── AppearanceHairColor.tsx    — (legacy) Hair color
        │   │   └── AppearanceHairStyle.tsx    — (legacy) Hair style
        │   ├── OnboardingTraits.tsx      — 6 personality trait questions
        │   ├── OnboardingPreferences.tsx — Spicy photos + age confirmation
        │   ├── OnboardingIdentity.tsx    — Name, job vibe, hobbies, origin
        │   ├── OnboardingGenerating.tsx  — Calls completeOnboarding or createAdditionalGirlfriend, shows spinner
        │   ├── GirlfriendReveal.tsx      — Blurred photo + signup form
        │   ├── SubscriptionPlan.tsx      — 3-tier subscription paywall
        │   ├── RevealSuccess.tsx         — Unblurred photo + "Let's chat" after subscribing
        │   ├── PersonaPreview.tsx        — Final persona summary
        │   ├── Chat.tsx                  — Main chat interface (per-girlfriend history)
        │   ├── Gallery.tsx               — Photo gallery (per-girlfriend)
        │   ├── Profile.tsx               — Girlfriend profile
        │   ├── Settings.tsx              — User settings
        │   ├── Billing.tsx               — Billing/plans management (upgrade, cancel)
        │   ├── PaymentOptions.tsx        — View/update saved card
        │   └── Safety.tsx                — Safety/moderation
        └── components/
            ├── billing/
            │   ├── AddCardModal.tsx        — Stripe Elements card-saving modal
            │   └── UpgradeModal.tsx        — Inline Premium upgrade (uses saved card)
            ├── chat/
            │   ├── ChatHeader.tsx          — Header with avatar, name, girl switcher dropdown, plan badge
            │   ├── Composer.tsx            — Message input + gift button
            │   ├── GiftModal.tsx           — Gift catalog modal with tabs + preview + inline Stripe payment
            │   ├── MessageBubble.tsx       — Message bubble with avatar
            │   ├── MessageList.tsx         — Scrollable message list
            │   ├── ImageMessage.tsx        — Image message display
            │   ├── PaywallInlineCard.tsx   — In-chat paywall card
            │   ├── RelationshipMeter.tsx   — Intimacy-based level meter
            │   └── TypingIndicator.tsx     — Typing animation
            ├── gallery/
            │   ├── GalleryGrid.tsx         — Image grid layout
            │   └── ImageViewerModal.tsx    — Fullscreen image viewer
            ├── layout/
            │   ├── AppShell.tsx            — App shell (fetches & syncs girlfriends list)
            │   ├── SideNav.tsx             — Desktop sidebar with "My Girls" section + girl switcher + create CTA
            │   ├── TopNav.tsx              — Top navigation bar
            │   ├── MobileNav.tsx           — Mobile bottom nav
            │   └── Footer.tsx              — Footer
            ├── onboarding/
            │   ├── AppearanceStepPage.tsx  — Reusable appearance step wrapper
            │   ├── OnboardingSignIn.tsx    — "Sign in" button (hidden in additional-girl mode)
            │   ├── PersonaPreviewCard.tsx  — Companion preview card
            │   ├── ProgressStepper.tsx     — Step progress indicator
            │   ├── TraitCard.tsx           — Single trait option card
            │   └── TraitSelector.tsx       — Trait question + options
            ├── safety/
            │   ├── ContentPreferences.tsx  — Content pref toggles
            │   └── ReportDialog.tsx        — Report content dialog
            └── ui/
                ├── AvatarCircle.tsx        — Avatar with image or gradient initial fallback
                ├── badge.tsx, button.tsx, card.tsx, checkbox.tsx, dialog.tsx
                ├── dropdown-menu.tsx, input.tsx, label.tsx, separator.tsx
                ├── skeleton.tsx, tabs.tsx, tooltip.tsx
```

---

## Backend API Summary

### Auth & User

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/signup` | Create account (mock session cookie) |
| `POST` | `/api/auth/login` | Login (preserves girlfriend/plan data) |
| `POST` | `/api/auth/logout` | Logout (clears all session data) |
| `GET` | `/api/me` | Current user + flags (has_girlfriend, age_gate_passed) |
| `POST` | `/api/me/age-gate` | Set `age_gate_passed = true` |

### Girlfriends (Multi-Girl)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/girlfriends` | List all girlfriends + current_id + girls_max + can_create_more |
| `POST` | `/api/girlfriends` | Create girlfriend (first onboarding, legacy) |
| `GET` | `/api/girlfriends/current` | Get current girlfriend |
| `POST` | `/api/girlfriends/current` | Switch to a different girlfriend |
| `POST` | `/api/girlfriends/create` | Create additional girlfriend (plan-gated: Free=1, Premium=5) |

### Onboarding

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/onboarding/prompt-images` | Prompt key → image URL map |
| `POST` | `/api/onboarding/complete` | Complete onboarding; generates identity canon |

### Chat (per-girlfriend)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/chat/history` | Chat message history (`?girlfriend_id=`) |
| `GET` | `/api/chat/state` | Relationship state (`?girlfriend_id=`) |
| `POST` | `/api/chat/send` | Send message (SSE) — uses `girlfriend_id` from body |
| `POST` | `/api/chat/app_open` | App open event (initiation + jealousy) |
| `POST` | `/api/chat/stream` | Chat gateway: SSE proxy + canon injection (accepts `girlfriend_id`) |

### Images & Gallery (per-girlfriend)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/images/request` | Request AI image job (accepts `girlfriend_id`) |
| `GET` | `/api/images/jobs/{id}` | Image job status |
| `GET` | `/api/images/gallery` | Gallery items (`?girlfriend_id=`) |

### Billing & Payments

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/billing/status` | Plan + caps + girls_max + girls_count |
| `POST` | `/api/billing/setup-intent` | Create Stripe SetupIntent for card saving |
| `POST` | `/api/billing/confirm-card` | Confirm saved card |
| `POST` | `/api/billing/subscribe` | Subscribe to plan (inline, uses saved card) |
| `POST` | `/api/billing/cancel` | Cancel subscription |
| `GET` | `/api/billing/payment-method` | Get saved card details |
| `GET` | `/api/billing/stripe-key` | Get Stripe publishable key |
| `POST` | `/api/billing/checkout` | Create Stripe Checkout session (redirect) |
| `POST` | `/api/billing/webhook` | Stripe webhook handler |

### Gifts (per-girlfriend)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/gifts/list` | Full gift catalog (4 tiers, 28 gifts, €2–€200) |
| `POST` | `/api/gifts/checkout` | Create gift PaymentIntent (inline, saved card) |
| `POST` | `/api/gifts/confirm-payment` | Confirm gift payment |
| `GET` | `/api/gifts/history` | Gift purchase history for current girlfriend |
| `POST` | `/api/gifts/webhook` | Stripe gift webhook |

### Memory

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/memory/summary` | Memory context (facts, emotions, habits) |
| `GET` | `/api/memory/items` | Raw memory items |
| `GET` | `/api/memory/stats` | Memory statistics |

### Other

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/moderation/report` | Report content |
| `POST` | `/v1/chat/completions` | Internal mock LLM (OpenAI contract) |

---

## Multi-Girlfriend Architecture

### Storage (In-Memory)

All per-girlfriend data is keyed by `(session_id, girlfriend_id)`:

| Store | Key | Description |
|-------|-----|-------------|
| `_all_girlfriends` | `session_id → list[dict]` | All girlfriends for a session |
| `_messages` | `(session_id, girlfriend_id)` | Chat messages per girl |
| `_relationship_state` | `(session_id, girlfriend_id)` | Trust, intimacy, level per girl |
| `_habit_profile` | `(session_id, girlfriend_id)` | User habit data per girl |
| `_gallery` | `(session_id, girlfriend_id)` | Gallery images per girl |

### Plan Limits

| Plan | Max Girls |
|------|-----------|
| Free | 1 |
| Plus | 1 |
| Premium | 5 |

### Frontend State

- `useAppStore.girlfriends[]` — all girls (persisted to localStorage)
- `useAppStore.currentGirlfriendId` — active girl (persisted)
- `useAppStore.onboardingMode` — `"first"` or `"additional"` (persisted)
- Girl switching: SideNav "My Girls" section + ChatHeader dropdown
- All queries (chat, gallery, state) include `currentGirlfriendId` in query keys

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
Reveal Success (unblurred photo + "Let's chat")
  ↓
Chat
```

**Additional girl onboarding** (Premium users): Same flow but skips signup/reveal/subscribe. Goes straight from Generating → Chat. Sign-in button is hidden.

---

## Subscription Tiers

| Tier | Price | Tagline | Features |
|------|-------|---------|----------|
| **Free** | €0.00/mo | "Meet [name] and chat to her" | Reveal photo, unlimited messaging |
| **Plus** | €14.99/mo | "Your sweetheart" | Everything in Free, voice messages, 30 photos/month |
| **Premium** | €29.99/mo | "Exclusive relationship" | Everything in Plus, 80 photos/month, up to 5 girls |

---

## Gift System

28 gifts across 4 tiers (Everyday €2–€9, Dates €12–€35, Luxury €60–€140, Legendary €160–€200).

Each gift has:
- Unique emotional effect (stored in memory)
- Relationship boost (trust + intimacy)
- Optional image album reward
- Cooldown (some gifts)

Payment: Inline via saved Stripe card (PaymentIntent), no redirect.

---

## Key Schemas

### Backend (`schemas/girlfriend.py`)

- **TraitsPayload**: `emotional_style`, `attachment_style`, `reaction_to_absence`, `communication_style`, `relationship_pace`, `cultural_personality`
- **AppearancePrefsPayload**: `vibe`, `age_range`, `ethnicity`, `breast_size`, `butt_size`, `hair_color`, `hair_style`, `eye_color`, `body_type`
- **ContentPrefsPayload**: `wants_spicy_photos`
- **IdentityPayload**: `girlfriend_name`, `job_vibe`, `hobbies`, `origin_vibe`
- **IdentityCanon**: `backstory`, `daily_routine`, `favorites` (music_vibe, comfort_food, weekend_idea), `memory_seeds`
- **GirlfriendListResponse**: `girlfriends[]`, `current_girlfriend_id`, `girls_max`, `can_create_more`

### Frontend (`lib/api/types.ts`)

- **User**: `id`, `email`, `display_name`, `age_gate_passed`, `has_girlfriend`, `current_girlfriend_id`
- **Girlfriend**: `id`, `display_name`, `name`, `avatar_url`, `traits`, `appearance_prefs`, `content_prefs`, `identity`, `identity_canon`
- **ChatMessage**: `id`, `role`, `content`, `image_url`, `event_type`
- **RelationshipState**: `trust`, `intimacy`, `level`, `milestones_reached`
- **BillingStatus**: `plan`, `has_card_on_file`, `message_cap`, `image_cap`, `girls_max`, `girls_count`, `can_create_more_girls`
- **GiftDefinition**: `id`, `name`, `price_eur`, `tier`, `relationship_boost`, `unique_effect_name`, `unique_effect_description`, `cooldown_days`
- **BigFive**: `openness`, `conscientiousness`, `extraversion`, `agreeableness`, `neuroticism` (0–100)

---

## Zustand Stores

### `useAppStore` (persisted to localStorage)

- `user`, `girlfriend` — current session
- `girlfriends[]`, `currentGirlfriendId` — multi-girl state (persisted)
- `onboardingMode` — `"first"` | `"additional"` (persisted)
- `onboardingDraft` — legacy trait draft
- `onboardingTraits`, `onboardingAppearance`, `onboardingContentPrefs`, `onboardingIdentity` — extended onboarding state (all persisted)
- `setGirlfriends()`, `setCurrentGirlfriend()`, `addGirlfriend()` — multi-girl actions
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
- **Relationship tracking** — trust/intimacy/level with decay and milestones (per-girlfriend)
- **Memory system** — factual + emotional memory extraction and context building
- **Habit profiling** — preferred hours, typical message gaps (per-girlfriend)
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
| `STRIPE_SECRET_KEY` | — | Stripe secret key (test mode) |
| `STRIPE_WEBHOOK_SECRET` | — | Stripe webhook signing secret |
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
uvicorn app.main:app --host 0.0.0.0 --port 8000

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
