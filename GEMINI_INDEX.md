# VirtualFR Project Index

**Comprehensive documentation of the VirtualFR codebase structure, APIs, and architecture.**

---

## 1. Project Overview

**VirtualFR** is an AI-powered virtual girlfriend companion application built as a monorepo with a FastAPI backend and React frontend. The app provides:

- **Onboarding Flow**: Multi-step persona creation (traits, appearance, identity, preferences)
- **Chat System**: Real-time SSE streaming chat with personality-aware responses
- **Relationship Engine**: Dynamic trust/intimacy system with relationship levels (STRANGER → FAMILIAR → CLOSE → INTIMATE → EXCLUSIVE)
- **Intimacy Achievements**: Tiered intimate content progression system
- **Memory System**: Long-term factual and emotional memory extraction from conversations
- **Gifting System**: Stripe-powered gift purchases (€2–€200) with unique effects and relationship boosts
- **Mystery Boxes**: "Surprise Her" slot machine and "Seduce Her Now" intimate gift boxes
- **Billing**: Stripe subscriptions (Free w/ 7-day trial, Plus, Premium tiers) with message/image caps and multi-card management
- **Multi-Girlfriend**: Support for up to 3 companions on paid plans
- **Personality Engines**: Big Five personality mapping, trait behavior rules, initiation engine, habit profiling
- **Gallery**: Image generation and storage
- **Safety & Moderation**: Reporting system

**Subscription Tiers:**
- **Free**: 7-day trial (auto-upgrades to Plus), limited messages (20/day), 1 girl max, blurred image paywall
- **Plus**: Unlimited messages, 30 photos/month, unlock spicy nude photos, 2 free gift mystery boxes, up to 3 girls
- **Premium**: Unlimited messages, 80 photos/month, 2 free gift + 2 free intimacy boxes/month, more explicit photos, up to 3 girls

**Cancellation Flows:** Multi-step manipulative retention flows for both trial and paid plan cancellations (emotional hooks, FOMO, spicy photo tease).

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
│   │   │   ├── routes/              # API route handlers
│   │   │   │   ├── auth.py
│   │   │   │   ├── billing.py
│   │   │   │   ├── chat.py
│   │   │   │   ├── gifts.py
│   │   │   │   ├── girlfriends.py
│   │   │   │   ├── health.py
│   │   │   │   ├── images.py
│   │   │   │   ├── intimacy_achievements.py
│   │   │   │   ├── me.py
│   │   │   │   ├── memory.py
│   │   │   │   ├── moderation.py
│   │   │   │   ├── onboarding.py
│   │   │   │   └── relationship.py
│   │   │   ├── store.py             # In-memory session store
│   │   │   └── supabase_store.py    # Supabase persistence layer
│   │   ├── core/                    # Core config, auth, CORS, rate limiting
│   │   ├── routers/                 # Chat gateway, mock model
│   │   ├── schemas/                 # Pydantic models
│   │   │   ├── auth.py
│   │   │   ├── billing.py
│   │   │   ├── chat.py
│   │   │   ├── gift.py
│   │   │   ├── girlfriend.py
│   │   │   ├── image.py
│   │   │   ├── intimacy.py
│   │   │   ├── intimacy_achievements.py
│   │   │   ├── payment_method.py
│   │   │   ├── relationship.py
│   │   │   └── trust_intimacy.py
│   │   ├── services/                # Business logic engines
│   │   ├── utils/                   # Utilities (SSE, moderation, identity canon)
│   │   └── main.py                  # FastAPI app entry point
│   ├── docs/                        # Setup guides
│   ├── inference/                   # Docker inference container
│   ├── logs/                        # Chat JSONL logs
│   ├── scripts/                     # Utility scripts
│   ├── tests/                       # Test suite
│   ├── supabase_schema.sql          # Database schema
│   ├── requirements.txt             # Python dependencies
│   └── .env.example                 # Environment template
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── billing/             # Stripe card & upgrade modals
    │   │   │   ├── AddCardModal.tsx
    │   │   │   └── UpgradeModal.tsx
    │   │   ├── chat/                # Chat UI components
    │   │   │   ├── AchievementUnlockedCard.tsx
    │   │   │   ├── BlurredImageCard.tsx
    │   │   │   ├── ChatHeader.tsx
    │   │   │   ├── Composer.tsx
    │   │   │   ├── GiftCollectionPanel.tsx
    │   │   │   ├── GiftModal.tsx
    │   │   │   ├── ImageMessage.tsx
    │   │   │   ├── ImageTeaseCard.tsx
    │   │   │   ├── IntimateProgressionPanel.tsx
    │   │   │   ├── MessageBubble.tsx
    │   │   │   ├── MessageList.tsx
    │   │   │   ├── MysteryBoxPanel.tsx
    │   │   │   ├── PaywallInlineCard.tsx
    │   │   │   ├── RelationshipGainCard.tsx
    │   │   │   ├── RelationshipMeter.tsx
    │   │   │   └── TypingIndicator.tsx
    │   │   ├── gallery/             # Image gallery
    │   │   │   ├── GalleryGrid.tsx
    │   │   │   └── ImageViewerModal.tsx
    │   │   ├── layout/              # App shell, nav, footer
    │   │   │   ├── AppShell.tsx
    │   │   │   ├── Footer.tsx
    │   │   │   ├── MobileNav.tsx
    │   │   │   ├── SideNav.tsx
    │   │   │   └── TopNav.tsx
    │   │   ├── onboarding/          # Onboarding wizard components
    │   │   │   ├── AppearanceStepPage.tsx
    │   │   │   ├── OnboardingSignIn.tsx
    │   │   │   ├── PersonaPreviewCard.tsx
    │   │   │   ├── ProgressStepper.tsx
    │   │   │   ├── TraitCard.tsx
    │   │   │   └── TraitSelector.tsx
    │   │   ├── safety/              # Reporting
    │   │   │   ├── ContentPreferences.tsx  (legacy, removed from UI)
    │   │   │   └── ReportDialog.tsx
    │   │   └── ui/                  # shadcn/ui components
    │   │       ├── AvatarCircle.tsx
    │   │       ├── badge.tsx
    │   │       ├── button.tsx
    │   │       ├── card.tsx
    │   │       ├── checkbox.tsx
    │   │       ├── dialog.tsx
    │   │       ├── dropdown-menu.tsx
    │   │       ├── input.tsx
    │   │       ├── label.tsx
    │   │       ├── separator.tsx
    │   │       ├── skeleton.tsx
    │   │       ├── tabs.tsx
    │   │       └── tooltip.tsx
    │   ├── lib/
    │   │   ├── api/                 # API client, endpoints, types
    │   │   ├── engines/             # Frontend personality engines
    │   │   ├── hooks/               # React hooks (auth, SSE chat)
    │   │   ├── store/               # Zustand stores
    │   │   └── constants/           # Identity constants
    │   ├── pages/                   # Route pages
    │   │   ├── appearance/          # Appearance sub-pages
    │   │   │   ├── AppearanceAge.tsx
    │   │   │   ├── AppearanceBody.tsx
    │   │   │   ├── AppearanceBodyDetails.tsx
    │   │   │   ├── AppearanceBreast.tsx
    │   │   │   ├── AppearanceButt.tsx
    │   │   │   ├── AppearanceEthnicity.tsx
    │   │   │   ├── AppearanceEyes.tsx
    │   │   │   ├── AppearanceHairColor.tsx
    │   │   │   ├── AppearanceHairEyes.tsx
    │   │   │   └── AppearanceHairStyle.tsx
    │   │   ├── AgeGate.tsx
    │   │   ├── Billing.tsx
    │   │   ├── Chat.tsx
    │   │   ├── Gallery.tsx
    │   │   ├── GirlfriendReveal.tsx
    │   │   ├── GirlPage.tsx
    │   │   ├── Landing.tsx
    │   │   ├── Login.tsx
    │   │   ├── OnboardingAppearance.tsx
    │   │   ├── OnboardingGenerating.tsx
    │   │   ├── OnboardingIdentity.tsx
    │   │   ├── OnboardingPreferences.tsx
    │   │   ├── OnboardingTraits.tsx
    │   │   ├── PaymentOptions.tsx
    │   │   ├── PersonaPreview.tsx
    │   │   ├── Profile.tsx
    │   │   ├── Relationship.tsx
    │   │   ├── RevealSuccess.tsx
    │   │   ├── Safety.tsx
    │   │   ├── Settings.tsx
    │   │   ├── Signup.tsx
    │   │   └── SubscriptionPlan.tsx
    │   ├── routes/                  # React Router config + guards
    │   └── styles/                  # Global CSS
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
- `GET /api/girlfriends/list` — List all girlfriends for multi-girl support
- `POST /api/girlfriends/switch` — Switch active girlfriend
- `POST /api/girlfriends/create-additional` — Create additional girlfriend (plan limits: free=1, plus=3, premium=3)

#### **`chat.py`** — Chat System
- `GET /api/chat/history` — Get message history
- `GET /api/chat/state` — Get relationship state (trust, intimacy, level)
- `POST /api/chat/send` — Send message (SSE stream response, 20/day cap for free)
- `POST /api/chat/app_open` — App open handler (initiation + jealousy reactions)

#### **`onboarding.py`** — Onboarding
- `GET /api/onboarding/prompt-images` — Get prompt image URLs for appearance steps
- `POST /api/onboarding/complete` — Finalize onboarding (create girlfriend with identity canon)

#### **`billing.py`** — Stripe Billing & Payment Methods
- `GET /api/billing/status` — Get plan, caps, card status, free_trial_ends_at
- `GET /api/billing/stripe-key` — Get Stripe publishable key
- `GET /api/billing/payment-method` — Get primary payment method card summary
- `GET /api/billing/payment-methods` — List all saved payment cards (with default marker)
- `POST /api/billing/set-default-card` — Set a specific card as default payment method
- `DELETE /api/billing/payment-method/{pm_id}` — Remove (detach) a saved card
- `POST /api/billing/setup-intent` — Create Stripe SetupIntent for card saving
- `POST /api/billing/preview-change` — Preview proration cost for plan change
- `POST /api/billing/change-plan` — Change subscription plan (upgrade/downgrade with proration)
- `POST /api/billing/subscribe` — Create subscription (plus/premium)
- `POST /api/billing/cancel` — Cancel subscription (user logged out by frontend)
- `POST /api/billing/checkout` — Create Stripe Checkout Session
- `POST /api/billing/webhook` — Stripe webhook handler
- `POST /api/billing/confirm-card` — Optimistic card confirmation

**Dev/Demo Fallback:** When Stripe is not configured (`stripe_secret_key` is empty), `change-plan`, `preview-change`, and `cancel` endpoints fall back to in-memory-only plan changes.

#### **`gifts.py`** — Gift System
- `GET /api/gifts/list` — Get full gift catalog
- `POST /api/gifts/checkout` — Create Stripe Checkout Session for gift
- `POST /api/gifts/webhook` — Stripe webhook for gift payments
- `GET /api/gifts/history` — Get gift purchase history
- `GET /api/gifts/collection` — Get gift collection

#### **`relationship.py`** — Relationship & Achievements
- `GET /api/relationship/achievements` — Get relationship achievements catalog

#### **`intimacy_achievements.py`** — Intimacy Progression
- Tiered intimacy achievement endpoints for intimate content progression

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

#### **`image_decision_engine.py`**
- Gating logic for images based on plan (blurred paywall for Free users)

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
- **`billing.py`**: `BillingStatusResponse` (includes `free_trial_ends_at`), `ChangePlanResponse`, `PreviewChangeResponse`, `ChangePlanRequest`, `PreviewChangeRequest`
- **`chat.py`**: `SendMessageRequest`, `AppOpenRequest`, `ChatMessage`, `RelationshipState`
- **`gift.py`**: `GiftDefinition`, `RelationshipBoost`, `ImageReward`
- **`girlfriend.py`**: `CreateGirlfriendRequest`, `GirlfriendResponse`, `IdentityResponse`, `OnboardingCompletePayload`
- **`image.py`**: `ImageRequestResponse`, `ImageJobResponse`, `GalleryItem`
- **`intimacy.py`**: Intimacy-related models
- **`intimacy_achievements.py`**: Tiered intimacy achievement models
- **`payment_method.py`**: `PaymentMethodCardSummary` (id, brand, last4, exp, is_default), `PaymentMethodResponse`, `PaymentMethodsListResponse`, `SetDefaultCardRequest`
- **`relationship.py`**: Relationship state models
- **`trust_intimacy.py`**: Trust/intimacy state models

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
- `appearance/AppearanceAge.tsx` — Age range selection
- `appearance/AppearanceEthnicity.tsx` — Ethnicity selection
- `appearance/AppearanceBody.tsx` — Body type
- `appearance/AppearanceBodyDetails.tsx` — Body details
- `appearance/AppearanceBreast.tsx` — Breast size
- `appearance/AppearanceButt.tsx` — Butt size
- `appearance/AppearanceHairColor.tsx` — Hair color
- `appearance/AppearanceHairStyle.tsx` — Hair style
- `appearance/AppearanceEyes.tsx` — Eye color
- `appearance/AppearanceHairEyes.tsx` — Combined hair/eyes selection
- `OnboardingPreferences.tsx` — Content preferences (spicy photos)
- `OnboardingIdentity.tsx` — Identity (name, job, hobbies, origin)
- `OnboardingGenerating.tsx` — Loading state during generation
- `GirlfriendReveal.tsx` — Reveal animation
- `SubscriptionPlan.tsx` — Subscription selection (includes 7-day trial notice)
- `RevealSuccess.tsx` — Success page
- `PersonaPreview.tsx` — Final persona preview

#### **App Pages** (under `/app`)
- `GirlPage.tsx` — Main girlfriend page (chat, gallery, relationship meter, sidebar buttons)
  - Desktop sidebar order: My Relationship → Intimate Progression → Seduce Her Now → Gift Collection → Surprise Her
- `Relationship.tsx` — Relationship achievements and milestones
- `Profile.tsx` — Girlfriend profile (companion card with avatar, traits)
- `Settings.tsx` — User settings
  - **Notifications**: Push notification master toggle, new messages toggle, new photos toggle
  - **Account**: Change password (expandable form), Log out, Delete account (with destructive confirmation)
- `Billing.tsx` — Billing management
  - Current plan card with features and free trial notice
  - Upgrade options with proration preview
  - 4-step manipulative trial cancel flow (emotional hook → FOMO → spicy photo tease → final)
  - 4-step manipulative paid cancel flow (emotional hook → what you lose → spicy photo tease → final)
- `PaymentOptions.tsx` — Payment card management
  - Lists all saved cards (always at least one)
  - Default card selection (click to set)
  - Card deletion (trash icon)
  - Add new card via AddCardModal
- `Safety.tsx` — Report & moderation (ContentPreferences removed from UI)

### 4.2 Components (`frontend/src/components/`)

#### **Billing**
- `AddCardModal.tsx` — Stripe card collection modal
- `UpgradeModal.tsx` — Plan upgrade modal with shimmer animations (handles NO_PAYMENT_METHOD → opens AddCardModal)

#### **Chat**
- `AchievementUnlockedCard.tsx` — Achievement unlock notification
- `BlurredImageCard.tsx` — Blurred image preview with paywall for free users
- `ChatHeader.tsx` — Chat header with girlfriend info
- `Composer.tsx` — Message input
- `GiftCollectionPanel.tsx` — Gift collection display
- `GiftModal.tsx` — Gift purchase modal
- `ImageMessage.tsx` — Image message display
- `ImageTeaseCard.tsx` — Image tease card
- `IntimateProgressionPanel.tsx` — Intimate achievements and "Seduce Her Now" mystery boxes (prices: €4.99+)
- `MessageBubble.tsx` — Message display
- `MessageList.tsx` — Message list container
- `MysteryBoxPanel.tsx` — "Surprise Her" slot machine panel
- `PaywallInlineCard.tsx` — Paywall card for free tier limits (gradient, shimmer)
- `RelationshipGainCard.tsx` — Relationship gain notification
- `RelationshipMeter.tsx` — Trust/intimacy visualization
- `TypingIndicator.tsx` — Typing animation

#### **Gallery**
- `GalleryGrid.tsx` — Image grid display
- `ImageViewerModal.tsx` — Full-screen image viewer

#### **Layout**
- `AppShell.tsx` — Main app layout wrapper
- `TopNav.tsx` — Top navigation bar
- `SideNav.tsx` — Side navigation (girlsMax: 3 for paid, 1 for free)
- `MobileNav.tsx` — Mobile navigation
- `Footer.tsx` — Footer component

#### **Onboarding**
- `AppearanceStepPage.tsx` — Appearance step wrapper
- `OnboardingSignIn.tsx` — Sign-in prompt during onboarding
- `PersonaPreviewCard.tsx` — Live persona preview
- `ProgressStepper.tsx` — Onboarding progress indicator
- `TraitCard.tsx` — Individual trait card
- `TraitSelector.tsx` — Trait selection UI

#### **Safety**
- `ContentPreferences.tsx` — Legacy file (removed from Safety and Settings UI)
- `ReportDialog.tsx` — Report dialog

#### **UI** (shadcn/ui)
- `AvatarCircle.tsx`, `badge.tsx`, `button.tsx`, `card.tsx`, `checkbox.tsx`, `dialog.tsx`, `dropdown-menu.tsx`, `input.tsx`, `label.tsx`, `separator.tsx`, `skeleton.tsx`, `tabs.tsx`, `tooltip.tsx`

### 4.3 Lib (`frontend/src/lib/`)

#### **API Client** (`lib/api/`)
- **`client.ts`**: `apiGet()`, `apiPost()`, `apiDelete()` helpers with cookie auth. Parses `err.detail` (FastAPI) and `err.error` from non-2xx responses.
- **`endpoints.ts`**: All API endpoint functions:
  - Auth: `signup`, `login`, `logout`
  - Me: `getMe`, `postAgeGate`
  - Girlfriends: `createGirlfriend`, `getCurrentGirlfriend`, `listGirlfriends`, `switchGirlfriend`, `createAdditionalGirlfriend`
  - Chat: `getChatHistory`, `getChatState`, `postChatAppOpen`, `getChatSendStreamUrl`
  - Images: `requestImage`, `getImageJob`, `getGallery`
  - Billing: `getBillingStatus`, `createSetupIntent`, `confirmCard`, `subscribeToPlan`, `cancelSubscription`, `getPaymentMethod`, `listPaymentMethods`, `setDefaultCard`, `deletePaymentMethod`, `getStripePublishableKey`, `checkout`, `previewPlanChange`, `changePlan`
  - Gifts: `getGiftsList`, `createGiftCheckout`, `confirmGiftPayment`, `getGiftHistory`, `getGiftCollection`
  - Memory: `getMemorySummaryContext`, `getFactualMemoryItems`, `getEmotionalMemoryItems`, `getMemoryStats`
  - Moderation: `report`
  - Onboarding: `getOnboardingPromptImages`, `completeOnboarding`
  - Relationship: `getAchievementsCatalog`
  - Intimacy: `getIntimacyAchievements`, `mysteryUnlockIntimacyAchievement`
- **`types.ts`**: TypeScript types matching backend schemas:
  - Core: `User`, `TraitSelection`, `AppearancePrefs`, `ContentPrefs`, `IdentityPrefs`, `IdentityCanon`, `OnboardingCompleteRequest`, `Girlfriend`, `Traits`
  - Chat: `ChatMessage`, `ChatMessageRole`, `RelationshipState`, `RegionKey`
  - Achievements: `AchievementRarity`, `RelationshipAchievement`, `AchievementsByRegion`, `AchievementsCatalogResponse`
  - Intimacy: `IntimacyAchievementItem`, `IntimacyTierInfo`, `IntimacyAchievementsByTier`
  - Habits: `UserHabitProfile`
  - Images: `ImageJob`, `GalleryItem`
  - Billing: `Plan`, `BillingStatus` (includes `free_trial_ends_at`), `PreviewPlanChangeResponse`, `ChangePlanResponse`, `ProrationLineItem`, `InvoiceSummary`
  - Multi-girl: `GirlfriendListResponse`, `SetCurrentGirlfriendRequest`, `SwitchGirlfriendResponse`, `CreateGirlfriendResponse`
  - Payment: `SetupIntentResponse`, `PaymentMethodCardSummary` (id, brand, last4, exp_month, exp_year, is_default), `PaymentMethodResponse`, `PaymentMethodsListResponse`
  - Memory: `MemoryType`, `FactualMemoryItem`, `EmotionalMemoryItem`, `MemoryContext`, `MemorySummary`, `MemoryItemsResponse`
  - Big Five: `BigFive`, `BigFiveSource`, `BigFiveProfile`
  - Gifts: `GiftImageReward`, `GiftRelationshipBoost`, `GiftDefinition`, `GiftListResponse`, `GiftCheckoutResponse`, `GiftHistoryItem`, `GiftHistoryResponse`, `GiftEventData`, `GiftCollectionItem`, `GiftCollectionResponse`
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
- `useSSEChat.ts` — SSE chat streaming hook (handles 429 daily_limit_reached for free users)

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
  - `/onboarding/traits` — Trait selection
  - `/onboarding/appearance` — Appearance wizard
  - `/onboarding/preferences` — Content preferences
  - `/onboarding/identity` — Identity creation
  - `/onboarding/generating` — Generation loading
  - `/onboarding/reveal` — Girlfriend reveal
  - `/onboarding/subscribe` — Subscription selection
  - `/onboarding/reveal-success` — Reveal success
  - `/onboarding/preview` — Persona preview
- `/app/*` — App pages (requires auth + age gate + girlfriend)
  - `/app/girl` — Main girlfriend page (chat, gallery, sidebar actions)
  - `/app/girls/:girlId/relationship` — Per-girl relationship page
  - `/app/profile` — Girlfriend profile
  - `/app/settings` — Settings (notifications + account)
  - `/app/billing` — Billing & subscription management
  - `/app/payment-options` — Payment card management
  - `/app/safety` — Safety & reporting
- Legacy redirects: `/app/chat`, `/app/gallery`, `/app/relationship` → `/app/girl`

---

## 5. Key Integrations

### 5.1 Stripe

**Billing:**
- SetupIntent for card saving (`/api/billing/setup-intent`)
- Subscriptions (Plus, Premium tiers)
- Plan changes with proration (`/api/billing/change-plan`, `/api/billing/preview-change`)
- Multi-card management (`/api/billing/payment-methods`, `/api/billing/set-default-card`, `DELETE /api/billing/payment-method/{pm_id}`)
- Webhook handler (`/api/billing/webhook`) for subscription events
- Dev/demo fallback: in-memory plan changes when Stripe is not configured

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

### 8.1 Subscription & Trial System

- **Free Plan**: 7-day trial, after which user is auto-upgraded to Plus. Legal disclosure shown on onboarding and billing pages. Includes 20 messages/day, 1 girlfriend, blurred image paywall.
- **Plus Plan**: Unlimited messages, 30 photos/month, spicy content, 2 free gift boxes, up to 3 girls.
- **Premium Plan**: Unlimited messages, 80 photos/month, explicit content, 2 gift + 2 intimacy boxes/month, up to 3 girls.
- **Cancellation**: Multi-step manipulative retention flows (emotional hooks, FOMO, "spicy photo she's been saving" tease). Cancelling logs user out; free plan is not a fallback for paid users.
- **Payment**: Card required at signup. Multi-card support with default card selection.

### 8.2 Relationship System

- **Levels**: STRANGER (0-15 intimacy) → FAMILIAR (16-35) → CLOSE (36-60) → INTIMATE (61-80) → EXCLUSIVE (81-100)
- **Trust/Intimacy**: 0-100 scale, updated on interactions
- **Decay**: Intimacy decays after 24h/72h inactivity (based on attachment style)
- **Milestones**: Automatic milestone detection on level transitions
- **Jealousy**: Reactions based on absence duration and jealousy level trait
- **Achievements**: Relationship achievement catalog with rarity tiers

### 8.3 Memory System

- **Factual Memory**: Stable facts (name, city, preferences) extracted via regex patterns
- **Emotional Memory**: Events + feelings (stress, affection, etc.) via keyword detection
- **Memory Context**: Compact summaries for LLM prompts (max 8 facts, 5 emotions, habit hints)

### 8.4 Personality Engines

- **Big Five Mapping**: 6 onboarding traits → Big Five scores (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism)
- **Trait Behavior Rules**: Trait-specific behavior expressions
- **Initiation Engine**: Decides when girlfriend should initiate conversations
- **Habit Profiling**: Analyzes user message patterns (preferred hours, typical gaps)

### 8.5 Gifting & Mystery Boxes

- **24 Gifts**: €2–€200 range, 4 tiers (everyday, dates, luxury, legendary)
- **Relationship Boosts**: Trust/intimacy gains per gift
- **Unique Effects**: Gift-specific effects (patron badge, outfit era, theme song, etc.)
- **Image Rewards**: Some gifts trigger image generation (1-6 images)
- **Cooldowns**: Rare gifts have 14-60 day cooldowns
- **Mystery Boxes**: "Surprise Her" slot machine, "Seduce Her Now" intimate gift boxes (€4.99+)
- **Gift Collection**: Tracked collection panel

### 8.6 Intimacy Progression

- Tiered intimate content system with achievements
- Progressive unlocks based on relationship level and subscription tier

### 8.7 Onboarding Flow

1. **Traits** (6 questions): Emotional style, attachment, reaction to absence, communication style, relationship pace, cultural personality
2. **Appearance**: Vibe, age, ethnicity, body details (body type, breast, butt), hair (color, style), eyes
3. **Preferences**: Content preferences (spicy photos)
4. **Identity**: Name, job vibe, hobbies, origin vibe
5. **Generation**: Creates identity canon (backstory, daily routine, favorites, memory seeds)
6. **Reveal**: Animated reveal + subscription selection (7-day trial notice)

---

## 9. Key Files Reference

### Backend Entry Points
- `backend/app/main.py` — Main FastAPI app (includes `POST /api/dev/reset` for wiping in-memory state)
- `backend/app/mock_main.py` — Mock model server
- `backend/app/routers/chat.py` — Chat gateway
- `backend/app/routers/mock_model.py` — Mock OpenAI-compatible model

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
- lucide-react (icons)
- vite, typescript

---

**Last Updated**: February 11, 2026  
**Project**: VirtualFR  
**Repository**: `c:\Users\matej\OneDrive\Desktop\virtualfr`
