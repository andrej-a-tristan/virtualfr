# PROJECT INDEX — Companion (AI Girlfriend App)

> Paste this into ChatGPT/Claude/etc. so it understands the entire codebase at a glance.

---

## 1. What This App Is

**Companion** is a full-stack AI girlfriend web app. Users create a customizable AI companion through a multi-step onboarding flow (personality traits, appearance, identity), then chat with her in real-time via OpenAI's API. The AI's responses are shaped by a deep engine pipeline: bond engine (memory, disclosure, consistency), behavior engine (intent classification, response contracts), personality mapping (Big Five), and relationship progression. Monetization is via Stripe subscriptions (Free / Plus / Premium) and in-app gift purchases. Collectible "spicy leaks" and intimacy achievements add gamification.

---

## 2. Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, TypeScript, Vite 5, Tailwind CSS 3, Zustand (state), @tanstack/react-query, react-router-dom v6, Radix UI primitives, Stripe.js |
| **Backend** | Python 3.11+, FastAPI, Uvicorn, Pydantic v2 + pydantic-settings |
| **Database** | Supabase (PostgreSQL + Auth + RLS). Falls back to in-memory dict store (pickle-persisted) when Supabase is not configured |
| **AI/LLM** | OpenAI API (gpt-4o-mini) via `openai` Python SDK. SSE streaming to frontend |
| **Payments** | Stripe (subscriptions, setup intents, gift checkout) |
| **Auth** | Supabase Auth (email/password signup). Anonymous guest sessions for onboarding before signup |
| **Dev proxy** | Vite proxies `/api` and `/v1` to `localhost:8000` |

---

## 3. Monorepo Structure

```
virtualfr/
├── frontend/                    # React + Vite SPA
│   ├── index.html               # Entry HTML
│   ├── package.json             # Dependencies (react, zustand, stripe, tanstack-query, etc.)
│   ├── vite.config.ts           # Dev server config, proxy /api -> :8000
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx             # ReactDOM.createRoot
│       ├── App.tsx              # QueryClientProvider + TooltipProvider + RouterProvider
│       ├── routes/
│       │   ├── router.tsx       # All routes (onboarding, app shell, auth pages)
│       │   └── guards.tsx       # RequireAuth, RequireAgeGate, RequireGirlfriend
│       ├── pages/               # 22 page components (see §4)
│       ├── components/
│       │   ├── chat/            # Chat UI (MessageBubble, Composer, SpicyLeaksPanel, IntimateProgressionPanel, etc.)
│       │   ├── layout/          # AppShell, TopNav, SideNav, MobileNav, Footer
│       │   ├── ui/              # Reusable primitives (button, card, dialog, input, badge, etc.)
│       │   ├── onboarding/      # TraitCard, TraitSelector, ProgressStepper, PersonaPreviewCard
│       │   ├── billing/         # AddCardModal, UpgradeModal
│       │   ├── gallery/         # GalleryGrid, ImageViewerModal
│       │   └── safety/          # ContentPreferences, ReportDialog
│       ├── lib/
│       │   ├── api/
│       │   │   ├── client.ts    # Base fetch wrapper (apiGet, apiPost, apiFetch) — credentials: include
│       │   │   ├── endpoints.ts # All API calls (auth, chat, billing, gifts, memory, onboarding, progression, images, intimacy)
│       │   │   ├── types.ts     # TypeScript interfaces (User, Girlfriend, TraitSelection, ChatMessage, RelationshipState, etc.)
│       │   │   └── zod.ts       # Zod schemas for runtime validation
│       │   ├── hooks/
│       │   │   ├── useSSEChat.ts    # POST /api/chat/send SSE streaming — parses token/message/done/error/image_decision/relationship_gain/achievement events
│       │   │   └── useAuth.ts       # Auth hooks (login, signup, logout, session check)
│       │   ├── store/
│       │   │   ├── useAppStore.ts   # Zustand global state: user, girlfriend(s), onboarding draft, persisted to localStorage
│       │   │   └── useChatStore.ts  # Zustand chat state: messages, streaming content, isStreaming
│       │   ├── engines/             # Frontend mirrors of backend engines (used for local prediction/UI)
│       │   │   ├── prompt_builder.ts
│       │   │   ├── relationship_state.ts
│       │   │   ├── big_five_modulation.ts
│       │   │   ├── trait_behavior_rules.ts
│       │   │   ├── initiation_engine.ts
│       │   │   ├── memory.ts
│       │   │   ├── habits.ts
│       │   │   └── index.ts
│       │   ├── constants/identity.ts
│       │   ├── onboarding/vibe.ts
│       │   └── utils.ts             # cn() helper (clsx + tailwind-merge)
│       └── styles/globals.css       # Tailwind base + CSS vars (dark theme) + animations
│
├── backend/                     # FastAPI Python API
│   ├── .env                     # Environment vars (SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, API_KEY for OpenAI, STRIPE_*)
│   ├── requirements.txt         # fastapi, uvicorn, pydantic, supabase, openai, stripe, httpx, python-dotenv
│   ├── supabase_schema.sql      # Full DB schema (sessions, users_profile, girlfriends, messages, relationship_state, habit_profile, factual_memory, emotional_memory, gift_purchases, moment_cards + RLS policies)
│   ├── supabase_full_architecture.sql
│   │
│   ├── app/
│   │   ├── main.py              # FastAPI app creation, router mounting, CORS, startup logging, dev reset endpoint
│   │   ├── mock_main.py         # Alternate entrypoint for mock-only mode
│   │   │
│   │   ├── api/
│   │   │   ├── deps.py              # Session resolution: cookie -> in-memory -> Supabase restore -> guest auto-recreate
│   │   │   ├── request_context.py   # get_current_user() from request
│   │   │   ├── store.py             # IN-MEMORY DATA STORE — all dicts (sessions, girlfriends, messages, relationship, habits, gallery, progression, intimacy, trust, achievements, spicy leaks). Pickle-persisted to _store_cache.pkl. Dual-writes to Supabase when configured. Key functions: get/set_session_user, add/get_girlfriend, get/append_messages, migrate_session_data, find_session_by_user_id
│   │   │   ├── supabase_store.py    # Supabase CRUD helpers (mirrors store.py but hits DB)
│   │   │   │
│   │   │   └── routes/              # 19 route modules
│   │   │       ├── auth.py          # POST /auth/signup, /auth/login, /auth/logout, /auth/guest. Guest->real session migration
│   │   │       ├── me.py            # GET /me, POST /me/age-gate. Returns User with has_girlfriend, age_gate_passed
│   │   │       ├── chat.py          # GET /chat/history, /chat/state; POST /chat/send (MAIN CHAT — full engine pipeline + OpenAI streaming), /chat/app_open (initiation + jealousy)
│   │   │       ├── girlfriends.py   # POST /girlfriends (create), GET /girlfriends (list), GET /girlfriends/current, POST /girlfriends/current (switch), POST /girlfriends/create (additional)
│   │   │       ├── onboarding.py    # POST /onboarding/complete (creates girlfriend from traits+appearance+identity+content prefs)
│   │   │       ├── billing.py       # Stripe: /billing/status, /billing/setup-intent, /billing/subscribe, /billing/cancel, /billing/change-plan, /billing/payment-method(s), /billing/stripe-key, webhook
│   │   │       ├── gifts.py         # /gifts/list, /gifts/checkout, /gifts/confirm-payment, /gifts/history, /gifts/collection
│   │   │       ├── images.py        # /images/request, /images/jobs/:id, /images/gallery
│   │   │       ├── relationship.py  # /relationship/achievements
│   │   │       ├── progression.py   # /progression/messages, /progression/summary, mark-read, dismiss, record-action
│   │   │       ├── intimacy_achievements.py  # /intimacy/achievements, /intimacy/purchase-box, /intimacy/mystery-unlock
│   │   │       ├── spicy_leaks.py   # /spicy-leaks/catalog, /spicy-leaks/spin, /spicy-leaks/unlocked (50 collectible solo photos)
│   │   │       ├── memory.py        # /memory/summary, /memory/items, /memory/stats
│   │   │       ├── profile.py       # /profile/girls
│   │   │       ├── prompt.py        # /prompt/build (debug: shows assembled system prompt)
│   │   │       ├── dossier.py       # /dossier (girlfriend self-knowledge)
│   │   │       ├── moderation.py    # /moderation/report
│   │   │       ├── health.py        # /health (liveness check)
│   │   │       └── check.py         # /check (config verification)
│   │   │
│   │   ├── core/
│   │   │   ├── config.py            # Settings (pydantic-settings): loads .env, all env vars (Supabase, Stripe, OpenAI, CORS, LLM gateway)
│   │   │   ├── supabase_client.py   # get_supabase() (anon key), get_supabase_admin() (service role key)
│   │   │   ├── auth.py              # Auth utilities
│   │   │   ├── cors.py              # CORS setup
│   │   │   ├── rate_limit.py        # Rate limiting
│   │   │   ├── chat_logging.py      # Chat audit logging
│   │   │   └── __init__.py          # Exports get_settings, get_api_key, setup_cors
│   │   │
│   │   ├── routers/
│   │   │   ├── chat.py              # Chat GATEWAY: /v1/chat/stream and /api/chat/stream. Proxies to OpenAI (direct API call with gpt-4o-mini when API_KEY is set) or falls back to mock model
│   │   │   └── mock_model.py        # /v1/chat/completions mock endpoint (returns canned responses when no API key)
│   │   │
│   │   ├── schemas/                 # Pydantic models
│   │   │   ├── auth.py              # SignupRequest, LoginRequest, UserResponse
│   │   │   ├── chat.py              # SendMessageRequest, AppOpenRequest, ChatMessage, RelationshipState
│   │   │   ├── girlfriend.py        # GirlfriendCreate, GirlfriendResponse
│   │   │   ├── billing.py           # BillingStatus, SubscribeRequest
│   │   │   ├── gift.py
│   │   │   ├── intimacy.py          # IntimacyState
│   │   │   ├── intimacy_achievements.py
│   │   │   ├── profile.py
│   │   │   ├── progression.py
│   │   │   ├── trust_intimacy.py    # TrustIntimacyState
│   │   │   └── payment_method.py
│   │   │
│   │   ├── services/                # CORE AI + GAME ENGINES
│   │   │   │
│   │   │   ├── ─── BOND ENGINE (unified per-turn pipeline) ───
│   │   │   ├── bond_engine/
│   │   │   │   ├── bond_orchestrator.py     # BondTurnContext: ingest_turn -> update_state -> plan_response -> build_prompt -> validate -> persist. Single entry point per chat turn
│   │   │   │   ├── memory_fabric.py         # MemoryBundle: ingest_user_turn (extract facts/emotions/episodes), build_prompt_memory_bundle, record_used_memories
│   │   │   │   ├── memory_ingest.py         # Low-level memory extraction from user text
│   │   │   │   ├── memory_retrieval.py      # Retrieve relevant memories for prompt context
│   │   │   │   ├── memory_scoring.py        # Score and rank memories by relevance
│   │   │   │   ├── memory_patterns.py       # Detect recurring user patterns
│   │   │   │   ├── memory_conflict_resolution.py  # Resolve contradictory memories
│   │   │   │   ├── consistency_guard.py     # PersonaKernel + PersonaGrowthState — ensures AI stays in character
│   │   │   │   ├── depth_planner.py         # Capability unlocks (e.g., "can discuss dreams at level 30")
│   │   │   │   ├── disclosure_planner.py    # DisclosureState — gradual self-revelation over time
│   │   │   │   ├── initiation_planner.py    # plan_initiation() — proactive messages from AI
│   │   │   │   └── response_director.py     # ResponseContract — style, tone, length constraints per turn [NOTE: referenced as response_director but may also be in bond_engine]
│   │   │   │
│   │   │   ├── ─── BEHAVIOR ENGINE (natural response shaping) ───
│   │   │   ├── behavior_engine/
│   │   │   │   ├── behavior_orchestrator.py # BehaviorTurnInput/Result: classify intent -> build dossier -> create contract -> validate. Single entry point
│   │   │   │   ├── intent_classifier.py     # TurnIntent: classifies user message as banter/question/disclosure/emotional_need etc.
│   │   │   │   ├── response_contract.py     # BehaviorContract: tone, max_length, question_limit, emoji_density
│   │   │   │   └── validators.py            # Post-generation validation (no robotic patterns, length limits, etc.)
│   │   │   │
│   │   │   ├── ─── DOSSIER (girlfriend self-knowledge) ───
│   │   │   ├── dossier/
│   │   │   │   ├── retriever.py             # DossierContext: build_dossier_context() — backstory, daily routine, favorites
│   │   │   │   ├── self_memory.py           # update_dossier_from_response() — AI learns about herself
│   │   │   │   ├── bootstrap.py             # Initial dossier generation on girlfriend creation
│   │   │   │   └── llm_generator.py         # LLM-based dossier expansion
│   │   │   │
│   │   │   ├── ─── PROMPT ASSEMBLY ───
│   │   │   ├── prompt_builder.py            # Composes deterministic system prompt from: identity, traits, Big Five, memory, relationship state, bond context, behavior contract
│   │   │   ├── prompt_context.py            # PromptContext dataclass — aggregates all data needed for prompt building
│   │   │   │
│   │   │   ├── ─── PERSONALITY ───
│   │   │   ├── big_five.py                  # Big Five personality dimensions
│   │   │   ├── big_five_modulation.py       # Modulate AI behavior based on Big Five scores
│   │   │   ├── big_five_mapping.json        # Trait-to-Big-Five mappings
│   │   │   ├── trait_behavior_rules.py      # Maps trait selections to behavioral rules
│   │   │   │
│   │   │   ├── ─── RELATIONSHIP SYSTEM ───
│   │   │   ├── relationship_state.py        # create_initial, register_interaction, apply_inactivity_decay, get_jealousy_reaction, check_milestone
│   │   │   ├── relationship_progression.py  # RelationshipProgressState: level (0-200), points, daily_points, streak tracking
│   │   │   ├── relationship_regions.py      # 5 regions: Stranger(0-15), Familiar(16-39), Close(40-64), Intimate(65-89), Exclusive(90-100)
│   │   │   ├── relationship_descriptors.py  # Narrative hooks and micro-lines per region
│   │   │   ├── relationship_milestones.py   # Milestone definitions and region transitions
│   │   │   ├── streaks.py                   # Daily messaging streak tracking
│   │   │   │
│   │   │   ├── ─── TRUST & INTIMACY ───
│   │   │   ├── trust_intimacy_service.py    # Unified trust+intimacy: caps per region, banking, decay, quality scoring, gift awards
│   │   │   ├── intimacy_service.py          # Region-based intimacy milestones
│   │   │   ├── intimacy_milestones.py       # 50 intimacy achievement definitions (triggers, prompts, rarities: Common/Uncommon/Rare/Epic/Legendary)
│   │   │   ├── intimacy_achievement_engine.py  # Detects trigger keywords in chat to unlock achievements
│   │   │   │
│   │   │   ├── ─── ACHIEVEMENTS ───
│   │   │   ├── achievement_engine.py        # AchievementProgress: detect_signals, update_streak, try_unlock_for_triggers, TriggerType enum
│   │   │   │
│   │   │   ├── ─── IMAGE SYSTEM ───
│   │   │   ├── image_decision_engine.py     # Gates sensitive images: checks plan, intimacy level, user prefs, age. Returns allow/blur/deny
│   │   │   │
│   │   │   ├── ─── PROACTIVE MESSAGING ───
│   │   │   ├── initiation_engine.py         # Generates proactive "first message" or re-engagement
│   │   │   ├── habits.py                    # Habit profiling — tracks preferred hours, message frequency
│   │   │   │
│   │   │   ├── ─── OTHER ───
│   │   │   ├── gifting.py                   # Gift catalog, Stripe checkout, delivery
│   │   │   ├── delivery_service.py          # Gift delivery orchestration
│   │   │   ├── message_composer.py          # Compose messages with metadata
│   │   │   ├── experiment_service.py        # A/B testing / feature flags
│   │   │   ├── progression_service.py       # Milestone message generation and delivery
│   │   │   ├── telemetry_service.py         # Usage telemetry
│   │   │   └── time_utils.py
│   │   │
│   │   └── utils/
│   │       ├── sse.py                # sse_event() — formats SSE with event: type, data: json
│   │       ├── identity_canon.py     # Generate girlfriend backstory/identity from LLM
│   │       ├── prompt_identity.py    # Identity section of system prompt
│   │       └── moderation.py         # Content moderation
│   │
│   ├── docs/
│   │   ├── BIG_FIVE_MIGRATION.md
│   │   └── SETUP_SUPABASE.md
│   │
│   ├── migrations/
│   │   ├── 003_progression_system.sql
│   │   ├── 004_bond_engine.sql
│   │   └── 005_behavior_engine.sql
│   │
│   ├── scripts/
│   │   ├── bootstrap_existing_girls.py
│   │   ├── check_api_key.py
│   │   └── check_config.py
│   │
│   └── tests/                   # pytest tests
│       ├── test_achievements.py
│       ├── test_billing_proration_contract.py
│       ├── test_chat_canon_injection.py
│       ├── test_identity_canon.py
│       ├── test_intimacy.py
│       ├── test_intimacy_achievements.py
│       ├── test_openai_contract.py
│       ├── test_profile_stats.py
│       ├── test_relationship_progression.py
│       ├── test_relationship_regions.py
│       └── test_trust_intimacy.py
│
└── PROJECT_INDEX.md             # This file
```

---

## 4. Frontend Pages & Routes

| Route | Page Component | Auth? | Description |
|-------|---------------|-------|-------------|
| `/` | `Landing.tsx` | No | Entry: creates guest session, auto-passes age gate, redirects to `/onboarding/appearance` |
| `/login` | `Login.tsx` | No | Email/password login |
| `/signup` | `Signup.tsx` | No | Email/password signup |
| `/age-gate` | `AgeGate.tsx` | Yes | Age verification (bypassed automatically for guests) |
| `/onboarding/appearance` | `OnboardingAppearance.tsx` | No* | Pick appearance vibe (cute/elegant/sporty/etc.) |
| `/onboarding/appearance/age` | `AppearanceAge.tsx` | No* | Pick age range |
| `/onboarding/appearance/ethnicity` | `AppearanceEthnicity.tsx` | No* | Pick ethnicity |
| `/onboarding/appearance/body` | `AppearanceBodyDetails.tsx` | No* | Pick body details (breast/butt) |
| `/onboarding/appearance/hair-eyes` | `AppearanceHairEyes.tsx` | No* | Pick hair color/style and eye color |
| `/onboarding/traits` | `OnboardingTraits.tsx` | No* | Pick 6 personality traits |
| `/onboarding/preferences` | `OnboardingPreferences.tsx` | No* | Content preferences (spicy photos toggle) |
| `/onboarding/identity` | `OnboardingIdentity.tsx` | No* | Name, job vibe, hobbies, origin vibe |
| `/onboarding/generating` | `OnboardingGenerating.tsx` | No* | "Crafting companion" loading (2.2s min + fade-out) |
| `/onboarding/reveal` | `GirlfriendReveal.tsx` | No* | Blurred photo reveal + signup form (account wall) |
| `/onboarding/subscribe` | `SubscriptionPlan.tsx` | — | Stripe subscription plan picker |
| `/onboarding/reveal-success` | `RevealSuccess.tsx` | — | Photo fully revealed after signup |
| `/onboarding/preview` | `PersonaPreview.tsx` | — | Preview persona card |
| `/app` | `AppShell` → redirect to `/app/girl` | Yes+AgeGate+Girlfriend | Protected app shell |
| `/app/girl` | `GirlPage.tsx` | Yes | **Main page**: Chat + sidebar (relationship meter, gifts, "See Her Leaked Photos" slots, "Leaked Collection" button, intimate progression). Desktop sidebar is 2-column grid |
| `/app/girls/:girlId/relationship` | `Relationship.tsx` | Yes | Detailed relationship view for a specific girlfriend |
| `/app/profile` | `Profile.tsx` | Yes | User profile |
| `/app/settings` | `Settings.tsx` | Yes | App settings |
| `/app/billing` | `Billing.tsx` | Yes | Subscription management |
| `/app/payment-options` | `PaymentOptions.tsx` | Yes | Add/manage payment methods |
| `/app/safety` | `Safety.tsx` | Yes | Content preferences + report |

*\*No auth guards — guest session created by Landing.tsx*

---

## 5. Chat Flow (The Core Loop)

### Frontend → Backend → OpenAI → Frontend

1. **User types message** → `useSSEChat.ts` → `POST /api/chat/send` (SSE stream)
2. **Backend `chat.py` /chat/send handler**:
   a. Validates session, loads girlfriend data, relationship state, messages
   b. **Free-plan daily cap check** (20 messages/day)
   c. **Bond Engine** (`bond_orchestrator.py`): ingests user turn → extracts memories → updates disclosure/reciprocity → detects capability unlocks → retrieves relevant memories → consistency guard → builds bond context prompt
   d. **Behavior Engine** (`behavior_orchestrator.py`): classifies intent → retrieves dossier → builds behavior contract (tone, length, question limits)
   e. **Prompt Builder** (`prompt_builder.py`): assembles final system prompt from identity, traits, Big Five, memory, relationship state, bond context, behavior contract
   f. **OpenAI streaming call** (gpt-4o-mini) with assembled system prompt + conversation history
   g. **Streams tokens back** via SSE (`event: token`, `data: {"type":"token","token":"..."}`)
   h. After stream completes: updates relationship state (trust/intimacy gains), checks for achievements, checks for image decision, saves message to store + Supabase
   i. Sends final SSE events: `event: message` (saved message), `event: relationship_gain`, `event: relationship_achievement`, `event: intimacy_achievement`, `event: done`
3. **Frontend parses SSE**: renders tokens in real-time, then appends final message + any achievement/gain cards

### SSE Event Types

| Event | Payload | Description |
|-------|---------|-------------|
| `token` | `{"type":"token","token":"Hi"}` | Streaming token from AI |
| `message` | `{"type":"message","message":{...}}` | Final saved assistant message with DB id |
| `done` | `{"type":"done"}` | Stream complete |
| `error` | `{"type":"error","error":"..."}` | Error occurred |
| `relationship_gain` | `{"type":"relationship_gain","gain":{...}}` | Trust/intimacy change |
| `relationship_achievement` | `{"type":"relationship_achievement","achievement":{...}}` | Achievement unlocked |
| `intimacy_achievement` | `{"type":"intimacy_achievement","achievement":{...}}` | Intimacy achievement unlocked |
| `intimacy_photo_ready` | `{"type":"intimacy_photo_ready","photo":{...}}` | Photo reward for intimacy achievement |
| `image_decision` | `{"type":"image_decision","decision":{...},"message":{...}}` | Image generation decision (allow/blur/deny) |
| `blurred_preview` | `{"type":"blurred_preview","message":{...}}` | Teaser for free-plan upgrade |

---

## 6. Authentication Flow

1. **Landing** (`/`): Creates anonymous guest session → `POST /auth/guest` → sets `session` cookie → auto age-gate → redirects to onboarding
2. **Onboarding**: User picks traits, appearance, identity. At the end, `POST /onboarding/complete` creates the girlfriend in-memory under the guest session
3. **Reveal** (`/onboarding/reveal`): Shows blurred girlfriend photo. User must create an account (signup form)
4. **Signup**: `POST /auth/signup` → creates Supabase user → calls `migrate_session_data(old_guest_sid, new_sid)` to transfer all in-memory girlfriend data to the new real session → new session cookie
5. **Login** (returning users): `POST /auth/login` → authenticates with Supabase → restores session from DB or in-memory store → sets `age_gate_passed: true`, `has_girlfriend: true`
6. **Session recovery**: `deps.py` handles: (a) in-memory lookup, (b) Supabase DB restore, (c) guest session auto-recreate, (d) stale cookie cleanup

---

## 7. Database Schema (Supabase/PostgreSQL)

### Core Tables
- **`sessions`** — `id (text PK)`, `user_id (uuid FK)`, `email`, `display_name`, `current_girlfriend_id`
- **`users_profile`** — `user_id (uuid PK)`, `language_pref`, `age_gate_passed`, `plan`
- **`girlfriends`** — `id (uuid PK)`, `user_id`, `display_name`, `traits (jsonb)`
- **`messages`** — `id (uuid)`, `user_id`, `girlfriend_id`, `role`, `content`, `image_url`, `event_type`, `event_key`
- **`relationship_state`** — `(user_id, girlfriend_id) PK`, `trust (0-100)`, `intimacy (0-100)`, `level (STRANGER→EXCLUSIVE)`, `milestones_reached`
- **`habit_profile`** — `(user_id, girlfriend_id) PK`, `preferred_hours`, `typical_gap_hours`, `big_five_*`

### Memory Tables
- **`factual_memory`** — `user_id`, `girlfriend_id`, `key`, `value`, `confidence (0-100)`, `source_message_id`
- **`emotional_memory`** — `user_id`, `girlfriend_id`, `event`, `emotion_tags[]`, `valence (-5 to 5)`, `intensity (1-5)`
- **`memory_notes`** — manual notes/summaries

### Commerce Tables
- **`gift_purchases`** — Stripe payment tracking for in-app gifts
- **`moment_cards`** — Keepsake cards from gifts

All tables have RLS enabled: `auth.uid() = user_id`

---

## 8. AI Engine Pipeline (per chat turn)

```
User message
    │
    ▼
┌─────────────────────────────────┐
│  BOND ENGINE (bond_orchestrator) │
│  1. Memory Fabric: extract facts,│
│     emotions, episodes, patterns │
│  2. Disclosure Planner: advance  │
│     self-revelation schedule     │
│  3. Depth Planner: check if new  │
│     capabilities unlocked        │
│  4. Memory Retrieval: find        │
│     relevant memories for prompt │
│  5. Consistency Guard: validate   │
│     persona adherence            │
│  6. Build bond context prompt     │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│ BEHAVIOR ENGINE (behavior_orch)  │
│  1. Intent Classifier: banter?   │
│     question? disclosure? need?  │
│  2. Dossier Retriever: backstory,│
│     routine, favorites           │
│  3. Response Contract: tone,     │
│     max length, question limit,  │
│     emoji density                │
│  4. Post-gen validators          │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│ PROMPT BUILDER                   │
│  Identity + Traits + Big Five +  │
│  Memory Context + Relationship + │
│  Bond Context + Behavior Contract│
│  → Final System Prompt           │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│ OPENAI API (gpt-4o-mini)         │
│  System prompt + chat history    │
│  → Streaming completion          │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│ POST-PROCESSING                  │
│  1. Update relationship state    │
│  2. Check achievements           │
│  3. Image decision engine        │
│  4. Save message to store + DB   │
│  5. Stream SSE events to frontend│
└─────────────────────────────────┘
```

---

## 9. Gamification Systems

### Relationship Progression
- **Level 0-200** with points from conversations
- **5 Regions**: Stranger (0-15), Familiar (16-39), Close (40-64), Intimate (65-89), Exclusive (90-100)
- Trust and intimacy have **per-region caps** (e.g., trust cap in Stranger = 25)
- **Banking system**: excess gains are "banked" and released when entering new region
- **Decay**: inactivity reduces trust/intimacy over time
- **Streaks**: daily messaging streak with multipliers

### Intimacy Achievements
- **50 achievements** across 5 rarity tiers: Common (10), Uncommon (10), Rare (10), Epic (10), Legendary (10)
- Unlocked by trigger keywords detected in chat
- Each has an image generation prompt for a reward photo
- Content escalates with rarity (more explicit at higher tiers)
- All photos are **solo-only** (no other characters)

### Spicy Leaks Collection
- **50 collectible "leaked photos"** with rarities
- Unlocked via a **slot machine** mechanic
- Content escalates with rarity
- All photos are **strictly solo** (no other individuals or male anatomy)

### Achievements
- Relationship achievements unlocked by emotional signals in conversation
- Per-region achievement sets

---

## 10. Payments (Stripe)

### Plans
- **Free**: 20 messages/day, blurred images
- **Plus**: Unlimited messages, image generation, more features
- **Premium**: Everything + priority, exclusive content

### Integration Points
- `POST /billing/subscribe` — Creates Stripe subscription
- `POST /billing/setup-intent` — Card setup
- `POST /billing/change-plan` — With proration preview
- `POST /gifts/checkout` — One-time gift purchases
- Webhook handler for Stripe events

---

## 11. Key Environment Variables (.env)

```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
API_KEY=sk-...                    # OpenAI API key
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_PRICE_PLUS=price_...
STRIPE_PRICE_PREMIUM=price_...
```

---

## 12. How to Run

```bash
# Backend (terminal 1)
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000

# Frontend (terminal 2)
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

**Important**: Delete `backend/_store_cache.pkl` if you get schema mismatch errors after code changes.

---

## 13. Key Architectural Decisions

1. **Dual storage**: In-memory dicts (pickle-persisted) + Supabase. Store.py dual-writes to both. This lets the app work without Supabase for local dev, while persisting to DB in production.
2. **Guest sessions**: Anonymous onboarding before signup. `migrate_session_data()` transfers all in-memory data to the real user session on signup.
3. **Engine pipeline**: Bond Engine → Behavior Engine → Prompt Builder → OpenAI. Each engine is independently testable.
4. **SSE streaming**: Real-time token streaming from OpenAI through FastAPI to React. Custom SSE event types for rich chat events (achievements, relationship gains, image decisions).
5. **Frontend engine mirrors**: `lib/engines/` has TypeScript ports of backend engines for client-side prediction and UI rendering.
6. **Per-girlfriend state**: All relationship, memory, and game state is keyed by `(session_id, girlfriend_id)` tuple, enabling multi-girlfriend support.
