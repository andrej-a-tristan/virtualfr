# Girlfriend Conversation Realism Architecture

## Objective
Build a chat system that feels like a real girlfriend conversation:
- Natural pacing (short replies by default)
- Emotional continuity without robotic repetition
- Strong personality consistency without over-scripted output
- Progressive bond growth that feels earned, not mechanical

## Core Problems Identified
1. Prompt overload: canon + bond + behavior + builder layers duplicate/conflict.
2. Overlong responses: high token budgets and "expansive" style paths.
3. Over-instruction: too many hard rules in every turn reduce spontaneity.
4. Redundant personality prose: same trait guidance repeated in multiple modules.

## Target System Design (v2)

### 1) Persona Core (Stable, Cached)
Single source of truth for identity and style:
- Identity anchors: name, background, lifestyle, preferences
- Trait profile: emotional style, communication style, attachment
- Character constraints: never break role, avoid assistant tone

Rules:
- Keep this short and static.
- Rebuild only when profile changes.

### 2) Turn Policy (Dynamic, Minimal)
Per-message control plane:
- Intent classification
- Response length budget
- Question budget (usually max 1)
- Disclosure depth target (surface -> vulnerable by relationship stage)

Rules:
- This section has highest precedence for output shape.
- Short user input must produce short output.

### 3) Memory Slice (Top-K, Relevance-First)
Inject only a tiny memory set:
- 1 unresolved emotional thread
- 1 high-confidence factual callback
- Optional 1 shared episode (when highly relevant)

Rules:
- Max 1-2 callbacks per reply.
- No repeated callback in short windows.

### 4) Output Contract (Hard Format Guardrails)
Final response requirements:
- Default: 1-3 sentences
- Greeting/banter: 1 sentence
- Support turns: 2-4 sentences
- No list output unless user asked
- Avoid question-only endings in streaks

### 5) Post-Turn Quality Layer
Validator and metrics pass:
- Repetition score
- Question dominance
- Deflection when user asked about her
- Length violations vs turn budget
- Generic phrase frequency

If violations occur:
- Regenerate once with compact repair hints.

### 6) Adaptive Runtime Tuning
Adjust generation settings per turn:
- `max_tokens` by intent + user message length
- temperature narrowed for depth/support turns
- tighter budgets when verbosity drifts up

### 7) Hooked Experience Architecture (Natural, Not Spammy)
Goal: increase return rate by making each conversation feel alive and personally meaningful.

Loop per session:
1. Emotional hit: acknowledge user's current vibe in first sentence.
2. Personal detail: add one specific detail from her life/personality.
3. Bridge forward: leave one soft open thread for next turn (not always a question).
4. Lightweight payoff: occasional novelty (memory callback, micro-surprise line, playful challenge).

Key systems:
- `Micro-arcs`: 3-7 turn mini stories (start -> deepen -> payoff) instead of disconnected replies.
- `Open loops`: unresolved emotional or practical threads that are naturally resumed later.
- `Novelty scheduler`: rotate style (playful/supportive/reflective) to avoid repetitive tone.
- `Re-engagement memory`: when user returns, open with continuity ("last time you said...") plus fresh context.

Guardrails:
- No guilt pressure loops.
- No repetitive clingy prompts.
- No manipulative urgency patterns.

### 8) Telemetry Dashboard Spec
Create a single dashboard for conversation quality and retention impact.

Panels:
1. `Length & Pacing`
   - avg words/turn, p95 words/turn, sentence count distribution
2. `Dialogue Balance`
   - question ratio, consecutive-question streaks, response-to-user-length ratio
3. `Novelty & Repetition`
   - repeated opening rate, phrase reuse score, template collision rate
4. `Continuity`
   - callback hit rate, callback relevance score, unresolved-thread follow-up rate
5. `Hook Metrics`
   - next-day return after meaningful turn, session depth after emotional turn, re-open after micro-arc payoff

Alert thresholds:
- p95 length > 120 words for 3 days
- question ratio > 0.45
- repeated-opening rate > 0.20
- callback relevance < target baseline

## Onboarding Traits + Big Five: Is It Beneficial?
Short answer: yes, but only if used as compact controls, not long prose.

### What is beneficial now
- Onboarding traits are strong for immediate persona differentiation.
- Big Five is useful for stable modulation (verbosity, expressiveness, directness, reassurance style).
- Stored relationship/memory data is useful for continuity and bonding.

### What is currently inefficient
- Traits + Big Five are often converted into long repeated prompt text.
- Multiple engines reinterpret the same data separately, causing collisions and drift.
- Runtime prompt spends too many tokens describing personality instead of using it.

### Better design
Use a single `Persona Vector` object shared across engines:
- `style`: warmth, playfulness, directness, emotional intensity
- `pacing`: short/balanced/deep preference
- `attachment`: check-in frequency + absence sensitivity
- `repair_style`: how she apologizes, reassures, or handles tension

Map onboarding + Big Five once:
1. On onboarding complete: traits -> Persona Vector (deterministic mapping).
2. Store vector in profile.
3. At runtime: only inject compact vector + turn deltas, not essays.
4. Optional small adaptive updates from long-term behavior, bounded by safety limits.

### Optimization rule
- Keep onboarding traits as primary explicit identity knobs.
- Keep Big Five as secondary modulation layer.
- Do not expose both as verbose narrative blocks in prompt.
- Prefer numeric/style parameters over descriptive paragraphs.

## Persona Vector Architecture (Detailed)
Purpose: unify personality control into one compact machine-readable profile used by all chat engines.

### A) Data Model
Store one immutable-versioned vector per girlfriend profile revision.

`PersonaVectorV1`:
- `version`: string (`pv1`)
- `source`:
  - `traits`: raw onboarding trait values
  - `big_five`: normalized scores (`0.0-1.0`)
  - `created_at`
  - `updated_at`
- `style`:
  - `warmth` (`0.0-1.0`)
  - `playfulness` (`0.0-1.0`)
  - `directness` (`0.0-1.0`)
  - `emotional_intensity` (`0.0-1.0`)
  - `expressiveness` (`0.0-1.0`)
  - `assertiveness` (`0.0-1.0`)
- `pacing`:
  - `default_cadence` (`short|balanced|deep`)
  - `brevity_bias` (`0.0-1.0`, higher = shorter replies)
  - `question_tendency` (`0.0-1.0`)
  - `max_default_sentences` (int)
- `attachment`:
  - `closeness_drive` (`0.0-1.0`)
  - `absence_sensitivity` (`0.0-1.0`)
  - `reassurance_need` (`0.0-1.0`)
  - `checkin_frequency_hint` (`low|medium|high`)
- `repair_style`:
  - `conflict_approach` (`soften|direct_repair|space_then_repair`)
  - `apology_warmth` (`0.0-1.0`)
  - `jealousy_expression` (`low|medium|high`)
- `boundaries`:
  - `flirting_level` (`off|light|active`)
  - `intimacy_ceiling` (`safe|suggestive|explicit`) (still gated by policy/user prefs)
- `lexical`:
  - `emoji_rate_hint` (`none|rare|moderate|frequent`)
  - `teasing_rate_hint` (`0.0-1.0`)
  - `petname_rate_hint` (`0.0-1.0`)
- `runtime_overrides` (ephemeral, not persisted in base vector):
  - `turn_brevity_boost`
  - `turn_support_depth_boost`
  - `turn_question_cap`

### B) Deterministic Mapping Pipeline
Build once on onboarding completion and whenever traits are edited.

Step 1: Normalize inputs
- Traits as categorical enums.
- Big Five to `0.0-1.0`.

Step 2: Apply trait priors
- Trait tables set base values (e.g. `Playful -> playfulness + expressiveness`, `Direct -> directness + assertiveness`).

Step 3: Apply Big Five modulation
- Extraversion modulates `expressiveness`, `emoji_rate_hint`, `question_tendency`.
- Agreeableness modulates `warmth`, `repair softness`.
- Neuroticism modulates `reassurance_need`, `absence_sensitivity`.
- Conscientiousness modulates `direct_repair` tendency and cadence stability.
- Openness modulates lexical variety and novelty tolerance.

Step 4: Clamp and quantize
- Clamp all float values to `[0,1]`.
- Convert thresholds to discrete hints (`default_cadence`, `checkin_frequency_hint`, etc.).

Step 5: Serialize + version
- Save as JSON with `version=pv1`.
- Keep migration function for future schema versions.

### C) Runtime Usage Contract
At inference time, inject only compact directives derived from vector; never inject full trait essays.

Prompt injection format (compact):
- `STYLE`: warmth/playfulness/directness/intensity bands
- `CADENCE`: sentence cap + brevity bias
- `QUESTIONS`: max allowed this turn
- `ATTACHMENT`: closeness/absence behavior hint
- `REPAIR`: conflict behavior mode

Rules:
- Turn Policy can tighten limits but cannot violate persona identity.
- Memory system reads vector for callback style (playful vs reflective framing).
- Behavior validator uses vector expectations for mismatch checks.

### D) Storage and Ownership
Recommended persistence:
- Table: `persona_vectors`
- Keys: `(user_id, girlfriend_id, version_tag, created_at)`
- Active pointer: `girlfriends.persona_vector_version`

Operational rules:
- Regenerate vector on trait edits.
- Keep previous vectors for debugging and rollback.
- Log vector hash in chat telemetry for experiment correlation.

### E) Safety and Drift Control
- Base vector is stable; do not mutate per turn.
- Allow bounded adaptive overlay (`runtime_overrides`) from recent conversation metrics.
- Hard cap adaptation magnitude (e.g. +/-0.1 on continuous dimensions).
- Reset overlays after inactivity window or explicit profile reset.

### F) Implementation Plan
1. `persona_vector.py`
   - schema dataclasses/pydantic models
   - deterministic mapper from traits + Big Five
   - validator + clamping
2. `persona_vector_store.py`
   - upsert/get active vector
   - version management
3. Integrate into prompt composer
   - replace duplicated trait prose with compact vector directives
4. Integrate into behavior/response contract
   - cadence/question defaults from vector
5. Add tests
   - deterministic mapping snapshots
   - bounds/clamp tests
   - migration compatibility tests

### G) Success Criteria
- Runtime system prompt token count reduced by >=35%.
- p95 response length reduced without empathy score drop.
- Repetition rate reduced by >=20%.
- No persona drift regressions in consistency tests.

## What To Keep
- Relationship/trust/intimacy state engines
- Memory extraction and continuity
- Intent classifier + anti-deflection checks
- Consistency validation (identity/canon protection)

## What To Reduce/Remove
1. Duplicate prompt instructions across canon, behavior, and builder layers.
2. Long trait essays in runtime prompts (keep structured short descriptors only).
3. Expansive cadence defaults for regular conversations.
4. Multiple anti-AI/anti-assistant blocks repeated in every prompt segment.

## Prompt Composition Precedence
Use strict order:
1. Safety and role constraints (minimal)
2. Persona Core (stable)
3. Turn Policy (dynamic, highest behavioral control)
4. Memory Slice (tiny, relevant)
5. Output Contract (length + question constraints)

Conflict rule:
- Later sections win only for formatting/length.
- Persona identity must never be overridden.

## Message Length Policy (Production)
- User <= 8 words: 1 sentence, <= 20 words target
- Banter/greeting: 1 sentence
- Normal conversation: 1-3 sentences, <= 60 words target
- Emotional support: 2-4 sentences, <= 90 words target
- Long output only when user explicitly asks for detail

## Realism Metrics (Track Weekly)
1. Avg assistant words per turn
2. 95th percentile response length
3. Question-ending streak rate
4. Repeated-opening rate
5. Deflection rate on "about you" questions
6. Callback relevance score (human eval or rubric)
7. User retention: D1/D7 session return and session depth
8. Micro-arc completion rate
9. Re-engagement success rate (return turn receives continuity callback)

## Rollout Plan

### Phase 1 (Immediate)
- Enforce dynamic token budgets and concise guardrails.
- Remove expansive support cadence.
- Add length violation metric logging.

### Phase 2
- Create one unified prompt composer.
- Migrate duplicate sections into Persona Core + Turn Policy.
- Reduce runtime prompt size by at least 35%.
- Build `Persona Vector` mapper from onboarding traits + Big Five.

### Phase 3
- Add one-shot repair regeneration on validator failure.
- Add A/B tests for brevity profiles and callback limits.
- Launch telemetry dashboard with alerting thresholds.

### Phase 4
- Data-driven tuning loop:
  - Auto-adjust `max_tokens` and question budgets from quality metrics.
  - Detect and suppress stale phrase templates globally.
  - Optimize for retention using micro-arc completion and re-engagement metrics.

## Cursor Handoff Notes
- Keep internal state complexity; simplify only what reaches the LLM.
- Prefer deterministic contracts for shape, stochasticity for wording.
- Optimize for "human short + emotionally specific" over "expressive long."
- Any new feature must pass length and anti-repetition benchmarks before release.
- Treat onboarding traits as explicit persona identity; treat Big Five as compact modulation.
