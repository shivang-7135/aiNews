"""DailyAI section pages for Saved and Settings."""

from urllib.parse import urlencode

from nicegui import ui

from dailyai.config import COUNTRIES, UI_LANGUAGES
from dailyai.ui.components.nav_bar import nav_bar
from dailyai.ui.components.theme import COUNTRY_FLAGS, GLOBAL_CSS
from dailyai.ui.i18n import normalize_ui_language, tr


def _js_str(text: str) -> str:
    return (
        str(text or "")
        .replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
    )


def _current_lang_country() -> tuple[str, str]:
    params = ui.context.client.request.query_params
    language = normalize_ui_language(str(params.get("language", "en")))
    country = str(params.get("country", "GLOBAL")).upper()
    if country not in COUNTRIES:
        country = "GLOBAL"
    return language, country


def _setup_page(title: str) -> None:
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>")
    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1.0,'
        ' maximum-scale=1.0, user-scalable=no, viewport-fit=cover">'
    )
    ui.page_title(f"DailyAI — {title}")
    ui.dark_mode(True)


@ui.page("/saved")
async def saved_page():
    language, country = _current_lang_country()
    _setup_page(tr(language, "saved_title"))

    ui.add_head_html(
        """
    <style>
        .saved-shell { width: min(100%, 980px); margin: 0 auto; padding: 12px 12px 108px; }
        .saved-title { font-size: 24px; font-weight: 700; color: var(--text-primary); margin-bottom: 2px; }
        .saved-subtitle { font-size: 12px; color: var(--text-muted); margin-bottom: 12px; }
        .saved-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 14px;
        }
        .saved-news-card { cursor: pointer; }
        .saved-empty {
            color: var(--text-secondary);
            background: var(--bg-card);
            border: 0.5px solid var(--border-ghost);
            border-radius: 16px;
            padding: 18px;
            text-align: center;
            font-size: 14px;
        }
        .saved-count {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
            font-weight: 700;
            color: var(--text-secondary);
            background: var(--bg-elevated);
            border-radius: 999px;
            padding: 5px 10px;
            margin-bottom: 10px;
        }
        .saved-remove-btn {
            width: 24px;
            height: 24px;
            border: none;
            background: transparent;
            color: #fff;
            display: grid;
            place-items: center;
            cursor: pointer;
        }
    </style>
    """
    )

    with ui.column().classes("saved-shell"):
        ui.label(tr(language, "saved_title")).classes("saved-title")
        ui.label(tr(language, "saved_subtitle")).classes("saved-subtitle")
        ui.html(f'<div id="savedCount" class="saved-count">{tr(language, "saved_count", count=0)}</div>')
        ui.html('<div id="savedFeed" class="saved-grid"></div>')
        ui.html(f'<div id="savedEmpty" class="saved-empty" style="display:none;">{tr(language, "saved_empty")}</div>')

    js = """
        (function() {
            function esc(value) {
                return String(value || '')
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#39;');
            }

            function getSavedFlags() {
                try { return JSON.parse(localStorage.getItem('dailyai_saved_articles') || '{}') || {}; }
                catch (e) { return {}; }
            }

            function getSavedPayloads() {
                try { return JSON.parse(localStorage.getItem('dailyai_saved_payloads') || '{}') || {}; }
                catch (e) { return {}; }
            }

            function persist(flags, payloads) {
                localStorage.setItem('dailyai_saved_articles', JSON.stringify(flags));
                localStorage.setItem('dailyai_saved_payloads', JSON.stringify(payloads));
            }

            window.renderSavedFeed = function() {
                var payloads = getSavedPayloads();
                var items = Object.keys(payloads)
                    .map(function(uid) { return payloads[uid]; })
                    .filter(Boolean)
                    .sort(function(a, b) { return (b.savedAt || 0) - (a.savedAt || 0); });

                var feed = document.getElementById('savedFeed');
                var empty = document.getElementById('savedEmpty');
                var count = document.getElementById('savedCount');
                if (!feed || !empty || !count) return;

                count.textContent = '__SAVED_COUNT_TEMPLATE__'.replace('{count}', String(items.length));

                if (!items.length) {
                    feed.innerHTML = '';
                    empty.style.display = 'block';
                    return;
                }

                empty.style.display = 'none';
                feed.innerHTML = items.map(function(it) {
                    var uid = esc(it.uid || '');
                    var headline = esc(it.headline || 'Untitled');
                    var summary = esc(it.summary || '__SUMMARY_FALLBACK__');
                    var cover = esc(it.coverImg || '/static/topic-covers/general.png');
                    var source = esc(it.source || 'pagesandbits');
                    var link = esc(it.articleUrl || it.link || '/');
                    return `
                        <article class="news-card-premium saved-news-card" onclick="window.location.href='${link}'">
                            <div class="card-image-area">
                                <img src="${cover}" alt="${headline}" loading="lazy" />
                            </div>
                            <div class="card-body-area">
                                <div class="card-headline-text">${headline}</div>
                                <div class="card-summary-text">${summary}</div>
                            </div>
                            <div class="card-action-bar">
                                <div class="card-source-info">
                                    <div class="source-avatar" aria-hidden="true"></div>
                                    <span class="source-name-text">${source}</span>
                                </div>
                                <div class="card-actions">
                                    <button class="saved-remove-btn" aria-label="__REMOVE_LABEL__"
                                        onclick="event.stopPropagation(); window.removeSavedArticle('${uid}')">
                                        <svg class="bookmark-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                                            <path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z" fill="rgba(255,255,255,0.28)" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
                                        </svg>
                                    </button>
                                </div>
                            </div>
                        </article>
                    `;
                }).join('');
            };

            window.removeSavedArticle = function(uid) {
                var flags = getSavedFlags();
                var payloads = getSavedPayloads();
                delete flags[uid];
                delete payloads[uid];
                persist(flags, payloads);
                window.dispatchEvent(new CustomEvent('dailyai:saved-updated', {
                    detail: { count: Object.keys(payloads).length },
                }));
                window.renderSavedFeed();
            };

            window.addEventListener('dailyai:saved-updated', function() {
                window.renderSavedFeed();
            });

            window.renderSavedFeed();
        })();
    """
    js = js.replace("__SAVED_COUNT_TEMPLATE__", _js_str(tr(language, "saved_count", count="{count}")))
    js = js.replace("__SUMMARY_FALLBACK__", _js_str(tr(language, "read_full_article")))
    js = js.replace("__REMOVE_LABEL__", _js_str(tr(language, "remove_saved")))
    ui.run_javascript(js)

    nav_bar(active_route="/saved", language=language, country=country)


@ui.page("/settings")
async def settings_page():
    language, country = _current_lang_country()
    _setup_page(tr(language, "settings_title"))

    language_options = (
        {"en": "Englisch", "de": "Deutsch"}
        if language == "de"
        else {"en": "English", "de": "German"}
    )

    with ui.column().classes("w-full max-w-xl mx-auto min-h-screen pb-28 px-4 pt-4"):
        ui.label(tr(language, "settings_title")).style(
            "font-size: 24px; font-weight: 700; color: var(--text-primary);"
        )
        ui.label(tr(language, "settings_subtitle")).style(
            "font-size: 12px; color: var(--text-muted); margin-bottom: 14px;"
        )

        country_select = ui.select(
            options={code: f"{COUNTRY_FLAGS.get(code, '🏳️')} {name}" for code, name in COUNTRIES.items()},
            value=country,
            label=tr(language, "region"),
        ).classes("w-full").props("dark outlined")

        language_select = ui.select(
            options=language_options,
            value=language,
            label=tr(language, "language"),
        ).classes("w-full").props("dark outlined")

        async def _apply_to_feed():
            selected_country = str(country_select.value or "GLOBAL").upper()
            selected_language = normalize_ui_language(str(language_select.value or "en"))
            if selected_country not in COUNTRIES:
                selected_country = "GLOBAL"
            ui.navigate.to(f'/?{urlencode({"country": selected_country, "language": selected_language})}')

        ui.button(tr(language, "apply_to_feed"), on_click=_apply_to_feed).classes("w-full").props("color=accent")
        ui.button(
            tr(language, "back_to_discover"),
            on_click=lambda: ui.navigate.to(f'/?{urlencode({"country": country, "language": language})}'),
        ).classes("w-full").props("outline")

    nav_bar(active_route="/settings", language=language, country=country)


@ui.page("/trending")
async def trending_page():
    language, country = _current_lang_country()
    _setup_page("Trending")
    with ui.column().classes("w-full max-w-3xl mx-auto min-h-screen pb-24 sm:pb-28 px-4 pt-6"):
        ui.label("Trending").classes("text-3xl font-black mb-3")
        ui.label(tr(language, "coming_soon_discover")).classes("text-secondary mb-6")
        ui.button(
            tr(language, "go_discover"),
            on_click=lambda: ui.navigate.to(f'/?{urlencode({"country": country, "language": language})}'),
        ).props("color=accent icon=home")
    nav_bar(active_route="/trending", language=language, country=country)


@ui.page("/profile")
async def profile_page():
    language, country = _current_lang_country()
    _setup_page("Profile")
    with ui.column().classes("w-full max-w-3xl mx-auto min-h-screen pb-24 sm:pb-28 px-4 pt-6"):
        ui.label("Profile").classes("text-3xl font-black mb-3")
        ui.label(tr(language, "coming_soon_profile")).classes("text-secondary mb-6")
        ui.button(
            tr(language, "go_discover"),
            on_click=lambda: ui.navigate.to(f'/?{urlencode({"country": country, "language": language})}'),
        ).props("color=accent icon=home")
    nav_bar(active_route="/profile", language=language, country=country)
