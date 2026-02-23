-- 006_persona_vector.sql
-- Persona Vector persistence + telemetry fields for realism architecture v2.

CREATE TABLE IF NOT EXISTS public.persona_vectors (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    girlfriend_id   uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
    version_tag     text NOT NULL DEFAULT 'pv1',
    vector_json     jsonb NOT NULL DEFAULT '{}'::jsonb,
    vector_hash     text NOT NULL DEFAULT '',
    is_active       boolean NOT NULL DEFAULT true,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, girlfriend_id, version_tag)
);

CREATE INDEX IF NOT EXISTS idx_persona_vectors_active
    ON public.persona_vectors(user_id, girlfriend_id, is_active, updated_at DESC);

ALTER TABLE public.girlfriends
    ADD COLUMN IF NOT EXISTS persona_vector_version text DEFAULT 'pv1';

ALTER TABLE public.conversation_mode_state
    ADD COLUMN IF NOT EXISTS repeated_opening_rate real DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS callback_hit_rate real DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS last_quality_issues text[] DEFAULT '{}';

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_persona_vectors_updated_at ON public.persona_vectors;
CREATE TRIGGER trg_persona_vectors_updated_at
BEFORE UPDATE ON public.persona_vectors
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.persona_vectors ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS persona_vectors_user_policy ON public.persona_vectors;
CREATE POLICY persona_vectors_user_policy ON public.persona_vectors
FOR ALL USING (auth.uid() = user_id);
