# VirtualFR Project Index

This document is the up-to-date map of the AI girlfriend monorepo in `virtualfr/`.

## 1. Project Summary

VirtualFR is an AI companion platform with:
- FastAPI backend (`backend/`) for auth, onboarding, chat streaming, relationship systems, billing, gifts, leaks, profile, and moderation.
- React + Vite frontend (`frontend/`) for onboarding, girlfriend hub, chat, gallery, billing, and settings.
- Personality and memory systems (Big Five, behavior engine, bond engine, dossier, relationship progression, trust/intimacy banked caps).
- Stripe subscription and one-time purchase flows.
- Optional Supabase persistence with in-memory fallback.

Core user journey:
1. Landing -> auth/guest session
2. Age gate
3. Onboarding (appearance, traits, preferences, identity)
4. Reveal + subscription
5. Girl hub (`/app/girl`) with chat, relationship panels, collection systems, and billing-backed actions

## 2. Monorepo Layout

- `backend/`: FastAPI application, services, schemas, migrations, tests
- `frontend/`: React application, route pages, components, client-side stores/hooks
- `docs/`: top-level architecture docs
- `README.md`: run instructions and high-level feature summary

## 3. Backend Architecture

Entry points:
- `backend/app/main.py`: mounts `/api/*`, `/v1/chat/stream`, mock OpenAI-compatible endpoints, and optional production static frontend
- `backend/app/mock_main.py`: mock model app for local inference testing

Main API route groups (`backend/app/api/routes/`):
- `auth.py`: signup/login/logout
- `me.py`: current user and age gate
- `girlfriends.py`: list/create/switch/current girlfriend
- `onboarding.py`: prompt images and onboarding completion
- `chat.py`: history, state, send, app-open flows
- `dossier.py`: dossier retrieval/bootstrap endpoints
- `progression.py`: progression and relationship progression APIs
- `relationship.py`: relationship achievement catalog and related data
- `intimacy_achievements.py`: intimacy progression achievements
- `gifts.py`: gift catalog, checkout, collection, history
- `leaks.py`: leaks collection and spin flows
- `images.py`: image request/job/gallery
- `billing.py`: plan status, checkout, card/payment methods, plan changes, webhook
- `payments.py`: additional payment routes
- `profile.py`: aggregated per-girlfriend profile stats
- `prompt.py`: prompt inspection/debug endpoints
- `memory.py`: memory summary/items/stats
- `moderation.py`: safety reporting
- `health.py`: health endpoints

Core engine areas (`backend/app/services/`):
- `behavior_engine/`: intent classification, orchestration, response contract validation/repair
- `bond_engine/`: depth/disclosure/consistency/memory orchestration
- `dossier/`: self memory + retriever + generator
- `relationship_*`: regions, milestones, descriptors, progression
- `trust_intimacy_service.py`: banked/visible trust-intimacy logic and cap release mechanics
- `persona_vector*.py`: persona vector runtime controls and storage
- `prompt_builder.py` + `prompt_context.py`: response prompt assembly
- `gifting.py` + `stripe_payments.py`: purchases and fulfillment
- `memory.py`, `habits.py`, `streaks.py`, `initiation_engine.py`: long-term behavior and messaging context

Support layers:
- `backend/app/core/`: config, CORS, auth, rate limiting, logging, Supabase client
- `backend/app/schemas/`: all API contracts
- `backend/app/utils/`: SSE helpers, identity canon, moderation, prompt identity
- `backend/migrations/`: SQL migrations including progression/bond/behavior/persona vector
- `backend/tests/`: unit and contract tests for progression, trust/intimacy, achievements, profile, billing, chat contract

## 4. Frontend Architecture

Entry points:
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`

Routing:
- `frontend/src/routes/router.tsx`
- Guards in `frontend/src/routes/guards.tsx`:
  - `RequireAuth`
  - `RequireAgeGate`
  - `RequireGirlfriend`
  - `RequireSubscription`

Primary pages:
- Onboarding: traits, appearance steps, preferences, identity, generating, reveal, subscription, reveal-success
- App: `GirlPage`, `Profile`, `Settings`, `Billing`, `PaymentOptions`, `Safety`
- Legacy route redirects for `/app/chat`, `/app/gallery`, `/app/relationship`

UI domains (`frontend/src/components/`):
- `chat/`: composer, list, bubbles, relationship panels, mystery/leaks/gift panels
- `billing/`: Stripe provider, card add flow, unified payment panel, upgrade modal
- `layout/`: app shell and nav
- `onboarding/`: step/page components
- `gallery/`: grid + viewer
- `safety/`: report UI
- `ui/`: reusable primitives

Client runtime (`frontend/src/lib/`):
- `api/`: typed endpoints and client wrappers
- `store/`: Zustand app/chat state
- `hooks/`: auth and SSE chat hooks
- `engines/`: frontend mirrors for behavior/personality logic
- `constants/` and onboarding helpers

## 5. Data and Runtime Notes

- Default local dev frontend: `http://localhost:5173`
- Default local backend: `http://localhost:8000`
- Frontend proxies `/api` to backend via Vite config.
- On Windows, if `uvicorn --reload` causes multiprocessing permission issues, run backend without `--reload`.
- In-memory state is available for local/dev and can be reset via `POST /api/dev/reset`.

## 6. Full Repository File Inventory

```text
backend\.env.example
backend\app\api\__init__.py
backend\app\api\deps.py
backend\app\api\request_context.py
backend\app\api\routes\auth.py
backend\app\api\routes\billing.py
backend\app\api\routes\chat.py
backend\app\api\routes\dossier.py
backend\app\api\routes\gifts.py
backend\app\api\routes\girlfriends.py
backend\app\api\routes\health.py
backend\app\api\routes\images.py
backend\app\api\routes\intimacy_achievements.py
backend\app\api\routes\leaks.py
backend\app\api\routes\me.py
backend\app\api\routes\memory.py
backend\app\api\routes\moderation.py
backend\app\api\routes\onboarding.py
backend\app\api\routes\payments.py
backend\app\api\routes\profile.py
backend\app\api\routes\progression.py
backend\app\api\routes\prompt.py
backend\app\api\routes\relationship.py
backend\app\api\store.py
backend\app\api\supabase_store.py
backend\app\core\__init__.py
backend\app\core\auth.py
backend\app\core\chat_logging.py
backend\app\core\config.py
backend\app\core\cors.py
backend\app\core\rate_limit.py
backend\app\core\supabase_client.py
backend\app\main.py
backend\app\mock_main.py
backend\app\routers\__init__.py
backend\app\routers\chat.py
backend\app\routers\mock_model.py
backend\app\schemas\__init__.py
backend\app\schemas\auth.py
backend\app\schemas\billing.py
backend\app\schemas\chat.py
backend\app\schemas\gift.py
backend\app\schemas\girlfriend.py
backend\app\schemas\image.py
backend\app\schemas\intimacy.py
backend\app\schemas\intimacy_achievements.py
backend\app\schemas\payment_method.py
backend\app\schemas\profile.py
backend\app\schemas\progression.py
backend\app\schemas\relationship.py
backend\app\schemas\trust_intimacy.py
backend\app\services\__init__.py
backend\app\services\achievement_engine.py
backend\app\services\behavior_engine\__init__.py
backend\app\services\behavior_engine\behavior_orchestrator.py
backend\app\services\behavior_engine\intent_classifier.py
backend\app\services\behavior_engine\repair.py
backend\app\services\behavior_engine\response_contract.py
backend\app\services\behavior_engine\validators.py
backend\app\services\big_five.py
backend\app\services\big_five_mapping.json
backend\app\services\big_five_modulation.py
backend\app\services\bond_engine\__init__.py
backend\app\services\bond_engine\bond_orchestrator.py
backend\app\services\bond_engine\consistency_guard.py
backend\app\services\bond_engine\depth_planner.py
backend\app\services\bond_engine\disclosure_planner.py
backend\app\services\bond_engine\initiation_planner.py
backend\app\services\bond_engine\memory_conflict_resolution.py
backend\app\services\bond_engine\memory_fabric.py
backend\app\services\bond_engine\memory_ingest.py
backend\app\services\bond_engine\memory_patterns.py
backend\app\services\bond_engine\memory_retrieval.py
backend\app\services\bond_engine\memory_scoring.py
backend\app\services\bond_engine\response_director.py
backend\app\services\delivery_service.py
backend\app\services\dossier\__init__.py
backend\app\services\dossier\bootstrap.py
backend\app\services\dossier\llm_generator.py
backend\app\services\dossier\retriever.py
backend\app\services\dossier\self_memory.py
backend\app\services\experiment_service.py
backend\app\services\gifting.py
backend\app\services\habits.py
backend\app\services\image_decision_engine.py
backend\app\services\initiation_engine.py
backend\app\services\intimacy_achievement_engine.py
backend\app\services\intimacy_milestones.py
backend\app\services\intimacy_service.py
backend\app\services\memory.py
backend\app\services\message_composer.py
backend\app\services\persona_vector.py
backend\app\services\persona_vector_store.py
backend\app\services\progression_service.py
backend\app\services\prompt_builder.py
backend\app\services\prompt_context.py
backend\app\services\relationship_descriptors.py
backend\app\services\relationship_milestones.py
backend\app\services\relationship_progression.py
backend\app\services\relationship_regions.py
backend\app\services\relationship_state.py
backend\app\services\streaks.py
backend\app\services\stripe_payments.py
backend\app\services\telemetry_service.py
backend\app\services\time_utils.py
backend\app\services\trait_behavior_rules.py
backend\app\services\trust_intimacy_service.py
backend\app\utils\__init__.py
backend\app\utils\identity_canon.py
backend\app\utils\moderation.py
backend\app\utils\prompt_identity.py
backend\app\utils\sse.py
backend\docs\BIG_FIVE_MIGRATION.md
backend\docs\SETUP_SUPABASE.md
backend\inference\Dockerfile
backend\inference\README.md
backend\migrations\003_progression_system.sql
backend\migrations\004_bond_engine.sql
backend\migrations\005_behavior_engine.sql
backend\migrations\006_persona_vector.sql
backend\requirements.txt
backend\scripts\bootstrap_existing_girls.py
backend\scripts\check_api_key.py
backend\scripts\check_config.py
backend\supabase_full_architecture.sql
backend\supabase_schema.sql
backend\tests\test_achievements.py
backend\tests\test_billing_proration_contract.py
backend\tests\test_chat_canon_injection.py
backend\tests\test_identity_canon.py
backend\tests\test_intimacy.py
backend\tests\test_intimacy_achievements.py
backend\tests\test_openai_contract.py
backend\tests\test_profile_stats.py
backend\tests\test_relationship_progression.py
backend\tests\test_relationship_regions.py
backend\tests\test_trust_intimacy.py
docs\GIRLFRIEND_CONVERSATION_ARCHITECTURE.md
frontend\index.html
frontend\package.json
frontend\package-lock.json
frontend\postcss.config.js
frontend\public\assets\companion-avatar.png
frontend\src\App.tsx
frontend\src\components\billing\AddCardModal.tsx
frontend\src\components\billing\StripeProvider.tsx
frontend\src\components\billing\UnifiedPaymentPanel.tsx
frontend\src\components\billing\UpgradeModal.tsx
frontend\src\components\chat\AchievementUnlockedCard.tsx
frontend\src\components\chat\BlurredImageCard.tsx
frontend\src\components\chat\ChatHeader.tsx
frontend\src\components\chat\Composer.tsx
frontend\src\components\chat\GiftCollectionPanel.tsx
frontend\src\components\chat\GiftModal.tsx
frontend\src\components\chat\ImageMessage.tsx
frontend\src\components\chat\ImageTeaseCard.tsx
frontend\src\components\chat\IntimateProgressionPanel.tsx
frontend\src\components\chat\LeaksPanel.tsx
frontend\src\components\chat\MessageBubble.tsx
frontend\src\components\chat\MessageList.tsx
frontend\src\components\chat\MilestoneCard.tsx
frontend\src\components\chat\MilestoneInbox.tsx
frontend\src\components\chat\MysteryBoxPanel.tsx
frontend\src\components\chat\PaywallInlineCard.tsx
frontend\src\components\chat\RelationshipGainCard.tsx
frontend\src\components\chat\RelationshipMeter.tsx
frontend\src\components\chat\TypingIndicator.tsx
frontend\src\components\gallery\GalleryGrid.tsx
frontend\src\components\gallery\ImageViewerModal.tsx
frontend\src\components\layout\AppShell.tsx
frontend\src\components\layout\Footer.tsx
frontend\src\components\layout\MobileNav.tsx
frontend\src\components\layout\SideNav.tsx
frontend\src\components\layout\TopNav.tsx
frontend\src\components\onboarding\AppearanceStepPage.tsx
frontend\src\components\onboarding\OnboardingSignIn.tsx
frontend\src\components\onboarding\PersonaPreviewCard.tsx
frontend\src\components\onboarding\ProgressStepper.tsx
frontend\src\components\onboarding\TraitCard.tsx
frontend\src\components\onboarding\TraitSelector.tsx
frontend\src\components\safety\ContentPreferences.tsx
frontend\src\components\safety\ReportDialog.tsx
frontend\src\components\ui\AvatarCircle.tsx
frontend\src\components\ui\badge.tsx
frontend\src\components\ui\button.tsx
frontend\src\components\ui\card.tsx
frontend\src\components\ui\checkbox.tsx
frontend\src\components\ui\dialog.tsx
frontend\src\components\ui\dropdown-menu.tsx
frontend\src\components\ui\input.tsx
frontend\src\components\ui\label.tsx
frontend\src\components\ui\separator.tsx
frontend\src\components\ui\skeleton.tsx
frontend\src\components\ui\tabs.tsx
frontend\src\components\ui\tooltip.tsx
frontend\src\lib\api\client.ts
frontend\src\lib\api\endpoints.ts
frontend\src\lib\api\types.ts
frontend\src\lib\api\zod.ts
frontend\src\lib\constants\identity.ts
frontend\src\lib\engines\big_five_modulation.ts
frontend\src\lib\engines\habits.ts
frontend\src\lib\engines\index.ts
frontend\src\lib\engines\initiation_engine.ts
frontend\src\lib\engines\memory.ts
frontend\src\lib\engines\prompt_builder.ts
frontend\src\lib\engines\relationship_state.ts
frontend\src\lib\engines\trait_behavior_rules.ts
frontend\src\lib\hooks\useAuth.ts
frontend\src\lib\hooks\useSSEChat.ts
frontend\src\lib\onboarding\vibe.ts
frontend\src\lib\store\useAppStore.ts
frontend\src\lib\store\useChatStore.ts
frontend\src\lib\utils.ts
frontend\src\main.tsx
frontend\src\pages\AgeGate.tsx
frontend\src\pages\appearance\AppearanceAge.tsx
frontend\src\pages\appearance\AppearanceBody.tsx
frontend\src\pages\appearance\AppearanceBodyDetails.tsx
frontend\src\pages\appearance\AppearanceBreast.tsx
frontend\src\pages\appearance\AppearanceButt.tsx
frontend\src\pages\appearance\AppearanceEthnicity.tsx
frontend\src\pages\appearance\AppearanceEyes.tsx
frontend\src\pages\appearance\AppearanceHairColor.tsx
frontend\src\pages\appearance\AppearanceHairEyes.tsx
frontend\src\pages\appearance\AppearanceHairStyle.tsx
frontend\src\pages\Billing.tsx
frontend\src\pages\Chat.tsx
frontend\src\pages\Gallery.tsx
frontend\src\pages\GirlfriendReveal.tsx
frontend\src\pages\GirlPage.tsx
frontend\src\pages\Landing.tsx
frontend\src\pages\Login.tsx
frontend\src\pages\OnboardingAppearance.tsx
frontend\src\pages\OnboardingGenerating.tsx
frontend\src\pages\OnboardingIdentity.tsx
frontend\src\pages\OnboardingPreferences.tsx
frontend\src\pages\OnboardingTraits.tsx
frontend\src\pages\PaymentOptions.tsx
frontend\src\pages\PersonaPreview.tsx
frontend\src\pages\Profile.tsx
frontend\src\pages\Relationship.tsx
frontend\src\pages\RevealSuccess.tsx
frontend\src\pages\Safety.tsx
frontend\src\pages\Settings.tsx
frontend\src\pages\Signup.tsx
frontend\src\pages\SubscriptionPlan.tsx
frontend\src\routes\guards.tsx
frontend\src\routes\router.tsx
frontend\src\styles\globals.css
frontend\tailwind.config.ts
frontend\tsconfig.json
frontend\tsconfig.node.json
frontend\vite.config.ts
GEMINI_INDEX.md
onboarding_questions.md.txt
PROJECT_INDEX.md
README.md
```

## 7. Quick Start

Backend:
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

## 8. Key References

- `README.md`
- `docs/GIRLFRIEND_CONVERSATION_ARCHITECTURE.md`
- `backend/docs/SETUP_SUPABASE.md`
- `backend/docs/BIG_FIVE_MIGRATION.md`

