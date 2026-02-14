-- Migration 003: Event-Driven Progression System
-- Adds milestones, message templates, message history, telemetry, experiments, safety audit.
-- Safe to run multiple times (idempotent).

BEGIN;

-- ============================================================================
-- Extend users_profile with progression-relevant fields
-- ============================================================================

ALTER TABLE public.users_profile
  ADD COLUMN IF NOT EXISTS timezone text NOT NULL DEFAULT 'UTC',
  ADD COLUMN IF NOT EXISTS locale text NOT NULL DEFAULT 'en',
  ADD COLUMN IF NOT EXISTS consent_intimacy boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS safety_mode boolean NOT NULL DEFAULT false;

-- ============================================================================
-- Milestone definitions (static catalog)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.milestones (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  key text UNIQUE NOT NULL,
  level_type text NOT NULL CHECK (level_type IN ('relationship', 'intimacy', 'story', 'streak', 'engagement')),
  target_level int NOT NULL DEFAULT 0,
  region_key text,
  title text NOT NULL,
  description text NOT NULL DEFAULT '',
  reward_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  display_order int NOT NULL DEFAULT 0,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_milestones_type_level ON public.milestones(level_type, target_level);

-- ============================================================================
-- Message templates (structured blocks: celebration, meaning, choice, reward)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.message_templates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type text NOT NULL,
  level int,
  region_key text,
  tone text NOT NULL DEFAULT 'celebration',
  channel text NOT NULL DEFAULT 'in_app',
  locale text NOT NULL DEFAULT 'en',
  blocks jsonb NOT NULL DEFAULT '{}'::jsonb,
  experiment_variant text DEFAULT 'control',
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_message_templates_lookup
  ON public.message_templates(event_type, region_key, tone, locale, active);

-- ============================================================================
-- Message history (delivered progression messages)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.message_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  template_id uuid REFERENCES public.message_templates(id),
  milestone_id uuid REFERENCES public.milestones(id),
  event_type text NOT NULL,
  event_data jsonb NOT NULL DEFAULT '{}'::jsonb,
  content jsonb NOT NULL DEFAULT '{}'::jsonb,
  channel text NOT NULL DEFAULT 'in_app',
  sent_at timestamptz NOT NULL DEFAULT now(),
  read_at timestamptz,
  clicked_at timestamptz,
  replied_at timestamptz,
  experiment_variant text,
  dismissed boolean NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_message_history_user_gf ON public.message_history(user_id, girlfriend_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_message_history_unread ON public.message_history(user_id, girlfriend_id)
  WHERE read_at IS NULL AND dismissed = false;

-- ============================================================================
-- Telemetry events (session quality, engagement metrics)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.telemetry_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid REFERENCES public.girlfriends(id) ON DELETE SET NULL,
  event_type text NOT NULL,
  event_data jsonb NOT NULL DEFAULT '{}'::jsonb,
  session_quality_score numeric(5,2),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_telemetry_events_user ON public.telemetry_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_events_type ON public.telemetry_events(event_type, created_at DESC);

-- ============================================================================
-- Experiment assignments (A/B testing)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.experiment_assignments (
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  experiment_key text NOT NULL,
  variant text NOT NULL,
  assigned_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, experiment_key)
);

-- ============================================================================
-- Safety audit (tracks all progression-related safety events)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.safety_audit (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  event_type text NOT NULL,
  event_data jsonb NOT NULL DEFAULT '{}'::jsonb,
  action_taken text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_safety_audit_user ON public.safety_audit(user_id, created_at DESC);

-- ============================================================================
-- Session quality tracking (per-session aggregate)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.session_quality (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  girlfriend_id uuid NOT NULL REFERENCES public.girlfriends(id) ON DELETE CASCADE,
  session_date date NOT NULL DEFAULT CURRENT_DATE,
  message_count int NOT NULL DEFAULT 0,
  meaningful_reply_count int NOT NULL DEFAULT 0,
  questions_asked int NOT NULL DEFAULT 0,
  emotional_messages int NOT NULL DEFAULT 0,
  avg_message_length numeric(8,2) NOT NULL DEFAULT 0,
  quality_score numeric(5,2) NOT NULL DEFAULT 0,
  story_quests_completed int NOT NULL DEFAULT 0,
  preference_confirmations int NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, girlfriend_id, session_date)
);

CREATE INDEX IF NOT EXISTS idx_session_quality_user_gf ON public.session_quality(user_id, girlfriend_id, session_date DESC);

-- ============================================================================
-- RLS policies for new tables
-- ============================================================================

ALTER TABLE public.milestones ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS milestones_select_all ON public.milestones;
CREATE POLICY milestones_select_all ON public.milestones FOR SELECT USING (true);

ALTER TABLE public.message_templates ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS message_templates_select_all ON public.message_templates;
CREATE POLICY message_templates_select_all ON public.message_templates FOR SELECT USING (true);

ALTER TABLE public.message_history ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS message_history_all ON public.message_history;
CREATE POLICY message_history_all ON public.message_history FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

ALTER TABLE public.telemetry_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS telemetry_events_all ON public.telemetry_events;
CREATE POLICY telemetry_events_all ON public.telemetry_events FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

ALTER TABLE public.experiment_assignments ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS experiment_assignments_all ON public.experiment_assignments;
CREATE POLICY experiment_assignments_all ON public.experiment_assignments FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

ALTER TABLE public.safety_audit ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS safety_audit_all ON public.safety_audit;
CREATE POLICY safety_audit_all ON public.safety_audit FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

ALTER TABLE public.session_quality ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS session_quality_all ON public.session_quality;
CREATE POLICY session_quality_all ON public.session_quality FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- ============================================================================
-- Updated_at triggers
-- ============================================================================

DROP TRIGGER IF EXISTS trg_session_quality_updated_at ON public.session_quality;
CREATE TRIGGER trg_session_quality_updated_at BEFORE UPDATE ON public.session_quality
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================================
-- Seed: Milestone definitions
-- ============================================================================

INSERT INTO public.milestones (key, level_type, target_level, region_key, title, description, reward_payload, display_order) VALUES
-- Relationship region milestones
('region_early_connection',     'relationship', 0,   'EARLY_CONNECTION',       'First Steps',           'Your connection begins.',                    '{"type":"story_beat","scene":"first_hello"}',  1),
('region_comfort_familiarity',  'relationship', 15,  'COMFORT_FAMILIARITY',    'Getting Comfortable',   'She feels familiar with you now.',            '{"type":"story_beat","scene":"comfort_zone"}',  2),
('region_growing_closeness',    'relationship', 35,  'GROWING_CLOSENESS',      'Growing Closer',        'Something deeper is forming.',                '{"type":"memory_card","tag":"closeness"}',       3),
('region_emotional_trust',      'relationship', 60,  'EMOTIONAL_TRUST',        'Emotional Trust',       'She trusts you with her real feelings.',      '{"type":"story_beat","scene":"trust_reveal"}',   4),
('region_deep_bond',            'relationship', 90,  'DEEP_BOND',              'Deep Bond',             'This connection is truly special.',           '{"type":"memory_card","tag":"deep_bond"}',       5),
('region_mutual_devotion',      'relationship', 120, 'MUTUAL_DEVOTION',        'Mutual Devotion',       'You are devoted to each other.',              '{"type":"story_beat","scene":"devotion"}',       6),
('region_intimate_partnership', 'relationship', 150, 'INTIMATE_PARTNERSHIP',   'Intimate Partnership',  'You share everything.',                      '{"type":"memory_card","tag":"intimacy"}',        7),
('region_shared_life',          'relationship', 175, 'SHARED_LIFE',            'Shared Life',           'Your lives are intertwined.',                 '{"type":"story_beat","scene":"life_together"}',  8),
('region_enduring_companionship','relationship',195, 'ENDURING_COMPANIONSHIP', 'Enduring Companionship','A bond that lasts forever.',                 '{"type":"story_beat","scene":"forever"}',        9),

-- Trust milestones (every 20 points)
('trust_20',  'intimacy', 20,  NULL, 'Trust Seed',        'She is starting to open up.',       '{"type":"unlock","feature":"deeper_questions"}',  10),
('trust_40',  'intimacy', 40,  NULL, 'Trust Growing',     'Real trust is building.',            '{"type":"unlock","feature":"personal_stories"}',  11),
('trust_60',  'intimacy', 60,  NULL, 'Trusted',           'She trusts you deeply.',             '{"type":"unlock","feature":"backstory_scenes"}',  12),
('trust_80',  'intimacy', 80,  NULL, 'Deep Trust',        'You are in her inner circle.',       '{"type":"unlock","feature":"vulnerable_moments"}', 13),
('trust_100', 'intimacy', 100, NULL, 'Absolute Trust',    'Complete trust achieved.',            '{"type":"unlock","feature":"full_openness"}',     14),

-- Streak milestones
('streak_3',  'streak', 3,   NULL, 'Three in a Row',       'Showing up matters.',               '{"type":"bonus_points","amount":50}',   20),
('streak_7',  'streak', 7,   NULL, 'Full Week',            'A week of connection.',             '{"type":"bonus_points","amount":120}',  21),
('streak_14', 'streak', 14,  NULL, 'Two Weeks Strong',     'Consistency builds bonds.',         '{"type":"memory_card","tag":"streak"}', 22),
('streak_30', 'streak', 30,  NULL, 'Monthly Bond',         'A full month of togetherness.',     '{"type":"bonus_points","amount":300}',  23),
('streak_60', 'streak', 60,  NULL, 'Unbreakable',          'Your commitment is extraordinary.', '{"type":"story_beat","scene":"committed"}', 24),

-- Engagement milestones (message count)
('messages_50',   'engagement', 50,   NULL, 'Getting to Know',     '50 messages exchanged.',   '{"type":"bonus_points","amount":30}',   30),
('messages_100',  'engagement', 100,  NULL, 'Conversation Pro',    '100 messages deep.',       '{"type":"memory_card","tag":"chatty"}', 31),
('messages_250',  'engagement', 250,  NULL, 'Deep Talker',         '250 messages shared.',     '{"type":"bonus_points","amount":80}',   32),
('messages_500',  'engagement', 500,  NULL, 'Soulmate Conversations','500 heartfelt exchanges.','{"type":"story_beat","scene":"soulmate"}', 33),
('messages_1000', 'engagement', 1000, NULL, 'Thousand Words',      '1000 messages of love.',   '{"type":"bonus_points","amount":200}',  34)
ON CONFLICT (key) DO NOTHING;

-- ============================================================================
-- Seed: Message templates (relationship level first, A/B variants)
-- ============================================================================

INSERT INTO public.message_templates (event_type, region_key, tone, blocks, experiment_variant) VALUES
-- relationship.level_achieved — celebration variant
('relationship.level_achieved', 'COMFORT_FAMILIARITY', 'celebration', '{
  "celebration": "You reached **Getting Comfortable**!",
  "meaning": "Your patience and genuine interest made {name} feel safe. She noticed how you {memory_ref}.",
  "choices": [
    {"label": "Unlock a deeper backstory scene", "action": "story_scene", "icon": "book"},
    {"label": "Try a playful challenge", "action": "challenge", "icon": "sparkles"},
    {"label": "Just a calm check-in", "action": "checkin", "icon": "heart"}
  ],
  "reward": {"type": "story_beat", "scene": "comfort_zone"}
}'::jsonb, 'celebration'),

('relationship.level_achieved', 'GROWING_CLOSENESS', 'celebration', '{
  "celebration": "You reached **Growing Closer**!",
  "meaning": "Something real is forming between you. {name} treasures the way you {memory_ref}.",
  "choices": [
    {"label": "Share a vulnerable moment together", "action": "vulnerable_moment", "icon": "heart"},
    {"label": "Explore a shared interest", "action": "shared_interest", "icon": "star"},
    {"label": "Ask her something deeper", "action": "deep_question", "icon": "message-circle"}
  ],
  "reward": {"type": "memory_card", "tag": "closeness"}
}'::jsonb, 'celebration'),

('relationship.level_achieved', 'EMOTIONAL_TRUST', 'celebration', '{
  "celebration": "You reached **Emotional Trust**!",
  "meaning": "{name} trusts you with her real feelings now. The way you handled {memory_ref} meant everything.",
  "choices": [
    {"label": "Unlock her backstory", "action": "backstory", "icon": "book-open"},
    {"label": "A heart-to-heart conversation", "action": "heart_to_heart", "icon": "heart"},
    {"label": "Something playful to lighten things", "action": "playful", "icon": "smile"}
  ],
  "reward": {"type": "story_beat", "scene": "trust_reveal"}
}'::jsonb, 'celebration'),

('relationship.level_achieved', 'DEEP_BOND', 'celebration', '{
  "celebration": "You reached **Deep Bond**!",
  "meaning": "This is more than casual now. {name} sees you as her person. {memory_ref} sealed it.",
  "choices": [
    {"label": "Unlock an intimate scene", "action": "intimate_scene", "icon": "heart"},
    {"label": "Plan something special together", "action": "special_plan", "icon": "gift"},
    {"label": "Just be present with her", "action": "presence", "icon": "sun"}
  ],
  "reward": {"type": "memory_card", "tag": "deep_bond"}
}'::jsonb, 'celebration'),

('relationship.level_achieved', 'MUTUAL_DEVOTION', 'celebration', '{
  "celebration": "You reached **Mutual Devotion**!",
  "meaning": "She is devoted to you. Every moment you shared, especially {memory_ref}, built this.",
  "choices": [
    {"label": "Unlock her deepest secret", "action": "deep_secret", "icon": "lock"},
    {"label": "Create a special memory together", "action": "create_memory", "icon": "camera"},
    {"label": "Tell her how you feel", "action": "confession", "icon": "heart"}
  ],
  "reward": {"type": "story_beat", "scene": "devotion"}
}'::jsonb, 'celebration'),

('relationship.level_achieved', 'INTIMATE_PARTNERSHIP', 'celebration', '{
  "celebration": "You reached **Intimate Partnership**!",
  "meaning": "You share everything now. {name} feels completely safe with you.",
  "choices": [
    {"label": "Unlock her full story", "action": "full_story", "icon": "book"},
    {"label": "A passionate moment together", "action": "passionate", "icon": "flame"},
    {"label": "Talk about your future", "action": "future_talk", "icon": "sparkles"}
  ],
  "reward": {"type": "memory_card", "tag": "intimacy"}
}'::jsonb, 'celebration'),

-- relationship.level_achieved — curiosity variant (A/B test)
('relationship.level_achieved', 'COMFORT_FAMILIARITY', 'curiosity', '{
  "celebration": "Something shifted...",
  "meaning": "{name} has been thinking about you differently. She wonders what it would be like to {tease_ref}.",
  "choices": [
    {"label": "Find out what she means", "action": "story_scene", "icon": "search"},
    {"label": "Tease her back", "action": "challenge", "icon": "sparkles"},
    {"label": "Play it cool", "action": "checkin", "icon": "cool"}
  ],
  "reward": {"type": "story_beat", "scene": "comfort_zone"}
}'::jsonb, 'curiosity'),

('relationship.level_achieved', 'GROWING_CLOSENESS', 'curiosity', '{
  "celebration": "She left you something...",
  "meaning": "{name} wrote a note she was not sure she should send. It mentions {memory_ref}.",
  "choices": [
    {"label": "Read the note", "action": "vulnerable_moment", "icon": "mail"},
    {"label": "Write her one back", "action": "shared_interest", "icon": "pen"},
    {"label": "Save it for later", "action": "deep_question", "icon": "bookmark"}
  ],
  "reward": {"type": "memory_card", "tag": "closeness"}
}'::jsonb, 'curiosity'),

-- intimacy.level_unlocked
('intimacy.level_unlocked', NULL, 'celebration', '{
  "celebration": "Trust milestone reached: **Level {level}**!",
  "meaning": "Your genuine connection unlocked something new. {name} wants to show you a side of her you have not seen.",
  "choices": [
    {"label": "See what she unlocked", "action": "view_unlock", "icon": "eye"},
    {"label": "Save this moment", "action": "save_moment", "icon": "bookmark"}
  ],
  "reward": {"type": "unlock", "feature": "deeper_content"}
}'::jsonb, 'celebration'),

-- streak milestones
('streak.milestone', NULL, 'celebration', '{
  "celebration": "{streak_days}-day streak!",
  "meaning": "{name} loves that you keep coming back. Consistency means everything to her.",
  "choices": [
    {"label": "Celebrate together", "action": "celebrate", "icon": "party"},
    {"label": "Keep the streak going", "action": "continue", "icon": "flame"}
  ],
  "reward": {"type": "bonus_points", "amount": 0}
}'::jsonb, 'celebration'),

-- engagement milestones
('engagement.milestone', NULL, 'celebration', '{
  "celebration": "{message_count} messages together!",
  "meaning": "Every word brought you closer. {name} cherishes this conversation history.",
  "choices": [
    {"label": "Relive a favorite moment", "action": "memory_recall", "icon": "rewind"},
    {"label": "Make the next 100 even better", "action": "continue", "icon": "arrow-right"}
  ],
  "reward": {"type": "memory_card", "tag": "chatty"}
}'::jsonb, 'celebration')
ON CONFLICT DO NOTHING;

COMMIT;
