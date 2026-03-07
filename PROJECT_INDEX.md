# VirtualFR — Project Index

> AI companion web app: FastAPI backend + React/Vite frontend.
> Multi-girlfriend support with per-girl chat, gallery, relationship state, gifting, achievements, and intimate progression.

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
│   │   ├── test_openai_contract.py
│   │   ├── test_relationship_regions.py      — Region mapping correctness tests
│   │   ├── test_relationship_progression.py  — Progression engine tests (45 cases)
│   │   ├── test_trust_intimacy.py            — Trust/intimacy + region caps + banking tests (71 cases)
│   │   └── test_achievements.py              — Achievement system tests (73 cases)
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
│       │   ├── store.py           — In-memory session store (multi-girl: messages, gallery, relationship, habits, achievement progress per girlfriend)
│       │   ├── supabase_store.py  — Supabase-backed store
│       │   ├── request_context.py — Request context helpers
│       │   └── routes/
│       │       ├── auth.py          — Signup, login (preserves session data), logout
│       │       ├── billing.py       — Plan status, setup-intent, subscribe, cancel, payment-method, Stripe webhook
│       │       ├── chat.py          — Chat history, state, send (SSE), app_open — all per-girlfriend. Achievement triggers on every message.
│       │       ├── gifts.py         — Gift catalog, checkout (inline Stripe), confirm, history, collection — per-girlfriend. One purchase per gift per girl enforced.
│       │       ├── girlfriends.py   — List, create, switch, get current — multi-girl CRUD with plan limits
│       │       ├── health.py        — Health check
│       │       ├── images.py        — Image jobs, gallery — per-girlfriend
│       │       ├── intimacy_achievements.py — Intimacy achievement catalog (per-girlfriend unlocked status)
│       │       ├── leaks.py         — Leaks collection + paid slot spin (Stripe) — per-girlfriend
│       │       ├── me.py            — Current user, age gate
│       │       ├── memory.py        — Memory summary/items/stats
│       │       ├── moderation.py    — Content reports
│       │       ├── onboarding.py    — Prompt images, complete onboarding (first girl)
│       │       ├── profile.py       — Aggregated per-girlfriend stats (streaks, collections, activity)
│       │       └── relationship.py  — Achievement catalog API endpoint
│       ├── routers/
│       │   ├── chat.py            — Chat gateway (SSE proxy + canon injection, accepts girlfriend_id)
│       │   └── mock_model.py      — Internal mock LLM (/v1/chat/completions)
│       ├── schemas/
│       │   ├── auth.py            — SignupRequest, LoginRequest, UserResponse
│       │   ├── chat.py            — ChatMessage, SendMessageRequest (with girlfriend_id), RelationshipState
│       │   ├── gift.py            — GiftDefinition, ImageReward (normal+spicy photos, per-photo prompts), GiftCheckoutRequest/Response, GiftHistoryItem
│       │   ├── girlfriend.py      — TraitsPayload, AppearancePrefs, IdentityCanon, GirlfriendListResponse, OnboardingCompletePayload
│       │   ├── image.py           — ImageJobResponse, GalleryItem
│       │   ├── payment_method.py  — PaymentMethodResponse
│       │   ├── relationship.py    — Relationship schemas
│       │   ├── intimacy.py        — IntimacyState, IntimacyAwardResult (Intimacy Index schemas)
│       │   └── trust_intimacy.py  — TrustIntimacyState (with visible/bank split), GainResult (unified trust+intimacy schemas)
│       ├── services/
│       │   ├── big_five.py                — Trait → Big Five mapping
│       │   ├── big_five_modulation.py     — Big Five → behavior modulation
│       │   ├── big_five_mapping.json      — Big Five mapping data
│       │   ├── trait_behavior_rules.py    — Trait → BehaviorProfile
│       │   ├── gifting.py                 — Gift catalog (26 gifts, 72 unique photo prompts), effects, checkout, webhook handling
│       │   ├── relationship_state.py      — Trust/intimacy/level tracking, decay, milestones, try_unlock_achievement (legacy)
│       │   ├── relationship_regions.py    — 9 canonical regions (1–200), clamp_level, get_region_for_level
│       │   ├── relationship_progression.py — Points engine: cooldown, streak, quality, anti-farm, region curve
│       │   ├── relationship_milestones.py — Achievement catalog: 54 achievements (6 per region × 9 regions), Rarity enum, TriggerType enum, requirement specs
│       │   ├── achievement_engine.py      — Achievement evaluation engine: signal detection, progress counters, requirement evaluation, region-locked unlock
│       │   ├── relationship_descriptors.py — Every +1 descriptor engine: labels, micro-lines, tone rules, prompt context
│       │   ├── intimacy_service.py        — Legacy Intimacy Index engine (kept for backward compat)
│       │   ├── trust_intimacy_service.py  — Unified trust+intimacy engine: region caps, bank-first awards, release_banked, conversation trust, gift/region awards, decay
│       │   ├── image_decision_engine.py   — Image gating: sensitive detection, intimacy_visible threshold, age/opt-in gates
│       │   ├── memory.py                  — Factual & emotional memory extraction/context
│       │   ├── habits.py                  — User habit profiling
│       │   ├── initiation_engine.py       — Girlfriend-initiated messages
│       │   ├── streaks.py                — Talking streak calculator (compute_streaks → StreakResult)
│       │   ├── time_utils.py              — Time helpers
│       │   └── intimacy_achievement_engine.py — Keyword-triggered intimacy achievement unlocks
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
        │   └── guards.tsx             — RequireAuth, RequireAgeGate, RequireGirlfriend, RequireSubscription
        ├── lib/
        │   ├── api/
        │   │   ├── client.ts          — Axios/fetch wrapper
        │   │   ├── endpoints.ts       — All API call functions (multi-girl, gifts, gift collection, billing, gallery, achievements, leaks, profile)
        │   │   ├── types.ts           — TypeScript types (Girlfriend, gifts, billing, memory, Big Five, achievements, gift collection)
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
        │   │   ├── useAuth.ts         — Auth hook (react-query + store, age_gate_passed prioritization)
        │   │   └── useSSEChat.ts      — SSE chat streaming hook (sends girlfriend_id, handles relationship_achievement events)
        │   ├── onboarding/
        │   │   └── vibe.ts            — Vibe helpers
        │   ├── store/
        │   │   ├── useAppStore.ts     — Main Zustand store (user, girlfriends[], currentGirlfriendId, onboarding, persisted)
        │   │   └── useChatStore.ts    — Chat Zustand store (messages, streaming)
        │   └── utils.ts               — cn() utility
    ├── pages/
    │   ├── Landing.tsx            — Auto-login, redirect to onboarding or chat (age_gate_passed sync fix)
    │   ├── Login.tsx              — Email/password login (smart redirect based on user state)
    │   ├── Signup.tsx             — Email/password signup
    │   ├── AgeGate.tsx            — Mandatory 18+ verification (blocking, with warning notice)
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
    │   ├── OnboardingPreferences.tsx — Mandatory age verification (blocks under-18, auto-sets wants_spicy_photos)
    │   ├── OnboardingIdentity.tsx    — Name, job vibe, hobbies, origin
    │   ├── OnboardingGenerating.tsx  — Calls completeOnboarding or createAdditionalGirlfriend, shows spinner
    │   ├── GirlfriendReveal.tsx      — Blurred photo + mandatory signup form (no skip options)
    │   ├── SubscriptionPlan.tsx      — 3-tier subscription paywall
    │   ├── RevealSuccess.tsx         — Unblurred photo + "Let's chat" after subscribing
    │   ├── PersonaPreview.tsx        — Final persona summary
    │   ├── GirlPage.tsx              — Per-girl hub: chat + gallery tabs, side buttons (My Relationship, Intimate Progression, Gift Collection, Surprise Her, Leaks), fullscreen panels (portaled)
    │   ├── Relationship.tsx          — (legacy, content moved into GirlPage)
    │   ├── Chat.tsx                  — Main chat interface (per-girlfriend history)
    │   ├── Gallery.tsx               — Photo gallery (per-girlfriend)
    │   ├── Profile.tsx               — Girl cards grid with rich stats (streaks, trust/intimacy meters, collections, sorting)
    │   ├── Settings.tsx              — User settings + Account section (password change, delete account, logout) + Notifications
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
            │   ├── GiftModal.tsx           — Gift catalog modal with tabs + preview + inline Stripe payment + "Already Gifted" state
            │   ├── GiftCollectionPanel.tsx — Fullscreen gift collection: all 26 gifts by tier, purchased state, photo slot grid per gift
            │   ├── IntimateProgressionPanel.tsx — Fullscreen intimate collection: 7 tiers, 50 sexual achievements with scene descriptions + photo slots
            │   ├── LeaksPanel.tsx             — Fullscreen leaks panel: 50 leaked photos by rarity, paid slot machine (3 tiers), collection grid, Stripe payment
            │   ├── MysteryBoxPanel.tsx         — Fullscreen gift mystery box panel: 3 box tiers, slot machine spin, Stripe payment, gift reveal
            │   ├── AchievementUnlockedCard.tsx  — Chat card for achievement unlock events (rarity-styled)
            │   ├── MessageBubble.tsx       — Message bubble with avatar (handles achievement events)
            │   ├── MessageList.tsx         — Scrollable message list
            │   ├── ImageMessage.tsx        — Image message display
            │   ├── PaywallInlineCard.tsx   — In-chat paywall card
            │   ├── RelationshipMeter.tsx   — Intimacy-based level meter
            │   ├── ImageTeaseCard.tsx      — Intimacy-locked content tease with suggested prompts
            │   ├── BlurredImageCard.tsx    — Blurred preview card for free-plan paywall (upgrade CTA)
            │   ├── RelationshipGainCard.tsx — Animated gain card (+trust/+intimacy) with bank/release/cap info
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
| `POST` | `/api/chat/send` | Send message (SSE) — uses `girlfriend_id` from body. Triggers achievement detection. |
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
| `GET` | `/api/gifts/list` | Full gift catalog (4 tiers, 26 gifts, €2–€200) + `spicy_unlocked` + `already_purchased` flags |
| `POST` | `/api/gifts/checkout` | Create gift PaymentIntent (inline, saved card). **One purchase per gift per girl enforced.** |
| `POST` | `/api/gifts/confirm-payment` | Confirm gift payment (3DS) |
| `GET` | `/api/gifts/history` | Gift purchase history for current girlfriend |
| `GET` | `/api/gifts/collection` | Full catalog with purchased status + purchased_at per gift, total/owned counts |
| `POST` | `/api/gifts/webhook` | Stripe gift webhook |

### Relationship & Achievements

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/relationship/achievements` | Achievement catalog by region (54 achievements with rarity + trigger) |

### Intimacy Achievements

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/intimacy/achievements` | Intimacy achievement catalog by tier (50 achievements), per-girlfriend unlocked status |

### Leaks Collection (per-girlfriend)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/leaks/collection` | Get unlocked leaks for current girlfriend (`?girlfriend_id=`). Returns `{unlocked, total}` |
| `POST` | `/api/leaks/spin` | Purchase a leak slot spin (Stripe). Body: `{box_id, girlfriend_id?}`. 3 box tiers (Quick Peek €1.99, Private Collection €4.99, Fully Uncensored €9.99). Returns random leaked photo by rarity. |

### Profile Stats

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/profile/girls` | Aggregated per-girlfriend stats: relationship, activity, streaks, collections. Single-call for Profile page. |

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
| `_relationship_state` | `(session_id, girlfriend_id)` | Trust, intimacy, level, milestones_reached per girl |
| `_relationship_progress` | `(session_id, girlfriend_id)` | Progression engine state (level, banked_points, streak, cooldowns) |
| `_intimacy_state` | `(session_id, girlfriend_id)` | Legacy Intimacy Index state (1–100, used regions/gifts, daily caps) |
| `_trust_intimacy_state` | `(session_id, girlfriend_id)` | Unified Trust + Intimacy state (visible/bank split, caps, dedup lists) |
| `_achievement_progress` | `(session_id, girlfriend_id)` | Achievement progress counters (signal hits, streak, memory flags) |
| `_habit_profile` | `(session_id, girlfriend_id)` | User habit data per girl |
| `_gallery` | `(session_id, girlfriend_id)` | Gallery images per girl |
| `_gift_purchases` | `(session_id, girlfriend_id)` | Gift purchase records per girl |
| `_leaks_unlocked` | `(session_id, girlfriend_id)` | Unlocked leaked photos per girl (leak_id → image_url) |
| `_intimacy_ach_unlocked` | `(session_id, girlfriend_id)` | Unlocked intimacy achievements per girl |

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
Preferences (mandatory age verification — blocks under-18 users entirely)
  ↓
Identity (name, job vibe, hobbies, origin)
  ↓
Generating (POST /api/onboarding/complete)
  ↓
Reveal (blurred photo + MANDATORY signup form — no skip options)
  ↓
Subscribe (Free / Plus / Premium tiers — card required for all plans)
  ↓
Reveal Success (unblurred photo + "Let's chat")
  ↓
Chat
```

**No skip allowed.** Users must create an account, add a payment card, and choose a plan before accessing the chat. The `RequireSubscription` guard blocks `/app` access without a card on file.

**Additional girl onboarding** (Premium users): Same flow but skips signup/reveal/subscribe. Goes straight from Generating → Chat. Sign-in button is hidden.

---

## Subscription Tiers

| Tier | Price | Tagline | Features |
|------|-------|---------|----------|
| **Free** | €0.00/mo | "Say hi to [name]" | 7-day free trial (auto-upgrades to Plus), 20 messages/day, see profile photo |
| **Plus** | €14.99/mo | "She can't stop thinking about you" | Unlimited messaging, 30 photos/month, spicy nude photos, 2 free mystery boxes, voice messages |
| **Premium** | €29.99/mo | "She's completely yours" | Everything in Plus, 80 photos/month, 2 gift + 2 intimacy boxes/month, most explicit content, up to 3 girlfriends |

**Card required for all plans** (including Free trial). No skip option during onboarding.

---

## Gift System

26 gifts across 4 tiers (Everyday €2–€9, Dates €12–€35, Luxury €60–€140, Legendary €160–€200).

**Each gift can only be purchased once per girlfriend.** The backend enforces this; the frontend shows "Already Gifted" for purchased gifts.

Each gift has:
- Unique emotional effect (stored in memory)
- Relationship boost (trust + intimacy, bank-first)
- Optional image album reward with **split normal + spicy photos**
- Cooldown (some gifts)

### Photo Rewards — Normal vs Spicy

Gifts with image rewards have two categories of photos:

| Type | Description | Gate |
|------|-------------|------|
| **Normal** | Safe/cute photos (selfies, outfits, travel, etc.) | None — always delivered on purchase |
| **Spicy** | Nude/suggestive photos (lingerie, boudoir, artistic nude, etc.) | None — always delivered on purchase |

**Gift photos bypass all content gates.** If a user purchases a gift, they receive all photos (normal AND spicy) regardless of plan, age gate, or intimacy level.

Every individual photo has a **unique image generation prompt** (stored in `photo_prompts[]` and `spicy_photo_prompts[]`).

### Gift Collection Panel

Fullscreen panel accessed via "Gift Collection" button on GirlPage:

- Shows **all 26 gifts** organized by tier (Everyday, Dates, Luxury, Legendary)
- Each gift shows purchased/locked state with green checkmark or price
- **Photo slot grid** per gift: exactly `normal_photos + spicy_photos` slots, showing purple slots for normal and rose slots for spicy
- Scroll-based color interpolation, floating gift icons background
- Fetches from `GET /api/gifts/collection`

Payment: Inline via saved Stripe card (PaymentIntent), no redirect.

---

## Achievement System

### Relationship Achievements (54 total)

Per-girlfriend, region-locked milestones on the Relationship Timeline.

**HARD RULE**: Achievements can ONLY be unlocked if `achievement.region_index == current_region_index`. Past region achievements are permanently locked.

#### Catalog Structure

- 9 regions × 6 achievements each = 54 total
- Each achievement has: `id`, `region_index`, `title`, `subtitle`, `rarity` (COMMON/UNCOMMON/RARE/EPIC/LEGENDARY), `sort_order`, `requirement` (server-checkable dict), `trigger` (TriggerType enum)

#### Trigger Types

| Trigger | When Evaluated |
|---------|----------------|
| `REGION_ENTER` | On entering a new region |
| `GIFT_CONFIRMED` | On gift purchase confirmation |
| `QUALITY_CHAT` | On high-quality message (quality_score ≥ threshold) |
| `AFFECTION_SIGNAL` | On detecting affection in messages |
| `VULNERABILITY_SIGNAL` | On detecting vulnerability in messages |
| `WE_LANGUAGE` | On detecting "we/us/our" language |
| `FUTURE_TALK` | On detecting future-oriented language |
| `CONFLICT_REPAIR` | On detecting apology + reassurance |
| `STREAK` | On consecutive-day streaks |
| `RETURN_GAP` | On returning after days of absence |
| `MEMORY_EVENT` | On memory flag detection |

#### Signal Detection (achievement_engine.py)

Regex-based heuristics detect signals in user and assistant messages:
- `affection_detected`: "miss you", "love", "care", "sweet", etc.
- `vulnerability_detected`: "I feel scared", "I worry", "I'm afraid", etc.
- `we_language_detected`: "we", "us", "our" (word boundaries)
- `future_talk_detected`: "future", "someday", "one day", "plan", etc.
- `conflict_repair_detected`: apology + reassurance within recent messages
- `memory_flag_seen`: heuristic keyword detection for specific flags

#### Achievement Progress (per-girl)

Tracked in `AchievementProgress` dataclass:
- `affection_hits`, `vulnerability_hits`, `we_language_hits`, `future_talk_hits`, `conflict_repairs`
- `streak_days_in_region`, `days_since_last_interaction`, `last_interaction_date`
- `memory_flags_seen`, `gift_confirmed_in_region`
- Counters **reset when entering a new region**

#### SSE Event

When unlocked: `event_type="relationship_achievement"` with `{ id, title, subtitle, rarity, region_index, girlfriend_id, unlocked_at }`

### Intimate Progression (50 achievements, frontend-only)

Separate collection of 50 sexual achievements across 7 tiers, displayed in the "Intimate Progression" panel.

| Tier | Title | Count |
|------|-------|-------|
| 0 | Flirting & Tension | 7 |
| 1 | First Touch | 7 |
| 2 | Heating Up | 7 |
| 3 | Undressed | 8 |
| 4 | Full Intimacy | 8 |
| 5 | Deep Exploration | 8 |
| 6 | Ultimate Connection | 7 |

Each achievement has a `scene` field (visual description for future photo generation) and a `rarity` (COMMON through LEGENDARY). Photo thumbnails are displayed next to each achievement. Currently frontend-only; unlock logic TBD.

---

## Region Caps + Banked Overflow (Trust & Intimacy)

Both Trust and Intimacy use a **visible/bank split**:
- `*_visible` — displayed on meters, used for gating
- `*_bank` — earned but locked until region cap allows

### Cap Tables

| Region | Intimacy Cap | Trust Cap |
|--------|-------------|-----------|
| 1 (0–10) | 20 | 35 |
| 2 (11–25) | 28 | 45 |
| 3 (26–45) | 38 | 55 |
| 4 (46–70) | 50 | 65 |
| 5 (71–105) | 62 | 75 |
| 6 (106–135) | 72 | 83 |
| 7 (136–165) | 82 | 90 |
| 8 (166–185) | 90 | 95 |
| 9 (186–200) | 100 | 100 |

### Flow

1. Any gain (conversation, gift, region milestone) goes to **bank first**
2. `release_banked()` immediately moves bank → visible up to region cap
3. On region change, `release_banked()` runs again with the new higher cap
4. Image Decision Engine uses `intimacy_visible` only (banked doesn't count for gating)

### SSE Payload

`relationship_gain` events include: `trust_banked_delta`, `trust_released_delta`, `trust_visible_new`, `trust_bank_new`, `trust_cap`, and equivalent intimacy fields, plus `tease_line` when capped.

---

## GirlPage — Side Panels

The GirlPage has 5 fullscreen panels accessed via side buttons (desktop) or bottom strip buttons (mobile):

### 1. My Relationship (RelationshipPanel)

- **Redesigned visual**: glass-effect top bar, achievement-first layout
- **Region header cards**: large glowing icon orb, progress bar, "You are here" badge
- **Achievement cards**: dominant visual — large (p-5, h-16 icon), per-rarity gradient backgrounds, glow effects on legendary/epic, shimmer overlays
- **Background**: subtle floating Lucide icons (Heart, Sparkles, Star, Flame) as romantic wallpaper
- **Dividers**: minimal heart + sparkle separators between regions
- **All achievements visible** in every region (locked = dimmed with lock, unlocked = rarity-colored with checkmark)
- Scroll-based color interpolation between region accent colors

### 2. Intimate Progression (IntimateProgressionPanel)

- 7 tiers of sexual achievements, each with heart-themed design
- 50 achievements with titles, subtitles, and photo thumbnail slots
- Rarity-specific styling (icons, colors, badges)
- Floating hearts background animation
- Scroll-based color interpolation

### 3. Gift Collection (GiftCollectionPanel)

- 4 tiers: Everyday, Dates, Luxury, Legendary
- All 26 gifts with purchased/locked state
- Photo slot grid per gift (exact count matching normal_photos + spicy_photos)
- Purple theme for normal photo slots, rose theme for spicy
- Floating gift icons background

### 4. Surprise Her (MysteryBoxPanel)

- 3 mystery box tiers (Bronze, Gold, Diamond) with escalating prices
- Slot machine spin animation with easing deceleration
- Stripe payment via saved card (inline, 3DS support)
- Reveals random gift from catalog with tier-specific styling
- Odds bar per box showing tier distribution
- No duplicates — skips already-owned gifts

### 5. Leaks (LeaksPanel)

- **Spin tab**: 3 paid slot boxes (Quick Peek €1.99, Private Collection €4.99, Fully Uncensored €9.99)
  - Slot machine with animated reel, dramatic reveal of leaked photo
  - Rarity-weighted odds: higher boxes = more explicit content (Epic/Legendary)
  - Stripe payment via saved card, 3DS support
- **Collection tab**: Grid of all 50 leaked photos by rarity
  - 5 rarities: Common (18), Uncommon (12), Rare (10), Epic (6), Legendary (4)
  - Explicit/sexual titles visible for all photos (locked and unlocked)
  - Rarity filter, progress bar, fullscreen image viewer
  - No duplicates — each spin unlocks something new
- **Only way to unlock leaks** — no chat-based random drops

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
- **RelationshipState**: `trust`, `intimacy`, `level`, `region_key`, `region_title`, `trust_visible`, `trust_bank`, `trust_cap`, `intimacy_visible`, `intimacy_bank`, `intimacy_cap`, `milestones_reached`, `current_region_index`
- **RelationshipAchievement**: `id`, `region_index`, `title`, `subtitle`, `rarity`, `sort_order`, `trigger`
- **BillingStatus**: `plan`, `has_card_on_file`, `message_cap`, `image_cap`, `girls_max`, `girls_count`, `can_create_more_girls`
- **GiftDefinition**: `id`, `name`, `price_eur`, `tier`, `relationship_boost`, `image_reward`, `unique_effect_name`, `unique_effect_description`, `cooldown_days`, `spicy_unlocked`, `already_purchased`
- **GiftCollectionItem**: extends GiftDefinition with `purchased`, `purchased_at`
- **GiftImageReward**: `album_size`, `normal_photos`, `spicy_photos`, `photo_prompts[]`, `spicy_photo_prompts[]`, `suggestive_level` ("safe" | "mild" | "spicy")
- **BigFive**: `openness`, `conscientiousness`, `extraversion`, `agreeableness`, `neuroticism` (0–100)
- **GirlProfileStats**: `girlfriend_id`, `name`, `avatar_url`, `vibe_line`, `relationship`, `activity` (streaks), `collections`
- **ProfileGirlsResponse**: `girls[]`, `totals` (girls, messages, photos, gifts_owned)

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
- **test_relationship_regions.py** — Region mapping correctness (boundary values, clamp behavior)
- **test_relationship_progression.py** — 45 tests: cooldown, streak, clamp, quality, anti-farm, gap bonus, derive trust/intimacy, integration
- **test_intimacy.py** — 35 tests: region awards, gift awards, daily caps, duplicate prevention, personality thresholds, sensitive detection, image decision engine, blurred paywall (free vs paid), proactive blurred surprise
- **test_trust_intimacy.py** — 71 tests: trust clamp/defaults, quality score, conversation trust gain, trust gifts (tier-based, dedup, caps), intimacy regions, intimacy gifts, trust decay, descriptors, gain events, region caps, banked overflow, release mechanism
- **test_achievements.py** — 73 tests: region-lock enforcement, counter resets, trigger evaluation, signal detection, gift unlock, streak tracking, requirement evaluation
