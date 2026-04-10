"""
DailyAI — Inshorts-style News Card v3.1
Cards open a FULL-SCREEN detail overlay on click (not an inline dropdown).
The overlay shows: cover image, headline, bullet summary, why-it-matters,
share/save actions, and a "Read Full Article" CTA.
"""

import hashlib
import html
from urllib.parse import urlencode

from nicegui import ui

from dailyai.ui.components.theme import (
    CATEGORY_COLORS,
    COLORS,
    SENTIMENT_ICONS,
    TRUST_LABELS,
    resolve_image_url,
)
from dailyai.ui.i18n import normalize_ui_language, tr, tr_time_ago


def _clean_text(value: str) -> str:
    import re
    text = html.unescape(str(value or "")).replace("\xa0", " ")
    # Strip any remaining HTML tags (like <a> links from RSS)
    text = re.sub(r'<[^>]*>', '', text)
    return " ".join(text.split()).strip()


def _format_time_ago(iso_date: str, language: str = "en") -> str:
    return tr_time_ago(language, iso_date)


def _short_summary(article: dict, language: str = "en") -> str:
    import re
    
    # Prefer 'why_it_matters' because it's generating an engaging hook
    why = _clean_text(str(article.get("why_it_matters", "") or ""))
    if why and len(why) > 20:
        return why

    summary = _clean_text(str(article.get("summary", "") or ""))
    # Skip generic fallback summaries
    if summary and not re.match(
        r'^Reported by .+\.\s*(Tap to read|Click to read)', summary, re.IGNORECASE
    ) and len(summary) > 20:
        return summary
    
    headline = _clean_text(str(article.get("headline", "") or ""))
    source = _clean_text(str(article.get("source_name", "") or ""))
    if headline and source:
        return f"{headline}. Source: {source}."
    if headline:
        return headline
    return tr(language, "latest_ai_news_from", source=source) if source else tr(language, "tap_to_read")


def _calculate_read_time(article: dict) -> int:
    """Calculate estimated reading time in minutes based on text length."""
    text = f"{article.get('headline', '')} {article.get('summary', '')} {article.get('why_it_matters', '')}"
    words = len(text.split())
    # Average reading speed is ~238 words per minute.
    return max(1, round(words / 200))


def _build_article_link(article: dict) -> str:
    article_id = article.get('id', 'GLOBAL-en-0')
    payload = {
        'headline': article.get('headline', ''),
        'summary': _short_summary(article),
        'why_it_matters': article.get('why_it_matters', ''),
        'topic': article.get('topic', ''),
        'source_name': article.get('source_name', ''),
        'source_trust': article.get('source_trust', ''),
        'sentiment': article.get('sentiment', ''),
        'article_url': article.get('article_url', ''),
        'published_at': article.get('published_at', ''),
    }
    return f"/article/{article_id}?{urlencode(payload)}"


def _source_color(name: str) -> str:
    h = sum(ord(c) for c in str(name)) % 360
    return f"hsl({h}, 50%, 45%)"


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def _js_str(text: str) -> str:
    """Escape text for safe embedding inside JS string literals."""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def _make_bullets(raw_summary: str, headline: str = "", why: str = "", language: str = "en") -> list[str]:
    """Build informative bullet points (5 bullets, ~15-20 words each) for the detail view.
    
    Uses the raw summary field (not the fallback). When summary is empty,
    constructs bullets from headline + why_it_matters.
    """
    import re
    text = (raw_summary or "").strip()
    why = (why or "").strip()
    headline = (headline or "").strip()

    # Detect and discard generic fallback summaries
    if re.match(r'^Reported by .+\.\s*(Tap to read|Click to read)', text, re.IGNORECASE):
        text = ""
    # Detect and discard generic why_it_matters
    if why and "Stay informed" in why:
        why = ""

    bullets: list[str] = []

    if text:
        # Have actual summary — split into sentence-level bullets
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) >= 2:
            bullets = sentences[:5]
        else:
            words = text.split()
            if len(words) > 20:
                # Try splitting on semicolons/commas for compound sentences
                chunks = re.split(r'[;,]\s*', text)
                chunks = [c.strip() for c in chunks if len(c.strip()) > 10]
                if len(chunks) >= 2:
                    bullets = chunks[:5]
                else:
                    # Split long single sentence into ~3 roughly equal parts
                    third = len(words) // 3
                    bullets = [
                        ' '.join(words[:third]),
                        ' '.join(words[third:2*third]),
                        ' '.join(words[2*third:]),
                    ]
            else:
                bullets = [text]

        # Pad to 5 bullets using headline and why_it_matters
        if why and why.lower() not in text.lower() and len(bullets) < 5:
            bullets.append(why)
        if headline and headline.lower() not in text.lower() and len(bullets) < 5:
            bullets.insert(0, headline)
    else:
        # No summary at all — build bullets from headline + why
        if headline:
            bullets.append(headline)
        if why and "Stay informed" not in why:
            bullets.append(why)
            
    # Remove bullets that are just truncations/duplicates of the headline
    if headline:
        hl_lower = headline.lower()
        cleaned_bullets = []
        for b in bullets:
            b_lower = b.lower()
            # If bullet is >80% identical to the headline, consider it a duplicate
            if b_lower in hl_lower or hl_lower in b_lower:
                continue
            cleaned_bullets.append(b)
        
        bullets = cleaned_bullets
        bullets.insert(0, headline)

    if len(bullets) <= 1:
        bullets.append(tr(language, "bullet_fallback"))

    # Enforce total ~120 word limit & punctuation
    final: list[str] = []
    word_count = 0
    for b in bullets:
        b_words = b.split()
        if word_count + len(b_words) > 120 and final:
            break
        if b and b[-1] not in '.!?':
            b += '.'
        final.append(b)
        word_count += len(b_words)

    return final if final else [headline or tr(language, "tap_for_details")]


def _card_uid(article: dict) -> str:
    identity = article.get("headline", "") + article.get("source_name", "")
    return "c" + hashlib.md5(identity.encode()).hexdigest()[:8]


def _inject_detail_overlay_once(language: str = "en"):
    """Inject the single, reusable full-screen detail overlay + JS into the page.
    Called once per NiceGUI client (page load). The JS-side window.__dailyaiDetailInit
    guard handles browser-level deduplication within a single tab/session.
    Do NOT add a Python module-level guard here — module-level state persists across
    all page loads (all clients), which would prevent any client after the first from
    ever receiving the run_javascript call and having openDetail defined.
    """
    # <style> in add_head_html is fine — CSS applies even from dynamically injected style tags.
    # <script> in add_head_html is NOT executed (HTML5 spec: scripts injected via innerHTML/
    # insertAdjacentHTML are silently discarded). Use run_javascript instead for JS.
    ui.add_head_html('''
    <style>
    /* Shimmer loading animation for brief fetch */
    .brief-loading { padding: 8px 0; }
    .shimmer-line {
        height: 14px; border-radius: 7px; margin-bottom: 12px;
        background: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.10) 50%, rgba(255,255,255,0.04) 75%);
        background-size: 200% 100%;
        animation: shimmer 1.4s ease-in-out infinite;
    }
    .shimmer-line:nth-child(1) { width: 95%; }
    .shimmer-line:nth-child(2) { width: 88%; }
    .shimmer-line:nth-child(3) { width: 78%; }
    .shimmer-line:nth-child(4) { width: 65%; }
    .shimmer-line:nth-child(5) { width: 72%; }
    @keyframes shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
    .brief-error {
        color: var(--text-secondary, #999); font-size: 13px;
        padding: 8px 0; font-style: italic;
    }
    </style>
    ''')

    lang = normalize_ui_language(language)
    link_copied_text = _js_str(tr(lang, 'link_copied'))
    back_to_feed_text = tr(lang, 'back_to_feed')
    key_takeaways_text = tr(lang, 'key_takeaways')
    why_it_matters_text = tr(lang, 'why_it_matters')
    read_full_article_text = tr(lang, 'read_full_article')

    overlay_script = '''
    if (!window.__dailyaiDetailInit) {
        window.__dailyaiDetailInit = true;

        /* ── Brief cache ── */
        window.__articleBriefs = window.__articleBriefs || {};

        /* ── Saved state cache (persists across routes) ── */
        window._savedArticles = window._savedArticles || {};
        window._savedPayloads = window._savedPayloads || {};
        try {
            window._savedArticles = JSON.parse(localStorage.getItem('dailyai_saved_articles') || '{}') || {};
        } catch (e) {
            window._savedArticles = {};
        }
        try {
            window._savedPayloads = JSON.parse(localStorage.getItem('dailyai_saved_payloads') || '{}') || {};
        } catch (e) {
            window._savedPayloads = {};
        }

        window._persistSavedState = function() {
            localStorage.setItem('dailyai_saved_articles', JSON.stringify(window._savedArticles || {}));
            localStorage.setItem('dailyai_saved_payloads', JSON.stringify(window._savedPayloads || {}));
            window.dispatchEvent(new CustomEvent('dailyai:saved-updated', {
                detail: { count: Object.keys(window._savedPayloads || {}).length },
            }));
        };

        /* ── Share helper ── */
        window.shareArticle = function(headline, url) {
            if (navigator.share) {
                navigator.share({ title: headline, url: url });
            } else {
                navigator.clipboard.writeText(url).then(function() {
                    if (window.Quasar) Quasar.Notify.create({
                        message: '__LINK_COPIED__', position: 'bottom', timeout: 1500,
                        classes: 'text-body1'
                    });
                });
            }
        };

        /* ── Save toggle ── */
        window.toggleSaveArticle = function(uid) {
            window._savedArticles[uid] = !window._savedArticles[uid];
            var articleData = window.__articleData && window.__articleData[uid];
            if (window._savedArticles[uid]) {
                if (articleData) {
                    window._savedPayloads[uid] = Object.assign({ uid: uid, savedAt: Date.now() }, articleData);
                }
            } else {
                delete window._savedArticles[uid];
                delete window._savedPayloads[uid];
            }

            var cardBtn = document.getElementById('card-save-' + uid);
            if (cardBtn) {
                cardBtn.classList.toggle('saved', window._savedArticles[uid]);
                cardBtn.setAttribute('aria-pressed', window._savedArticles[uid] ? 'true' : 'false');
            }
            var detailBtn = document.getElementById('detail-save-btn');
            if (detailBtn) {
                var dicon = detailBtn.querySelector('.material-icons');
                if (dicon) dicon.textContent = window._savedArticles[uid] ? 'bookmark' : 'bookmark_border';
                detailBtn.classList.toggle('saved', window._savedArticles[uid]);
                detailBtn.setAttribute('aria-pressed', window._savedArticles[uid] ? 'true' : 'false');
            }

            window._persistSavedState();
        };

        /* ── Render bullet points from text ── */
        window._renderBullets = function(bulletsEl, bulletTexts) {
            bulletsEl.innerHTML = '';
            bulletTexts.forEach(function(b) {
                var div = document.createElement('div');
                div.className = 'detail-bullet';
                div.innerHTML = '<div class="detail-bullet-dot"></div><div class="detail-bullet-text">' + b + '</div>';
                bulletsEl.appendChild(div);
            });
        };

        /* ── Show loading shimmer ── */
        window._showBriefLoading = function(bulletsEl) {
            bulletsEl.innerHTML = '<div class="brief-loading">' +
                '<div class="shimmer-line"></div>' +
                '<div class="shimmer-line"></div>' +
                '<div class="shimmer-line"></div>' +
                '<div class="shimmer-line"></div>' +
                '<div class="shimmer-line"></div>' +
                '</div>';
        };

        /* ── Parse brief text into bullet array ── */
        window._parseBriefBullets = function(briefText) {
            if (!briefText) return [];
            var lines = briefText.split(/\\n/).map(function(l) { return l.trim(); }).filter(Boolean);
            var bullets = [];

            /* Pass 1: only lines that start with an explicit bullet marker (•, -, *, 1.) */
            lines.forEach(function(line) {
                if (/^[•\-\*]/.test(line) || /^\d+[\.\)\:]/.test(line)) {
                    var cleaned = line.replace(/^[•\-\*\s]+/, '').replace(/^\d+[\.\)\:]\s*/, '').trim();
                    if (cleaned.length > 8) bullets.push(cleaned);
                }
            });

            /* Pass 2: no explicit markers — treat every non-empty line as a bullet (LLM used plain lines) */
            if (bullets.length < 2) {
                bullets = lines.filter(function(l) { return l.length > 8; });
            }

            /* Pass 3: single blob of text — split by sentences (no lookbehind for compatibility) */
            if (bullets.length < 2) {
                var sentences = briefText.replace(/([.!?])\\s+/g, '$1\\n').split('\\n');
                bullets = sentences.map(function(s) { return s.trim(); }).filter(function(s) { return s.length > 8; });
            }

            return bullets.slice(0, 5);
        };

        /* ── Fetch LLM brief on demand ── */
        window._fetchBrief = function(uid, data) {
            var bulletsEl = document.getElementById('detailBullets');
            var whyBox = document.getElementById('detailWhyBox');
            if (!bulletsEl) return;

            /* Check cache first */
            if (window.__articleBriefs[uid]) {
                var cached = window.__articleBriefs[uid];
                window._renderBullets(bulletsEl, cached.bullets);
                if (cached.why) {
                    whyBox.style.display = 'block';
                    document.getElementById('detailWhyText').textContent = cached.why;
                }
                return;
            }

            /* Show shimmer immediately to improve perceived load speed */
            window._showBriefLoading(bulletsEl);

            /* Change 1: AbortController with 22s timeout to prevent infinite shimmer */
            var controller = new AbortController();
            var fetchTimeout = setTimeout(function() { controller.abort(); }, 22000);

            /* Call the Brief API */
            fetch('/api/articles/brief', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                signal: controller.signal,
                body: JSON.stringify({
                    title: data.headline || '',
                    source: data.source || '',
                    link: data.articleUrl || data.link || '',
                    summary: data.rawSummary || '',
                    why_it_matters: data.rawWhy || '',
                    topic: data.topic || 'general',
                    language: data.language || 'en'
                })
            })
            .then(async function(r) {
                clearTimeout(fetchTimeout);

                /* Verify overlay is still open for this uid */
                var overlay = document.getElementById('detailOverlay');
                if (!overlay || overlay.dataset.uid !== uid) return;

                const reader = r.body.getReader();
                const decoder = new TextDecoder('utf-8');
                let briefText = '';

                try {
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;
                        
                        var currentOverlay = document.getElementById('detailOverlay');
                        if (!currentOverlay || currentOverlay.dataset.uid !== uid) break;
                        
                        briefText += decoder.decode(value, {stream: true});
                        if (briefText.trim().length > 10) {
                            var parsedChunk = window._parseBriefBullets(briefText);
                            if (parsedChunk.length > 0) {
                                window._renderBullets(bulletsEl, parsedChunk);
                            }
                        }
                    }
                } catch (e) {
                    console.error("Stream read error:", e);
                }

                briefText = briefText.trim();
                
                if (!briefText || briefText.includes('No additional details available yet.')) {
                    /* LLM returned nothing useful — show original bullets */
                    window._renderBullets(bulletsEl, data.bullets);
                    return;
                }

                /* Change 3: Skip re-parsing if brief echoes back the raw summary or why text */
                if (briefText === (data.rawSummary || '').trim() || briefText === (data.rawWhy || '').trim()) {
                    window._renderBullets(bulletsEl, data.bullets);
                    return;
                }

                var parsed = window._parseBriefBullets(briefText);
                if (parsed.length < 1) {
                    window._renderBullets(bulletsEl, data.bullets);
                    return;
                }

                /* Cache and render */
                window.__articleBriefs[uid] = { bullets: parsed, why: '' };
                window._renderBullets(bulletsEl, parsed);

                /* If we got a good brief, hide the generic WHY box (the brief covers it) */
                if (parsed.length >= 3) {
                    whyBox.style.display = 'none';
                }
            })
            .catch(function(err) {
                clearTimeout(fetchTimeout);
                console.warn('Brief fetch failed:', err);
                /* Show original bullets on error (including timeout abort) */
                var overlay = document.getElementById('detailOverlay');
                if (overlay && overlay.dataset.uid === uid) {
                    window._renderBullets(bulletsEl, data.bullets);
                }
            });
        };

        /* ── Open detail overlay ── */
        window.openDetail = function(uid) {
            var data = window.__articleData && window.__articleData[uid];
            if (!data) return;

            var overlay = document.getElementById('detailOverlay');
            if (!overlay) return;

            // Set up fallback image if the primary fails
            var coverEl = document.getElementById('detailCover');
            coverEl.onerror = function() {
                this.onerror = null;
                this.src = "data:image/svg+xml;charset=UTF-8,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22400%22 height=%22200%22 viewBox=%220 0 400 200%22%3E%3Crect width=%22400%22 height=%22200%22 fill=%22%232a2a2a%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 fill=%22%23666%22 font-family=%22sans-serif%22 font-size=%2214%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22%3EArticle Image%3C/text%3E%3C/svg%3E";
            };

            // Populate static content
            coverEl.src = data.coverImg;
            coverEl.alt = data.topic;
            document.getElementById('detailTopicPill').textContent = data.topic;
            document.getElementById('detailHeadline').textContent = data.headline;
            document.getElementById('detailSourceDot').style.background = data.sourceColor;
            document.getElementById('detailSourceDot').textContent = data.sourceInitial;
            document.getElementById('detailSourceName').textContent = data.source;
            document.getElementById('detailSourceTime').textContent = data.published;

            // Badges
            document.getElementById('detailBadges').innerHTML = data.badgesHtml;

            // Show original bullets first (instant), then fetch better ones
            var bulletsEl = document.getElementById('detailBullets');
            window._renderBullets(bulletsEl, data.bullets);

            // Why it matters (initial)
            var whyBox = document.getElementById('detailWhyBox');
            if (data.why) {
                whyBox.style.display = 'block';
                document.getElementById('detailWhyText').textContent = data.why;
            } else {
                whyBox.style.display = 'none';
            }

            // CTA link
            document.getElementById('detailCTA').href = data.articleUrl || data.link;

            // Share/Save
            document.getElementById('detailShareBtn').onclick = function() {
                shareArticle(data.headline, data.articleUrl || data.link);
            };
            document.getElementById('detail-save-btn').onclick = function() {
                toggleSaveArticle(uid);
            };
            var isSaved = window._savedArticles[uid] || false;
            var saveIcon = document.querySelector('#detail-save-btn .material-icons');
            if (saveIcon) saveIcon.textContent = isSaved ? 'bookmark' : 'bookmark_border';
            document.getElementById('detail-save-btn').classList.toggle('saved', isSaved);
            document.getElementById('detail-save-btn').setAttribute('aria-pressed', isSaved ? 'true' : 'false');

            // Store uid and open
            overlay.dataset.uid = uid;
            overlay.classList.add('open');
            document.body.style.overflow = 'hidden';
            overlay.scrollTop = 0;

            // Fetch LLM-powered brief (always — replaces static bullets with AI summary)
            window._fetchBrief(uid, data);
        };

        /* ── Close detail overlay ── */
        window.closeDetail = function() {
            var overlay = document.getElementById('detailOverlay');
            if (overlay) overlay.classList.remove('open');
            document.body.style.overflow = '';
        };

        /* ── Keyboard: Escape closes ── */
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') closeDetail();
        });

        /* ── Event delegation for all detail overlay buttons ── */
        document.addEventListener('click', function(e) {
            var backBtn = e.target.closest('#detailBackBtn');
            if (backBtn) { e.stopPropagation(); closeDetail(); return; }
        });

        /* ── Swipe down to close on mobile ── */
        var _touchStartY = 0;
        document.addEventListener('touchstart', function(e) {
            var overlay = document.getElementById('detailOverlay');
            if (overlay && overlay.classList.contains('open') && overlay.scrollTop <= 0) {
                _touchStartY = e.touches[0].clientY;
            }
        }, { passive: true });
        document.addEventListener('touchend', function(e) {
            var overlay = document.getElementById('detailOverlay');
            if (overlay && overlay.classList.contains('open')) {
                var dy = e.changedTouches[0].clientY - _touchStartY;
                if (dy > 120) closeDetail();
            }
        }, { passive: true });

        /* ── Article data store ── */
        window.__articleData = window.__articleData || {};

        /* ═══════════════════════════════════════════════════════════
         *  DailyAI Analytics Tracker
         *  Tracks: impressions, clicks, holds, detail_open, read_time,
         *  scroll_depth, share, save, external_click
         * ═══════════════════════════════════════════════════════════ */
        (function() {
            /* Session & sync code management */
            if (!sessionStorage.getItem('dailyai_session_id')) {
                sessionStorage.setItem('dailyai_session_id',
                    'ses_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 8));
            }
            window.__dailyaiSessionId = sessionStorage.getItem('dailyai_session_id');
            window.__dailyaiSyncCode = localStorage.getItem('dailyai_sync_code') || '';

            /* Event buffer — flushed every 30s or on page unload */
            window.__analyticsBuffer = [];
            window.__analyticsFlushTimer = null;

            window._trackEvent = function(eventType, articleId, topic, category, value, metadata) {
                window.__analyticsBuffer.push({
                    event_type: eventType,
                    article_id: articleId || '',
                    topic: topic || '',
                    category: category || '',
                    value: value || 0,
                    metadata: metadata || {}
                });
                /* Auto-flush if buffer gets large */
                if (window.__analyticsBuffer.length >= 50) {
                    window._flushAnalytics();
                }
            };

            window._flushAnalytics = function() {
                if (!window.__analyticsBuffer.length) return;
                var events = window.__analyticsBuffer.splice(0);
                var payload = {
                    session_id: window.__dailyaiSessionId,
                    sync_code: window.__dailyaiSyncCode,
                    events: events
                };
                try {
                    if (navigator.sendBeacon) {
                        navigator.sendBeacon('/api/analytics/events',
                            new Blob([JSON.stringify(payload)], { type: 'application/json' }));
                    } else {
                        fetch('/api/analytics/events', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(payload),
                            keepalive: true
                        }).catch(function() {});
                    }
                } catch(e) { /* silent */ }
            };

            /* Flush every 30 seconds */
            if (window.__analyticsFlushTimer) clearInterval(window.__analyticsFlushTimer);
            window.__analyticsFlushTimer = setInterval(window._flushAnalytics, 30000);

            /* Flush on page unload */
            window.addEventListener('beforeunload', function() {
                window._flushAnalytics();
            });
            document.addEventListener('visibilitychange', function() {
                if (document.visibilityState === 'hidden') window._flushAnalytics();
            });

            /* ── Card impression tracking (IntersectionObserver) ── */
            window.__impressedCards = window.__impressedCards || {};
            if (window.IntersectionObserver) {
                window.__cardObserver = new IntersectionObserver(function(entries) {
                    entries.forEach(function(entry) {
                        if (entry.isIntersecting) {
                            var card = entry.target;
                            var uid = card.dataset.cardUid;
                            if (uid && !window.__impressedCards[uid]) {
                                window.__impressedCards[uid] = true;
                                var data = window.__articleData && window.__articleData[uid];
                                if (data) {
                                    window._trackEvent('impression', uid, data.topic, data.category, 0);
                                }
                            }
                        }
                    });
                }, { threshold: 0.5 });
            }

            /* ── Hold timer (long press = 3s+) ── */
            window.__holdTimers = {};
            document.addEventListener('pointerdown', function(e) {
                var card = e.target.closest('.news-card-premium');
                if (!card || !card.dataset.cardUid) return;
                var uid = card.dataset.cardUid;
                window.__holdTimers[uid] = { start: Date.now() };
            });
            document.addEventListener('pointerup', function(e) {
                var card = e.target.closest('.news-card-premium');
                if (!card || !card.dataset.cardUid) return;
                var uid = card.dataset.cardUid;
                if (window.__holdTimers[uid]) {
                    var dur = (Date.now() - window.__holdTimers[uid].start) / 1000;
                    if (dur >= 3) {
                        var data = window.__articleData && window.__articleData[uid];
                        window._trackEvent('hold', uid, data ? data.topic : '', data ? data.category : '', dur);
                    }
                    delete window.__holdTimers[uid];
                }
            });

            /* ── Detail read time & scroll depth tracking ── */
            window.__detailOpenTime = 0;
            window.__detailMaxScroll = 0;
            window.__detailUid = '';

            /* Hook into openDetail */
            var _origOpenDetail = window.openDetail;
            window.openDetail = function(uid) {
                /* Track click event */
                var data = window.__articleData && window.__articleData[uid];
                if (data) {
                    window._trackEvent('click', uid, data.topic, data.category, 0);
                    window._trackEvent('detail_open', uid, data.topic, data.category, 0);
                }
                window.__detailOpenTime = Date.now();
                window.__detailMaxScroll = 0;
                window.__detailUid = uid;
                _origOpenDetail(uid);
            };

            /* Track scroll depth in overlay */
            var overlay = document.getElementById('detailOverlay');
            if (overlay) {
                overlay.addEventListener('scroll', function() {
                    if (!overlay.classList.contains('open')) return;
                    var scrollPct = Math.round((overlay.scrollTop / Math.max(1, overlay.scrollHeight - overlay.clientHeight)) * 100);
                    if (scrollPct > window.__detailMaxScroll) {
                        window.__detailMaxScroll = scrollPct;
                    }
                });
            }

            /* Hook into closeDetail */
            var _origCloseDetail = window.closeDetail;
            window.closeDetail = function() {
                if (window.__detailUid && window.__detailOpenTime) {
                    var readTime = (Date.now() - window.__detailOpenTime) / 1000;
                    var data = window.__articleData && window.__articleData[window.__detailUid];
                    var topic = data ? data.topic : '';
                    var cat = data ? data.category : '';
                    window._trackEvent('read_time', window.__detailUid, topic, cat, readTime);
                    if (window.__detailMaxScroll > 0) {
                        window._trackEvent('scroll_depth', window.__detailUid, topic, cat, window.__detailMaxScroll);
                    }
                }
                window.__detailOpenTime = 0;
                window.__detailMaxScroll = 0;
                window.__detailUid = '';
                _origCloseDetail();
            };

            /* ── Track external article clicks ── */
            document.addEventListener('click', function(e) {
                var cta = e.target.closest('#detailCTA');
                if (cta) {
                    var uid = document.getElementById('detailOverlay') ?
                        document.getElementById('detailOverlay').dataset.uid : '';
                    var data = window.__articleData && window.__articleData[uid];
                    if (data) {
                        window._trackEvent('external_click', uid, data.topic, data.category, 0);
                    }
                }
            });

            /* ── Track share/save through existing functions ── */
            var _origShare = window.shareArticle;
            window.shareArticle = function(headline, url) {
                var overlay = document.getElementById('detailOverlay');
                var uid = overlay ? overlay.dataset.uid : '';
                var data = window.__articleData && window.__articleData[uid];
                if (data) {
                    window._trackEvent('share', uid, data.topic, data.category, 0);
                }
                _origShare(headline, url);
            };

            var _origToggleSave = window.toggleSaveArticle;
            window.toggleSaveArticle = function(uid) {
                var wasSaved = window._savedArticles && window._savedArticles[uid];
                _origToggleSave(uid);
                var data = window.__articleData && window.__articleData[uid];
                if (data) {
                    window._trackEvent(wasSaved ? 'unsave' : 'save', uid, data.topic, data.category, 0);
                }
            };

            /* ── Sync code helper ── */
            window.setSyncCode = function(code) {
                localStorage.setItem('dailyai_sync_code', code);
                window.__dailyaiSyncCode = code;
            };
            window.getSyncCode = function() {
                return window.__dailyaiSyncCode || '';
            };
        })();
    }
    '''
    ui.run_javascript(overlay_script.replace('__LINK_COPIED__', link_copied_text))

    # Inject the single shared overlay element (hidden by default)
    ui.html(f'''
    <div class="detail-overlay" id="detailOverlay">
        <!-- Close bar -->
        <div class="detail-close-bar">
            <button class="detail-back-btn" id="detailBackBtn">
                <span class="material-icons" style="font-size:20px;">arrow_back</span>
                {back_to_feed_text}
            </button>
            <div class="detail-actions-row">
                <button class="action-btn" id="detailShareBtn" title="Share">
                    <span class="material-icons" style="font-size:20px;">share</span>
                </button>
                <button class="action-btn" id="detail-save-btn" title="Save">
                    <span class="material-icons" style="font-size:20px;">bookmark_border</span>
                </button>
            </div>
        </div>

        <!-- Cover image -->
        <div class="detail-cover-wrap">
            <img class="detail-cover" id="detailCover" src="" alt="" />
            <div class="detail-cover-gradient"></div>
            <div class="detail-topic-pill" id="detailTopicPill"></div>
        </div>

        <!-- Body -->
        <div class="detail-body">
            <div class="detail-badges" id="detailBadges"></div>
            <h1 class="detail-headline" id="detailHeadline"></h1>

            <div class="detail-source-row">
                <div class="source-dot" id="detailSourceDot"></div>
                <span class="detail-source-name" id="detailSourceName"></span>
                <span class="detail-source-time" id="detailSourceTime"></span>
            </div>

            <div class="detail-section-label">
                <span class="material-icons" style="font-size:14px;">summarize</span>
                {key_takeaways_text}
            </div>
            <div id="detailBullets"></div>

            <div class="detail-why-box" id="detailWhyBox" style="display:none;">
                <div class="detail-why-label">
                    <span class="material-icons" style="font-size:14px;">lightbulb</span>
                    {why_it_matters_text}
                </div>
                <div class="detail-why-text" id="detailWhyText"></div>
            </div>

            <a class="detail-cta" id="detailCTA" href="#" target="_blank" rel="noopener">
                {read_full_article_text}
                <span class="material-icons" style="font-size:18px;">open_in_new</span>
            </a>
        </div>
    </div>
    ''')


def news_card(article: dict, index: int = 0, position_chip: str = "", language: str = "en"):
    """Render a compact feed card. Clicking opens a full-screen detail view."""
    cat = article.get("category", "general")
    color = CATEGORY_COLORS.get(cat, COLORS["cat_general"])
    sentiment = article.get("sentiment", "neutral")
    sent_icon = SENTIMENT_ICONS.get(sentiment, "trending_flat")
    sent_color = COLORS.get(sentiment, COLORS["text_secondary"])

    trust_tier = article.get("source_trust", "low")
    trust_label, trust_icon = TRUST_LABELS.get(trust_tier, TRUST_LABELS["low"])
    trust_color = COLORS.get(f"trust_{trust_tier}", COLORS["trust_low"])

    importance = article.get("importance", 5)
    published = _format_time_ago(article.get("published_at", ""), language=language)
    source = _clean_text(str(article.get("source_name", "Unknown") or "Unknown"))
    topic_label = article.get("topic", cat).upper()
    headline = _clean_text(str(article.get("headline", "") or ""))
    summary_text = _short_summary(article, language=language)
    why = _clean_text(str(article.get("why_it_matters", "") or ""))

    image_key = topic_label if cat == "general" else cat
    # Use the original article image if available, else use a category cover
    # Providing the headline as the seed ensures variety within the same category
    raw_img = article.get("image_url") or article.get("image")
    cover_img = resolve_image_url(raw_img, topic=image_key, seed=article.get("id", headline))
    link = _build_article_link(article)
    article_url = article.get("article_url", link)
    uid = _card_uid(article)
    # Use RAW summary for bullets (not the fallback text)
    raw_summary = _clean_text(str(article.get("summary", "") or ""))
    bullets = _make_bullets(raw_summary, headline=headline, why=why, language=language)

    # If why is already in bullets, don't duplicate it in the WHY IT MATTERS box
    why_in_bullets = any(why.lower() in b.lower() for b in bullets) if why else False
    # Always show WHY IT MATTERS if we have meaningful content
    clean_why = why if (not why_in_bullets and why and len(why) > 15) else ""
    delay = min(index * 0.07, 0.5)

    # Build badges HTML for detail view
    badges_html = ""
    if importance >= 7:
        fire = "🔥" if importance >= 9 else "⭐"
        badges_html += f'<span class="badge-importance">{fire} {importance}/10</span>'
    trust_bg = f"{trust_color}18"
    badges_html += f'''<span class="badge-trust" style="background:{trust_bg};color:{trust_color};">
        <span class="material-icons" style="font-size:12px;">{trust_icon}</span>{trust_label}
    </span>'''
    sent_bg = f"{sent_color}18"
    badges_html += f'''<span class="badge-sentiment" style="background:{sent_bg};color:{sent_color};">
        <span class="material-icons" style="font-size:12px;">{sent_icon}</span>{sentiment.capitalize()}
    </span>'''

    # Register article data for JS (include raw fields for on-demand brief fetching)
    bullets_js = "[" + ",".join(f"'{_js_str(_esc(b))}'" for b in bullets) + "]"
    # clean_why already computed above (line 591)
    ui.run_javascript(f'''
        window.__articleData = window.__articleData || {{}};
        window.__articleData['{uid}'] = {{
            headline: '{_js_str(headline)}',
            summary: '{_js_str(summary_text)}',
            rawSummary: '{_js_str(raw_summary)}',
            rawWhy: '{_js_str(why)}',
            why: '{_js_str(clean_why)}',
            topic: '{_js_str(topic_label)}',
            source: '{_js_str(source)}',
            sourceInitial: '{_js_str(source[:1].upper())}',
            sourceColor: '{_source_color(source)}',
            published: '{_js_str(published)}',
            coverImg: '{cover_img}',
            link: '{_js_str(link)}',
            articleUrl: '{_js_str(article_url)}',
            language: '{_js_str(str(article.get("language", "en") or "en"))}',
            topic: '{_js_str(str(article.get("topic", "general")))}',
            category: '{_js_str(str(article.get("category", "general")))}',
            bullets: {bullets_js},
            badgesHtml: '{_js_str(badges_html)}',
        }};
    ''')

    # ── Render the compact card ──
    read_time = _calculate_read_time(article)
    base_classes = 'news-card-premium w-full p-0 mb-4 card-animate'
    card_classes = f'{base_classes} news-card-trending' if importance >= 8 else base_classes
    
    card_el = ui.card().classes(card_classes)
    card_el._props['data-card-uid'] = uid
    with card_el.style(f'animation-delay: {delay}s;'):

        # Category accent line
        ui.html(f'<div class="card-cat-accent" style="background: {color};"></div>')

        # Image area
        with ui.element('div').classes('card-image-area cursor-pointer').on('click', lambda: ui.run_javascript(f"openDetail('{uid}')")):
            svg_fallback = "data:image/svg+xml;charset=UTF-8,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22400%22 height=%22200%22 viewBox=%220 0 400 200%22%3E%3Crect width=%22400%22 height=%22200%22 fill=%22%232a2a2a%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 fill=%22%23666%22 font-family=%22sans-serif%22 font-size=%2214%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22%3EArticle Image%3C/text%3E%3C/svg%3E"
            ui.html(f'''
                <img src="{cover_img}" alt="{_esc(topic_label)}"
                     loading="lazy"
                     onerror="this.onerror=null; this.src='{svg_fallback}';" />
                <div class="card-image-gradient"></div>
                <div class="card-topic-tag">{_esc(topic_label)}</div>
                 {f'<div class="card-position-chip">{_esc(position_chip)}</div>' if position_chip else ''}
            ''')

        # Card body (compact preview — no inline expand)
        with ui.element('div').classes('card-body-area cursor-pointer').on('click', lambda: ui.run_javascript(f"openDetail('{uid}')")):
            # Badges
            with ui.element('div').classes('card-badges'):
                if importance >= 7:
                    fire = "🔥" if importance >= 9 else "⭐"
                    ui.html(f'<span class="badge-importance">{fire} {importance}/10</span>')
                ui.html(f'''<span class="badge-trust" style="background:{trust_bg};color:{trust_color};">
                    <span class="material-icons" style="font-size:12px;">{trust_icon}</span>{trust_label}
                </span>''')
                ui.html(f'''<span class="badge-sentiment" style="background:{sent_bg};color:{sent_color};">
                    <span class="material-icons" style="font-size:12px;">{sent_icon}</span>{sentiment.capitalize()}
                </span>''')

            # Headline
            ui.html(f'<div class="card-headline-text">{_esc(headline)}</div>')

            # Summary preview (2-line clamp)
            ui.label(summary_text).classes('card-summary-text')

        # Action bar: publisher + bookmark
        publisher_name = source or "DailyAI"
        publisher_initial = publisher_name[0].upper() if publisher_name else "D"
        bg_hsl = f"hsl({sum(ord(c) for c in publisher_name) * 137 % 360}, 70%, 55%)"
        
        ui.html(f'''<div class="card-action-bar">
            <div class="card-source-info">
                <div class="source-avatar blink-dot" aria-hidden="true" style="background: {bg_hsl};">{publisher_initial}</div>
                <span class="source-name-text">{publisher_name}</span>
            </div>
            <div class="card-actions">
                <span class="card-read-time" style="font-size: 11px; color: rgba(255,255,255,0.6); display: flex; align-items: center; gap: 4px;">
                    <span class="material-icons" style="font-size: 13px;">schedule</span>
                    {read_time} min read
                </span>
            </div>
        </div>''')

        ui.run_javascript(f'''
            (function() {{
                /* Register with IntersectionObserver for impression tracking */
                var cards = document.querySelectorAll('[data-card-uid="{uid}"]');
                cards.forEach(function(card) {{
                    if (window.__cardObserver) window.__cardObserver.observe(card);
                }});
            }})();
        ''')


def skeleton_card():
    """Skeleton loading placeholder card."""
    with ui.card().classes('skeleton-card w-full p-0 mb-5'):
        ui.html('<div class="skeleton-image"></div>')
        with ui.element('div').style('padding: 18px;'):
            ui.html('<div class="skeleton-line w-75" style="height: 18px; margin-bottom: 12px;"></div>')
            ui.html('<div class="skeleton-line w-50" style="height: 18px; margin-bottom: 16px;"></div>')
            ui.html('<div class="skeleton-line" style="margin-bottom: 8px;"></div>')
            ui.html('<div class="skeleton-line w-75"></div>')
            ui.html('<div class="skeleton-line w-30" style="margin-top: 16px; height: 10px;"></div>')
