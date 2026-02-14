-- 005_behavior_engine.sql
-- Girl Dossier System + Conversation Mode State + Self-Memory Architecture
-- Run after 004_bond_engine.sql

-- ═══════════════════════════════════════════════════════════════════════════════
-- 1. GIRLFRIEND CORE PROFILE
--    Voice, worldview, values, boundaries, speech quirks — seeded from onboarding
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.girlfriend_core_profile (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    girlfriend_id   uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
    voice_style     text NOT NULL DEFAULT 'warm',         -- warm/playful/direct/gentle/passionate
    worldview       text DEFAULT '',                       -- short paragraph: how she sees the world
    values_text     text DEFAULT '',                       -- what matters to her
    boundaries      text DEFAULT '',                       -- things she won't do/say
    speech_quirks   text[] DEFAULT '{}',                   -- e.g. {"uses 'honestly' often", "trails off with ..."}
    attachment_tone text DEFAULT 'present',                -- clingy/present/independent/warm-distant
    json_profile    jsonb NOT NULL DEFAULT '{}'::jsonb,    -- full structured profile blob
    version         integer DEFAULT 1,
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now(),
    UNIQUE (user_id, girlfriend_id)
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 2. GIRLFRIEND LIFE GRAPH — NODES
--    People, places, work, hobbies, time periods in her life
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.girlfriend_life_graph_nodes (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    girlfriend_id   uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
    node_type       text NOT NULL,                         -- person/place/work/hobby/period/routine
    node_key        text NOT NULL,                         -- normalized key e.g. "best_friend.nina"
    label           text NOT NULL,                         -- display label e.g. "Nina (best friend)"
    attributes      jsonb DEFAULT '{}'::jsonb,             -- flexible detail {"age": 24, "met_at": "college"}
    confidence      integer DEFAULT 80 CHECK (confidence BETWEEN 0 AND 100),
    source          text DEFAULT 'onboarding',             -- onboarding/bootstrap/conversation/refresh
    created_at      timestamptz DEFAULT now(),
    UNIQUE (user_id, girlfriend_id, node_key)
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 3. GIRLFRIEND LIFE GRAPH — EDGES
--    Relationships between nodes
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.girlfriend_life_graph_edges (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    girlfriend_id   uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
    from_node_key   text NOT NULL,
    edge_type       text NOT NULL,                         -- works_at/lives_in/friends_with/hobby_at/remembers
    to_node_key     text NOT NULL,
    weight          real DEFAULT 1.0,
    created_at      timestamptz DEFAULT now()
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 4. GIRLFRIEND STORY BANK
--    Pre-generated personal anecdotes, opinions, memories by topic
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.girlfriend_story_bank (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    girlfriend_id   uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
    topic           text NOT NULL,                         -- childhood/work/hobbies/values/funny/future/food/music/family/travel
    story_type      text NOT NULL DEFAULT 'anecdote',      -- anecdote/opinion/memory/plan/preference
    story_text      text NOT NULL,                         -- the actual story/opinion text
    tone            text DEFAULT 'warm',                   -- warm/playful/reflective/vulnerable/excited
    intimacy_min    integer DEFAULT 0,                     -- minimum relationship level to use this story
    tags            text[] DEFAULT '{}',                   -- search tags
    novelty_weight  real DEFAULT 1.0,                      -- decays with usage
    last_used_at    timestamptz,
    usage_count     integer DEFAULT 0,
    source          text DEFAULT 'bootstrap',              -- bootstrap/conversation/refresh
    created_at      timestamptz DEFAULT now()
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 5. GIRLFRIEND CURRENT STATE
--    Today's mood, energy, focus, open conversational loops
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.girlfriend_current_state (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    girlfriend_id   uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
    mood            text DEFAULT 'content',                -- content/excited/reflective/tired/playful/anxious
    energy          text DEFAULT 'medium',                 -- low/medium/high
    focus_topics    text[] DEFAULT '{}',                   -- topics she's thinking about today
    open_loops      jsonb DEFAULT '[]'::jsonb,             -- [{"topic": "...", "context": "...", "created_at": "..."}]
    today_context   text DEFAULT '',                       -- "had a chill morning, thinking about weekend plans"
    last_refreshed_at timestamptz DEFAULT now(),
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now(),
    UNIQUE (user_id, girlfriend_id)
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 6. GIRLFRIEND SELF MEMORY
--    Facts she has claimed about herself — evolving, with consistency tracking
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.girlfriend_self_memory (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    girlfriend_id   uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
    memory_key      text NOT NULL,                         -- e.g. "favorite_color", "childhood_pet", "biggest_fear"
    memory_value    text NOT NULL,
    confidence      integer DEFAULT 80 CHECK (confidence BETWEEN 0 AND 100),
    salience        integer DEFAULT 50 CHECK (salience BETWEEN 0 AND 100),
    is_immutable    boolean DEFAULT false,                 -- true for core identity facts (origin, name)
    is_conflicted   boolean DEFAULT false,
    conflict_group  text,                                  -- links related conflict records
    first_seen_at   timestamptz DEFAULT now(),
    last_seen_at    timestamptz DEFAULT now(),
    source_turn_id  text,
    source          text DEFAULT 'bootstrap',              -- bootstrap/conversation/refresh
    created_at      timestamptz DEFAULT now(),
    UNIQUE (user_id, girlfriend_id, memory_key)
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 7. GIRLFRIEND SELF CONFLICTS
--    Tracks contradictions in what she's said about herself
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.girlfriend_self_conflicts (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    girlfriend_id   uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
    memory_key      text NOT NULL,
    old_value       text,
    new_value       text,
    status          text DEFAULT 'unresolved',             -- unresolved/accepted/rejected/evolved
    resolution_note text,
    created_at      timestamptz DEFAULT now(),
    resolved_at     timestamptz
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 8. CONVERSATION MODE STATE
--    Rolling question ratio, disclosure depth, last intents — per girlfriend
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.conversation_mode_state (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                  uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    girlfriend_id            uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
    question_ratio_10        real DEFAULT 0.0,              -- questions / last 10 assistant turns
    self_disclosure_ratio_10 real DEFAULT 0.0,              -- self-disclosures / last 10 assistant turns
    last_intents             text[] DEFAULT '{}',           -- last 10 detected intents
    last_cadences            text[] DEFAULT '{}',           -- last 10 cadences used
    consecutive_questions    integer DEFAULT 0,             -- current streak of question-ending turns
    story_ids_used_recently  text[] DEFAULT '{}',           -- story bank IDs used in last 20 turns
    generic_response_count   integer DEFAULT 0,             -- rolling count of generic/vague replies
    created_at               timestamptz DEFAULT now(),
    updated_at               timestamptz DEFAULT now(),
    UNIQUE (user_id, girlfriend_id)
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- INDEXES
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_gf_core_profile_gf ON public.girlfriend_core_profile(user_id, girlfriend_id);
CREATE INDEX IF NOT EXISTS idx_gf_life_nodes_gf ON public.girlfriend_life_graph_nodes(user_id, girlfriend_id);
CREATE INDEX IF NOT EXISTS idx_gf_life_edges_gf ON public.girlfriend_life_graph_edges(user_id, girlfriend_id);
CREATE INDEX IF NOT EXISTS idx_gf_story_bank_gf_topic ON public.girlfriend_story_bank(user_id, girlfriend_id, topic);
CREATE INDEX IF NOT EXISTS idx_gf_current_state_gf ON public.girlfriend_current_state(user_id, girlfriend_id);
CREATE INDEX IF NOT EXISTS idx_gf_self_memory_gf ON public.girlfriend_self_memory(user_id, girlfriend_id);
CREATE INDEX IF NOT EXISTS idx_gf_self_conflicts_gf ON public.girlfriend_self_conflicts(user_id, girlfriend_id);
CREATE INDEX IF NOT EXISTS idx_conv_mode_state_gf ON public.conversation_mode_state(user_id, girlfriend_id);

-- ═══════════════════════════════════════════════════════════════════════════════
-- UPDATED_AT TRIGGERS
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    t text;
BEGIN
    FOR t IN SELECT unnest(ARRAY[
        'girlfriend_core_profile',
        'girlfriend_current_state',
        'conversation_mode_state'
    ])
    LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS trg_%s_updated_at ON public.%I; '
            'CREATE TRIGGER trg_%s_updated_at BEFORE UPDATE ON public.%I '
            'FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();',
            t, t, t, t
        );
    END LOOP;
END;
$$;

-- ═══════════════════════════════════════════════════════════════════════════════
-- RLS
-- ═══════════════════════════════════════════════════════════════════════════════
DO $$
DECLARE
    t text;
BEGIN
    FOR t IN SELECT unnest(ARRAY[
        'girlfriend_core_profile',
        'girlfriend_life_graph_nodes',
        'girlfriend_life_graph_edges',
        'girlfriend_story_bank',
        'girlfriend_current_state',
        'girlfriend_self_memory',
        'girlfriend_self_conflicts',
        'conversation_mode_state'
    ])
    LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', t);
        EXECUTE format(
            'DROP POLICY IF EXISTS %s_user_policy ON public.%I; '
            'CREATE POLICY %s_user_policy ON public.%I '
            'FOR ALL USING (auth.uid() = user_id);',
            t, t, t, t
        );
    END LOOP;
END;
$$;
