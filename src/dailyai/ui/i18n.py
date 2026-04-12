"""UI localization helpers for DailyAI."""

from __future__ import annotations

from typing import Any


def normalize_ui_language(language: str | None) -> str:
    lang = (language or "en").strip().lower()
    return "de" if lang == "de" else "en"


_UI_TEXTS: dict[str, dict[str, str]] = {
    "en": {
        # ── Navigation & Core ─────────────────────────────────────
        "discover": "Discover",
        "saved": "Saved",
        "settings": "Settings",
        "region": "Region",
        "language": "Language",
        "sort_by": "Sort by",
        "relevance": "Relevance",
        "latest": "Latest",
        "refresh_news": "Refresh News",
        "ai_news_intelligence": "AI News Intelligence",
        "boot_loader": "Curating your AI intelligence...",
        "trust_signal": "AI-curated from 50+ trusted sources • Updated hourly",
        # ── Notifications ─────────────────────────────────────────
        "region_notify": "Region: {flag} {country}",
        "language_notify": "Language: {language}",
        "refreshing_news": "Refreshing news...",
        # ── Feed states ───────────────────────────────────────────
        "loading_more": "Loading more stories...",
        "load_more": "Load More",
        "loaded_progress": "{loaded} of {total} loaded",
        "empty_wait": "News is being curated by our AI...",
        "empty_warmup": "The server is warming up. Please refresh in a moment.",
        "failed_feed": "Failed to load feed: {error}",
        "failed_more": "Failed to load more stories: {error}",
        # ── Detail overlay ────────────────────────────────────────
        "link_copied": "Link copied!",
        "back_to_feed": "Back to Feed",
        "key_takeaways": "Key Takeaways",
        "why_it_matters": "Why It Matters",
        "read_full_article": "Read Full Article",
        # ── Saved page ────────────────────────────────────────────
        "saved_title": "Saved",
        "saved_subtitle": "Your bookmarked stories, synced in this browser.",
        "saved_empty": "No saved stories yet. Tap the bookmark on any card to save it here.",
        "saved_count": "{count} saved",
        "remove_saved": "Remove saved article",
        # ── Settings page ─────────────────────────────────────────
        "settings_title": "Settings",
        "settings_subtitle": "Customize your feed and apply instantly.",
        "apply_to_feed": "Apply to Discover Feed",
        "back_to_discover": "Back to Discover",
        "coming_soon_discover": "This section is coming soon. Use Discover for now.",
        "coming_soon_profile": "Profile management is coming soon.",
        "go_discover": "Go to Discover",
        # ── Topics ────────────────────────────────────────────────
        "topic_for_you": "For You",
        "topic_top_stories": "🔥 Top Stories",
        "topic_ai_models": "🤖 AI Models",
        "topic_business": "💼 Business",
        "topic_research": "🔬 Research",
        "topic_tools": "🛠 Tools",
        "topic_regulation": "⚖️ Regulation",
        "topic_funding": "💰 Funding",
        # ── Time ago ──────────────────────────────────────────────
        "just_now": "Just now",
        "minutes_ago": "{m}m ago",
        "hours_ago": "{h}h ago",
        "days_ago": "{d}d ago",
        # ── Card / bullet fallbacks ───────────────────────────────
        "bullet_fallback": "Our AI models are experiencing high traffic right now. Please tap 'Read Original' to view the full story on the publisher's website.",
        "tap_to_read": "Tap to read the full story.",
        "tap_for_details": "Tap to read the full story for more details on this topic.",
        "latest_ai_news_from": "Latest AI news from {source}.",
        # ── Sidebar footer ────────────────────────────────────────
        "powered_by": "Powered by AI · Built with ❤️",
        "version_label": "v3.0 · DailyAI",
        "impressum": "Impressum",
        "datenschutz": "Privacy Policy",
        "agb": "Terms",
        "api_docs": "API Docs",
        # ── Sync code ────────────────────────────────────────────
        "your_sync_code": "Your Sync Code",
        "sync_code_info": "Use this code to sync your preferences across devices.",
        "sync_code_copied": "Sync code copied!",
        "enter_sync_code": "Enter sync code...",
        "link_device": "Link Device",
        "device_linked": "Device linked successfully!",
        # ── Admin ─────────────────────────────────────────────────
        "admin_title": "Admin Dashboard",
        "admin_rss_feeds": "RSS Feed Management",
        "admin_cache_health": "Cache Health",
        "admin_analytics": "Analytics Overview",
        "admin_save": "Save Changes",
        "admin_saved": "Changes saved!",
        "admin_password": "Admin Password",
        "admin_login": "Login",
        "admin_invalid_password": "Invalid password",
        # ── Region badge ──────────────────────────────────────────
        "showing_global": "Showing global results",
        # ── Onboarding ────────────────────────────────────────────
        "onboarding_welcome_title": "Welcome to DailyAI ✨",
        "onboarding_welcome_text": "Your personalized, vibrant daily feed for AI news. Swipe, read, and stay ahead without the noise.",
        "onboarding_swipe_title": "Bite-Sized Summaries",
        "onboarding_swipe_text": "Scroll through beautiful cards containing just the facts. Tap any card to read the full summary.",
        "onboarding_sync_title": "Your Sync Code",
        "onboarding_sync_text": "A unique Sync Code was just generated for you! Use it in the sidebar to sync your saved reading and preferences across devices.",
        "onboarding_start_button": "Let's Go!",
        "onboarding_next": "Next",
        # ── Persona ───────────────────────────────────────────────
        "your_ai_persona": "👤 Your AI Persona",
        "persona_description": "This is how we understand your interests. You can manually edit this instruction to fine-tune your bespoke briefings.",
        "persona_textarea": "Persona",
        "save_persona": "Save Persona",
        "persona_saved": "Persona saved! Refresh feeds to apply.",
        "persona_error": "Error saving persona: {error}",
        # ── Leaderboard ───────────────────────────────────────────
        "daily_leaderboard": "Top Readers Today",
        "leaderboard_desc": "Rankings across the dailyAI network.",
        # ── Engagement badges ─────────────────────────────────────
        "engagement_title": "Engagement",
        "engagement_desc": "Track your daily reading streak and complete today's goal.",
        "engagement_streak_fmt": "{days} day streak",
        "engagement_progress_fmt": "Today {done}/{goal}",
        "engagement_goal_complete": "Daily goal complete! Keep the streak alive 🔥",
    },
    "de": {
        # ── Navigation & Core ─────────────────────────────────────
        "discover": "Entdecken",
        "saved": "Gespeichert",
        "settings": "Einstellungen",
        "region": "Region",
        "language": "Sprache",
        "sort_by": "Sortierung",
        "relevance": "Relevanz",
        "latest": "Neueste",
        "refresh_news": "News aktualisieren",
        "ai_news_intelligence": "KI-News Intelligence",
        "boot_loader": "KI-News werden für dich kuratiert...",
        "trust_signal": "KI-kuratiert aus 50+ vertrauenswürdigen Quellen • Stündlich aktualisiert",
        # ── Notifications ─────────────────────────────────────────
        "region_notify": "Region: {flag} {country}",
        "language_notify": "Sprache: {language}",
        "refreshing_news": "News werden aktualisiert...",
        # ── Feed states ───────────────────────────────────────────
        "loading_more": "Weitere Meldungen werden geladen...",
        "load_more": "Mehr laden",
        "loaded_progress": "{loaded} von {total} geladen",
        "empty_wait": "News werden gerade von unserer KI kuratiert...",
        "empty_warmup": "Der Server startet gerade. Bitte in einem Moment erneut laden.",
        "failed_feed": "Feed konnte nicht geladen werden: {error}",
        "failed_more": "Weitere Meldungen konnten nicht geladen werden: {error}",
        # ── Detail overlay ────────────────────────────────────────
        "link_copied": "Link kopiert!",
        "back_to_feed": "Zurück zum Feed",
        "key_takeaways": "Kurzüberblick",
        "why_it_matters": "Warum das wichtig ist",
        "read_full_article": "Vollständigen Artikel lesen",
        # ── Saved page ────────────────────────────────────────────
        "saved_title": "Gespeichert",
        "saved_subtitle": "Deine gemerkten Artikel in diesem Browser.",
        "saved_empty": "Noch keine gespeicherten Artikel. Tippe auf das Lesezeichen in einer Karte.",
        "saved_count": "{count} gespeichert",
        "remove_saved": "Gespeicherten Artikel entfernen",
        # ── Settings page ─────────────────────────────────────────
        "settings_title": "Einstellungen",
        "settings_subtitle": "Passe deinen Feed an und übernimm sofort.",
        "apply_to_feed": "Auf Entdecken-Feed anwenden",
        "back_to_discover": "Zurück zu Entdecken",
        "coming_soon_discover": "Dieser Bereich kommt bald. Nutze vorerst Entdecken.",
        "coming_soon_profile": "Profilverwaltung kommt bald.",
        "go_discover": "Zu Entdecken",
        # ── Topics ────────────────────────────────────────────────
        "topic_for_you": "Für dich",
        "topic_top_stories": "🔥 Top-News",
        "topic_ai_models": "🤖 KI-Modelle",
        "topic_business": "💼 Wirtschaft",
        "topic_research": "🔬 Forschung",
        "topic_tools": "🛠 Tools",
        "topic_regulation": "⚖️ Regulierung",
        "topic_funding": "💰 Finanzierung",
        # ── Time ago ──────────────────────────────────────────────
        "just_now": "Gerade eben",
        "minutes_ago": "vor {m} Min.",
        "hours_ago": "vor {h} Std.",
        "days_ago": "vor {d} T.",
        # ── Card / bullet fallbacks ───────────────────────────────
        "bullet_fallback": "Unsere KI-Modelle verzeichnen gerade hohes Aufkommen. Bitte tippe auf 'Original lesen', um den vollständigen Artikel auf der Verlagsseite zu lesen.",
        "tap_to_read": "Tippe, um die ganze Story zu lesen.",
        "tap_for_details": "Tippe, um die ganze Story zu diesem Thema zu lesen.",
        "latest_ai_news_from": "Aktuelle KI-News von {source}.",
        # ── Sidebar footer ────────────────────────────────────────
        "powered_by": "Powered by KI · Mit ❤️ gebaut",
        "version_label": "v3.0 · DailyAI",
        "impressum": "Impressum",
        "datenschutz": "Datenschutz",
        "agb": "AGB",
        "api_docs": "API-Dokumentation",
        # ── Sync code ────────────────────────────────────────────
        "your_sync_code": "Dein Sync-Code",
        "sync_code_info": "Verwende diesen Code, um deine Einstellungen geräteübergreifend zu synchronisieren.",
        "sync_code_copied": "Sync-Code kopiert!",
        "enter_sync_code": "Sync-Code eingeben...",
        "link_device": "Gerät verknüpfen",
        "device_linked": "Gerät erfolgreich verknüpft!",
        # ── Admin ─────────────────────────────────────────────────
        "admin_title": "Admin-Dashboard",
        "admin_rss_feeds": "RSS-Feed-Verwaltung",
        "admin_cache_health": "Cache-Status",
        "admin_analytics": "Analyse-Übersicht",
        "admin_save": "Änderungen speichern",
        "admin_saved": "Änderungen gespeichert!",
        "admin_password": "Admin-Passwort",
        "admin_login": "Anmelden",
        "admin_invalid_password": "Ungültiges Passwort",
        # ── Region badge ──────────────────────────────────────────
        "showing_global": "Globale Ergebnisse werden angezeigt",
        # ── Onboarding ────────────────────────────────────────────
        "onboarding_welcome_title": "Willkommen bei DailyAI ✨",
        "onboarding_welcome_text": "Dein personalisierter, lebendiger Feed für KI-News. Kurz, präzise, ohne Lärm.",
        "onboarding_swipe_title": "Bite-Sized Summaries",
        "onboarding_swipe_text": "Scrolle durch hübsche Karten mit Fakten. Tippe sie an, um die ganze Zusammenfassung zu lesen.",
        "onboarding_sync_title": "Dein Synchronisierungscode",
        "onboarding_sync_text": "Ein Sync-Code wurde für Dich generiert! Nutze ihn in der Sidebar, um Lesezeichen und Einstellungen auf allen Geräten zu synchronisieren.",
        "onboarding_start_button": "Los geht's!",
        "onboarding_next": "Weiter",
        # ── Persona ───────────────────────────────────────────────
        "your_ai_persona": "👤 Deine KI-Persona",
        "persona_description": "So verstehen wir deine Interessen. Du kannst diese Anweisung manuell bearbeiten, um deine maßgeschneiderten Briefings zu verfeinern.",
        "persona_textarea": "Persona",
        "save_persona": "Persona speichern",
        "persona_saved": "Persona gespeichert! Aktualisiere den Feed, um die Änderungen anzuwenden.",
        "persona_error": "Fehler beim Speichern der Persona: {error}",
        # ── Leaderboard ───────────────────────────────────────────
        "daily_leaderboard": "Top-Leser heute",
        "leaderboard_desc": "Rangliste im gesamten dailyAI-Netzwerk.",
        # ── Engagement badges ─────────────────────────────────────
        "engagement_title": "Engagement",
        "engagement_desc": "Verfolge deine tägliche Leseserie und erfülle dein Tagesziel.",
        "engagement_streak_fmt": "{days} Tage Serie",
        "engagement_progress_fmt": "Heute {done}/{goal}",
        "engagement_goal_complete": "Tagesziel erreicht! Halte die Serie am Leben 🔥",
    },
}


def tr(lang_code: str | None, key: str, **kwargs: Any) -> str:
    lang = normalize_ui_language(lang_code)
    template = _UI_TEXTS.get(lang, _UI_TEXTS["en"]).get(key, _UI_TEXTS["en"].get(key, key))
    return template.format(**kwargs) if kwargs else template


def tr_time_ago(lang_code: str | None, iso_date: str) -> str:
    """Format an ISO date string as a localized 'time ago' label."""
    if not iso_date:
        return ""
    try:
        from datetime import UTC, datetime

        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        now = datetime.now(UTC)
        diff = now - dt
        hours = int(diff.total_seconds() / 3600)
        if hours < 1:
            mins = int(diff.total_seconds() / 60)
            return tr(lang_code, "just_now") if mins <= 0 else tr(lang_code, "minutes_ago", m=mins)
        if hours < 24:
            return tr(lang_code, "hours_ago", h=hours)
        return tr(lang_code, "days_ago", d=hours // 24)
    except Exception:
        return ""
