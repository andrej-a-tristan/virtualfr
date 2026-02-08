-- Idempotent Supabase schema for companion app.
-- Run in Supabase SQL editor. RLS: user owns rows.

-- Sessions (so login survives backend restart; service-role only, no RLS)
CREATE TABLE IF NOT EXISTS public.sessions (
  id text PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  email text,
  display_name text,
  current_girlfriend_id text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON public.sessions(user_id);

-- Users profile (extends auth.users)
CREATE TABLE IF NOT EXISTS public.users_profile (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  language_pref text NOT NULL DEFAULT 'en' CHECK (language_pref IN ('en', 'sk')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_profile_language ON public.users_profile(language_pref);

-- Girlfriends (per user)
CREATE TABLE IF NOT EXISTS public.girlfriends (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name text NOT NULL,
  traits jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_girlfriends_user ON public.girlfriends(user_id);

-- Messages (per user + girlfriend)
CREATE TABLE IF NOT EXISTS public.messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content text,
  image_url text,
  event_type text,
  event_key text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_user_gf ON public.messages(user_id, girlfriend_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON public.messages(created_at);

-- Relationship state (per user + girlfriend)
CREATE TABLE IF NOT EXISTS public.relationship_state (
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  trust int NOT NULL DEFAULT 10 CHECK (trust >= 0 AND trust <= 100),
  intimacy int NOT NULL DEFAULT 10 CHECK (intimacy >= 0 AND intimacy <= 100),
  level text NOT NULL DEFAULT 'STRANGER' CHECK (level IN ('STRANGER', 'FAMILIAR', 'CLOSE', 'INTIMATE', 'EXCLUSIVE')),
  last_interaction_at timestamptz,
  milestones_reached text[] NOT NULL DEFAULT '{}',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, girlfriend_id)
);

-- Habit profile (per user + girlfriend)
CREATE TABLE IF NOT EXISTS public.habit_profile (
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  preferred_hours int[],
  typical_gap_hours int,
  big_five_openness numeric(3,2) CHECK (big_five_openness >= 0.0 AND big_five_openness <= 1.0),
  big_five_conscientiousness numeric(3,2) CHECK (big_five_conscientiousness >= 0.0 AND big_five_conscientiousness <= 1.0),
  big_five_extraversion numeric(3,2) CHECK (big_five_extraversion >= 0.0 AND big_five_extraversion <= 1.0),
  big_five_agreeableness numeric(3,2) CHECK (big_five_agreeableness >= 0.0 AND big_five_agreeableness <= 1.0),
  big_five_neuroticism numeric(3,2) CHECK (big_five_neuroticism >= 0.0 AND big_five_neuroticism <= 1.0),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, girlfriend_id)
);

-- RLS: enable and policies (user owns rows)
ALTER TABLE public.users_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.girlfriends ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.relationship_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.habit_profile ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS users_profile_select ON public.users_profile;
CREATE POLICY users_profile_select ON public.users_profile FOR SELECT USING (auth.uid() = user_id);
DROP POLICY IF EXISTS users_profile_insert ON public.users_profile;
CREATE POLICY users_profile_insert ON public.users_profile FOR INSERT WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS users_profile_update ON public.users_profile;
CREATE POLICY users_profile_update ON public.users_profile FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS girlfriends_all ON public.girlfriends;
CREATE POLICY girlfriends_all ON public.girlfriends FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS messages_all ON public.messages;
CREATE POLICY messages_all ON public.messages FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS relationship_state_all ON public.relationship_state;
CREATE POLICY relationship_state_all ON public.relationship_state FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS habit_profile_all ON public.habit_profile;
CREATE POLICY habit_profile_all ON public.habit_profile FOR ALL USING (auth.uid() = user_id);

-- ============================================================================
-- MEMORY SYSTEM TABLES (Task 1.2)
-- ============================================================================

-- Factual memory: stable facts about the user (name, city, preferences, etc.)
CREATE TABLE IF NOT EXISTS public.factual_memory (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  key text NOT NULL,                          -- e.g. "user.name", "user.city", "pref.music"
  value text NOT NULL,
  confidence int NOT NULL DEFAULT 70 CHECK (confidence >= 0 AND confidence <= 100),
  source_message_id uuid REFERENCES public.messages(id) ON DELETE SET NULL,
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, girlfriend_id, key)
);

CREATE INDEX IF NOT EXISTS idx_factual_memory_user_gf ON public.factual_memory(user_id, girlfriend_id);
CREATE INDEX IF NOT EXISTS idx_factual_memory_key ON public.factual_memory(key);
CREATE INDEX IF NOT EXISTS idx_factual_memory_last_seen ON public.factual_memory(last_seen_at DESC);

-- Emotional memory: events + feelings (stress, affection, sadness, etc.)
CREATE TABLE IF NOT EXISTS public.emotional_memory (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  event text NOT NULL,                        -- short "what happened" summary
  emotion_tags text[] NOT NULL DEFAULT '{}',  -- e.g. ['stress','anxiety'] or ['affection']
  valence int NOT NULL DEFAULT 0 CHECK (valence >= -5 AND valence <= 5),  -- negative to positive
  intensity int NOT NULL DEFAULT 3 CHECK (intensity >= 1 AND intensity <= 5),
  occurred_at timestamptz NOT NULL DEFAULT now(),
  source_message_id uuid REFERENCES public.messages(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_emotional_memory_user_gf ON public.emotional_memory(user_id, girlfriend_id);
CREATE INDEX IF NOT EXISTS idx_emotional_memory_occurred ON public.emotional_memory(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_emotional_memory_tags ON public.emotional_memory USING GIN (emotion_tags);

-- Memory notes (optional, for future manual notes / summaries)
CREATE TABLE IF NOT EXISTS public.memory_notes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  note text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memory_notes_user_gf ON public.memory_notes(user_id, girlfriend_id);

-- RLS for memory tables
ALTER TABLE public.factual_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.emotional_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_notes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS factual_memory_all ON public.factual_memory;
CREATE POLICY factual_memory_all ON public.factual_memory FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS emotional_memory_all ON public.emotional_memory;
CREATE POLICY emotional_memory_all ON public.emotional_memory FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS memory_notes_all ON public.memory_notes;
CREATE POLICY memory_notes_all ON public.memory_notes FOR ALL USING (auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- Gift Purchases
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.gift_purchases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.users(id),
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id),
  gift_id text NOT NULL,
  gift_name text NOT NULL,
  amount_eur numeric(10,2) NOT NULL,
  currency text NOT NULL DEFAULT 'eur',
  stripe_session_id text UNIQUE,
  stripe_payment_intent text,
  status text NOT NULL DEFAULT 'pending',  -- pending | paid | failed
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_gift_purchases_user ON public.gift_purchases(user_id, girlfriend_id);
CREATE INDEX IF NOT EXISTS idx_gift_purchases_stripe ON public.gift_purchases(stripe_session_id);

-- Moment cards (optional keepsake from gift)
CREATE TABLE IF NOT EXISTS public.moment_cards (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.users(id),
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id),
  gift_purchase_id uuid REFERENCES public.gift_purchases(id),
  title text NOT NULL,
  description text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_moment_cards_user ON public.moment_cards(user_id, girlfriend_id);

-- RLS
ALTER TABLE public.gift_purchases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.moment_cards ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS gift_purchases_all ON public.gift_purchases;
CREATE POLICY gift_purchases_all ON public.gift_purchases FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS moment_cards_all ON public.moment_cards;
CREATE POLICY moment_cards_all ON public.moment_cards FOR ALL USING (auth.uid() = user_id);
