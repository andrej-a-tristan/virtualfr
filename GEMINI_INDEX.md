# GEMINI_INDEX.md - VirtualFR Project Index

Comprehensive index of all source files in the VirtualFR monorepo (FastAPI backend + React frontend).

## Root Directory

- **README.md** - Main project documentation explaining the monorepo structure, development setup, production deployment, and features including auth, onboarding, chat, gallery, billing, and safety.
- **.gitignore** - Git ignore patterns for dependencies (node_modules, __pycache__), build artifacts, IDE files, OS files, logs, and test coverage.
- **onboarding_questions.md.txt** - Text file containing onboarding questions (likely used for reference or documentation).
- **PROJECT_INDEX.md** - Existing project index file (may contain similar information).

## Backend (`backend/`)

### Configuration & Setup

- **requirements.txt** - Python dependencies including FastAPI, uvicorn, pydantic, supabase, httpx, openai, stripe, and pytest.
- **.env.example** - Environment variable template showing required configuration for Supabase, API keys, Stripe, and chat gateway settings.
- **supabase_schema.sql** - SQL schema definitions for Supabase database tables (users, sessions, girlfriends, messages, relationship_state, memories, etc.).

### Main Application (`backend/app/`)

#### Entry Points

- **main.py** - FastAPI application entry point that loads environment variables, sets up CORS, mounts API routers under `/api`, includes chat gateway routes, and serves static frontend files in production mode.
- **mock_main.py** - Standalone entrypoint for internal LLM mock server providing OpenAI-compatible endpoints (`POST /v1/chat/completions`) for development and testing.

#### Core (`backend/app/core/`)

- **config.py** - Application settings loaded from environment variables including host/port, CORS origins, Supabase credentials, API keys, Stripe configuration, and chat gateway settings.
- **auth.py** - Bearer token authentication for chat gateway endpoints using HTTPBearer security scheme and CHAT_API_KEY validation.
- **cors.py** - CORS middleware configuration for FastAPI application allowing cross-origin requests from configured origins.
- **rate_limit.py** - Rate limiting implementation for API endpoints to prevent abuse and ensure fair usage.
- **supabase_client.py** - Supabase client initialization and management, providing functions to get Supabase client instances and check if Supabase is configured.
- **chat_logging.py** - Chat request logging functionality that writes JSONL logs to `backend/logs/chat.jsonl` with request metadata, messages, responses, and performance metrics.
- **__init__.py** - Core module initialization exporting settings and CORS setup functions.

#### API Routes (`backend/app/api/routes/`)

- **auth.py** - Authentication endpoints for signup, login, and logout using mock session cookies stored in-memory or Supabase.
- **billing.py** - Billing endpoints for plan status, Stripe SetupIntent creation for card saving, subscription management (subscribe, cancel), webhook handling, and card confirmation.
- **chat.py** - Chat endpoints for message history, relationship state, sending messages with SSE streaming, and app_open initiation/jealousy reactions with full personality and memory integration.
- **girlfriends.py** - Girlfriend CRUD endpoints for creating and retrieving current girlfriend data with traits and display name.
- **health.py** - Simple health check endpoint returning `{"ok": True}` to verify API availability.
- **images.py** - Image request endpoints for creating image generation jobs, checking job status, and retrieving gallery items (currently using mock data).
- **me.py** - Current user endpoint returning user information with age gate and girlfriend flags, plus age gate POST endpoint to mark age gate as passed.
- **memory.py** - Memory API endpoints for accessing memory summary, raw memory items (factual/emotional), and memory statistics for debugging and UI display.
- **moderation.py** - Moderation endpoint for reporting inappropriate content (currently returns success without processing).
- **onboarding.py** - Onboarding endpoints for retrieving prompt images and completing onboarding by creating girlfriend avatar with identity canon generation.

#### API Utilities (`backend/app/api/`)

- **store.py** - In-memory session store for users, girlfriends, relationship state, messages, and habit profiles with Supabase persistence fallback when configured.
- **supabase_store.py** - Supabase-specific storage functions for persisting sessions, girlfriends, messages, relationship state, habit profiles, and memories to Supabase database.
- **request_context.py** - Request context utilities for extracting current user, session ID, and girlfriend ID from FastAPI requests.
- **__init__.py** - API module initialization.

#### Routers (`backend/app/routers/`)

- **chat.py** - Chat gateway router providing `POST /v1/chat/stream` endpoint with Bearer auth, rate limiting, timeouts, SSE proxy to internal LLM, and JSONL logging.
- **mock_model.py** - Mock LLM model router providing OpenAI-compatible `POST /v1/chat/completions` endpoint for development and testing without real LLM.
- **__init__.py** - Routers module initialization.

#### Schemas (`backend/app/schemas/`)

- **auth.py** - Pydantic schemas for authentication requests (SignupRequest, LoginRequest) and user responses (UserResponse).
- **chat.py** - Pydantic schemas for chat messages, relationship state, send message requests, and app open requests.
- **girlfriend.py** - Pydantic schemas for girlfriend creation requests, responses, identity responses, and onboarding completion payloads.
- **image.py** - Pydantic schemas for image request responses, job responses, and gallery items.
- **relationship.py** - Pydantic schemas for relationship state representation.
- **__init__.py** - Schemas module initialization.

#### Services (`backend/app/services/`)

- **big_five.py** - Big Five personality mapping service that converts 6 onboarding traits to Big Five scores (0.0-1.0) using JSON mapping configuration.
- **big_five_mapping.json** - JSON configuration file mapping trait values to Big Five personality scores (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism).
- **big_five_modulation.py** - Big Five personality modulation service for adjusting personality traits based on relationship state and interactions.
- **habits.py** - Habit profile service that analyzes user message timestamps to determine preferred hours, typical gap hours, and communication patterns.
- **initiation_engine.py** - Initiation engine service that determines when the girlfriend should initiate conversations based on relationship state, attachment intensity, inactivity, and user habits.
- **memory.py** - Memory system service providing short-term, long-term factual, and emotional memory storage and retrieval with Supabase persistence, including memory context building for prompt generation.
- **relationship_state.py** - Relationship state engine managing trust/intimacy levels, relationship progression (STRANGER → FAMILIAR → CLOSE → INTIMATE → EXCLUSIVE), inactivity decay, milestones, and jealousy reactions.
- **time_utils.py** - Time utility functions for ISO timestamp generation and calculating hours since last interaction.
- **trait_behavior_rules.py** - Trait behavior rules service defining how personality traits influence conversation behavior and responses.
- **__init__.py** - Services module initialization.

#### Utils (`backend/app/utils/`)

- **identity_canon.py** - Identity canon generation utility that creates deterministic personality descriptions and background stories for girlfriends based on traits and preferences.
- **prompt_identity.py** - Prompt identity utility for building system prompts that include girlfriend identity canon for LLM context.
- **moderation.py** - Moderation utilities for content filtering and safety checks (currently minimal implementation).
- **sse.py** - Server-Sent Events (SSE) utility functions for formatting SSE event messages in the chat streaming protocol.
- **__init__.py** - Utils module initialization.

### Documentation (`backend/docs/`)

- **SETUP_SUPABASE.md** - Setup guide for configuring Supabase connection and API keys in the backend, including environment variable configuration.
- **BIG_FIVE_MIGRATION.md** - Documentation about Big Five personality system migration and architecture decisions.

### Inference (`backend/inference/`)

- **Dockerfile** - Dockerfile for building CPU-only vLLM inference container that serves OpenAI-compatible API endpoints.
- **README.md** - Documentation for running CPU-only inference container with vLLM, including build instructions and configuration for pointing gateway at container.

### Scripts (`backend/scripts/`)

- **check_api_key.py** - Utility script for checking if API key is properly configured in environment.
- **check_config.py** - Utility script for validating backend configuration settings.

### Tests (`backend/tests/`)

- **test_chat_canon_injection.py** - Tests for verifying identity canon injection into chat prompts.
- **test_identity_canon.py** - Tests for identity canon generation functionality.
- **test_openai_contract.py** - Tests for verifying OpenAI-compatible API contract compliance.

## Frontend (`frontend/`)

### Configuration

- **package.json** - NPM package configuration with dependencies including React, Vite, TypeScript, TailwindCSS, React Router, TanStack Query, Zustand, Zod, Stripe, and shadcn/ui components.
- **vite.config.ts** - Vite build configuration with React plugin, path aliases (@/), dev server proxy for `/api` and `/v1` endpoints, and port 5173.
- **tsconfig.json** - TypeScript compiler configuration with strict mode, ES2020 target, React JSX, and path aliases.
- **tsconfig.node.json** - TypeScript configuration for Node.js build tools.
- **tailwind.config.ts** - TailwindCSS configuration with dark mode support, custom color variables, and animation plugin.
- **postcss.config.js** - PostCSS configuration with TailwindCSS and Autoprefixer plugins.
- **index.html** - HTML entry point for the React application.

### Source (`frontend/src/`)

#### Entry Points

- **main.tsx** - React application entry point that renders the App component with React.StrictMode.
- **App.tsx** - Main App component that sets up QueryClientProvider, TooltipProvider, and RouterProvider for the application.

#### Pages (`frontend/src/pages/`)

- **Landing.tsx** - Landing page that auto-signs in users, passes age gate, and redirects to onboarding (development convenience).
- **Login.tsx** - Login page with email/password form that calls login API and redirects based on user state.
- **Signup.tsx** - Signup page with email, password, and display name form that creates new user account.
- **AgeGate.tsx** - Age gate page requiring users to confirm they are 18+ before accessing the app.
- **Chat.tsx** - Main chat page that loads chat history, displays messages, and provides composer for sending messages.
- **Gallery.tsx** - Gallery page displaying generated images in a grid with modal viewer.
- **Profile.tsx** - User profile page showing girlfriend information and relationship details.
- **Settings.tsx** - Settings page for user preferences and account configuration.
- **Billing.tsx** - Billing management page showing current plan, upgrade/downgrade options across all tiers, and subscription cancellation with confirmation.
- **Safety.tsx** - Safety page for content preferences and reporting functionality.
- **SubscriptionPlan.tsx** - Onboarding subscription plan selection page for choosing free/plus/premium tiers with Stripe card collection.
- **RevealSuccess.tsx** - Post-subscription reveal page showing unblurred girlfriend photo with plan badge and "Let's chat" button.
- **GirlfriendReveal.tsx** - Girlfriend reveal page during onboarding for account creation before subscription selection.
- **PersonaPreview.tsx** - Persona preview page showing girlfriend summary before starting chat.
- **OnboardingTraits.tsx** - Onboarding traits page for selecting 6 relationship-style personality traits.
- **OnboardingAppearance.tsx** - Onboarding appearance page serving as hub for appearance customization steps.
- **OnboardingPreferences.tsx** - Onboarding preferences page for content and interaction preferences.
- **OnboardingIdentity.tsx** - Onboarding identity page for setting girlfriend name, job vibe, hobbies, and origin.
- **OnboardingGenerating.tsx** - Onboarding generating page showing loading state while girlfriend is being created.

#### Appearance Pages (`frontend/src/pages/appearance/`)

- **AppearanceAge.tsx** - Appearance age selection page for choosing girlfriend age range.
- **AppearanceEthnicity.tsx** - Appearance ethnicity selection page for choosing girlfriend ethnicity.
- **AppearanceBody.tsx** - Appearance body type selection page.
- **AppearanceBodyDetails.tsx** - Appearance body details page for selecting body type, breast size, and butt size on a single page.
- **AppearanceBreast.tsx** - Appearance breast size selection page.
- **AppearanceButt.tsx** - Appearance butt size selection page.
- **AppearanceHairColor.tsx** - Appearance hair color selection page.
- **AppearanceHairStyle.tsx** - Appearance hair style selection page.
- **AppearanceHairEyes.tsx** - Appearance hair and eye color/style selection page.
- **AppearanceEyes.tsx** - Appearance eye color selection page.

#### Components (`frontend/src/components/`)

##### Chat Components (`frontend/src/components/chat/`)

- **ChatHeader.tsx** - Chat header displaying girlfriend avatar, name, subscription plan badge, and relationship meter.
- **Composer.tsx** - Message composer with input field, send button, and SSE streaming support with billing-aware message limits.
- **MessageList.tsx** - Scrollable message list rendering chat messages in chronological order.
- **MessageBubble.tsx** - Individual message bubble component for user and assistant messages.
- **ImageMessage.tsx** - Image message component for displaying image attachments in chat.
- **TypingIndicator.tsx** - Animated typing indicator shown when girlfriend is generating a response.
- **RelationshipMeter.tsx** - Visual relationship meter showing trust/intimacy levels and relationship stage.
- **PaywallInlineCard.tsx** - Paywall card displayed inline when user hits message/image limits.

##### Layout Components (`frontend/src/components/layout/`)

- **AppShell.tsx** - Main application shell providing layout with top nav, sidebar, content area, and mobile nav.
- **TopNav.tsx** - Top navigation bar with app branding, subscription plan badge (color-coded by tier), and user dropdown menu.
- **SideNav.tsx** - Desktop sidebar navigation with links to chat, gallery, profile, settings, billing, and safety.
- **MobileNav.tsx** - Mobile bottom navigation bar for responsive layout.
- **Footer.tsx** - Footer component with links and copyright information.

##### Onboarding Components (`frontend/src/components/onboarding/`)

- **TraitSelector.tsx** - Trait selector component for choosing personality traits during onboarding.
- **TraitCard.tsx** - Individual trait card displaying trait option with description and selection state.
- **PersonaPreviewCard.tsx** - Persona preview card showing girlfriend summary and personality description.
- **ProgressStepper.tsx** - Progress stepper showing onboarding progress through numbered steps.
- **AppearanceStepPage.tsx** - Reusable appearance step page with image previews and option selection grid.
- **OnboardingSignIn.tsx** - Sign-in component displayed during onboarding flow for authentication.

##### Gallery Components (`frontend/src/components/gallery/`)

- **GalleryGrid.tsx** - Responsive image grid for the gallery page.
- **ImageViewerModal.tsx** - Full-screen image viewer modal with navigation controls.

##### Billing Components (`frontend/src/components/billing/`)

- **AddCardModal.tsx** - Stripe Elements modal for collecting payment method using SetupIntent, with dynamic title/button text based on selected plan.

##### Safety Components (`frontend/src/components/safety/`)

- **ContentPreferences.tsx** - Content preferences component for setting safety and filtering options.
- **ReportDialog.tsx** - Report dialog for flagging inappropriate content.

##### UI Components (`frontend/src/components/ui/`)

- **badge.tsx** - Badge component for labels and status indicators with variant styling.
- **button.tsx** - Button component with variants (default, destructive, outline, ghost, link) and sizes.
- **card.tsx** - Card container component with header, content, and footer sections.
- **checkbox.tsx** - Checkbox form input component.
- **dialog.tsx** - Dialog/modal overlay component.
- **dropdown-menu.tsx** - Dropdown menu component for context menus.
- **input.tsx** - Text input form component.
- **label.tsx** - Form field label component.
- **separator.tsx** - Visual divider component.
- **skeleton.tsx** - Skeleton loading placeholder component.
- **tabs.tsx** - Tabbed interface component.
- **tooltip.tsx** - Hover tooltip component.

#### Libraries (`frontend/src/lib/`)

##### API (`frontend/src/lib/api/`)

- **client.ts** - API client providing `apiGet` and `apiPost` with error handling and cookie credentials.
- **endpoints.ts** - All backend API call functions (auth, chat, girlfriends, images, billing with subscribe/cancel, memory, onboarding) with TypeScript types.
- **types.ts** - TypeScript type definitions for API request/response types including User, Girlfriend, ChatMessage, RelationshipState, BillingStatus, SetupIntentResponse, etc.
- **zod.ts** - Zod schema definitions for runtime type validation of API responses.

##### Engines (`frontend/src/lib/engines/`)

- **big_five_modulation.ts** - Frontend Big Five personality modulation engine (mirrors backend logic).
- **habits.ts** - Frontend habit analysis engine for user communication patterns.
- **initiation_engine.ts** - Frontend initiation engine for conversation initiation timing.
- **memory.ts** - Frontend memory engine utilities.
- **relationship_state.ts** - Frontend relationship state engine for level calculations and progression.
- **trait_behavior_rules.ts** - Frontend trait behavior rules defining personality-driven behaviors.
- **index.ts** - Engines module barrel export.

##### Hooks (`frontend/src/lib/hooks/`)

- **useAuth.ts** - Authentication hook providing user state, auth status, and actions (login, logout, signup).
- **useSSEChat.ts** - SSE chat hook for handling server-sent event streaming, parsing tokens and messages.

##### Store (`frontend/src/lib/store/`)

- **useAppStore.ts** - Zustand store for global state (user, girlfriend, onboarding traits/appearance/prefs/identity) with localStorage persistence.
- **useChatStore.ts** - Zustand store for chat state (messages, streaming content, streaming status) with message manipulation actions.

##### Constants (`frontend/src/lib/constants/`)

- **identity.ts** - Identity-related constants including job vibes, hobbies, origin vibes, and identity options for onboarding.

##### Onboarding (`frontend/src/lib/onboarding/`)

- **vibe.ts** - Vibe generation utilities for personality descriptions and summaries.

##### Utilities (`frontend/src/lib/`)

- **utils.ts** - General utility functions including class name merging and helper functions.

#### Routes (`frontend/src/routes/`)

- **router.tsx** - React Router configuration with all routes, route guards, nested `/app` routes, and onboarding flow including reveal-success page.
- **guards.tsx** - Route guard components (RequireAuth, RequireAgeGate, RequireGirlfriend) protecting routes with redirects.

#### Styles (`frontend/src/styles/`)

- **globals.css** - Global CSS with TailwindCSS directives, CSS custom properties for pink-themed dark mode, and base styles.

### Public Assets (`frontend/public/`)

- **assets/companion-avatar.png** - Default companion avatar placeholder image.

---

## Architecture Summary

**VirtualFR** is a full-stack AI companion application:

- **Backend**: FastAPI with in-memory sessions (Supabase optional), Stripe billing (SetupIntent + Subscriptions), SSE chat streaming, Big Five personality engine, relationship state progression, memory system, and identity canon generation.
- **Frontend**: React + TypeScript with Vite, TailwindCSS + shadcn/ui, React Router with route guards, TanStack Query for data fetching, Zustand for state management, and Stripe Elements for payment collection.
- **Flow**: Landing → Age Gate → Onboarding (Traits → Appearance → Preferences → Identity → Generating) → Girlfriend Reveal → Account Creation → Subscription Plan → Reveal Success → Chat.
