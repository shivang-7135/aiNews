-- DailyAI Supabase Bootstrap Schema
-- Apply this in Supabase SQL Editor before running migration.

CREATE TABLE IF NOT EXISTS public.articles (
    id BIGSERIAL PRIMARY KEY,
    store_key TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT DEFAULT '',
    why_it_matters TEXT DEFAULT '',
    category TEXT DEFAULT 'general',
    topic TEXT DEFAULT 'general',
    importance INTEGER DEFAULT 5,
    source TEXT DEFAULT '',
    source_trust TEXT DEFAULT 'low',
    sentiment TEXT DEFAULT 'neutral',
    story_thread TEXT DEFAULT '',
    link TEXT DEFAULT '',
    published TEXT DEFAULT '',
    fetched_at TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_articles_store_key_title
ON public.articles (store_key, title);

CREATE INDEX IF NOT EXISTS idx_articles_store_key
ON public.articles (store_key);

CREATE INDEX IF NOT EXISTS idx_articles_importance
ON public.articles (importance DESC);

CREATE INDEX IF NOT EXISTS idx_articles_topic
ON public.articles (topic);

CREATE TABLE IF NOT EXISTS public.profiles (
    sync_code TEXT PRIMARY KEY,
    preferred_topics JSONB DEFAULT '[]'::jsonb,
    country TEXT DEFAULT 'GLOBAL',
    language TEXT DEFAULT 'en',
    signals JSONB DEFAULT '{}'::jsonb,
    bookmarks JSONB DEFAULT '[]'::jsonb,
    analytics JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.subscribers (
    id BIGSERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    topics JSONB DEFAULT '[]'::jsonb,
    country TEXT DEFAULT 'GLOBAL',
    language TEXT DEFAULT 'en',
    subscribed_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_subscribers_email
ON public.subscribers (email);

CREATE TABLE IF NOT EXISTS public.api_keys (
    key_hash TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    tier TEXT DEFAULT 'free',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    requests_today INTEGER DEFAULT 0,
    last_request_date TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS public.metadata (
    key TEXT PRIMARY KEY,
    value TEXT DEFAULT ''
);
