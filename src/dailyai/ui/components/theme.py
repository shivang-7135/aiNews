"""
DailyAI — Vibrant Obsidian Design System v3
Dark base + warm vibrant accents for an inviting, happy, professional experience.
Inshorts-style mobile snap-scroll cards, expandable summaries, share/save actions.
"""

from pathlib import Path

# ── Color Palette ───────────────────────────────────────────────────

COLORS = {
    # Warm accent spectrum
    "accent": "#FFB800",       # Golden amber — primary
    "accent_alt": "#FF6B6B",   # Coral — secondary
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
    "breakthrough": [
        "/static/topic-covers/breakthrough-1.jpg",
        "/static/topic-covers/breakthrough-2.jpg",
        "/static/topic-covers/breakthrough-3.jpg",
    ],
    "product": [
        "/static/topic-covers/product-1.jpg",
        "/static/topic-covers/product-2.jpg",
        "/static/topic-covers/product-3.jpg",
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
    "research": [
        "/static/topic-covers/research-1.jpg",
        "/static/topic-covers/research-2.jpg",
        "/static/topic-covers/research-3.jpg",
    ],
    "industry": [
        "/static/topic-covers/industry-1.jpg",
        "/static/topic-covers/industry-2.jpg",
        "/static/topic-covers/industry-3.jpg",
    ],
    "general": [
        "/static/topic-covers/general-1.jpg",
        "/static/topic-covers/general-2.jpg",
        "/static/topic-covers/general-3.jpg",
    ],
}


def _normalize_category_key(category: str) -> str:
    """Map UI and data labels to known internal category keys."""
    raw = (category or "").strip().lower().replace("_", " ").replace("-", " ")
    if not raw:
        return "general"

    aliases = {
        "ai models": "breakthrough",
        "models": "breakthrough",
        "model": "breakthrough",
        "business": "industry",
        "industry": "industry",
        "research": "research",
        "tools": "product",
        "product": "product",
        "products": "product",
        "regulation": "regulation",
        "funding": "funding",
        "top stories": "general",
        "general": "general",
    }
    return aliases.get(raw, raw if raw in CATEGORY_IMAGE_SETS else "general")


def get_category_image(category: str, seed: str = "") -> str:
    """Select one of three cached cover images per category."""
    key = _normalize_category_key(category)
    options = CATEGORY_IMAGE_SETS.get(key, CATEGORY_IMAGE_SETS["general"])
    idx = 0 if not seed else sum(ord(c) for c in seed) % len(options)
    preferred = options[idx]

    project_root = Path(__file__).resolve().parents[4]
    preferred_path = project_root / preferred.lstrip("/")
    if preferred_path.exists() and preferred_path.stat().st_size > 1024:
        return preferred

    for candidate in options:
        candidate_path = project_root / candidate.lstrip("/")
        if candidate_path.exists() and candidate_path.stat().st_size > 1024:
            return candidate

    return CATEGORY_FALLBACK_IMAGES.get(key, CATEGORY_FALLBACK_IMAGES["general"])

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
    --text-secondary: #b0aeb5;
    --text-muted: #6c6b72;
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
body, html { padding: 0 !important; margin: 0 !important; }

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

/* ========== AMBIENT GRADIENT ORBS (warm) ========== */
.ambient-orb {
    position: fixed; border-radius: 50%;
    filter: blur(120px); opacity: 0.08;
    pointer-events: none; z-index: 0;
    animation: orbFloat 18s ease-in-out infinite alternate;
}
.orb-1 {
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(255,184,0,0.5), transparent 70%);
    top: -120px; left: -100px; animation-duration: 20s;
}
.orb-2 {
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(78,205,196,0.4), transparent 70%);
    bottom: 10%; right: -80px; animation-duration: 24s; animation-delay: -6s;
}
.orb-3 {
    width: 250px; height: 250px;
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
.boot-spinner {
    width: 48px; height: 48px; border-radius: 50%;
    border: 3px solid rgba(255,255,255,0.06);
    border-top-color: var(--accent);
    border-right-color: var(--accent-teal);
    animation: bootSpin 0.8s linear infinite;
    box-shadow: 0 0 24px rgba(255,184,0,0.2);
}
@keyframes bootSpin { to { transform: rotate(360deg); } }
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
    padding: 8px 16px !important;
    font-size: 13px !important; font-weight: 600 !important;
    cursor: pointer !important;
    transition: all 0.25s ease !important;
    white-space: nowrap !important; user-select: none;
    flex-shrink: 0;
}
.topic-chip:hover { background: var(--bg-highest) !important; color: var(--text-primary) !important; }
.topic-chip:active { transform: scale(0.95) !important; }
.topic-chip-active {
    background: rgba(255, 184, 0, 0.14) !important;
    color: var(--accent) !important;
    box-shadow: 0 0 14px rgba(255,184,0,0.1) !important;
}

/* ========== BOTTOM NAVIGATION ========== */
.bottom-nav {
    position: fixed !important; bottom: 0 !important; left: 0 !important; right: 0 !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    z-index: 900 !important;
    padding: 0 12px 0 !important;
    padding-bottom: env(safe-area-inset-bottom, 8px) !important;
    background: none !important; pointer-events: none;
    transition: transform 0.3s ease !important;
}
.bottom-nav-inner {
    display: flex; align-items: center; justify-content: center; gap: 2px;
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
    position: fixed; inset: 0; z-index: 950;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
    opacity: 0; visibility: hidden; transition: all 0.35s ease;
}
.sidebar-backdrop.show { opacity: 1; visibility: visible; }
.sidebar-panel {
    position: fixed; top: 0; left: 0; bottom: 0;
    width: 300px; max-width: 85vw; z-index: 960;
    background: linear-gradient(180deg, var(--bg-card), #10121a);
    box-shadow: 8px 0 48px rgba(0,0,0,0.5);
    transform: translateX(-100%);
    transition: transform 0.35s cubic-bezier(0.32, 1.25, 0.36, 1);
    overflow-y: auto; overflow-x: hidden;
    display: flex; flex-direction: column;
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

/* ========== TOP BAR — scrolls naturally, NOT sticky ========== */
.top-bar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 18px 12px;
}
.top-bar-brand { display: flex; align-items: center; gap: 8px; }
.top-bar-logo { font-size: 26px; }
.top-bar-logo-img {
    height: 28px; width: 28px;
    border-radius: 6px; object-fit: contain;
    flex-shrink: 0;
}
.top-bar-title {
    font-size: 22px; font-weight: 900;
    letter-spacing: -0.03em; color: var(--text-primary);
    background: linear-gradient(135deg, #FFB800, #FF6B6B);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}
.top-bar-right { display: flex; align-items: center; gap: 10px; }

/* ========== TRUST SIGNAL ========== */
.trust-signal {
    display: flex; align-items: center; justify-content: center;
    gap: 6px; padding: 8px 18px;
    background: linear-gradient(90deg,
        rgba(255,184,0,0.04) 0%, rgba(78,205,196,0.06) 50%, rgba(255,184,0,0.04) 100%);
    font-size: 11px; font-weight: 600;
    color: var(--text-muted); letter-spacing: 0.02em;
}

/* ═══════════════════════════════════════════════════════════════════
   INSHORTS-STYLE NEWS CARD — Full viewport on mobile, standard on desktop
   ═══════════════════════════════════════════════════════════════════ */
.news-card-premium {
    background: var(--bg-card) !important;
    border: none !important;
    border-radius: var(--radius) !important;
    overflow: hidden !important;
    transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1) !important;
    box-shadow: 0 4px 24px rgba(0,0,0,0.25) !important;
    position: relative;
    display: flex; flex-direction: column;
}
.news-card-premium::before {
    content: ''; position: absolute; inset: 0;
    border-radius: inherit;
    border: 0.5px solid rgba(255,255,255,0.04);
    pointer-events: none; z-index: 2;
}

/* Card image with actual photos */
.card-image-area {
    position: relative; height: 220px; overflow: hidden;
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
    position: absolute; bottom: 0; left: 0; right: 0;
    height: 70%;
    background: linear-gradient(to top, var(--bg-card) 0%, transparent 100%);
    pointer-events: none;
}
.card-topic-tag {
    position: absolute; top: 14px; left: 14px; z-index: 5;
    padding: 5px 14px; border-radius: 999px;
    background: rgba(0,0,0,0.55);
    backdrop-filter: blur(10px);
    color: #fff; font-size: 10px; font-weight: 800;
    letter-spacing: 0.06em; text-transform: uppercase;
}
/* Category color accent line at card top */
.card-cat-accent {
    position: absolute; top: 0; left: 0; right: 0;
    height: 3px; z-index: 5;
}

/* Card body */
.card-body-area { padding: 16px 18px 10px; flex: 1; display: flex; flex-direction: column; }
.card-headline-text {
    font-size: 17px; font-weight: 800;
    line-height: 1.35; letter-spacing: -0.01em;
    color: var(--text-primary); margin-bottom: 8px;
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
    overflow: hidden; cursor: pointer;
}
.card-summary-text {
    font-size: 13px; font-weight: 400;
    line-height: 1.65; color: var(--text-secondary);
    margin-bottom: 10px;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    overflow: hidden;
}
.card-badges {
    display: flex; align-items: center; gap: 6px;
    margin-bottom: 8px; flex-wrap: wrap;
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
    position: sticky; top: 0; z-index: 10;
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 16px;
    background: rgba(13, 15, 20, 0.85);
    backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
}
.detail-back-btn {
    display: flex; align-items: center; gap: 4px;
    border: none; background: transparent;
    color: var(--accent); font-size: 14px; font-weight: 700;
    font-family: var(--font); cursor: pointer;
    padding: 6px 10px; border-radius: 10px;
    transition: background 0.2s;
}
.detail-back-btn:hover { background: var(--bg-elevated); }
.detail-actions-row {
    display: flex; align-items: center; gap: 4px;
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
}
.detail-source-row {
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 20px; padding-bottom: 16px;
    border-bottom: 0.5px solid var(--border-ghost);
}
.detail-source-name {
    font-size: 13px; font-weight: 700; color: var(--text-secondary);
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
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 18px 14px;
    border-top: 0.5px solid var(--border-ghost);
}
.card-source-info {
    display: flex; align-items: center; gap: 8px;
    flex: 1; min-width: 0;
}
.source-dot {
    width: 24px; height: 24px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 10px; font-weight: 800; color: #fff;
    flex-shrink: 0;
}
.source-name-text {
    font-size: 11px; font-weight: 600; color: var(--text-secondary);
    max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.card-time-text {
    font-size: 11px; font-weight: 600; color: var(--text-muted);
    margin-right: 8px;
}
.card-actions {
    display: flex; align-items: center; gap: 2px;
}
.action-btn {
    width: 36px; height: 36px;
    border-radius: 10px; border: none;
    background: transparent;
    color: var(--text-muted);
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; transition: all 0.2s; flex-shrink: 0;
    -webkit-tap-highlight-color: transparent;
}
.action-btn:hover { background: var(--bg-elevated); color: var(--text-primary); }
.action-btn:active { transform: scale(0.9); }
.action-btn.saved { color: var(--accent); }
.action-btn.shared { color: var(--accent-teal); }

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
.empty-state { text-align: center; padding: 48px 24px; }
.empty-icon { font-size: 52px; margin-bottom: 16px; opacity: 0.4; }
.empty-text { font-size: 14px; color: var(--text-muted); line-height: 1.7; }

/* ========== MOBILE — Inshorts-style snap scroll ========== */
@media (max-width: 768px) {
    .desktop-only { display: none !important; }

    /* Kill ALL NiceGUI/Quasar wrapper spacing on mobile */
    .q-page, .nicegui-content, .q-page-container {
        padding: 0 !important; margin: 0 !important;
    }

    /* Compact sticky top bar — flush at very top, only safe-area offset */
    .top-bar {
        padding: 0 14px 3px;
        position: sticky; top: 0; z-index: 50;
        background: rgba(13, 15, 20, 0.94);
        backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
        border-bottom: 0.5px solid rgba(255,255,255,0.04);
        /* Only add space for iOS notch / Dynamic Island */
        padding-top: env(safe-area-inset-top, 0px);
    }
    .top-bar-logo { font-size: 20px; }
    .top-bar-logo-img { height: 22px; width: 22px; }
    .top-bar-title { font-size: 17px; }
    .top-bar-right { gap: 6px; }

    /* Trust signal — compact single line */
    .trust-signal { padding: 4px 14px; font-size: 10px; }

    /* Topic chips — tighter row */
    .topic-chip { padding: 5px 12px !important; font-size: 11px !important; }

    .feed-container {
        scroll-snap-type: y mandatory;
        overflow-y: auto;
        /* Leave room for bottom nav (56px) + safe area */
        height: calc(100dvh - 56px - env(safe-area-inset-bottom, 0px));
        scroll-behavior: smooth;
        -webkit-overflow-scrolling: touch;
    }
    .news-card-premium {
        scroll-snap-align: start;
        /* Fixed height = viewport minus top-bar/trust/chips (~110px) minus bottom-nav (~68px) */
        height: calc(100dvh - 178px - env(safe-area-inset-bottom, 0px));
        max-height: calc(100dvh - 178px - env(safe-area-inset-bottom, 0px));
        overflow: hidden;
        border-radius: 0 !important;
        margin-bottom: 0 !important;
        box-shadow: none !important;
        border-bottom: 1px solid var(--border-ghost) !important;
    }
    .card-image-area { height: 26vh; }
    .card-body-area { flex: 1; padding: 8px 14px 4px; overflow: hidden; }
    .card-headline-text { font-size: 16px; -webkit-line-clamp: 2; }
    .card-summary-text { -webkit-line-clamp: 2; font-size: 12px; }

    /* Bottom nav — always visible, proper safe-area for iPhones */
    .bottom-nav {
        padding: 0 !important;
        padding-bottom: max(env(safe-area-inset-bottom, 12px), 12px) !important;
        transform: translateY(0) !important; /* Never hide */
        background: rgba(13, 15, 20, 0.95) !important;
        pointer-events: auto !important;
    }
    .bottom-nav-inner {
        padding: 4px 6px; border-radius: 0;
        max-width: 100%; width: 100%;
        background: transparent;
        backdrop-filter: none; -webkit-backdrop-filter: none;
        border: none; box-shadow: none;
    }
    .nav-btn {
        padding: 8px 0; font-size: 9px;
        min-height: 44px; min-width: 0; flex: 1;
    }
    .nav-btn .material-icons { font-size: 22px !important; }

    /* Detail overlay mobile fixes */
    .detail-cover { height: 200px; }
    .detail-headline { font-size: 20px; }
    .detail-body { padding: 0 16px calc(80px + env(safe-area-inset-bottom, 0px)); }
    .detail-bullet-text { font-size: 14px; }
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
    .news-card-premium:hover {
        transform: translateY(-4px) !important;
        box-shadow: 0 12px 40px rgba(0,0,0,0.3), 0 0 20px rgba(255,184,0,0.04) !important;
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
    .feed-grid .news-card-premium:first-child {
        grid-column: 1 / -1;
    }
}
"""
