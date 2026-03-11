-- 007_vector_memory.sql
-- Semantic vector memory layer for girlfriend chat.
-- Run after 004_bond_engine.sql and 005_behavior_engine.sql.

-- ═══════════════════════════════════════════════════════════════════════════════
-- 1. MEMORY VECTOR DOCUMENTS
--    Canonical text snippets to be embedded & stored in Pinecone
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.memory_vector_documents (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    girlfriend_id       uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
    source_type         text NOT NULL,                -- factual|emotional|episode|chat_chunk
    source_id           text NOT NULL,                -- id from source table (or message id for chat_chunk)
    canonical_text      text NOT NULL,                -- cleaned, single-purpose text to embed
    text_hash           text NOT NULL,                -- hash of canonical_text for dedupe
    memory_type         text NOT NULL,                -- user_fact|user_feeling|relationship_event|shared_episode|persona_fact|other
    salience            integer DEFAULT 50,
    confidence          integer DEFAULT 80,
    valence             integer DEFAULT 0,
    intensity           integer DEFAULT 0,
    is_resolved         boolean DEFAULT false,
    occurred_at         timestamptz,
    last_reinforced_at  timestamptz,
    privacy_level       text DEFAULT 'private',       -- public|private|sensitive
    expires_at          timestamptz,
    embedding_model     text DEFAULT '',
    schema_version      text DEFAULT 'v1',
    created_at          timestamptz DEFAULT now(),
    updated_at          timestamptz DEFAULT now(),
    UNIQUE (user_id, girlfriend_id, source_type, source_id)
);

CREATE INDEX IF NOT EXISTS idx_memvec_user_gf
    ON public.memory_vector_documents(user_id, girlfriend_id);

CREATE INDEX IF NOT EXISTS idx_memvec_user_gf_type
    ON public.memory_vector_documents(user_id, girlfriend_id, source_type);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 2. MEMORY VECTOR SYNC JOBS
--    Tracks pending upsert/delete jobs for Pinecone
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.memory_vector_sync_jobs (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    girlfriend_id   uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
    document_id     uuid NOT NULL REFERENCES public.memory_vector_documents(id) ON DELETE CASCADE,
    job_type        text NOT NULL,                   -- upsert|delete
    status          text NOT NULL DEFAULT 'pending', -- pending|processing|done|failed
    attempts        integer DEFAULT 0,
    last_error      text,
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memvec_jobs_status
    ON public.memory_vector_sync_jobs(status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_memvec_jobs_user_gf
    ON public.memory_vector_sync_jobs(user_id, girlfriend_id, status);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 3. USAGE METADATA ON EXISTING MEMORY TABLES
-- ═══════════════════════════════════════════════════════════════════════════════

ALTER TABLE public.factual_memory
    ADD COLUMN IF NOT EXISTS last_used_at timestamptz,
    ADD COLUMN IF NOT EXISTS use_count integer DEFAULT 0;

ALTER TABLE public.emotional_memory
    ADD COLUMN IF NOT EXISTS last_used_at timestamptz,
    ADD COLUMN IF NOT EXISTS use_count integer DEFAULT 0;

ALTER TABLE public.memory_episodes
    ADD COLUMN IF NOT EXISTS last_used_at timestamptz,
    ADD COLUMN IF NOT EXISTS use_count integer DEFAULT 0;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 4. UPDATED_AT TRIGGER FOR MEMORY VECTOR TABLES
-- ═══════════════════════════════════════════════════════════════════════════════

DO $$
DECLARE
    t text;
BEGIN
    FOR t IN SELECT unnest(ARRAY[
        'memory_vector_documents',
        'memory_vector_sync_jobs'
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
-- 5. ROW LEVEL SECURITY
-- ═══════════════════════════════════════════════════════════════════════════════

DO $$
DECLARE
    t text;
BEGIN
    FOR t IN SELECT unnest(ARRAY[
        'memory_vector_documents',
        'memory_vector_sync_jobs'
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

