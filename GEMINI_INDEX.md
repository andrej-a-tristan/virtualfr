# VirtualFR Project Index

**Comprehensive documentation of the VirtualFR codebase structure, APIs, and architecture.**

---

## 1. Project Overview

**VirtualFR** is an AI-powered virtual girlfriend companion application built as a monorepo with a FastAPI backend and React frontend. The app provides:

- **Onboarding Flow**: Multi-step persona creation (traits, appearance, identity, preferences)
- **Chat System**: Real-time SSE streaming chat with personality-aware responses
- **Relationship Engine**: Dynamic trust/intimacy system with relationship levels (STRANGER → FAMILIAR → CLOSE → INTIMATE → EXCLUSIVE)
- **Memory System**: Long-term factual and emotional memory extraction from conversations
- **Gifting System**: Stripe-powered gift purchases (€2–€200) with unique effects and relationship boosts
- **Billing**: Stripe subscriptions (Free, Plus, Premium tiers) with message/image caps
- **Personality Engines**: Big Five personality mapping, trait behavior rules, initiation engine, habit profiling
- **Gallery**: Image generation and storage
- **Safety & Moderation**: Content preferences and reporting

**Tech Stack:**
- **Backend**: FastAPI (Python 3.11+), Supabase (optional PostgreSQL), Stripe
- **Frontend**: React 18, Vite, TypeScript, TailwindCSS, shadcn/ui, React Router, TanStack Query, Zustand
- **LLM**: OpenAI-compatible API gateway (supports mock, vLLM, or OpenAI)

---

## 2. Directory Structure

```
virtualfr/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/          # API route handlers
│   │   │   ├── store.py         # In-memory session store
│   │   │   └── supabase_store.py # Supabase persistence layer
│   │   ├── core/                # Core config, auth, CORS, rate limiting
│   │   ├── routers/             # Chat gateway, mock model
│   │   ├── schemas/             # Pydantic models
│   │   ├── services/            # Business logic engines
│   │   ├── utils/               # Utilities (SSE, moderation, identity canon)
│   │   └── main.py              # FastAPI app entry point
│   ├── docs/                    # Setup guides
│   ├── inference/               # Docker inference container
│   ├── logs/                    # Chat JSONL logs
│   ├── scripts/                 # Utility scripts
│   ├── tests/                   # Test suite
│   ├── supabase_schema.sql      # Database schema
│   ├── requirements.txt         # Python dependencies
│   └── .env.example             # Environment template
│
└── frontend/
    ├── src/
    │   ├── components/          # React components
    │   │   ├── billing/        # Stripe card collection
    │   │   ├── chat/           # Chat UI components
    │   │   ├── gallery/        # Image gallery
    │   │   ├── layout/         # App shell, nav, footer
    │   │   ├── onboarding/     # Onboarding wizard components
    │   │   ├── safety/         # Content preferences, reporting
    │   │   └── ui/              # shadcn/ui components
    │   ├── lib/
    │   │   ├── api/            # API client, endpoints, types
    │   │   ├── engines/        # Frontend personality engines (mirrors backend)
    │   │   ├── hooks/          # React hooks (auth, SSE chat)
    │   │   ├── store/          # Zustand stores
    │   │   └── constants/      # Identity constants
    │   ├── pages/              # Route pages
    │   ├── routes/             # React Router config + guards
    │   └── styles/             # Global CSS
    ├── package.json
    └── vite.config.ts
```

---

## 3. Backend (FastAPI)

### 3.1 API Routes (`backend/app/api/routes/`)

All routes are mounted under `/api` prefix.

#### **`auth.py`** — Authentication
- `POST /api/auth/signup` — Mock signup (sets session cookie)
- `POST /api/auth/login` — Mock login (sets session cookie)
- `POST /api/auth/logout` — Clear session cookie

#### **`me.py`** — Current User
- `GET /api/me` — Get current user + flags (age_gate_passed, has_girlfriend)
- `POST /api/me/age-gate` — Set age_gate_passed=True

#### **`girlfriends.py`** — Girlfriend CRUD
- `POST /api/girlfriends` — Create girlfriend from displayName + traits
- `GET /api/girlfriends/current` — Get current girlfriend (404 if none)

#### **`chat.py`** — Chat System
- `GET /api/chat/history` — Get message history
- `GET /api/chat/state` — Get relationship state (trust, intimacy, level)
- `POST /api/chat/send` — Send message (SSE stream response)
- `POST /api/chat/app_open` — App open handler (initiation + jealousy reactions)

#### **`onboarding.py`** — Onboarding
- `GET /api/onboarding/prompt-images` — Get prompt image URLs for appearance steps
- `POST /api/onboarding/complete` — Finalize onboarding (create girlfriend with identity canon)

#### **`billing.py`** — Stripe Billing
- `GET /api/billing/status` — Get plan, caps, card status
- `POST /api/billing/setup-intent` — Create Stripe SetupIntent for card saving
- `POST /api/billing/subscribe` — Create subscription (plus/premium)
- `POST /api/billing/cancel` — Cancel subscription
- `POST /api/billing/webhook` — Stripe webhook handler
- `POST /api/billing/confirm-card` — Optimistic card confirmation

#### **`gifts.py`** — Gift System
- `GET /api/gifts/list` — Get full gift catalog
- `POST /api/gifts/checkout` — Create Stripe Checkout Session for gift
- `POST /api/gifts/webhook` — Stripe webhook for gift payments
- `GET /api/gifts/history` — Get gift purchase history

#### **`images.py`** — Image Generation
- `POST /api/images/request` — Request image generation (returns job_id)
- `GET /api/images/jobs/{job_id}` — Get job status
- `GET /api/images/gallery` — Get gallery items

#### **`memory.py`** — Memory System
- `GET /api/memory/summary` — Get compact memory context (facts, emotions, habits)
- `GET /api/memory/items` — Get raw memory items (factual/emotional)
- `GET /api/memory/stats` — Get memory statistics

#### **`moderation.py`** — Safety
- `POST /api/moderation/report` — Report content

#### **`health.py`** — Health Check
- `GET /api/health` — Health check endpoint

### 3.2 Chat Gateway (`backend/app/routers/chat.py`)

**External-facing OpenAI-compatible gateway:**

- `POST /v1/chat/stream` — SSE streaming chat endpoint
  - Auth: Bearer token (`CHAT_API_KEY`)
  - Rate limit: 30/min per token
  - Proxies to internal LLM (`INTERNAL_LLM_BASE_URL`)
  - Logs to `backend/logs/chat.jsonl`
  - Injects girlfriend identity canon system prompt

### 3.3 Services (`backend/app/services/`)

#### **`relationship_state.py`**
- `create_initial_relationship_state()` — Initialize trust=10, intimacy=5, level=STRANGER
- `calculate_relationship_level(intimacy)` — Map intimacy to level
- `register_interaction()` — Update trust/intimacy on message
- `apply_inactivity_decay()` — Decay intimacy after 24h/72h inactivity
- `get_jealousy_reaction()` — Generate jealousy messages based on absence
- `check_for_milestone_event()` — Detect level transitions

#### **`memory.py`**
- `build_memory_context()` — Build compact context for prompts (facts, emotions, habits)
- `write_memories_from_message()` — Extract factual/emotional memories from user messages
- `get_factual_memory()` — Query factual memory items
- `get_emotional_memory()` — Query emotional memory items
- `get_memory_summary()` — Get memory statistics

#### **`gifting.py`**
- `get_gift_catalog()` — Return full gift catalog (24 gifts, €2–€200)
- `get_gift_by_id()` — Get gift by ID
- `validate_cooldown()` — Check gift cooldown (14–60 days for rare gifts)
- `create_checkout_session()` — Create Stripe Checkout Session
- `apply_relationship_boost()` — Apply trust/intimacy boost
- `produce_gift_reaction_message()` — Generate personality-aware gift reaction
- `build_memory_summary()` — Create memory entry for gift

#### **`initiation_engine.py`**
- `should_initiate_conversation()` — Decide if girlfriend should initiate
- `get_initiation_message()` — Generate initiation message based on level/attachment

#### **`habits.py`**
- `build_habit_profile()` — Analyze user message timestamps (preferred hours, typical gap)

#### **`big_five.py`**
- `map_traits_to_big_five()` — Map 6 onboarding traits to Big Five scores (0.0–1.0)
- `big_five_to_description()` — Convert scores to human-readable description

#### **`big_five_modulation.py`**
- Modulate Big Five scores based on relationship level and interactions

#### **`trait_behavior_rules.py`**
- Trait-specific behavior rules for personality expression

### 3.4 Schemas (`backend/app/schemas/`)

- **`auth.py`**: `SignupRequest`, `LoginRequest`, `UserResponse`
- **`chat.py`**: `SendMessageRequest`, `AppOpenRequest`, `ChatMessage`, `RelationshipState`
- **`girlfriend.py`**: `CreateGirlfriendRequest`, `GirlfriendResponse`, `IdentityResponse`, `OnboardingCompletePayload`
- **`gift.py`**: `GiftDefinition`, `RelationshipBoost`, `ImageReward`
- **`image.py`**: `ImageRequestResponse`, `ImageJobResponse`, `GalleryItem`
- **`relationship.py`**: Relationship state models

### 3.5 Core (`backend/app/core/`)

- **`config.py`**: Settings from environment (Supabase, Stripe, LLM URLs, CORS)
- **`auth.py`**: Chat gateway Bearer token auth
- **`cors.py`**: CORS middleware setup
- **`rate_limit.py`**: Rate limiting (30/min per token)
- **`supabase_client.py`**: Supabase admin client initialization
- **`chat_logging.py`**: JSONL chat log writer

### 3.6 Store (`backend/app/api/store.py`)

In-memory session store (falls back to Supabase if configured):
- `get_session_user()` — Get user by session ID
- `set_session_user()` — Update user data
- `get_girlfriend()` — Get girlfriend data
- `set_girlfriend()` — Set girlfriend data
- `get_relationship_state()` — Get relationship state
- `set_relationship_state()` — Update relationship state
- `get_messages()` — Get message history
- `append_message()` — Append message
- `get_habit_profile()` — Get habit profile
- `set_habit_profile()` — Update habit profile

### 3.7 Database Schema (`backend/supabase_schema.sql`)

**Tables:**
- `sessions` — Session persistence (user_id, email, current_girlfriend_id)
- `users_profile` — User profile extensions (language_pref)
- `girlfriends` — Girlfriend records (traits, display_name)
- `messages` — Chat messages (role, content, image_url, event_type)
- `relationship_state` — Trust/intimacy/level/milestones
- `habit_profile` — User habits + Big Five scores
- `factual_memory` — Stable facts about user (name, city, preferences)
- `emotional_memory` — Emotional events (stress, affection, etc.)
- `memory_notes` — Optional manual notes
- `gift_purchases` — Gift purchase records
- `moment_cards` — Keepsake cards from gifts

**RLS**: All tables have Row Level Security (user owns rows)

---

## 4. Frontend (React/Vite/TypeScript)

### 4.1 Pages (`frontend/src/pages/`)

#### **Auth & Onboarding**
- `Landing.tsx` — Landing page
- `Login.tsx` — Login page
- `Signup.tsx` — Signup page
- `AgeGate.tsx` — Age verification gate
- `OnboardingTraits.tsx` — Trait selection (6 questions)
- `OnboardingAppearance.tsx` — Appearance wizard entry
- `AppearanceAge.tsx` — Age range selection
- `AppearanceEthnicity.tsx` — Ethnicity selection
- `AppearanceBodyDetails.tsx` — Body type, breast, butt size
- `AppearanceHairEyes.tsx` — Hair color/style, eye color
- `OnboardingPreferences.tsx` — Content preferences (spicy photos)
- `OnboardingIdentity.tsx` — Identity (name, job, hobbies, origin)
- `OnboardingGenerating.tsx` — Loading state during generation
- `GirlfriendReveal.tsx` — Reveal animation
- `SubscriptionPlan.tsx` — Subscription selection
- `RevealSuccess.tsx` — Success page
- `PersonaPreview.tsx` — Final persona preview

#### **App Pages** (under `/app`)
- `Chat.tsx` — Main chat interface with SSE streaming
- `Gallery.tsx` — Image gallery grid
- `Profile.tsx` — Girlfriend profile
- `Settings.tsx` — User settings
- `Billing.tsx` — Billing management (Stripe card, subscriptions)
- `Safety.tsx` — Content preferences and reporting

### 4.2 Components (`frontend/src/components/`)

#### **Chat**
- `ChatHeader.tsx` — Chat header with girlfriend info
- `Composer.tsx` — Message input
- `MessageBubble.tsx` — Message display
- `MessageList.tsx` — Message list container
- `GiftModal.tsx` — Gift purchase modal
- `RelationshipMeter.tsx` — Trust/intimacy visualization
- `TypingIndicator.tsx` — Typing animation
- `ImageMessage.tsx` — Image message display
- `PaywallInlineCard.tsx` — Paywall card for free tier limits

#### **Onboarding**
- `TraitSelector.tsx` — Trait selection UI
- `TraitCard.tsx` — Individual trait card
- `PersonaPreviewCard.tsx` — Live persona preview
- `ProgressStepper.tsx` — Onboarding progress indicator
- `AppearanceStepPage.tsx` — Appearance step wrapper
- `OnboardingSignIn.tsx` — Sign-in prompt during onboarding

#### **Billing**
- `AddCardModal.tsx` — Stripe card collection modal

#### **Gallery**
- `GalleryGrid.tsx` — Image grid display
- `ImageViewerModal.tsx` — Full-screen image viewer

#### **Layout**
- `AppShell.tsx` — Main app layout wrapper
- `TopNav.tsx` — Top navigation bar
- `SideNav.tsx` — Side navigation
- `MobileNav.tsx` — Mobile navigation
- `Footer.tsx` — Footer component

#### **Safety**
- `ContentPreferences.tsx` — Content preference settings
- `ReportDialog.tsx` — Report dialog

#### **UI** (shadcn/ui)
- `AvatarCircle.tsx`, `badge.tsx`, `button.tsx`, `card.tsx`, `checkbox.tsx`, `dialog.tsx`, `dropdown-menu.tsx`, `input.tsx`, `label.tsx`, `separator.tsx`, `skeleton.tsx`, `tabs.tsx`, `tooltip.tsx`

### 4.3 Lib (`frontend/src/lib/`)

#### **API Client** (`lib/api/`)
- **`client.ts`**: `apiGet()`, `apiPost()` helpers with cookie auth
- **`endpoints.ts`**: All API endpoint functions (signup, login, chat, gifts, etc.)
- **`types.ts`**: TypeScript types matching backend schemas
- **`zod.ts`**: Zod validation schemas

#### **Engines** (`lib/engines/`)
Frontend mirrors of backend personality engines:
- `relationship_state.ts` — Relationship level calculation
- `initiation_engine.ts` — Initiation logic
- `habits.ts` — Habit profiling
- `memory.ts` — Memory context building
- `trait_behavior_rules.ts` — Trait behavior rules
- `big_five_modulation.ts` — Big Five modulation

#### **Hooks** (`lib/hooks/`)
- `useAuth.ts` — Authentication hook (getMe, logout)
- `useSSEChat.ts` — SSE chat streaming hook

#### **Stores** (`lib/store/`)
- `useAppStore.ts` — Global app state (user, girlfriend, onboarding progress)
- `useChatStore.ts` — Chat state (messages, relationship state)

#### **Constants** (`lib/constants/`)
- `identity.ts` — Identity-related constants

### 4.4 Routing (`frontend/src/routes/`)

- **`router.tsx`**: React Router config with route definitions
- **`guards.tsx`**: Route guards (`RequireAuth`, `RequireAgeGate`, `RequireGirlfriend`)

**Route Structure:**
- `/` — Landing
- `/login`, `/signup` — Auth
- `/age-gate` — Age gate (requires auth)
- `/onboarding/*` — Onboarding flow (requires auth + age gate)
- `/app/*` — App pages (requires auth + age gate + girlfriend)
  - `/app/chat` — Chat
  - `/app/gallery` — Gallery
  - `/app/profile` — Profile
  - `/app/settings` — Settings
  - `/app/billing` — Billing
  - `/app/safety` — Safety

---

## 5. Key Integrations

### 5.1 Stripe

**Billing:**
- SetupIntent for card saving (`/api/billing/setup-intent`)
- Subscriptions (Plus, Premium tiers)
- Webhook handler (`/api/billing/webhook`) for subscription events

**Gifting:**
- Checkout Sessions for one-time gift purchases (`/api/gifts/checkout`)
- Webhook handler (`/api/gifts/webhook`) for gift payment completion
- Gift delivery triggers relationship boosts, memory entries, image rewards, unique effects

**Environment Variables:**
- `STRIPE_SECRET_KEY` — Stripe secret key
- `STRIPE_PUBLISHABLE_KEY` — Stripe publishable key
- `STRIPE_WEBHOOK_SECRET` — Webhook signature verification
- `STRIPE_PRICE_PLUS` — Plus tier price ID
- `STRIPE_PRICE_PREMIUM` — Premium tier price ID
- `STRIPE_SUCCESS_URL`, `STRIPE_CANCEL_URL` — Redirect URLs

### 5.2 Supabase (Optional)

**Database:**
- PostgreSQL database with RLS (Row Level Security)
- Tables: sessions, users_profile, girlfriends, messages, relationship_state, habit_profile, factual_memory, emotional_memory, gift_purchases

**Environment Variables:**
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_ANON_KEY` — Supabase anon key

**Fallback:**
- If Supabase not configured, backend uses in-memory store (data lost on restart)

### 5.3 OpenAI-Compatible LLM

**Chat Gateway:**
- `POST /v1/chat/stream` — External-facing gateway
- Proxies to internal LLM (`INTERNAL_LLM_BASE_URL`)
- Supports mock model (default), vLLM, or OpenAI

**Environment Variables:**
- `CHAT_API_KEY` — Bearer token for gateway clients
- `INTERNAL_LLM_BASE_URL` — Internal LLM base URL (default: `http://127.0.0.1:8001`)
- `INTERNAL_LLM_API_KEY` — Optional API key for internal LLM
- `API_KEY` — OpenAI API key (if using OpenAI directly)

**Mock Model:**
- `backend/app/routers/mock_model.py` — Mock OpenAI-compatible endpoint
- Returns personality-aware mock responses
- Runs on same port as main app (or separate port 8001)

---

## 6. Environment Variables

**Backend** (`backend/.env`):

```bash
# Server
HOST=0.0.0.0
PORT=8000
ENV=development

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:5174

# Supabase (optional)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here

# API Key (optional, for OpenAI)
API_KEY=

# Chat Gateway
CHAT_API_KEY=dev-key
INTERNAL_LLM_BASE_URL=http://127.0.0.1:8001
INTERNAL_LLM_API_KEY=

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PLUS=
STRIPE_PRICE_PREMIUM=
STRIPE_SUCCESS_URL=http://localhost:5173/app/chat?gift_success=1
STRIPE_CANCEL_URL=http://localhost:5173/app/chat?gift_cancel=1
```

---

## 7. How to Run

### 7.1 Development Setup

**Terminal 1 — Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend: http://localhost:8000  
API docs: http://localhost:8000/docs

**Terminal 2 — Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173  
Vite proxies `/api` to `http://localhost:8000`

### 7.2 Production Build

**Build Frontend:**
```bash
cd frontend
npm install
npm run build
```

**Run Backend (Production Mode):**
```bash
cd backend
source .venv/bin/activate
export ENV=production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Backend serves `frontend/dist` at `/` in production mode.

### 7.3 Chat Gateway + Mock Model

**Terminal 1 — Mock Model (port 8001):**
```bash
cd backend
uvicorn app.mock_main:app --reload --port 8001
```

**Terminal 2 — Gateway (port 8000):**
```bash
cd backend
export CHAT_API_KEY=dev-key
export INTERNAL_LLM_BASE_URL=http://127.0.0.1:8001
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Test Gateway:**
```bash
curl -N -X POST http://localhost:8000/v1/chat/stream \
  -H "Authorization: Bearer dev-key" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"abc","model":"mock-1","model_version":"2026-02-03","messages":[{"role":"user","content":"Hi"}]}'
```

### 7.4 Supabase Setup

1. Create Supabase project
2. Run `backend/supabase_schema.sql` in Supabase SQL editor
3. Get project URL and anon key from Settings > API
4. Add to `backend/.env`:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your_anon_key_here
   ```

---

## 8. Architecture Highlights

### 8.1 Relationship System

- **Levels**: STRANGER (0-15 intimacy) → FAMILIAR (16-35) → CLOSE (36-60) → INTIMATE (61-80) → EXCLUSIVE (81-100)
- **Trust/Intimacy**: 0-100 scale, updated on interactions
- **Decay**: Intimacy decays after 24h/72h inactivity (based on attachment style)
- **Milestones**: Automatic milestone detection on level transitions
- **Jealousy**: Reactions based on absence duration and jealousy level trait

### 8.2 Memory System

- **Factual Memory**: Stable facts (name, city, preferences) extracted via regex patterns
- **Emotional Memory**: Events + feelings (stress, affection, etc.) via keyword detection
- **Memory Context**: Compact summaries for LLM prompts (max 8 facts, 5 emotions, habit hints)

### 8.3 Personality Engines

- **Big Five Mapping**: 6 onboarding traits → Big Five scores (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism)
- **Trait Behavior Rules**: Trait-specific behavior expressions
- **Initiation Engine**: Decides when girlfriend should initiate conversations
- **Habit Profiling**: Analyzes user message patterns (preferred hours, typical gaps)

### 8.4 Gifting System

- **24 Gifts**: €2–€200 range, 4 tiers (everyday, dates, luxury, legendary)
- **Relationship Boosts**: Trust/intimacy gains per gift
- **Unique Effects**: Gift-specific effects (patron badge, outfit era, theme song, etc.)
- **Image Rewards**: Some gifts trigger image generation (1-6 images)
- **Cooldowns**: Rare gifts have 14-60 day cooldowns

### 8.5 Onboarding Flow

1. **Traits** (6 questions): Emotional style, attachment, reaction to absence, communication style, relationship pace, cultural personality
2. **Appearance**: Vibe, age, ethnicity, body details, hair/eyes
3. **Preferences**: Content preferences (spicy photos)
4. **Identity**: Name, job vibe, hobbies, origin vibe
5. **Generation**: Creates identity canon (backstory, daily routine, favorites, memory seeds)
6. **Reveal**: Animated reveal + subscription selection

---

## 9. Key Files Reference

### Backend Entry Points
- `backend/app/main.py` — Main FastAPI app
- `backend/app/mock_main.py` — Mock model server
- `backend/app/routers/chat.py` — Chat gateway

### Frontend Entry Points
- `frontend/src/main.tsx` — React app entry
- `frontend/src/App.tsx` — Root component
- `frontend/src/routes/router.tsx` — Router config

### Configuration
- `backend/app/core/config.py` — Settings singleton
- `backend/.env.example` — Environment template
- `frontend/vite.config.ts` — Vite config

### Database
- `backend/supabase_schema.sql` — Full database schema

---

## 10. Testing

**Backend Tests:**
```bash
cd backend
pytest
```

Test files:
- `backend/tests/test_chat_canon_injection.py`
- `backend/tests/test_identity_canon.py`
- `backend/tests/test_openai_contract.py`

---

## 11. Logging

- **Chat Logs**: `backend/logs/chat.jsonl` (JSONL format, one line per request)
- **Fields**: request_id, timestamp_utc, session_id, user_id, client_ip, model, model_version, messages, output_text, num_tokens, latency_ms, status, error_message

---

## 12. Dependencies

### Backend (`backend/requirements.txt`)
- fastapi>=0.109.0
- uvicorn[standard]>=0.27.0
- pydantic[email]>=2.5.0
- pydantic-settings>=2.1.0
- python-dotenv>=1.0.0
- supabase>=2.3.0
- httpx>=0.27.0
- openai>=1.0.0
- stripe>=8.0.0
- pytest

### Frontend (`frontend/package.json`)
- react, react-dom, react-router-dom
- @tanstack/react-query
- zustand
- @stripe/react-stripe-js, @stripe/stripe-js
- zod, react-hook-form
- tailwindcss, shadcn/ui components
- vite, typescript

---

**Last Updated**: February 9, 2026  
**Project**: VirtualFR  
**Repository**: `c:\Users\matej\OneDrive\Desktop\virtualfr`
