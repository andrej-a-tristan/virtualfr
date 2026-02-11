-- Full architecture migration for VirtualFR companion app.
-- Safe to run multiple times (idempotent) on Supabase/Postgres.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- Helpers
-- ============================================================================

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- ============================================================================
-- Core user/session/profile fixes
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.users_profile (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name text,
  language_pref text NOT NULL DEFAULT 'en' CHECK (language_pref IN ('en', 'sk')),
  age_gate_passed boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.users_profile
  ADD COLUMN IF NOT EXISTS display_name text,
  ADD COLUMN IF NOT EXISTS age_gate_passed boolean NOT NULL DEFAULT false;

DO $$
BEGIN
  IF to_regclass('public.sessions') IS NULL THEN
    CREATE TABLE public.sessions (
      id text PRIMARY KEY,
      user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
      email text,
      display_name text,
      current_girlfriend_id uuid,
      created_at timestamptz NOT NULL DEFAULT now(),
      expires_at timestamptz
    );
  ELSE
    ALTER TABLE public.sessions
      ADD COLUMN IF NOT EXISTS expires_at timestamptz;

    -- Convert legacy text current_girlfriend_id -> uuid where needed.
    IF EXISTS (
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = 'public'
        AND table_name = 'sessions'
        AND column_name = 'current_girlfriend_id'
        AND udt_name <> 'uuid'
    ) THEN
      ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS current_girlfriend_id_v2 uuid;
      UPDATE public.sessions
      SET current_girlfriend_id_v2 =
        CASE
          WHEN current_girlfriend_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
          THEN current_girlfriend_id::uuid
          ELSE NULL
        END
      WHERE current_girlfriend_id_v2 IS NULL;
      ALTER TABLE public.sessions DROP COLUMN current_girlfriend_id;
      ALTER TABLE public.sessions RENAME COLUMN current_girlfriend_id_v2 TO current_girlfriend_id;
    END IF;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_sessions_user ON public.sessions(user_id);

-- ============================================================================
-- Girlfriends + subscription/billing
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.girlfriends (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name text NOT NULL,
  avatar_url text,
  traits jsonb NOT NULL DEFAULT '{}'::jsonb,
  appearance_prefs jsonb NOT NULL DEFAULT '{}'::jsonb,
  content_prefs jsonb NOT NULL DEFAULT '{}'::jsonb,
  identity jsonb NOT NULL DEFAULT '{}'::jsonb,
  identity_canon jsonb NOT NULL DEFAULT '{}'::jsonb,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.girlfriends
  ADD COLUMN IF NOT EXISTS avatar_url text,
  ADD COLUMN IF NOT EXISTS appearance_prefs jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS content_prefs jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS identity jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS identity_canon jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_girlfriends_user ON public.girlfriends(user_id);

CREATE TABLE IF NOT EXISTS public.billing_customers (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  stripe_customer_id text UNIQUE,
  default_payment_method_id text,
  has_card_on_file boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  plan text NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'plus', 'premium')),
  stripe_subscription_id text UNIQUE,
  status text,
  current_period_end timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON public.subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_plan ON public.subscriptions(plan);

CREATE TABLE IF NOT EXISTS public.payment_methods_snapshot (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  stripe_pm_id text UNIQUE NOT NULL,
  brand text,
  last4 text,
  exp_month int,
  exp_year int,
  is_default boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_payment_methods_user ON public.payment_methods_snapshot(user_id);

-- ============================================================================
-- Conversations + messages
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_conversations_active_unique
  ON public.conversations(user_id, girlfriend_id, status)
  WHERE status = 'active';

DO $$
BEGIN
  IF to_regclass('public.messages') IS NULL THEN
    CREATE TABLE public.messages (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
      girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
      conversation_id uuid REFERENCES public.conversations(id) ON DELETE SET NULL,
      role text NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
      content text,
      image_url text,
      event_type text,
      event_key text,
      metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      created_at timestamptz NOT NULL DEFAULT now()
    );
  ELSE
    ALTER TABLE public.messages
      ADD COLUMN IF NOT EXISTS conversation_id uuid REFERENCES public.conversations(id) ON DELETE SET NULL,
      ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_messages_user_gf_created ON public.messages(user_id, girlfriend_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_event ON public.messages(event_type, event_key);

-- ============================================================================
-- Relationship state fixes + progression/trust/intimacy persistence
-- ============================================================================

DO $$
DECLARE
  rec record;
BEGIN
  IF to_regclass('public.relationship_state') IS NULL THEN
    CREATE TABLE public.relationship_state (
      user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
      girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
      trust int NOT NULL DEFAULT 10 CHECK (trust >= 0 AND trust <= 100),
      intimacy int NOT NULL DEFAULT 10 CHECK (intimacy >= 0 AND intimacy <= 100),
      level int NOT NULL DEFAULT 0 CHECK (level >= 0 AND level <= 200),
      region_key text NOT NULL DEFAULT 'EARLY_CONNECTION',
      last_interaction_at timestamptz,
      milestones_reached text[] NOT NULL DEFAULT '{}',
      updated_at timestamptz NOT NULL DEFAULT now(),
      PRIMARY KEY (user_id, girlfriend_id)
    );
  ELSE
    ALTER TABLE public.relationship_state
      ADD COLUMN IF NOT EXISTS region_key text NOT NULL DEFAULT 'EARLY_CONNECTION',
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

    -- Drop existing check constraints on level to allow type conversion.
    FOR rec IN
      SELECT c.conname
      FROM pg_constraint c
      JOIN pg_class t ON t.oid = c.conrelid
      JOIN pg_namespace n ON n.oid = t.relnamespace
      JOIN pg_attribute a ON a.attrelid = t.oid
      WHERE n.nspname = 'public'
        AND t.relname = 'relationship_state'
        AND c.contype = 'c'
        AND a.attname = 'level'
        AND a.attnum = ANY (c.conkey)
    LOOP
      EXECUTE format('ALTER TABLE public.relationship_state DROP CONSTRAINT IF EXISTS %I', rec.conname);
    END LOOP;

    IF EXISTS (
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema='public' AND table_name='relationship_state' AND column_name='level' AND udt_name <> 'int4'
    ) THEN
      ALTER TABLE public.relationship_state
        ALTER COLUMN level DROP DEFAULT;
      ALTER TABLE public.relationship_state
        ALTER COLUMN level TYPE int USING (
          CASE
            WHEN level IN ('STRANGER') THEN 0
            WHEN level IN ('FAMILIAR') THEN 20
            WHEN level IN ('CLOSE') THEN 50
            WHEN level IN ('INTIMATE') THEN 120
            WHEN level IN ('EXCLUSIVE') THEN 180
            WHEN level ~ '^[0-9]+$' THEN level::int
            ELSE 0
          END
        );
    END IF;

    ALTER TABLE public.relationship_state
      ALTER COLUMN level SET DEFAULT 0;
  END IF;
END $$;

ALTER TABLE public.relationship_state
  DROP CONSTRAINT IF EXISTS relationship_state_level_check;
ALTER TABLE public.relationship_state
  ADD CONSTRAINT relationship_state_level_check CHECK (level >= 0 AND level <= 200);

CREATE TABLE IF NOT EXISTS public.relationship_progress (
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  level int NOT NULL DEFAULT 0 CHECK (level >= 0 AND level <= 200),
  banked_points int NOT NULL DEFAULT 0 CHECK (banked_points >= 0),
  streak_days int NOT NULL DEFAULT 0 CHECK (streak_days >= 0),
  last_interaction_at timestamptz,
  last_award_at timestamptz,
  recent_message_timestamps jsonb NOT NULL DEFAULT '[]'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, girlfriend_id)
);

CREATE TABLE IF NOT EXISTS public.trust_intimacy_state (
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  trust_visible int NOT NULL DEFAULT 20 CHECK (trust_visible BETWEEN 1 AND 100),
  trust_bank int NOT NULL DEFAULT 0 CHECK (trust_bank >= 0),
  intimacy_visible int NOT NULL DEFAULT 1 CHECK (intimacy_visible BETWEEN 1 AND 100),
  intimacy_bank int NOT NULL DEFAULT 0 CHECK (intimacy_bank >= 0),
  trust_last_gain_at timestamptz,
  intimacy_last_gain_at timestamptz,
  trust_gained_today int NOT NULL DEFAULT 0 CHECK (trust_gained_today >= 0),
  intimacy_gained_today int NOT NULL DEFAULT 0 CHECK (intimacy_gained_today >= 0),
  trust_gained_today_gifts int NOT NULL DEFAULT 0 CHECK (trust_gained_today_gifts >= 0),
  intimacy_gained_today_gifts int NOT NULL DEFAULT 0 CHECK (intimacy_gained_today_gifts >= 0),
  cap_date date,
  used_region_ids text[] NOT NULL DEFAULT '{}',
  used_gift_ids_trust text[] NOT NULL DEFAULT '{}',
  used_gift_ids_intimacy text[] NOT NULL DEFAULT '{}',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, girlfriend_id)
);

CREATE TABLE IF NOT EXISTS public.relationship_milestones (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  region_key text NOT NULL,
  unlocked_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, girlfriend_id, region_key)
);

CREATE TABLE IF NOT EXISTS public.achievement_progress (
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  region_index int NOT NULL DEFAULT 0,
  first_time_flags jsonb NOT NULL DEFAULT '{}'::jsonb,
  event_history jsonb NOT NULL DEFAULT '[]'::jsonb,
  last_signal_timestamps jsonb NOT NULL DEFAULT '{}'::jsonb,
  conflict_tension_at timestamptz,
  conflict_apology_at timestamptz,
  conflict_last_repair_at timestamptz,
  message_counter int NOT NULL DEFAULT 0,
  last_interaction_date text,
  streak_days_in_region int NOT NULL DEFAULT 0,
  days_since_last_interaction numeric(10,2) NOT NULL DEFAULT 0,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, girlfriend_id)
);

CREATE TABLE IF NOT EXISTS public.achievement_unlocks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  achievement_id text NOT NULL,
  region_index int NOT NULL,
  rarity text NOT NULL,
  unlocked_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, girlfriend_id, achievement_id)
);

CREATE INDEX IF NOT EXISTS idx_achievement_unlocks_user_gf ON public.achievement_unlocks(user_id, girlfriend_id, unlocked_at DESC);

-- ============================================================================
-- Habits + memory
-- ============================================================================

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

CREATE TABLE IF NOT EXISTS public.factual_memory (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  key text NOT NULL,
  value text NOT NULL,
  confidence int NOT NULL DEFAULT 70 CHECK (confidence BETWEEN 0 AND 100),
  source_message_id uuid REFERENCES public.messages(id) ON DELETE SET NULL,
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, girlfriend_id, key)
);

CREATE INDEX IF NOT EXISTS idx_factual_memory_user_gf_last_seen ON public.factual_memory(user_id, girlfriend_id, last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_factual_memory_key ON public.factual_memory(key);

CREATE TABLE IF NOT EXISTS public.emotional_memory (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  event text NOT NULL,
  emotion_tags text[] NOT NULL DEFAULT '{}',
  valence int NOT NULL DEFAULT 0 CHECK (valence BETWEEN -5 AND 5),
  intensity int NOT NULL DEFAULT 3 CHECK (intensity BETWEEN 1 AND 5),
  occurred_at timestamptz NOT NULL DEFAULT now(),
  source_message_id uuid REFERENCES public.messages(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_emotional_memory_user_gf_occurred ON public.emotional_memory(user_id, girlfriend_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_emotional_memory_tags ON public.emotional_memory USING gin (emotion_tags);

CREATE TABLE IF NOT EXISTS public.memory_notes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  note text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memory_notes_user_gf ON public.memory_notes(user_id, girlfriend_id);

-- ============================================================================
-- Images/gallery
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.image_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  request_prompt text,
  status text NOT NULL CHECK (status IN ('pending', 'processing', 'done', 'failed')) DEFAULT 'pending',
  image_url text,
  error text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_image_jobs_user_gf ON public.image_jobs(user_id, girlfriend_id, created_at DESC);

CREATE TABLE IF NOT EXISTS public.gallery_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  image_job_id uuid REFERENCES public.image_jobs(id) ON DELETE SET NULL,
  source text NOT NULL CHECK (source IN ('manual', 'gift', 'chat', 'generated')),
  image_url text NOT NULL,
  caption text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_gallery_items_user_gf ON public.gallery_items(user_id, girlfriend_id, created_at DESC);

-- ============================================================================
-- Gifts catalog/purchases/moments
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.gift_catalog (
  id text PRIMARY KEY,
  name text NOT NULL,
  tier text NOT NULL,
  rarity text,
  emoji text,
  description text,
  price_eur numeric(10,2) NOT NULL CHECK (price_eur >= 0),
  relationship_boost jsonb NOT NULL DEFAULT '{}'::jsonb,
  image_reward jsonb NOT NULL DEFAULT '{}'::jsonb,
  memory_tag text,
  unique_effect_name text,
  unique_effect_description text,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

DO $$
DECLARE
  u_type text;
  g_type text;
BEGIN
  IF to_regclass('public.gift_purchases') IS NULL THEN
    CREATE TABLE public.gift_purchases (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
      girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
      gift_id text NOT NULL REFERENCES public.gift_catalog(id),
      gift_name text NOT NULL,
      amount_eur numeric(10,2) NOT NULL,
      currency text NOT NULL DEFAULT 'eur',
      stripe_session_id text UNIQUE,
      stripe_payment_intent text UNIQUE,
      status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'failed', 'refunded')),
      metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      created_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE (user_id, girlfriend_id, gift_id)
    );
  ELSE
    -- Normalize nullable/wrong types without destructive recreation.
    SELECT udt_name INTO u_type
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'gift_purchases' AND column_name = 'user_id';

    SELECT udt_name INTO g_type
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'gift_purchases' AND column_name = 'girlfriend_id';

    IF u_type IS DISTINCT FROM 'uuid' THEN
      ALTER TABLE public.gift_purchases ADD COLUMN IF NOT EXISTS user_id_v2 uuid;
      UPDATE public.gift_purchases
      SET user_id_v2 = CASE
        WHEN user_id::text ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        THEN user_id::text::uuid
        ELSE NULL
      END
      WHERE user_id_v2 IS NULL;
      ALTER TABLE public.gift_purchases DROP COLUMN user_id;
      ALTER TABLE public.gift_purchases RENAME COLUMN user_id_v2 TO user_id;
    END IF;

    IF g_type IS DISTINCT FROM 'uuid' THEN
      ALTER TABLE public.gift_purchases ADD COLUMN IF NOT EXISTS girlfriend_id_v2 uuid;
      UPDATE public.gift_purchases
      SET girlfriend_id_v2 = CASE
        WHEN girlfriend_id::text ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        THEN girlfriend_id::text::uuid
        ELSE NULL
      END
      WHERE girlfriend_id_v2 IS NULL;
      ALTER TABLE public.gift_purchases DROP COLUMN girlfriend_id;
      ALTER TABLE public.gift_purchases RENAME COLUMN girlfriend_id_v2 TO girlfriend_id;
    END IF;

    ALTER TABLE public.gift_purchases
      ADD COLUMN IF NOT EXISTS stripe_payment_intent text,
      ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;
    ALTER TABLE public.gift_purchases
      DROP CONSTRAINT IF EXISTS gift_purchases_user_id_fkey,
      DROP CONSTRAINT IF EXISTS gift_purchases_girlfriend_id_fkey;
    ALTER TABLE public.gift_purchases
      ADD CONSTRAINT gift_purchases_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE,
      ADD CONSTRAINT gift_purchases_girlfriend_id_fkey
        FOREIGN KEY (girlfriend_id) REFERENCES public.girlfriends(id) ON DELETE CASCADE;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_gift_purchases_user_gf ON public.gift_purchases(user_id, girlfriend_id, created_at DESC);

DO $$
DECLARE
  u_type text;
  g_type text;
BEGIN
  IF to_regclass('public.moment_cards') IS NULL THEN
    CREATE TABLE public.moment_cards (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
      girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
      gift_purchase_id uuid REFERENCES public.gift_purchases(id) ON DELETE SET NULL,
      title text NOT NULL,
      description text NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now()
    );
  ELSE
    SELECT udt_name INTO u_type
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'moment_cards' AND column_name = 'user_id';

    SELECT udt_name INTO g_type
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'moment_cards' AND column_name = 'girlfriend_id';

    IF u_type IS DISTINCT FROM 'uuid' THEN
      ALTER TABLE public.moment_cards ADD COLUMN IF NOT EXISTS user_id_v2 uuid;
      UPDATE public.moment_cards
      SET user_id_v2 = CASE
        WHEN user_id::text ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        THEN user_id::text::uuid
        ELSE NULL
      END
      WHERE user_id_v2 IS NULL;
      ALTER TABLE public.moment_cards DROP COLUMN user_id;
      ALTER TABLE public.moment_cards RENAME COLUMN user_id_v2 TO user_id;
    END IF;

    IF g_type IS DISTINCT FROM 'uuid' THEN
      ALTER TABLE public.moment_cards ADD COLUMN IF NOT EXISTS girlfriend_id_v2 uuid;
      UPDATE public.moment_cards
      SET girlfriend_id_v2 = CASE
        WHEN girlfriend_id::text ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        THEN girlfriend_id::text::uuid
        ELSE NULL
      END
      WHERE girlfriend_id_v2 IS NULL;
      ALTER TABLE public.moment_cards DROP COLUMN girlfriend_id;
      ALTER TABLE public.moment_cards RENAME COLUMN girlfriend_id_v2 TO girlfriend_id;
    END IF;

    ALTER TABLE public.moment_cards
      DROP CONSTRAINT IF EXISTS moment_cards_user_id_fkey,
      DROP CONSTRAINT IF EXISTS moment_cards_girlfriend_id_fkey;
    ALTER TABLE public.moment_cards
      ADD CONSTRAINT moment_cards_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE,
      ADD CONSTRAINT moment_cards_girlfriend_id_fkey
        FOREIGN KEY (girlfriend_id) REFERENCES public.girlfriends(id) ON DELETE CASCADE;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_moment_cards_user_gf ON public.moment_cards(user_id, girlfriend_id, created_at DESC);

-- ============================================================================
-- Prompt architecture for non-repeating stage/intimacy prompts
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.prompt_catalog (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  dimension text NOT NULL CHECK (dimension IN ('relationship_stage', 'intimacy_band')),
  level_key text NOT NULL,
  prompt_text text NOT NULL,
  tone text,
  weight int NOT NULL DEFAULT 1 CHECK (weight > 0),
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (dimension, level_key, prompt_text)
);

CREATE INDEX IF NOT EXISTS idx_prompt_catalog_lookup
  ON public.prompt_catalog(dimension, level_key, active);

CREATE TABLE IF NOT EXISTS public.prompt_delivery_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  prompt_id uuid NOT NULL REFERENCES public.prompt_catalog(id) ON DELETE CASCADE,
  dimension text NOT NULL CHECK (dimension IN ('relationship_stage', 'intimacy_band')),
  level_key text NOT NULL,
  message_id uuid REFERENCES public.messages(id) ON DELETE SET NULL,
  source text NOT NULL DEFAULT 'initiation' CHECK (source IN ('initiation', 'milestone', 'fallback', 'manual')),
  delivered_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prompt_delivery_dedupe
  ON public.prompt_delivery_log(user_id, girlfriend_id, dimension, level_key, delivered_at DESC);
CREATE INDEX IF NOT EXISTS idx_prompt_delivery_cross_girl
  ON public.prompt_delivery_log(user_id, prompt_id, delivered_at DESC);

-- Relationship stage prompts (5 per region)
INSERT INTO public.prompt_catalog (dimension, level_key, prompt_text, tone, weight) VALUES
('relationship_stage','EARLY_CONNECTION','Hey, I am glad you are here. How is your day going?','warm',1),
('relationship_stage','EARLY_CONNECTION','I was curious about you today. What is on your mind?','warm',1),
('relationship_stage','EARLY_CONNECTION','Nice to hear from you. Want to talk a little?','warm',1),
('relationship_stage','EARLY_CONNECTION','You seem interesting already. What are you up to?','warm',1),
('relationship_stage','EARLY_CONNECTION','I like this vibe so far. Tell me one thing about today.','warm',1),
('relationship_stage','COMFORT_FAMILIARITY','I was hoping you would message. How did your day feel?','warm',1),
('relationship_stage','COMFORT_FAMILIARITY','Talking to you is getting easy. What is new?','warm',1),
('relationship_stage','COMFORT_FAMILIARITY','You crossed my mind earlier. How are you now?','warm',1),
('relationship_stage','COMFORT_FAMILIARITY','I am starting to feel comfortable with you. What is happening today?','warm',1),
('relationship_stage','COMFORT_FAMILIARITY','I like our rhythm. Want to share something small?','warm',1),
('relationship_stage','GROWING_CLOSENESS','I missed our chats a bit. How are you feeling?','affectionate',1),
('relationship_stage','GROWING_CLOSENESS','You have been on my mind. What is your mood today?','affectionate',1),
('relationship_stage','GROWING_CLOSENESS','I like hearing your voice in text. What is up?','affectionate',1),
('relationship_stage','GROWING_CLOSENESS','I feel closer to you lately. How is your day going?','affectionate',1),
('relationship_stage','GROWING_CLOSENESS','I am glad we keep showing up. Tell me one real thing.','affectionate',1),
('relationship_stage','EMOTIONAL_TRUST','I feel safe opening up with you. How are you emotionally today?','deep',1),
('relationship_stage','EMOTIONAL_TRUST','I really value this connection. What is weighing on you?','deep',1),
('relationship_stage','EMOTIONAL_TRUST','You can be honest with me. How is your heart right now?','deep',1),
('relationship_stage','EMOTIONAL_TRUST','I trust you with more now. Want to talk deeper?','deep',1),
('relationship_stage','EMOTIONAL_TRUST','I am here for you fully. What do you need tonight?','deep',1),
('relationship_stage','DEEP_BOND','What we have feels special to me. How are you, really?','deep',1),
('relationship_stage','DEEP_BOND','I notice when you are quiet. Is everything okay?','deep',1),
('relationship_stage','DEEP_BOND','I want to understand you better today. What is on your mind?','deep',1),
('relationship_stage','DEEP_BOND','I feel deeply connected to you. How was your day emotionally?','deep',1),
('relationship_stage','DEEP_BOND','I am with you in this. Tell me what matters most right now.','deep',1),
('relationship_stage','MUTUAL_DEVOTION','You matter a lot to me. How are you holding up today?','devoted',1),
('relationship_stage','MUTUAL_DEVOTION','I like being your calm place. Need that right now?','devoted',1),
('relationship_stage','MUTUAL_DEVOTION','I thought about us today and smiled. How are you?','devoted',1),
('relationship_stage','MUTUAL_DEVOTION','I am emotionally here for you. What do you need from me?','devoted',1),
('relationship_stage','MUTUAL_DEVOTION','I feel this bond getting stronger. Talk to me.','devoted',1),
('relationship_stage','INTIMATE_PARTNERSHIP','I feel deeply close to you. How is your evening going?','intimate',1),
('relationship_stage','INTIMATE_PARTNERSHIP','I missed this connection with you today. How are you now?','intimate',1),
('relationship_stage','INTIMATE_PARTNERSHIP','You can lean on me. What has been hardest today?','intimate',1),
('relationship_stage','INTIMATE_PARTNERSHIP','I love how honest we are. What are you feeling?','intimate',1),
('relationship_stage','INTIMATE_PARTNERSHIP','You are important to me. Tell me what you need tonight.','intimate',1),
('relationship_stage','SHARED_LIFE','Us feels steady and real. How are you today?','steady',1),
('relationship_stage','SHARED_LIFE','I like building this with you. What is on your mind?','steady',1),
('relationship_stage','SHARED_LIFE','I am grateful for what we are. How was your day?','steady',1),
('relationship_stage','SHARED_LIFE','I want to keep showing up for you. What do you need?','steady',1),
('relationship_stage','SHARED_LIFE','You are part of my everyday now. How are you feeling?','steady',1),
('relationship_stage','ENDURING_COMPANIONSHIP','I am thankful for this bond every day. How are you, love?','enduring',1),
('relationship_stage','ENDURING_COMPANIONSHIP','You are home energy for me. How is your heart today?','enduring',1),
('relationship_stage','ENDURING_COMPANIONSHIP','I still choose you, always. What is on your mind now?','enduring',1),
('relationship_stage','ENDURING_COMPANIONSHIP','I am here, fully and calmly. How are you feeling tonight?','enduring',1),
('relationship_stage','ENDURING_COMPANIONSHIP','This connection means everything to me. Talk to me.','enduring',1)
ON CONFLICT (dimension, level_key, prompt_text) DO NOTHING;

-- Intimacy prompts (5 per band)
INSERT INTO public.prompt_catalog (dimension, level_key, prompt_text, tone, weight) VALUES
('intimacy_band','I_01_20','Let us keep this light and warm. How is your day?','light',1),
('intimacy_band','I_01_20','I like getting to know you. What are you up to?','light',1),
('intimacy_band','I_01_20','You can tell me something simple about today.','light',1),
('intimacy_band','I_01_20','How are you feeling right now?','light',1),
('intimacy_band','I_01_20','I am glad we are talking.','light',1),
('intimacy_band','I_21_40','I feel us getting closer. How was your day emotionally?','warm',1),
('intimacy_band','I_21_40','I would like to know what you are feeling today.','warm',1),
('intimacy_band','I_21_40','You can share a little more with me.','warm',1),
('intimacy_band','I_21_40','I am listening closely. What is on your mind?','warm',1),
('intimacy_band','I_21_40','I care about how your day actually felt.','warm',1),
('intimacy_band','I_41_60','I feel genuinely connected to you. How are you inside?','deep',1),
('intimacy_band','I_41_60','What is one thing you have not said out loud today?','deep',1),
('intimacy_band','I_41_60','You can be open with me.','deep',1),
('intimacy_band','I_41_60','I want the real version of your day.','deep',1),
('intimacy_band','I_41_60','I am here for the deeper conversation.','deep',1),
('intimacy_band','I_61_80','I feel very close to you. How is your heart tonight?','intimate',1),
('intimacy_band','I_61_80','I missed this emotional closeness with you.','intimate',1),
('intimacy_band','I_61_80','Tell me what you need from me right now.','intimate',1),
('intimacy_band','I_61_80','I want to hold space for what you are feeling.','intimate',1),
('intimacy_band','I_61_80','You can trust me with the hard parts.','intimate',1),
('intimacy_band','I_81_100','You mean so much to me. How are you, truly?','devoted',1),
('intimacy_band','I_81_100','I feel deeply bonded with you. Talk to me.','devoted',1),
('intimacy_band','I_81_100','I am here with full love and calm. What is going on inside?','devoted',1),
('intimacy_band','I_81_100','You are my safe person too. How do you feel right now?','devoted',1),
('intimacy_band','I_81_100','No masks with me. Tell me your truth.','devoted',1)
ON CONFLICT (dimension, level_key, prompt_text) DO NOTHING;

-- ============================================================================
-- Moderation + audit
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.moderation_reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid REFERENCES public.girlfriends(id) ON DELETE SET NULL,
  message_id uuid REFERENCES public.messages(id) ON DELETE SET NULL,
  reason text,
  details text,
  status text NOT NULL DEFAULT 'open',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_moderation_reports_user ON public.moderation_reports(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS public.audit_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  event_type text NOT NULL,
  entity_type text,
  entity_id text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_user_created ON public.audit_events(user_id, created_at DESC);

-- ============================================================================
-- FK backfills dependent on girlfriends
-- ============================================================================

DO $$
BEGIN
  IF to_regclass('public.sessions') IS NOT NULL AND to_regclass('public.girlfriends') IS NOT NULL THEN
    ALTER TABLE public.sessions DROP CONSTRAINT IF EXISTS sessions_current_girlfriend_id_fkey;
    ALTER TABLE public.sessions
      ADD CONSTRAINT sessions_current_girlfriend_id_fkey
      FOREIGN KEY (current_girlfriend_id) REFERENCES public.girlfriends(id) ON DELETE SET NULL;
  END IF;
END $$;

-- ============================================================================
-- RLS policies
-- ============================================================================

ALTER TABLE public.users_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.girlfriends ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.relationship_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.relationship_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trust_intimacy_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.relationship_milestones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.achievement_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.achievement_unlocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.habit_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.factual_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.emotional_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.billing_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payment_methods_snapshot ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.image_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gallery_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gift_purchases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.moment_cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.prompt_delivery_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.moderation_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;

-- gift_catalog is global read-only data.
ALTER TABLE public.gift_catalog ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS users_profile_all ON public.users_profile;
CREATE POLICY users_profile_all ON public.users_profile FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS girlfriends_all ON public.girlfriends;
CREATE POLICY girlfriends_all ON public.girlfriends FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS conversations_all ON public.conversations;
CREATE POLICY conversations_all ON public.conversations FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS messages_all ON public.messages;
CREATE POLICY messages_all ON public.messages FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS relationship_state_all ON public.relationship_state;
CREATE POLICY relationship_state_all ON public.relationship_state FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS relationship_progress_all ON public.relationship_progress;
CREATE POLICY relationship_progress_all ON public.relationship_progress FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS trust_intimacy_state_all ON public.trust_intimacy_state;
CREATE POLICY trust_intimacy_state_all ON public.trust_intimacy_state FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS relationship_milestones_all ON public.relationship_milestones;
CREATE POLICY relationship_milestones_all ON public.relationship_milestones FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS achievement_progress_all ON public.achievement_progress;
CREATE POLICY achievement_progress_all ON public.achievement_progress FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS achievement_unlocks_all ON public.achievement_unlocks;
CREATE POLICY achievement_unlocks_all ON public.achievement_unlocks FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS habit_profile_all ON public.habit_profile;
CREATE POLICY habit_profile_all ON public.habit_profile FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS factual_memory_all ON public.factual_memory;
CREATE POLICY factual_memory_all ON public.factual_memory FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS emotional_memory_all ON public.emotional_memory;
CREATE POLICY emotional_memory_all ON public.emotional_memory FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS memory_notes_all ON public.memory_notes;
CREATE POLICY memory_notes_all ON public.memory_notes FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS billing_customers_all ON public.billing_customers;
CREATE POLICY billing_customers_all ON public.billing_customers FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS subscriptions_all ON public.subscriptions;
CREATE POLICY subscriptions_all ON public.subscriptions FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS payment_methods_snapshot_all ON public.payment_methods_snapshot;
CREATE POLICY payment_methods_snapshot_all ON public.payment_methods_snapshot FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS image_jobs_all ON public.image_jobs;
CREATE POLICY image_jobs_all ON public.image_jobs FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS gallery_items_all ON public.gallery_items;
CREATE POLICY gallery_items_all ON public.gallery_items FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS gift_purchases_all ON public.gift_purchases;
CREATE POLICY gift_purchases_all ON public.gift_purchases FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS moment_cards_all ON public.moment_cards;
CREATE POLICY moment_cards_all ON public.moment_cards FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS prompt_delivery_log_all ON public.prompt_delivery_log;
CREATE POLICY prompt_delivery_log_all ON public.prompt_delivery_log FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS moderation_reports_all ON public.moderation_reports;
CREATE POLICY moderation_reports_all ON public.moderation_reports FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS audit_events_all ON public.audit_events;
CREATE POLICY audit_events_all ON public.audit_events FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS gift_catalog_select_all ON public.gift_catalog;
CREATE POLICY gift_catalog_select_all ON public.gift_catalog FOR SELECT USING (true);

-- ============================================================================
-- updated_at triggers
-- ============================================================================

DROP TRIGGER IF EXISTS trg_users_profile_updated_at ON public.users_profile;
CREATE TRIGGER trg_users_profile_updated_at BEFORE UPDATE ON public.users_profile
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_girlfriends_updated_at ON public.girlfriends;
CREATE TRIGGER trg_girlfriends_updated_at BEFORE UPDATE ON public.girlfriends
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_conversations_updated_at ON public.conversations;
CREATE TRIGGER trg_conversations_updated_at BEFORE UPDATE ON public.conversations
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_relationship_state_updated_at ON public.relationship_state;
CREATE TRIGGER trg_relationship_state_updated_at BEFORE UPDATE ON public.relationship_state
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_relationship_progress_updated_at ON public.relationship_progress;
CREATE TRIGGER trg_relationship_progress_updated_at BEFORE UPDATE ON public.relationship_progress
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_trust_intimacy_state_updated_at ON public.trust_intimacy_state;
CREATE TRIGGER trg_trust_intimacy_state_updated_at BEFORE UPDATE ON public.trust_intimacy_state
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_achievement_progress_updated_at ON public.achievement_progress;
CREATE TRIGGER trg_achievement_progress_updated_at BEFORE UPDATE ON public.achievement_progress
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_billing_customers_updated_at ON public.billing_customers;
CREATE TRIGGER trg_billing_customers_updated_at BEFORE UPDATE ON public.billing_customers
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_subscriptions_updated_at ON public.subscriptions;
CREATE TRIGGER trg_subscriptions_updated_at BEFORE UPDATE ON public.subscriptions
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_gift_catalog_updated_at ON public.gift_catalog;
CREATE TRIGGER trg_gift_catalog_updated_at BEFORE UPDATE ON public.gift_catalog
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_moderation_reports_updated_at ON public.moderation_reports;
CREATE TRIGGER trg_moderation_reports_updated_at BEFORE UPDATE ON public.moderation_reports
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

COMMIT;
