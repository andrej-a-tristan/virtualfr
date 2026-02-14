-- ============================================================================
-- Migration 004: Bond Engine — Unified Memory Fabric + Disclosure + Patterns
-- ============================================================================

-- ── 1. Extend factual_memory with ranking metadata ─────────────────────────
ALTER TABLE public.factual_memory
  ADD COLUMN IF NOT EXISTS salience       integer   DEFAULT 50,
  ADD COLUMN IF NOT EXISTS decay_rate     real      DEFAULT 0.01,
  ADD COLUMN IF NOT EXISTS last_reinforced_at timestamptz DEFAULT now(),
  ADD COLUMN IF NOT EXISTS conflict_count integer   DEFAULT 0,
  ADD COLUMN IF NOT EXISTS is_conflicted  boolean   DEFAULT false;

-- ── 2. Extend emotional_memory with ranking metadata ───────────────────────
ALTER TABLE public.emotional_memory
  ADD COLUMN IF NOT EXISTS salience       integer   DEFAULT 50,
  ADD COLUMN IF NOT EXISTS confidence     integer   DEFAULT 80,
  ADD COLUMN IF NOT EXISTS decay_rate     real      DEFAULT 0.05,
  ADD COLUMN IF NOT EXISTS last_reinforced_at timestamptz DEFAULT now(),
  ADD COLUMN IF NOT EXISTS is_resolved    boolean   DEFAULT false;

-- ── 3. Episodic memory — important moments, conflicts, wins, promises ──────
CREATE TABLE IF NOT EXISTS public.memory_episodes (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id   uuid        NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  episode_type    text        NOT NULL,                          -- 'conflict', 'win', 'promise', 'shared_moment', 'vulnerability', 'milestone'
  summary         text        NOT NULL,
  detail          text,
  emotion_tags    text[]      DEFAULT '{}',
  participants    text[]      DEFAULT '{user, girlfriend}',
  salience        integer     DEFAULT 60,
  confidence      integer     DEFAULT 80,
  decay_rate      real        DEFAULT 0.005,
  last_reinforced_at timestamptz DEFAULT now(),
  is_resolved     boolean     DEFAULT false,
  source_turn_id  text,
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memory_episodes_user_gf
  ON public.memory_episodes(user_id, girlfriend_id);
CREATE INDEX IF NOT EXISTS idx_memory_episodes_salience
  ON public.memory_episodes(user_id, girlfriend_id, salience DESC);

-- ── 4. Memory entities — normalized facts/people/places ────────────────────
CREATE TABLE IF NOT EXISTS public.memory_entities (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id   uuid        NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  entity_type     text        NOT NULL,                          -- 'person', 'place', 'thing', 'event', 'preference'
  entity_key      text        NOT NULL,                          -- normalized key, e.g. "user.brother.mike"
  entity_value    text        NOT NULL,
  attributes      jsonb       DEFAULT '{}',                      -- extra metadata
  salience        integer     DEFAULT 50,
  confidence      integer     DEFAULT 80,
  decay_rate      real        DEFAULT 0.01,
  last_reinforced_at timestamptz DEFAULT now(),
  conflict_count  integer     DEFAULT 0,
  is_conflicted   boolean     DEFAULT false,
  source_turn_id  text,
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now(),
  UNIQUE (user_id, girlfriend_id, entity_key)
);

CREATE INDEX IF NOT EXISTS idx_memory_entities_user_gf
  ON public.memory_entities(user_id, girlfriend_id);

-- ── 5. Pattern memory — time habits, topic cycles, response latency ────────
CREATE TABLE IF NOT EXISTS public.memory_patterns (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id   uuid        NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  pattern_type    text        NOT NULL,                          -- 'time_habit', 'topic_cycle', 'response_latency', 'style_preference', 'conversation_cadence'
  pattern_key     text        NOT NULL,                          -- e.g. "active_hours", "avg_response_gap", "favorite_topics"
  pattern_value   jsonb       NOT NULL DEFAULT '{}',             -- flexible storage: {"hours": [21,22,23], "weekday_dist": {...}}
  observation_count integer   DEFAULT 1,
  salience        integer     DEFAULT 40,
  confidence      integer     DEFAULT 50,
  last_reinforced_at timestamptz DEFAULT now(),
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now(),
  UNIQUE (user_id, girlfriend_id, pattern_key)
);

CREATE INDEX IF NOT EXISTS idx_memory_patterns_user_gf
  ON public.memory_patterns(user_id, girlfriend_id);

-- ── 6. Memory conflicts — when facts disagree over time ────────────────────
CREATE TABLE IF NOT EXISTS public.memory_conflicts (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id   uuid        NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  memory_type     text        NOT NULL,                          -- 'factual', 'episodic', 'entity'
  memory_key      text        NOT NULL,
  old_value       text,
  new_value       text,
  resolution      text,                                          -- 'updated', 'kept_old', 'asked_user', null = unresolved
  resolved_at     timestamptz,
  source_turn_id  text,
  created_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memory_conflicts_user_gf
  ON public.memory_conflicts(user_id, girlfriend_id);

-- ── 7. Disclosure state — tracks self-disclosure graph per relationship ─────
CREATE TABLE IF NOT EXISTS public.disclosure_state (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id   uuid        NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  disclosure_level integer    DEFAULT 0,                         -- 0-4 (surface -> deep attachment)
  disclosed_nodes text[]      DEFAULT '{}',                      -- list of disclosed node ids
  reciprocity_score real      DEFAULT 0.0,                       -- 0.0 - 1.0
  last_disclosure_at timestamptz,
  last_boundary_violation_at timestamptz,
  cooldown_until  timestamptz,
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now(),
  UNIQUE (user_id, girlfriend_id)
);

-- ── 8. Response fingerprints — tracks assistant style for anti-repetition ───
CREATE TABLE IF NOT EXISTS public.response_fingerprints (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id   uuid        NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  turn_id         text        NOT NULL,
  fingerprint     jsonb       NOT NULL DEFAULT '{}',             -- {"phrases": [...], "pattern": "...", "cadence": "..."}
  memory_ids_used text[]      DEFAULT '{}',                      -- which memory items were referenced
  created_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_response_fp_user_gf
  ON public.response_fingerprints(user_id, girlfriend_id, created_at DESC);

-- ── 9. Capability unlocks — tracks which conversational capabilities are active
CREATE TABLE IF NOT EXISTS public.capability_unlocks (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id   uuid        NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  capability_key  text        NOT NULL,                          -- 'personal_callbacks', 'emotional_depth_2', 'sensitive_story', 'future_plans', 'conflict_repair'
  unlocked_at     timestamptz DEFAULT now(),
  unlock_level    integer     NOT NULL,                          -- the relationship level when unlocked
  UNIQUE (user_id, girlfriend_id, capability_key)
);

-- ── 10. Add updated_at triggers ────────────────────────────────────────────
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
  tbl text;
BEGIN
  FOR tbl IN SELECT unnest(ARRAY[
    'memory_episodes', 'memory_entities', 'memory_patterns',
    'disclosure_state'
  ])
  LOOP
    EXECUTE format(
      'DROP TRIGGER IF EXISTS set_updated_at ON public.%I; '
      'CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.%I '
      'FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();',
      tbl, tbl
    );
  END LOOP;
END;
$$;

-- ── 11. Enable RLS on new tables ───────────────────────────────────────────
ALTER TABLE public.memory_episodes       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_entities       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_patterns       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_conflicts      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.disclosure_state      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.response_fingerprints ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.capability_unlocks    ENABLE ROW LEVEL SECURITY;
