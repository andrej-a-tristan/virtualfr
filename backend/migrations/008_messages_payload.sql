-- Migration 008: Rich payload for chat messages
-- Adds a generic JSONB `payload` column on `messages` so progression,
-- intimacy, and gift events can persist structured data for rich cards.
-- Safe to run multiple times (idempotent).

BEGIN;

ALTER TABLE public.messages
  ADD COLUMN IF NOT EXISTS payload jsonb;

-- Helpful indexes for event-style queries
CREATE INDEX IF NOT EXISTS idx_messages_event_type
  ON public.messages(event_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_messages_user_gf_event
  ON public.messages(user_id, girlfriend_id, event_type, created_at DESC);

COMMIT;

