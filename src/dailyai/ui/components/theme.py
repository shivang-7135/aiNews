"""
DailyAI — Vibrant Obsidian Design System v3
Dark base + warm vibrant accents for an inviting, happy, professional experience.
Inshorts-style mobile snap-scroll cards, expandable summaries, share/save actions.
"""

from nicegui import ui

from dailyai.ui.i18n import tr


def resolve_image_url(url: str | None, topic: str | None = None, seed: str | None = None) -> str:
    """Return a valid image URL. Falls back to a category image if invalid or missing."""
    if url and url.startswith("http"):
        return url
    return get_category_image(topic, seed)


def inject_boot_loader(language: str):
    boot_text = tr(language, "boot_loader")
    # Inject via <head> <template> + importNode so the browser parses SVG in
    # the correct namespace. NiceGUI's ui.html() mangles SVG elements.
    ui.add_head_html(f"""
    <template id="bootLoaderTpl">
        <div class="boot-loader" id="bootLoader">
            <div class="newspaper-loader">
                <svg viewBox="0 0 140 110" xmlns="http://www.w3.org/2000/svg" class="newspaper-svg">
                    <!-- Open newspaper base (left page) -->
                    <rect x="5" y="15" width="60" height="80" rx="2" ry="2"
                          fill="#1a1d26" stroke="rgba(255,184,0,0.25)" stroke-width="0.8"/>
                    <!-- Left page masthead -->
                    <rect x="12" y="22" width="28" height="4" rx="1.5" fill="rgba(255,184,0,0.6)"/>
                    <rect x="12" y="29" width="18" height="1.5" rx="0.7" fill="rgba(255,255,255,0.12)"/>
                    <line x1="12" y1="33" x2="58" y2="33" stroke="rgba(255,255,255,0.06)" stroke-width="0.4"/>
                    <!-- Left page text lines -->
                    <rect x="12" y="37" width="22" height="2" rx="1" fill="rgba(255,255,255,0.10)"/>
                    <rect x="12" y="41" width="20" height="2" rx="1" fill="rgba(255,255,255,0.07)"/>
                    <rect x="12" y="45" width="22" height="2" rx="1" fill="rgba(255,255,255,0.09)"/>
                    <rect x="12" y="49" width="18" height="2" rx="1" fill="rgba(255,255,255,0.06)"/>
                    <rect x="12" y="53" width="22" height="2" rx="1" fill="rgba(255,255,255,0.08)"/>
                    <rect x="12" y="57" width="15" height="2" rx="1" fill="rgba(255,255,255,0.05)"/>
                    <rect x="12" y="61" width="22" height="2" rx="1" fill="rgba(255,255,255,0.07)"/>
                    <rect x="12" y="65" width="20" height="2" rx="1" fill="rgba(255,255,255,0.06)"/>
                    <rect x="12" y="69" width="22" height="2" rx="1" fill="rgba(255,255,255,0.08)"/>
                    <rect x="37" y="37" width="20" height="2" rx="1" fill="rgba(255,255,255,0.07)"/>
                    <rect x="37" y="41" width="18" height="2" rx="1" fill="rgba(255,255,255,0.05)"/>
                    <rect x="37" y="45" width="20" height="2" rx="1" fill="rgba(255,255,255,0.06)"/>
                    <rect x="37" y="49" width="16" height="2" rx="1" fill="rgba(255,255,255,0.04)"/>
                    <rect x="37" y="53" width="20" height="2" rx="1" fill="rgba(255,255,255,0.06)"/>
                    <line x1="34" y1="36" x2="34" y2="72" stroke="rgba(255,255,255,0.04)" stroke-width="0.3"/>
                    <!-- Spine/fold line -->
                    <line x1="65" y1="15" x2="65" y2="95" stroke="rgba(255,184,0,0.15)" stroke-width="1"/>
                    <!-- Right page (static base under turning pages) -->
                    <rect x="65" y="15" width="60" height="80" rx="2" ry="2"
                          fill="#1e2130" stroke="rgba(255,184,0,0.2)" stroke-width="0.6"/>
                    <!-- Right page text lines (visible when pages are flipped away) -->
                    <rect x="72" y="24" width="22" height="2" rx="1" fill="rgba(255,255,255,0.06)"/>
                    <rect x="72" y="28" width="18" height="2" rx="1" fill="rgba(255,255,255,0.04)"/>
                    <rect x="72" y="32" width="22" height="2" rx="1" fill="rgba(255,255,255,0.05)"/>
                    <rect x="72" y="36" width="16" height="2" rx="1" fill="rgba(255,255,255,0.04)"/>
                </svg>
                <!-- Turning pages (HTML divs with 3D CSS transforms for real page flip) -->
                <div class="turning-page tp-3">
                    <div class="tp-line" style="width:70%; top:18%"></div>
                    <div class="tp-line" style="width:55%; top:28%"></div>
                    <div class="tp-line" style="width:65%; top:38%"></div>
                    <div class="tp-line" style="width:45%; top:48%"></div>
                    <div class="tp-line" style="width:60%; top:58%"></div>
                    <div class="tp-line" style="width:50%; top:68%"></div>
                </div>
                <div class="turning-page tp-2">
                    <div class="tp-line" style="width:60%; top:18%"></div>
                    <div class="tp-line" style="width:70%; top:28%"></div>
                    <div class="tp-line" style="width:50%; top:38%"></div>
                    <div class="tp-line" style="width:65%; top:48%"></div>
                    <div class="tp-line" style="width:55%; top:58%"></div>
                    <div class="tp-line" style="width:40%; top:68%"></div>
                </div>
                <div class="turning-page tp-1">
                    <div class="tp-line" style="width:65%; top:18%"></div>
                    <div class="tp-line" style="width:50%; top:28%"></div>
                    <div class="tp-line" style="width:70%; top:38%"></div>
                    <div class="tp-line" style="width:55%; top:48%"></div>
                    <div class="tp-line" style="width:45%; top:58%"></div>
                    <div class="tp-line" style="width:60%; top:68%"></div>
                </div>
            </div>
            <div class="boot-text">{boot_text}</div>
        </div>
    </template>
    <script>
    (function() {{
        function injectBootLoader() {{
            if (document.getElementById('bootLoader')) return;
            var tpl = document.getElementById('bootLoaderTpl');
            if (tpl) {{
                var clone = document.importNode(tpl.content, true);
                document.body.appendChild(clone);
            }}
        }}
        if (document.body) {{
            injectBootLoader();
        }} else {{
            document.addEventListener('DOMContentLoaded', injectBootLoader);
        }}
    }})();
    </script>
    """)


# ── Color Palette ───────────────────────────────────────────────────

COLORS = {
    # Warm accent spectrum
    "accent": "#FFB800",  # Golden amber — primary
    "accent_alt": "#FF6B6B",  # Coral — secondary
    "accent_teal": "#4ECDC4",  # Teal — tertiary
    "accent_glow": "rgba(255, 184, 0, 0.15)",
    # Backgrounds (dark with warmth)
    "bg_primary": "#0d0f14",
    "bg_card": "#151820",
    "bg_elevated": "#1c1f28",
    "bg_highest": "#232733",
    "bg_glass": "rgba(21, 24, 32, 0.88)",
    # Text
    "text_primary": "#f5f3f0",
    "text_secondary": "#b0aeb5",
    "text_muted": "#6c6b72",
    # Borders
    "border": "#35353d",
    "border_ghost": "rgba(255, 255, 255, 0.06)",
    # Semantic
    "success": "#10b981",
    "warning": "#f59e0b",
    "error": "#ff6e84",
    "info": "#3b82f6",
    # Category colors (vibrant & warm)
    "cat_breakthrough": "#4ECDC4",
    "cat_product": "#6366f1",
    "cat_regulation": "#FF6B6B",
    "cat_funding": "#10b981",
    "cat_research": "#a855f7",
    "cat_industry": "#3b82f6",
    "cat_general": "#FFB800",
    # Sentiment
    "bullish": "#10b981",
    "bearish": "#ff6e84",
    "neutral": "#6c6b72",
    # Trust
    "trust_high": "#10b981",
    "trust_medium": "#f59e0b",
    "trust_low": "#6c6b72",
}

CATEGORY_COLORS = {
    "breakthrough": COLORS["cat_breakthrough"],
    "product": COLORS["cat_product"],
    "regulation": COLORS["cat_regulation"],
    "funding": COLORS["cat_funding"],
    "research": COLORS["cat_research"],
    "industry": COLORS["cat_industry"],
    "general": COLORS["cat_general"],
}

# Map categories to cover images
CATEGORY_IMAGES = {
    "breakthrough": "/static/topic-covers/breakthrough-1.jpg",
    "product": "/static/topic-covers/product-1.jpg",
    "regulation": "/static/topic-covers/regulation-1.jpg",
    "funding": "/static/topic-covers/funding-1.jpg",
    "research": "/static/topic-covers/research-1.jpg",
    "industry": "/static/topic-covers/industry-1.jpg",
    "general": "/static/topic-covers/general-1.jpg",
}

CATEGORY_FALLBACK_IMAGES = {
    "breakthrough": "/static/topic-covers/ai-models.png",
    "product": "/static/topic-covers/tools.png",
    "regulation": "/static/topic-covers/regulation.png",
    "funding": "/static/topic-covers/funding.png",
    "research": "/static/topic-covers/research.png",
    "industry": "/static/topic-covers/business.png",
    "general": "/static/topic-covers/general.png",
}

CATEGORY_IMAGE_SETS = {
    "top_stories": [
        "/static/topic-covers/general-1.jpg",
        "/static/topic-covers/general-2.jpg",
        "/static/topic-covers/top-stories.svg",
    ],
    "ai_models": [
        "/static/topic-covers/breakthrough-1.jpg",
        "/static/topic-covers/breakthrough-2.jpg",
        "/static/topic-covers/ai-models.png",
    ],
    "business": [
        "/static/topic-covers/industry-1.jpg",
        "/static/topic-covers/industry-2.jpg",
        "/static/topic-covers/business.png",
    ],
    "research": [
        "/static/topic-covers/research-1.jpg",
        "/static/topic-covers/research-2.jpg",
        "/static/topic-covers/research-3.jpg",
    ],
    "tools": [
        "/static/topic-covers/product-1.jpg",
        "/static/topic-covers/product-2.jpg",
        "/static/topic-covers/tools.png",
    ],
    "regulation": [
        "/static/topic-covers/regulation-1.jpg",
        "/static/topic-covers/regulation-2.jpg",
        "/static/topic-covers/regulation-3.jpg",
    ],
    "funding": [
        "/static/topic-covers/funding-1.jpg",
        "/static/topic-covers/funding-2.jpg",
        "/static/topic-covers/funding-3.jpg",
    ],
    "general": [
        "/static/topic-covers/general-1.jpg",
        "/static/topic-covers/general-2.jpg",
        "/static/topic-covers/general-3.jpg",
    ],
}


def _normalize_category_key(category: str) -> str:
    """Map UI and data labels to known internal category keys."""
    raw = (category or "").strip().lower()
    if not raw:
        return "general"

    if "top stories" in raw or "🔥" in raw:
        return "top_stories"
    elif "ai model" in raw or "🤖" in raw or "llm" in raw:
        return "ai_models"
    elif "business" in raw or "💼" in raw or "startup" in raw or "industry" in raw:
        return "business"
    elif (
        "research" in raw
        or "🔬" in raw
        or "robotics" in raw
        or "healthcare" in raw
        or "autonomous" in raw
    ):
        return "research"
    elif "tools" in raw or "🛠" in raw or "open_source" in raw or "product" in raw:
        return "tools"
    elif (
        "regulation" in raw
        or "⚖" in raw
        or "policy" in raw
        or "governance" in raw
        or "ai_safety" in raw
    ):
        return "regulation"
    elif "funding" in raw or "💰" in raw:
        return "funding"
    return "general"


def get_category_image(category: str | None = None, seed: str | None = None) -> str:
    """Select one of three cached cover images per category."""
    key = _normalize_category_key(category or "")
    options = CATEGORY_IMAGE_SETS.get(key, CATEGORY_IMAGE_SETS["general"])
    # hash can be negative, so we must add len(options) and modulo.
    # We use python's modulo which inherently wraps correctly, but abs() is safer.
    idx = 0 if not seed else abs(hash(seed)) % len(options)
    return options[idx]


SENTIMENT_ICONS = {
    "bullish": "trending_up",
    "bearish": "trending_down",
    "neutral": "trending_flat",
}

TRUST_LABELS = {
    "high": ("Verified", "verified"),
    "medium": ("Known", "shield"),
    "low": ("Unrated", "help_outline"),
}

COUNTRY_FLAGS = {
    "US": "🇺🇸",
    "GB": "🇬🇧",
    "DE": "🇩🇪",
    "IN": "🇮🇳",
    "GLOBAL": "🌐",
}

# ── CSS ─────────────────────────────────────────────────────────────

GLOBAL_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ========== DESIGN TOKENS ========== */
:root {
    --accent: #FFB800;
    --accent-alt: #FF6B6B;
    --accent-teal: #4ECDC4;
    --accent-glow: rgba(255, 184, 0, 0.15);
    --bg-primary: #0d0f14;
    --bg-card: #151820;
    --bg-elevated: #1c1f28;
    --bg-highest: #232733;
    --text-primary: #f5f3f0;
    --text-secondary: #c6ccd6;
    --text-muted: #8a909a;
    --border: #35353d;
    --border-ghost: rgba(255, 255, 255, 0.06);
    --font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --radius: 20px;
}

/* ========== GLOBAL RESET ========== */
body,
.nicegui-content,
.q-page, .q-card, .q-btn, .q-chip, .q-item,
.q-list, .q-field, .q-menu, .q-dialog,
.q-select, .q-tooltip, .q-drawer, .q-notification {
    font-family: var(--font) !important;
}

.q-icon, .material-icons, .material-icons-outlined,
.material-icons-round, .material-icons-sharp,
.material-symbols-outlined, .material-symbols-rounded, .material-symbols-sharp {
    font-family: 'Material Icons', 'Material Icons Outlined', 'Material Icons Round',
        'Material Icons Sharp', 'Material Symbols Outlined', 'Material Symbols Rounded',
        'Material Symbols Sharp' !important;
    font-style: normal !important; font-weight: normal !important;
    letter-spacing: normal !important; text-transform: none !important;
    white-space: nowrap !important; direction: ltr !important;
    -webkit-font-feature-settings: 'liga' !important;
    font-feature-settings: 'liga' !important;
    -webkit-font-smoothing: antialiased;
}

body {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    overflow-x: hidden;
    overscroll-behavior-y: contain;
}

/* Kill ALL Quasar/NiceGUI wrapper spacing — they inject inline min-height + padding */
.q-header, .q-footer { display: none !important; }
.q-layout, .nicegui-layout {
    min-height: 0 !important; padding: 0 !important; margin: 0 !important;
}
.q-page-container {
    padding: 0 !important; margin: 0 !important; min-height: 0 !important;
    padding-top: 0 !important; /* Kill Quasar header offset */
}
.q-page {
    padding: 0 !important; margin: 0 !important;
    min-height: 0 !important;
    padding-top: 0 !important;
}
.nicegui-content {
    padding: 0 !important; margin: 0 !important;
    gap: 0 !important;
}
.q-page-container > div { padding: 0 !important; }
#app, #app > div { min-height: 0 !important; padding-top: 0 !important; }
/* Force layout to start at viewport top — Quasar reserves header space via inline padding */
.q-layout__section--marginal { display: none !important; height: 0 !important; }
body, html {
    padding: 0 !important;
    margin: 0 !important;
    overscroll-behavior-y: contain;
}

::-webkit-scrollbar { display: none !important; width: 0 !important; height: 0 !important; }
* { scrollbar-width: none !important; -ms-overflow-style: none !important; }
.q-scrollarea__thumb, .q-scrollarea__bar { display: none !important; opacity: 0 !important; }
.ambient-orb {
    position: fixed; border-radius: 50%;
    filter: blur(140px); opacity: 0.05;
    pointer-events: none; z-index: 0;
    animation: orbFloat 18s ease-in-out infinite alternate;
}
.orb-1 {
    width: 340px; height: 340px;
    background: radial-gradient(circle, rgba(255,184,0,0.5), transparent 70%);
    top: -120px; left: -100px; animation-duration: 20s;
}
.orb-2 {
    width: 250px; height: 250px;
    background: radial-gradient(circle, rgba(78,205,196,0.4), transparent 70%);
    bottom: 10%; right: -80px; animation-duration: 24s; animation-delay: -6s;
}
.orb-3 {
    width: 210px; height: 210px;
    background: radial-gradient(circle, rgba(255,107,107,0.3), transparent 70%);
    top: 45%; left: 50%; animation-duration: 28s; animation-delay: -10s;
}
@keyframes orbFloat {
    0%   { transform: translate(0, 0) scale(1); }
    50%  { transform: translate(-20px, 25px) scale(1.1); }
    100% { transform: translate(15px, -20px) scale(0.95); }
}

/* ========== BOOT LOADER ========== */
.boot-loader {
    position: fixed; inset: 0; z-index: 9999;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 20px;
    background:
        radial-gradient(circle at 30% 20%, rgba(255,184,0,0.12), transparent 50%),
        radial-gradient(circle at 70% 80%, rgba(78,205,196,0.08), transparent 50%),
        rgba(13, 15, 20, 0.98);
    transition: opacity 0.5s ease, visibility 0.5s ease;
}
.boot-loader.hidden { opacity: 0; visibility: hidden; pointer-events: none; }
/* ── Newspaper Loader with 3D Page Turn ── */
.newspaper-loader {
    position: relative;
    width: 130px; height: 96px;
    perspective: 600px;
}
.newspaper-svg {
    width: 100%; height: 100%;
    filter: drop-shadow(0 4px 24px rgba(255,184,0,0.12));
}
/* Individual turning pages — positioned over the right half of the newspaper */
.turning-page {
    position: absolute;
    top: 14.5%;   /* align with SVG right page y=15 of viewBox 110 */
    left: 47.8%;  /* align with SVG spine at x=65 of viewBox 140 */
    width: 42%;   /* right page width */
    height: 72.7%;
    background: #1e2130;
    border: 0.5px solid rgba(255,184,0,0.18);
    border-left: none;
    border-radius: 0 2px 2px 0;
    transform-origin: left center;
    transform-style: preserve-3d;
    backface-visibility: hidden;
    animation: pageFlip 3.6s ease-in-out infinite;
}
/* Text lines on turning pages */
.tp-line {
    position: absolute;
    left: 14%;
    height: 3%;
    border-radius: 1px;
    background: rgba(255,255,255,0.10);
}
/* Page stacking: tp-1 is on top (flips first), tp-3 is bottom (flips last) */
.turning-page.tp-1 {
    z-index: 3;
    background: #222638;
    animation-delay: 0s;
    box-shadow: -2px 0 8px rgba(0,0,0,0.15);
}
.turning-page.tp-1 .tp-line { background: rgba(255,255,255,0.12); }
.turning-page.tp-2 {
    z-index: 2;
    background: #1f2334;
    animation-delay: 1.2s;
    box-shadow: -1px 0 6px rgba(0,0,0,0.10);
}
.turning-page.tp-2 .tp-line { background: rgba(255,255,255,0.09); }
.turning-page.tp-3 {
    z-index: 1;
    background: #1c2030;
    animation-delay: 2.4s;
    box-shadow: -1px 0 4px rgba(0,0,0,0.08);
}
.turning-page.tp-3 .tp-line { background: rgba(255,255,255,0.07); }
/* 3D page flip keyframes — page lifts, rotates over the spine, settles on left */
@keyframes pageFlip {
    0%   { transform: rotateY(0deg); opacity: 1; }
    10%  { transform: rotateY(-15deg); opacity: 1; }
    35%  { transform: rotateY(-110deg); opacity: 0.85; }
    50%  { transform: rotateY(-170deg); opacity: 0.6; }
    55%  { transform: rotateY(-180deg); opacity: 0; }
    /* Page stays hidden while other pages flip */
    90%  { transform: rotateY(-180deg); opacity: 0; }
    95%  { transform: rotateY(-10deg); opacity: 0; }
    100% { transform: rotateY(0deg); opacity: 1; }
}
/* Subtle glow pulse on the whole newspaper */
.newspaper-loader::after {
    content: '';
    position: absolute;
    inset: -10px;
    border-radius: 14px;
    background: radial-gradient(circle, rgba(255,184,0,0.06), transparent 70%);
    animation: glowPulse 3.6s ease-in-out infinite;
    pointer-events: none;
}
@keyframes glowPulse {
    0%, 100% { opacity: 0.3; transform: scale(0.96); }
    50%      { opacity: 1; transform: scale(1.04); }
}
.boot-text {
    font-size: 14px; font-weight: 600;
    color: var(--text-secondary);
    letter-spacing: 0.03em;
    animation: pulseText 2s ease-in-out infinite;
}
@keyframes pulseText { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }

/* ========== SKELETON SHIMMER ========== */
.skeleton-card {
    background: var(--bg-card) !important;
    border-radius: var(--radius) !important;
    overflow: hidden; min-height: 300px;
    border: none !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.2) !important;
}
.skeleton-image {
    height: 200px;
    background: linear-gradient(120deg,
        var(--bg-elevated) 25%, var(--bg-highest) 37%,
        color-mix(in srgb, var(--accent) 4%, var(--bg-highest)) 50%,
        var(--bg-elevated) 75%);
    background-size: 300% 100%;
    animation: shimmer 1.8s ease-in-out infinite;
}
.skeleton-line {
    height: 14px; border-radius: 7px; margin-bottom: 10px;
    background: linear-gradient(120deg,
        var(--bg-elevated) 25%, var(--bg-highest) 37%,
        color-mix(in srgb, var(--accent) 4%, var(--bg-highest)) 50%,
        var(--bg-elevated) 75%);
    background-size: 300% 100%;
    animation: shimmer 1.8s ease-in-out infinite;
}
.skeleton-line.w-75 { width: 75%; }
.skeleton-line.w-50 { width: 50%; }
.skeleton-line.w-30 { width: 30%; }
@keyframes shimmer { 0% { background-position: 300% 0; } 100% { background-position: -300% 0; } }

/* ========== CARD ANIMATIONS ========== */
.card-animate {
    opacity: 0; transform: translateY(28px) scale(0.98);
    animation: cardEnter 0.5s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
@keyframes cardEnter { to { opacity: 1; transform: translateY(0) scale(1); } }

/* ========== TOPIC CHIPS ========== */
.topic-chip {
    background: var(--bg-elevated) !important;
    border: none !important;
    color: var(--text-secondary) !important;
    border-radius: 999px !important;
    padding: 9px 18px !important;
    font-size: 14px !important; font-weight: 700 !important;
    cursor: pointer !important;
    transition: all 0.25s ease !important;
    white-space: nowrap !important; user-select: none;
    flex-shrink: 0;
    position: relative;
    z-index: 100;
}
.topic-chip:hover { background: var(--bg-highest) !important; color: var(--text-primary) !important; }
.topic-chip:active { transform: scale(0.95) !important; }
.topic-chip-active {
    background: rgba(0, 175, 255, 0.2) !important;
    color: #2ec8ff !important;
    box-shadow: 0 0 0 1px rgba(46, 200, 255, 0.25) inset !important;
    z-index: 105;
}
/* Hide scrollbar on topic chips row */
.topic-chip:first-child { margin-left: 4px; }
.topic-rail {
    width: 100%;
    padding-top: 2px;
    background: transparent;
    z-index: 100;
    position: relative;
}
.q-scrollarea__container::-webkit-scrollbar { display: none; }
.q-scrollarea__container { scrollbar-width: none; }
/* ========== BOTTOM NAVIGATION ========== */
.bottom-nav {
    position: fixed !important; bottom: 0 !important; left: 0 !important; right: 0 !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 1200 !important;
    padding: 0 12px 0 !important;
    padding-bottom: env(safe-area-inset-bottom, 8px) !important;
    background: none !important; pointer-events: none;
    transition: transform 0.3s ease !important;
}
.bottom-nav-inner {
    display: flex !important;
    align-items: center;
    justify-content: center;
    gap: 2px;
    padding: 6px 8px;
    background: rgba(21, 24, 32, 0.94);
    backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
    border-radius: 22px;
    border-top: 0.5px solid rgba(255,255,255,0.05);
    box-shadow: 0 -4px 40px rgba(0,0,0,0.5), 0 0 0 0.5px rgba(255,255,255,0.04);
    pointer-events: auto;
    width: auto; max-width: 360px;
}
.nav-btn {
    display: flex; flex-direction: column; align-items: center; gap: 2px;
    padding: 8px 16px; border-radius: 16px; border: none;
    background: transparent; color: var(--text-muted);
    font-size: 10px; font-weight: 600; font-family: var(--font);
    cursor: pointer; transition: all 0.2s ease;
    user-select: none; -webkit-tap-highlight-color: transparent;
    min-height: 44px; min-width: 44px;
}
.nav-btn:hover { color: var(--text-secondary); }
.nav-btn.active { color: var(--accent); background: rgba(255,184,0,0.08); }
.nav-btn:active { transform: scale(0.92); }
.nav-btn-fab {
    padding: 10px 20px;
    background: linear-gradient(135deg, #e6a600, #FFB800);
    color: #0d0f14; border-radius: 16px;
    box-shadow: 0 6px 24px rgba(255,184,0,0.3);
    font-weight: 700; margin: 0 2px;
}
.nav-btn-fab:hover { box-shadow: 0 8px 32px rgba(255,184,0,0.4); }

/* ========== SIDEBAR ========== */
.sidebar-backdrop {
    position: fixed; inset: 0; z-index: 1050;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
    opacity: 0; visibility: hidden; transition: all 0.35s ease;
}
.sidebar-backdrop.show { opacity: 1; visibility: visible; }
.sidebar-panel {
    position: fixed; top: 0; left: 0; bottom: 0;
    width: 300px; max-width: 85vw; z-index: 1060;
    background: linear-gradient(180deg, var(--bg-card), #10121a);
    box-shadow: 8px 0 48px rgba(0,0,0,0.5);
    transform: translateX(-100%);
    transition: transform 0.35s cubic-bezier(0.32, 1.25, 0.36, 1);
    overflow-y: auto; overflow-x: hidden;
    display: flex; flex-direction: column;
    padding-bottom: calc(80px + env(safe-area-inset-bottom, 20px));
}
.sidebar-panel.show { transform: translateX(0); }
.sidebar-section {
    padding: 16px 18px;
    border-bottom: 0.5px solid var(--border-ghost);
}
.sidebar-section-title {
    font-size: 10px; font-weight: 800;
    letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--text-muted); margin-bottom: 10px;
    display: flex; align-items: center; gap: 6px;
}
.sidebar-select {
    width: 100%; padding: 10px 14px;
    border-radius: 12px; border: 0.5px solid var(--border-ghost);
    background: var(--bg-elevated); color: var(--text-primary);
    font-size: 14px; font-weight: 600; font-family: var(--font);
    cursor: pointer; appearance: none; -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%236c6b72'%3E%3Cpath d='M6 8L1 3h10z'/%3E%3C/svg%3E");
    background-repeat: no-repeat; background-position: right 12px center;
    transition: border-color 0.2s, box-shadow 0.2s; margin-bottom: 10px;
}
.sidebar-select:focus {
    outline: none;
    border-color: rgba(255,184,0,0.4);
    box-shadow: 0 0 0 3px rgba(255,184,0,0.08);
}
.sidebar-select option { background: var(--bg-card); color: var(--text-primary); }
.sidebar-action-btn {
    width: 100%; padding: 11px 16px;
    border-radius: 12px; border: 0.5px solid var(--border-ghost);
    background: var(--bg-elevated); color: var(--text-secondary);
    font-size: 13px; font-weight: 700; font-family: var(--font);
    cursor: pointer; transition: all 0.2s;
    display: flex; align-items: center; gap: 8px; justify-content: center;
}
.sidebar-action-btn:hover { background: var(--bg-highest); color: var(--text-primary); }
.sidebar-action-btn.primary {
    background: linear-gradient(135deg, #e6a600, #FFB800);
    color: #0d0f14; border: none;
    box-shadow: 0 4px 16px rgba(255,184,0,0.25);
}
.sidebar-close {
    width: 32px; height: 32px; border-radius: 10px; border: none;
    background: var(--bg-elevated); color: var(--text-secondary);
    font-size: 18px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: background 0.2s;
}
.sidebar-close:hover { background: var(--bg-highest); }
.sidebar-footer {
    padding: 14px 18px; margin-top: auto;
    font-size: 11px; color: var(--text-muted); text-align: center;
}
/* NiceGUI select styling for sidebar dropdowns */
.sidebar-nicegui-select {
    margin-bottom: 8px;
}
.sidebar-nicegui-select .q-field__control {
    background: var(--bg-elevated) !important;
    border-radius: 12px !important;
    min-height: 40px !important;
}
.sidebar-nicegui-select .q-field__control::before {
    border-color: var(--border-ghost) !important;
}
.sidebar-nicegui-select .q-field__native,
.sidebar-nicegui-select .q-select__selected {
    color: var(--text-primary) !important;
    font-family: var(--font) !important;
    font-size: 14px !important;
    font-weight: 600 !important;
}
.sidebar-nicegui-select .q-field__append .q-icon {
    color: var(--text-muted) !important;
}
.sort-group { display: flex; gap: 4px; background: var(--bg-primary); border-radius: 10px; padding: 3px; }
.sort-btn {
    flex: 1; padding: 8px 12px; border-radius: 8px; border: none;
    background: transparent; color: var(--text-muted);
    font-size: 12px; font-weight: 700; font-family: var(--font);
    cursor: pointer; transition: all 0.2s;
}
.sort-btn.active {
    background: var(--bg-elevated); color: var(--accent);
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

/* ========== TOP SHELL (Fixed Header + Categories) ========== */
.top-fixed-shell {
    position: sticky;
    top: 0;
    z-index: 120;
    width: 100%;
    padding: 8px 12px 6px;
    background: #0d0f14;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
    border-bottom: 0.5px solid rgba(255,255,255,0.05);
    box-shadow: 0 8px 22px rgba(0,0,0,0.28);
    opacity: 1;
    overflow: hidden;
    isolation: isolate;
}
.top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 2px 2px 6px;
}
.top-bar-title {
    font-size: 21px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--text-primary);
    background: none;
    -webkit-text-fill-color: initial;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; 
}
.top-bar-subline {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    padding: 4px 10px;
    border-radius: 999px;
    background: var(--bg-elevated);
    border: 0.5px solid rgba(255,255,255,0.06);
    white-space: nowrap;
}
.topic-rail {
    width: 100%;
    padding-top: 2px;
    background: #0d0f14;
    z-index: 100;
    position: relative;
}
.topic-rail .q-scrollarea,
.topic-rail .q-scrollarea__container,
.topic-rail .q-scrollarea__content {
    background: #0d0f14 !important;
}
.topic-rail .topic-chip:first-child {
    margin-left: 0;
}
.hide-scb::-webkit-scrollbar {
    display: none !important;
}
.hide-scb {
    -ms-overflow-style: none;
    scrollbar-width: none;
}
.topic-chip-scroll {
    height: 56px;
    overflow-x: auto;
    overflow-y: hidden !important;
    -webkit-overflow-scrolling: touch;
    touch-action: pan-x;
    overscroll-behavior-x: contain;
    overscroll-behavior-y: none;
}
.topic-chip-scroll::-webkit-scrollbar {
    height: 0 !important;
    width: 0 !important;
}
.topic-chip-row {
    min-height: 56px;
    padding-top: 8px;
    padding-bottom: 8px;
    align-items: center;
}

/* ========== TRUST SIGNAL ========== */
.trust-signal {
    display: none;
}

/* ═══════════════════════════════════════════════════════════════════
   INSHORTS-STYLE NEWS CARD — Full viewport on mobile, standard on desktop
   ═══════════════════════════════════════════════════════════════════ */
.news-card-premium {
    background: #A9ABB1 !important;
    border: none !important;
    border-radius: 20px !important;
    overflow: hidden !important;
    padding: 14px !important;
    transition: transform 0.25s ease, box-shadow 0.25s ease !important;
    box-shadow: 0 8px 20px rgba(10, 14, 26, 0.14) !important;
    position: relative;
    display: flex;
    flex-direction: column;
    font-family: "Roboto", "Helvetica Neue", Arial, sans-serif;
}
.news-card-premium::before {
    content: none;
}

/* ── Trending Card Animation ── */
.news-card-trending {
    /* Slightly lighter background or different border if desired */
}
/* The animated background glow placed behind the card */
.news-card-trending::before {
    content: '';
    position: absolute;
    inset: -4px; /* Expand outside the card bounds */
    z-index: -1; /* Place behind the card background */
    background: linear-gradient(135deg, rgba(255,184,0,0.8), rgba(255,107,107,0), rgba(78,205,196,0.8), rgba(255,107,107,0));
    background-size: 300% 300%;
    border-radius: 24px; /* Slightly larger than card radius (20px) */
    filter: blur(8px);
    opacity: 0.6;
    animation: trendingGlow 4s ease infinite;
}

/* Internal subtle pulse for trending cards */
.news-card-trending::after {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    border-radius: 20px;
    box-shadow: inset 0 0 0 1px rgba(255,184,0,0.3);
    animation: trendingPulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes trendingGlow {
    0% { background-position: 0% 50%; opacity: 0.4; }
    50% { background-position: 100% 50%; opacity: 0.8; }
    100% { background-position: 0% 50%; opacity: 0.4; }
}

@keyframes trendingPulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

/* Card image with actual photos */
.card-image-area {
    position: relative;
    width: 100%;
    aspect-ratio: 4 / 3;
    overflow: hidden;
    border-radius: 12px;
    flex-shrink: 0;
}
.card-image-area img {
    width: 100%; height: 100%;
    object-fit: cover;
    transition: transform 0.5s ease;
}
.news-card-premium:hover .card-image-area img {
    transform: scale(1.04);
}
.card-image-gradient {
    display: none;
}
.card-topic-tag {
    display: none;
}
.card-position-chip {
    display: none;
}
/* Category color accent line at card top */
.card-cat-accent {
    display: none;
}

/* Card body */
.card-body-area {
    padding: 10px 0 0;
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
/* Card Headline & Summary (Cleaner Typography) */
.card-headline-text {
    font-size: 22px;
    font-weight: 700;
    line-height: 1.22;
    color: #FFFFFF;
    margin-bottom: 8px;
    letter-spacing: -0.01em;
    display: -webkit-box; -webkit-line-clamp: 3;
    -webkit-box-orient: vertical; overflow: hidden;
    overflow-wrap: anywhere; word-break: break-word;
}
.card-summary-text {
    font-size: 14px;
    font-weight: 400;
    line-height: 1.4;
    color: rgba(255, 255, 255, 0.72);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical; overflow: hidden;
    overflow-wrap: anywhere; word-break: break-word;
}
.card-badges {
    display: none;
}
.badge-trust, .badge-sentiment {
    display: inline-flex; align-items: center; gap: 3px;
    padding: 3px 8px; border-radius: 6px;
    font-size: 10px; font-weight: 700;
}
.badge-importance {
    display: inline-flex; align-items: center; gap: 2px;
    padding: 3px 8px; border-radius: 6px;
    background: rgba(255,184,0,0.12); color: var(--accent);
    font-size: 10px; font-weight: 800;
}

/* ========== FULL-SCREEN DETAIL OVERLAY ========== */
.detail-overlay {
    position: fixed; inset: 0; z-index: 1000;
    background: var(--bg-primary);
    transform: translateY(100%);
    transition: transform 0.4s cubic-bezier(0.32, 0.72, 0, 1);
    overflow-y: auto; overflow-x: hidden;
    -webkit-overflow-scrolling: touch;
    display: flex; flex-direction: column;
}
.detail-overlay.open {
    transform: translateY(0);
}

/* Close / back button */
.detail-close-bar {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    z-index: 24;
    display: flex; align-items: center; justify-content: space-between;
    visibility: visible;
    opacity: 1;
    pointer-events: auto;
    padding: 12px 14px;
    padding-top: max(12px, env(safe-area-inset-top, 12px));
    background: linear-gradient(to bottom, rgba(9, 10, 14, 0.6), rgba(9, 10, 14, 0));
}
.detail-back-btn {
    display: flex; align-items: center; gap: 4px;
    border: none;
    background: rgba(12, 14, 19, 0.72);
    color: #eef2f6;
    font-size: 14px;
    font-weight: 700;
    font-family: var(--font); cursor: pointer;
    padding: 8px 12px;
    border-radius: 999px;
    transition: background 0.2s;
    visibility: visible;
    opacity: 1;
}
.detail-back-btn:hover { background: rgba(18, 22, 29, 0.86); }
.detail-actions-row {
    display: flex; align-items: center; gap: 4px;
}
.detail-actions-row .action-btn {
    background: rgba(12, 14, 19, 0.72);
    color: #eef2f6;
}
.detail-actions-row .action-btn:hover {
    background: rgba(18, 22, 29, 0.86);
}

/* Cover image in detail */
.detail-cover {
    width: 100%; height: 280px;
    object-fit: cover; display: block;
    flex-shrink: 0;
}
.detail-cover-wrap {
    position: relative; flex-shrink: 0;
}
.detail-cover-gradient {
    position: absolute; bottom: 0; left: 0; right: 0;
    height: 50%;
    background: linear-gradient(to top, var(--bg-primary), transparent);
}
.detail-topic-pill {
    position: absolute; top: 16px; left: 16px;
    padding: 5px 14px; border-radius: 999px;
    background: rgba(0,0,0,0.55); backdrop-filter: blur(10px);
    color: #fff; font-size: 10px; font-weight: 800;
    letter-spacing: 0.06em; text-transform: uppercase;
}

/* Detail body */
.detail-body {
    padding: 0 20px 100px; flex: 1;
}
.detail-badges {
    display: flex; align-items: center; gap: 6px;
    flex-wrap: wrap; margin-bottom: 12px;
}
.detail-headline {
    font-size: 24px; font-weight: 900;
    line-height: 1.3; letter-spacing: -0.02em;
    color: var(--text-primary);
    margin-bottom: 16px;
    overflow-wrap: anywhere; word-break: break-word;
}
.detail-source-row {
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 20px; padding-bottom: 16px;
    border-bottom: 0.5px solid var(--border-ghost);
}
.source-dot {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 800;
    color: #fff;
    flex-shrink: 0;
}
.detail-source-name {
    font-size: 13px; font-weight: 700; color: var(--text-secondary);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.detail-source-time {
    font-size: 12px; font-weight: 500; color: var(--text-muted);
}

/* Bullet summary section */
.detail-section-label {
    font-size: 11px; font-weight: 800;
    letter-spacing: 0.08em; text-transform: uppercase;
    color: var(--accent); margin-bottom: 12px;
    display: flex; align-items: center; gap: 6px;
}
.detail-bullet {
    display: flex; align-items: flex-start; gap: 10px;
    margin-bottom: 12px;
}
.detail-bullet-dot {
    width: 8px; height: 8px; min-width: 8px;
    border-radius: 50%; margin-top: 6px;
    background: var(--accent);
    box-shadow: 0 0 8px rgba(255,184,0,0.3);
}
.detail-bullet-text {
    font-size: 15px; font-weight: 400;
    line-height: 1.65; color: var(--text-primary);
    overflow-wrap: anywhere; word-break: break-word;
}

/* Why it matters */
.detail-why-box {
    margin-top: 20px; padding: 16px;
    border-radius: 14px;
    background: rgba(78,205,196,0.06);
    border-left: 3px solid var(--accent-teal);
}
.detail-why-label {
    font-size: 11px; font-weight: 800;
    letter-spacing: 0.08em; text-transform: uppercase;
    color: var(--accent-teal); margin-bottom: 6px;
    display: flex; align-items: center; gap: 6px;
}
.detail-why-text {
    font-size: 14px; font-weight: 500;
    line-height: 1.6; color: var(--text-secondary);
    font-style: italic;
}

/* Read full article CTA */
.detail-cta {
    display: flex; align-items: center; justify-content: center;
    gap: 8px; width: 100%; margin-top: 28px;
    padding: 14px 24px; border-radius: 14px; border: none;
    background: linear-gradient(135deg, #e6a600, #FFB800);
    color: #0d0f14; font-size: 15px; font-weight: 800;
    font-family: var(--font); cursor: pointer;
    transition: all 0.25s; text-decoration: none;
    box-shadow: 0 6px 24px rgba(255,184,0,0.25);
}
.detail-cta:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 32px rgba(255,184,0,0.35);
}
.detail-cta:active { transform: scale(0.98); }

/* ========== CARD ACTION BAR (Share / Save) ========== */
.card-action-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 0 0;
    margin-top: 6px;
}
.card-source-info {
    display: flex; align-items: center; gap: 8px;
    flex: 1; min-width: 0;
}
.source-avatar {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, rgba(255,255,255,0.55), rgba(255,255,255,0.2));
    border: 1px solid rgba(255,255,255,0.45);
    flex-shrink: 0;
}

@keyframes pulseDot {
    0% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(255,255,255, 0.4); }
    70% { transform: scale(1.05); opacity: 1; box-shadow: 0 0 0 6px rgba(255,255,255, 0); }
    100% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(255,255,255, 0); }
}
.blink-dot {
    animation: pulseDot 2s infinite ease-in-out;
    color: white;
    font-weight: 800;
    font-size: 12px;
    border: none !important;
}
.source-name-text {
    font-size: 12px;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.72);
    max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.card-time-text {
    display: none;
}
.card-actions {
    display: flex; align-items: center; gap: 2px;
}
.card-action-bar .action-btn {
    width: 24px;
    height: 24px;
    border-radius: 0;
    border: none;
    background: transparent;
    color: #FFFFFF;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; transition: all 0.2s; flex-shrink: 0;
    -webkit-tap-highlight-color: transparent;
}
.card-action-bar .action-btn:hover {
    opacity: 0.9;
    transform: translateY(-1px);
}
.card-action-bar .action-btn:active { transform: scale(0.94); }
.card-action-bar .action-btn.saved .bookmark-icon path {
    fill: rgba(255, 255, 255, 0.28);
}
.bookmark-icon {
    width: 20px;
    height: 20px;
    display: block;
}

.action-btn {
    width: 36px; height: 36px;
    border-radius: 999px; border: none;
    background: rgba(255,255,255,0.04);
    color: var(--text-muted);
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; transition: all 0.2s; flex-shrink: 0;
    -webkit-tap-highlight-color: transparent;
}
.action-btn:hover { background: var(--bg-elevated); color: var(--text-primary); }
.action-btn:active { transform: scale(0.9); }
.action-btn.saved { color: var(--accent); }
.action-btn.shared { color: var(--accent-teal); }
.card-action-bar .action-btn.saved { color: #FFFFFF; }

/* ========== QUASAR OVERRIDES ========== */
.q-card { background: var(--bg-card) !important; box-shadow: none !important; }
.q-field__label { color: var(--text-muted) !important; }
.q-field__control { color: var(--text-primary) !important; }
.q-tooltip {
    background: var(--bg-elevated) !important;
    color: var(--text-primary) !important;
    border: 0.5px solid var(--border-ghost) !important;
    border-radius: 12px !important;
    padding: 12px 16px !important;
    max-width: 320px !important;
    box-shadow: 0 12px 40px rgba(0,0,0,0.4) !important;
}
.q-notification__message { font-family: var(--font) !important; }
.q-menu {
    background: var(--bg-card) !important;
    border: 0.5px solid var(--border-ghost) !important;
    border-radius: 12px !important;
}

/* ========== EMPTY STATE ========== */
.empty-state {
    text-align: center; padding: 48px 24px;
    animation: fadeIn 0.5s ease;
}
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.empty-icon { font-size: 52px; margin-bottom: 16px; opacity: 0.6; }
.empty-text { font-size: 14px; color: var(--text-muted); line-height: 1.7; }

/* ========== MOBILE — Inshorts-style snap scroll ========== */
@media (max-width: 768px) {
    .desktop-only { display: none !important; }
    .ambient-orb { display: none !important; }

    /* Kill ALL NiceGUI/Quasar wrapper spacing on mobile */
    .q-page, .nicegui-content, .q-page-container {
        padding: 0 !important; margin: 0 !important;
    }

    /* Fixed top shell for mobile with safe area */
    .top-fixed-shell {
        top: 0;
        z-index: 130;
        width: 100%;
        padding: max(env(safe-area-inset-top, 0px), 8px) 12px 6px;
        background: #0d0f14;
        box-shadow: 0 8px 20px rgba(0,0,0,0.32);
    }

    .top-bar {
        padding: 0 2px 4px;
    }
    .top-bar-logo { font-size: 20px; }
    .top-bar-logo-img { display: none; }
    .top-bar-title {
        font-size: 24px;
        font-weight: 650;
        letter-spacing: -0.01em;
    }
    .top-bar-subline {
        font-size: 9.5px;
        padding: 3px 8px;
    }
    .topic-rail { padding-top: 0; }

    /* Trust signal — compact single line */
    .trust-signal { padding: 3px 12px; font-size: 9.5px; }

    /* Topic chips — tighter row */
    .topic-chip {
        padding: 8px 14px !important;
        font-size: 11.5px !important;
        border-radius: 18px !important;
    }

    .feed-container {
        scroll-snap-type: none;
        overflow-y: visible;
        height: auto;
        padding: 10px 0 calc(92px + max(env(safe-area-inset-bottom, 12px), 12px));
    }
    .news-card-premium {
        scroll-snap-align: none;
        height: auto;
        max-height: none;
        overflow: hidden;
        border-radius: 20px !important;
        margin: 0 auto 12px !important;
        width: calc(100% - 24px);
        max-width: 360px;
        box-shadow: 0 8px 20px rgba(10, 14, 26, 0.14) !important;
    }
    .card-image-area { min-height: 0; height: auto; }
    .card-body-area { flex: 1; padding: 10px 0 0; overflow: hidden; }
    .card-headline-text { font-size: 22px; -webkit-line-clamp: 3; margin-bottom: 8px; }
    .card-summary-text {
        -webkit-line-clamp: 2;
        font-size: 14px;
        margin-bottom: 0;
        line-height: 1.4;
    }
    .card-badges { margin-bottom: 3px; }
    .card-action-bar { padding: 14px 0 0; }
    .source-name-text { max-width: 120px; }

    /* Bottom nav — always visible, proper safe-area for iPhones */
    .bottom-nav {
        padding: 0 !important;
        padding-bottom: max(env(safe-area-inset-bottom, 12px), 12px) !important;
        transform: translateY(0) !important; /* Never hide */
        background: linear-gradient(to top, rgba(13, 15, 20, 0.9), rgba(13, 15, 20, 0.35) 70%, transparent) !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
    }
    .bottom-nav-inner {
        padding: 6px 8px;
        border-radius: 18px;
        max-width: 360px;
        width: calc(100% - 20px);
        background: rgba(13, 15, 20, 0.94) !important;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-top: 0.5px solid rgba(255,255,255,0.06);
        box-shadow: 0 -6px 24px rgba(0,0,0,0.45);
    }
    .nav-btn {
        padding: 7px 0; font-size: 9px;
        min-height: 44px; min-width: 0; flex: 1;
    }
    .nav-btn .material-icons { font-size: 20px !important; }

    /* Detail overlay mobile fixes */
    .detail-cover { height: 184px; }
    .detail-headline { font-size: 18px; margin-bottom: 12px; }
    .detail-body { padding: 0 16px calc(80px + env(safe-area-inset-bottom, 0px)); }
    .detail-bullet-text { font-size: 13.5px; line-height: 1.55; }
    .detail-close-bar {
        padding: 8px 12px;
        padding-top: max(8px, env(safe-area-inset-top, 8px));
    }
    .detail-cta { padding: 12px 20px; font-size: 14px; margin-top: 20px; border-radius: 12px; }
}

@media (min-width: 769px) {
    .mobile-only { display: none !important; }

    .news-card-premium {
        cursor: pointer;
    }
    .feed-grid {
        display: grid;
        justify-items: center;
    }
    .news-card-premium:hover {
        transform: translateY(-4px) !important;
        box-shadow: 0 14px 26px rgba(10, 14, 26, 0.18) !important;
    }
}

@media (min-width: 900px) {
    .bottom-nav-inner { height: 42px; padding: 4px 6px; border-radius: 14px; }
    .nav-btn { padding: 6px 16px; font-size: 11px; flex-direction: row; gap: 5px; }
    .nav-btn-fab { padding: 8px 20px; }

    /* Two-column grid on desktop */
    .feed-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 20px;
    }
}

.synthesis-banner {
    background: linear-gradient(135deg, rgba(88, 101, 242, 0.15) 0%, rgba(35, 39, 42, 0.5) 100%);
    border: 1px solid rgba(88, 101, 242, 0.3);
    border-radius: 12px;
    padding: 16px 20px;
    margin: 12px 16px 4px 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}
.synthesis-header {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #a5b4fc;
    margin-bottom: 8px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 6px;
}
.synthesis-content {
    font-size: 14px;
    line-height: 1.5;
    color: #f8f9fa;
    font-weight: 400;
}
"""
