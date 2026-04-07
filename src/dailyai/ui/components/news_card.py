"""
DailyAI — Inshorts-style News Card v3.1
Cards open a FULL-SCREEN detail overlay on click (not an inline dropdown).
The overlay shows: cover image, headline, bullet summary, why-it-matters,
share/save actions, and a "Read Full Article" CTA.
"""

import hashlib
from urllib.parse import urlencode

from nicegui import ui

from dailyai.ui.components.theme import (
    CATEGORY_COLORS,
    COLORS,
    SENTIMENT_ICONS,
    TRUST_LABELS,
    get_category_image,
)


def _format_time_ago(iso_date: str) -> str:
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
            return f"{mins}m ago" if mins > 0 else "Just now"
        if hours < 24:
            return f"{hours}h ago"
        return f"{hours // 24}d ago"
    except Exception:
        return ""


def _short_summary(article: dict) -> str:
    import re
    summary = str(article.get("summary", "") or "").strip()
    # Skip generic fallback summaries
    if summary and not re.match(
        r'^Reported by .+\.\s*(Tap to read|Click to read)', summary, re.IGNORECASE
    ):
        return summary
    why = str(article.get("why_it_matters", "") or "").strip()
    # Skip generic why_it_matters too
    if why and "Stay informed" not in why:
        return why
    headline = str(article.get("headline", "") or "").strip()
    source = str(article.get("source_name", "") or "Unknown source").strip()
    if headline:
        return f"{headline}. Reported by {source}."
    return f"Reported by {source}. Tap to read the full story."


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


def _make_bullets(raw_summary: str, headline: str = "", why: str = "") -> list[str]:
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
        if why:
            bullets.append(why)
        if not bullets:
            bullets = ["Tap to read the full story for more details on this topic."]

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

    return final if final else [headline or "Tap to read the full story for more details on this topic."]


def _card_uid(article: dict) -> str:
    identity = article.get("headline", "") + article.get("source_name", "")
    return "c" + hashlib.md5(identity.encode()).hexdigest()[:8]


def _inject_detail_overlay_once():
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

    ui.run_javascript('''
    if (!window.__dailyaiDetailInit) {
        window.__dailyaiDetailInit = true;

        /* ── Brief cache ── */
        window.__articleBriefs = window.__articleBriefs || {};

        /* ── Share helper ── */
        window.shareArticle = function(headline, url) {
            if (navigator.share) {
                navigator.share({ title: headline, url: url });
            } else {
                navigator.clipboard.writeText(url).then(function() {
                    if (window.Quasar) Quasar.Notify.create({
                        message: 'Link copied!', position: 'bottom', timeout: 1500,
                        classes: 'text-body1'
                    });
                });
            }
        };

        /* ── Save toggle ── */
        window._savedArticles = window._savedArticles || {};
        window.toggleSaveArticle = function(uid) {
            window._savedArticles[uid] = !window._savedArticles[uid];
            var cardBtn = document.getElementById('card-save-' + uid);
            if (cardBtn) {
                var icon = cardBtn.querySelector('.material-icons');
                if (icon) icon.textContent = window._savedArticles[uid] ? 'bookmark' : 'bookmark_border';
                cardBtn.classList.toggle('saved', window._savedArticles[uid]);
            }
            var detailBtn = document.getElementById('detail-save-btn');
            if (detailBtn) {
                var dicon = detailBtn.querySelector('.material-icons');
                if (dicon) dicon.textContent = window._savedArticles[uid] ? 'bookmark' : 'bookmark_border';
                detailBtn.classList.toggle('saved', window._savedArticles[uid]);
            }
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

            /* Change 2: Delay shimmer by 300ms — initial bullets stay visible for fast responses */
            var shimmerTimeout = setTimeout(function() {
                window._showBriefLoading(bulletsEl);
            }, 300);

            /* Change 1: AbortController with 10s timeout to prevent infinite shimmer */
            var controller = new AbortController();
            var fetchTimeout = setTimeout(function() { controller.abort(); }, 10000);

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
                    language: 'en'
                })
            })
            .then(function(r) { return r.json(); })
            .then(function(json) {
                clearTimeout(shimmerTimeout);
                clearTimeout(fetchTimeout);

                /* Verify overlay is still open for this uid */
                var overlay = document.getElementById('detailOverlay');
                if (!overlay || overlay.dataset.uid !== uid) return;

                var briefText = (json.brief || '').trim();
                if (!briefText || briefText === 'No additional details available yet.') {
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
                clearTimeout(shimmerTimeout);
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

            // Populate static content
            document.getElementById('detailCover').src = data.coverImg;
            document.getElementById('detailCover').alt = data.topic;
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
    }
    ''')

    # Inject the single shared overlay element (hidden by default)
    ui.html('''
    <div class="detail-overlay" id="detailOverlay">
        <!-- Close bar -->
        <div class="detail-close-bar">
            <button class="detail-back-btn" id="detailBackBtn">
                <span class="material-icons" style="font-size:20px;">arrow_back</span>
                Back
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
                Key Takeaways
            </div>
            <div id="detailBullets"></div>

            <div class="detail-why-box" id="detailWhyBox" style="display:none;">
                <div class="detail-why-label">
                    <span class="material-icons" style="font-size:14px;">lightbulb</span>
                    Why It Matters
                </div>
                <div class="detail-why-text" id="detailWhyText"></div>
            </div>

            <a class="detail-cta" id="detailCTA" href="#" target="_blank" rel="noopener">
                Read Full Article
                <span class="material-icons" style="font-size:18px;">open_in_new</span>
            </a>
        </div>
    </div>
    ''')


def news_card(article: dict, index: int = 0):
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
    published = _format_time_ago(article.get("published_at", ""))
    source = article.get("source_name", "Unknown")
    topic_label = article.get("topic", cat).upper()
    headline = article.get("headline", "")
    summary_text = _short_summary(article)
    why = article.get("why_it_matters", "")

    image_key = topic_label if cat == "general" else cat
    cover_img = get_category_image(image_key, article.get("id", headline))
    link = _build_article_link(article)
    article_url = article.get("article_url", link)
    uid = _card_uid(article)
    # Use RAW summary for bullets (not the fallback text)
    raw_summary = str(article.get("summary", "") or "").strip()
    bullets = _make_bullets(raw_summary, headline=headline, why=why)

    # If why is already in bullets, don't duplicate it in the WHY IT MATTERS box
    why_in_bullets = any(why.lower() in b.lower() for b in bullets) if why else False
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
    clean_why = why if (not why_in_bullets and "Stay informed" not in why) else ""
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
            bullets: {bullets_js},
            badgesHtml: '{_js_str(badges_html)}',
        }};
    ''')

    # ── Render the compact card ──
    with ui.card().classes('news-card-premium w-full p-0 mb-5 card-animate').style(
        f'animation-delay: {delay}s;'
    ).on('click', lambda: ui.run_javascript(f"openDetail('{uid}')")):

        # Category accent line
        ui.html(f'<div class="card-cat-accent" style="background: {color};"></div>')

        # Image area
        with ui.element('div').classes('card-image-area'):
            ui.html(f'''
                <img src="{cover_img}" alt="{_esc(topic_label)}"
                     loading="lazy"
                     onerror="this.style.display='none'; this.parentElement.style.background='linear-gradient(135deg, {color}22, var(--bg-card))';" />
                <div class="card-image-gradient"></div>
                <div class="card-topic-tag">{_esc(topic_label)}</div>
            ''')

        # Card body (compact preview — no inline expand)
        with ui.element('div').classes('card-body-area'):
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

        # Action bar: source info + Share / Save
        share_headline_js = _js_str(headline)
        article_url_js = _js_str(article_url)

        ui.html(f'''<div class="card-action-bar">
            <div class="card-source-info">
                <div class="source-dot" style="background:{_source_color(source)};">
                    {_esc(source[:1].upper())}
                </div>
                <span class="source-name-text">{_esc(source)}</span>
                <span class="card-time-text">{_esc(published)}</span>
            </div>
            <div class="card-actions">
                <button class="action-btn" title="Share"
                        onclick="event.stopPropagation(); shareArticle('{share_headline_js}', '{article_url_js}')">
                    <span class="material-icons" style="font-size:20px;">share</span>
                </button>
                <button class="action-btn" id="card-save-{uid}" title="Save"
                        onclick="event.stopPropagation(); toggleSaveArticle('{uid}')">
                    <span class="material-icons" style="font-size:20px;">bookmark_border</span>
                </button>
            </div>
        </div>''')


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
