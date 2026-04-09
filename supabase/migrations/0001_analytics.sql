-- Migration 0001: Analytics Tables

-- Raw analytics tracking events
CREATE TABLE IF NOT EXISTS public.user_events (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    sync_code TEXT DEFAULT '',
    event_type TEXT NOT NULL,
    article_id TEXT DEFAULT '',
    topic TEXT DEFAULT 'general',
    category TEXT DEFAULT 'general',
    value REAL DEFAULT 0.0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for querying events by session quickly
CREATE INDEX IF NOT EXISTS idx_user_events_session
ON public.user_events (session_id);

CREATE INDEX IF NOT EXISTS idx_user_events_sync_code
ON public.user_events (sync_code);

-- Aggregated topic preferences
CREATE TABLE IF NOT EXISTS public.user_topic_scores (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    sync_code TEXT DEFAULT '',
    topic TEXT NOT NULL,
    score REAL DEFAULT 0.0,
    event_count INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(session_id, sync_code, topic)
);

-- Index for retrieving scores directly for feed generation
CREATE INDEX IF NOT EXISTS idx_user_topic_scores_lookup
ON public.user_topic_scores (session_id, sync_code);
