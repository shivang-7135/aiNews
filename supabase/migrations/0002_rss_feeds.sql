-- Migration 0002: RSS feed configuration table

CREATE TABLE IF NOT EXISTS public.rss_feeds (
    id BIGSERIAL PRIMARY KEY,
    country_code TEXT NOT NULL,
    feed_key TEXT NOT NULL,
    query TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(country_code, feed_key)
);

CREATE INDEX IF NOT EXISTS idx_rss_feeds_country_active
ON public.rss_feeds (country_code, is_active);
