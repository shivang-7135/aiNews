/**
 * DailyAI — Frontend App Logic
 * Handles: hero banner, AI thought, topic filtering, sort toggle,
 * tile expand modal, share buttons, newsletter subscription, auto-refresh,
 * theme switching, onboarding.
 */

(function () {
    'use strict';

    // --- Category Emoji Map ---
    const CATEGORY_EMOJIS = {
        breakthrough: '🔬',
        product: '🚀',
        regulation: '⚖️',
        funding: '💰',
        research: '📄',
        industry: '🏢',
        general: '📰',
    };

    // --- Loading emoji cycle ---
    const LOADING_EMOJIS = ['🔍', '🤖', '📡', '🧠', '⚡', '✨'];
    let loadingEmojiInterval = null;

    // --- DOM Elements ---
    const countrySelect = document.getElementById('countrySelect');
    const tilesContainer = document.getElementById('tilesContainer');
    const loadingContainer = document.getElementById('loadingContainer');
    const emptyState = document.getElementById('emptyState');
    const updateBadge = document.getElementById('updateBadge');
    const refreshBtn = document.getElementById('refreshBtn');
    const clockDisplay = document.getElementById('clockDisplay');
    const topicBar = document.getElementById('topicBar');
    const topicScroll = document.getElementById('topicScroll');
    const subscribeForm = document.getElementById('subscribeForm');
    const emailInput = document.getElementById('emailInput');
    const subscriberCount = document.getElementById('subscriberCount');
    const heroBanner = document.getElementById('heroBanner');
    const heroTitle = document.getElementById('heroTitle');
    const heroSummary = document.getElementById('heroSummary');
    const heroWhy = document.getElementById('heroWhy');
    const heroLink = document.getElementById('heroLink');
    const heroMeta = document.getElementById('heroMeta');
    const thoughtBanner = document.getElementById('thoughtBanner');
    const modalOverlay = document.getElementById('modalOverlay');
    const sortToggle = document.getElementById('sortToggle');
    const onboardingBanner = document.getElementById('onboardingBanner');
    const statsTicker = document.getElementById('statsTicker');

    // --- State ---
    let currentCountry = localStorage.getItem('dailyai_country') || 'GLOBAL';
    let selectedTopics = JSON.parse(localStorage.getItem('dailyai_topics') || '["all"]');
    let currentSort = localStorage.getItem('dailyai_sort') || 'relevance';
    let allTiles = [];
    let renderedTiles = []; // keep a ref to what's actually shown
    let isLoading = false;

    // --- Init ---
    function init() {
        countrySelect.value = currentCountry;
        restoreTopicSelection();
        restoreSortSelection();
        showOnboarding();
        initTheme();

        // Events
        countrySelect.addEventListener('change', onCountryChange);
        refreshBtn.addEventListener('click', onRefreshClick);
        if (topicBar) topicBar.addEventListener('click', onTopicClick);
        if (subscribeForm) subscribeForm.addEventListener('submit', onSubscribe);
        if (sortToggle) sortToggle.addEventListener('click', onSortClick);

        // Theme toggle
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) themeToggle.addEventListener('click', toggleTheme);

        // Onboarding dismiss
        const onboardingClose = document.getElementById('onboardingClose');
        if (onboardingClose) onboardingClose.addEventListener('click', () => {
            onboardingBanner.style.display = 'none';
            localStorage.setItem('dailyai_onboarded', '1');
        });

        // Topic scroll arrows
        const scrollLeft = document.getElementById('topicScrollLeft');
        const scrollRight = document.getElementById('topicScrollRight');
        if (scrollLeft) scrollLeft.addEventListener('click', () => topicScroll.scrollBy({ left: -150, behavior: 'smooth' }));
        if (scrollRight) scrollRight.addEventListener('click', () => topicScroll.scrollBy({ left: 150, behavior: 'smooth' }));

        // Modal close
        const modalClose = document.getElementById('modalClose');
        if (modalClose) modalClose.addEventListener('click', closeModal);
        if (modalOverlay) modalOverlay.addEventListener('click', (e) => { if (e.target === modalOverlay) closeModal(); });
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });

        // Thought dismiss
        const thoughtClose = document.getElementById('thoughtClose');
        if (thoughtClose) thoughtClose.addEventListener('click', () => {
            thoughtBanner.style.display = 'none';
            sessionStorage.setItem('dailyai_thought_dismissed', '1');
        });

        // Mouse glow (only on non-touch devices)
        if (!('ontouchstart' in window)) {
            document.addEventListener('mousemove', (e) => {
                document.documentElement.style.setProperty('--mouse-x', e.clientX + 'px');
                document.documentElement.style.setProperty('--mouse-y', e.clientY + 'px');
            });
        }

        updateClock();
        setInterval(updateClock, 1000);
        loadNews();
        loadThought();
        fetchSubscriberCount();
        setInterval(() => loadNews(true), 5 * 60 * 1000);
    }

    // ====================== THEME ======================
    function initTheme() {
        const saved = localStorage.getItem('dailyai_theme') || 'light';
        document.documentElement.setAttribute('data-theme', saved);
        updateThemeIcon(saved);
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('dailyai_theme', next);
        updateThemeIcon(next);
    }

    function updateThemeIcon(theme) {
        const btn = document.getElementById('themeToggle');
        if (!btn) return;
        btn.innerHTML = theme === 'dark'
            ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>'
            : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
        btn.title = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
    }

    // ====================== ONBOARDING ======================
    function showOnboarding() {
        if (!localStorage.getItem('dailyai_onboarded') && onboardingBanner) {
            onboardingBanner.style.display = 'block';
        }
    }

    // ====================== AI THOUGHT ======================
    async function loadThought() {
        if (sessionStorage.getItem('dailyai_thought_dismissed')) return;
        try {
            const resp = await fetch('/api/thought');
            const data = await resp.json();
            if (data.text) {
                document.getElementById('thoughtEmoji').textContent = data.emoji || '🧠';
                document.getElementById('thoughtText').textContent = data.text;
                thoughtBanner.style.display = 'flex';
                thoughtBanner.className = `thought-banner vibe-${data.vibe || 'chill'}`;
            }
        } catch {}
    }

    // ====================== HERO BANNER ======================
    function renderHero(hero) {
        if (!hero) {
            heroBanner.style.display = 'none';
            return;
        }
        heroTitle.textContent = hero.title || '';
        heroSummary.textContent = hero.summary || '';
        heroWhy.textContent = hero.why_it_matters ? `💡 ${hero.why_it_matters}` : '';
        heroLink.href = hero.link || '#';
        heroMeta.textContent = `${hero.source || 'Unknown'} • ${getTimeAgo(hero.published || hero.fetched_at)}`;
        heroBanner.style.display = 'block';
    }

    // ====================== SORT ======================
    function restoreSortSelection() {
        document.querySelectorAll('.sort-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.sort === currentSort);
        });
    }

    function onSortClick(e) {
        const btn = e.target.closest('.sort-btn');
        if (!btn || btn.dataset.sort === currentSort) return;
        currentSort = btn.dataset.sort;
        localStorage.setItem('dailyai_sort', currentSort);
        restoreSortSelection();
        filterAndRenderTiles();
    }

    function sortTiles(tiles) {
        const sorted = [...tiles];
        if (currentSort === 'time') {
            sorted.sort((a, b) => {
                const da = new Date(a.published || a.fetched_at || 0);
                const db = new Date(b.published || b.fetched_at || 0);
                return db - da;
            });
        } else {
            sorted.sort((a, b) => (b.importance || 0) - (a.importance || 0));
        }
        return sorted;
    }

    // ====================== TOPICS ======================
    function restoreTopicSelection() {
        document.querySelectorAll('.topic-pill').forEach(pill => {
            pill.classList.toggle('active', selectedTopics.includes(pill.dataset.topic));
        });
    }

    function onTopicClick(e) {
        const pill = e.target.closest('.topic-pill');
        if (!pill) return;
        const topic = pill.dataset.topic;

        if (topic === 'all') {
            selectedTopics = ['all'];
        } else {
            selectedTopics = selectedTopics.filter(t => t !== 'all');
            if (selectedTopics.includes(topic)) {
                selectedTopics = selectedTopics.filter(t => t !== topic);
            } else {
                selectedTopics.push(topic);
            }
            if (selectedTopics.length === 0) selectedTopics = ['all'];
        }

        localStorage.setItem('dailyai_topics', JSON.stringify(selectedTopics));
        restoreTopicSelection();
        filterAndRenderTiles();
    }

    function filterAndRenderTiles() {
        let filtered = allTiles;
        if (!selectedTopics.includes('all')) {
            const topicFiltered = allTiles.filter(tile => {
                const tt = (tile.topic || 'general').toLowerCase();
                const tc = (tile.category || 'general').toLowerCase();
                return selectedTopics.includes(tt) || selectedTopics.includes(tc);
            });
            if (topicFiltered.length > 0) {
                filtered = topicFiltered;
            } else {
                showToast('No stories match — showing all');
            }
        }
        const sorted = sortTiles(filtered);
        renderedTiles = sorted; // store reference for modal click
        renderTiles(sorted);
        updateStats(sorted.length);
    }

    // ====================== STATS TICKER ======================
    function updateStats(storyCount) {
        const el = document.getElementById('statsStories');
        if (el) animateCounter(el, storyCount);
        if (statsTicker) statsTicker.classList.add('visible');
    }

    function animateCounter(el, target) {
        const duration = 800;
        const start = parseInt(el.textContent) || 0;
        const diff = target - start;
        if (diff === 0) { el.textContent = target; return; }

        const startTime = performance.now();
        function step(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.round(start + diff * eased);
            if (progress < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
    }

    function updateStatsTime(timeStr) {
        const el = document.getElementById('statsUpdated');
        if (el && timeStr && timeStr !== '—') {
            el.textContent = timeStr.replace('Updated: ', '');
        }
    }

    // ====================== LOAD NEWS ======================
    function onCountryChange() {
        currentCountry = countrySelect.value;
        localStorage.setItem('dailyai_country', currentCountry);
        loadNews();
    }

    async function onRefreshClick() {
        if (isLoading) return;
        refreshBtn.classList.add('spinning');
        showToast('Asking AI agent to refresh...');
        try {
            await fetch(`/api/refresh/${currentCountry}`, { method: 'POST' });
            await loadNews();
            showToast('✅ News refreshed!');
        } catch { showToast('❌ Refresh failed'); }
        finally { refreshBtn.classList.remove('spinning'); }
    }

    window.loadNews = loadNews;
    async function loadNews(silent = false) {
        if (isLoading) return;
        isLoading = true;
        if (!silent) showLoading();

        try {
            const resp = await fetch(`/api/news/${currentCountry}`);
            const data = await resp.json();

            renderHero(data.hero_tile || null);

            if (data.tiles && data.tiles.length > 0) {
                allTiles = data.tiles;
                filterAndRenderTiles();
                updateBadge.textContent = `Updated: ${data.last_updated}`;
                updateStatsTime(data.last_updated);
            } else if (data.hero_tile) {
                allTiles = [];
                tilesContainer.style.display = 'none';
                loadingContainer.style.display = 'none';
                emptyState.style.display = 'none';
                updateBadge.textContent = `Updated: ${data.last_updated}`;
            } else {
                showEmpty();
                updateBadge.textContent = 'No data yet';
            }
        } catch (err) {
            console.error('Load failed:', err);
            if (!silent) showEmpty();
            updateBadge.textContent = 'Error loading';
        } finally {
            isLoading = false;
            stopLoadingEmojis();
        }
    }

    // ====================== RENDER TILES ======================
    function renderTiles(tiles) {
        loadingContainer.style.display = 'none';
        emptyState.style.display = 'none';
        tilesContainer.style.display = 'grid';

        tilesContainer.innerHTML = tiles.map((tile, i) => {
            const category = (tile.category || 'general').toLowerCase();
            const emoji = CATEGORY_EMOJIS[category] || '📰';
            const importance = tile.importance || 5;
            const timeAgo = getTimeAgo(tile.published || tile.fetched_at);
            const whyItMatters = tile.why_it_matters || '';
            const staggerDelay = i * 60;

            const impPercent = Math.round((importance / 10) * 100);
            const impClass = importance >= 8 ? 'high' : importance >= 5 ? 'mid' : 'low';

            const shareText = encodeURIComponent(`${tile.title}\n\nvia DailyAI`);
            const shareUrl = encodeURIComponent(tile.link || '');
            const whyHtml = whyItMatters ? `<p class="tile-why">💡 ${escapeHtml(whyItMatters)}</p>` : '';

            return `
                <div class="news-tile cat-${category}" style="animation-delay:${staggerDelay}ms" id="tile-${i}"
                     onclick="openModal(${i})" role="button" tabindex="0">
                    <div class="tile-shine"></div>
                    <div class="tile-body">
                        <div class="tile-header">
                            <div class="tile-icon ${category}">${emoji}</div>
                            <div class="tile-header-text">
                                <span class="tile-category ${category}">${escapeHtml(category)}</span>
                                <div class="tile-importance-bar">
                                    <div class="importance-track">
                                        <div class="importance-fill ${impClass}" style="width:${impPercent}%"></div>
                                    </div>
                                    <span class="importance-num">${importance}/10</span>
                                </div>
                            </div>
                        </div>
                        <h2 class="tile-title">${escapeHtml(tile.title)}</h2>
                        <p class="tile-summary">${escapeHtml(tile.summary || '')}</p>
                        ${whyHtml}
                        <div class="tile-footer">
                            <span class="tile-source">${escapeHtml(tile.source || 'Unknown')}</span>
                            <span class="tile-time">${timeAgo}</span>
                        </div>
                        <div class="tile-actions" onclick="event.stopPropagation()">
                            <button class="share-btn share-twitter" onclick="event.stopPropagation(); window.open('https://twitter.com/intent/tweet?text=${shareText}&url=${shareUrl}','_blank','width=550,height=420')" title="Share on X">
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                            </button>
                            <button class="share-btn share-linkedin" onclick="event.stopPropagation(); window.open('https://www.linkedin.com/sharing/share-offsite/?url=${shareUrl}','_blank','width=550,height=420')" title="Share on LinkedIn">
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                            </button>
                        </div>
                    </div>
                    <div class="tile-cta">Tap to expand ↗</div>
                </div>`;
        }).join('');
    }

    // ====================== EXPAND MODAL ======================
    window.openModal = function(index) {
        // Use renderedTiles — the exact array that was rendered, so indices always match
        const tile = renderedTiles[index];
        if (!tile) return;

        const category = (tile.category || 'general').toLowerCase();
        const emoji = CATEGORY_EMOJIS[category] || '📰';
        const importance = tile.importance || 5;
        const impPercent = Math.round((importance / 10) * 100);
        const impClass = importance >= 8 ? 'high' : importance >= 5 ? 'mid' : 'low';

        const modalIconEl = document.getElementById('modalIcon');
        if (modalIconEl) {
            modalIconEl.className = `modal-icon ${category}`;
            modalIconEl.textContent = emoji;
        }

        document.getElementById('modalBadge').innerHTML = `<span class="tile-category ${category}">${escapeHtml(category)}</span>`;
        document.getElementById('modalTitle').textContent = tile.title || '';
        document.getElementById('modalSummary').textContent = tile.summary || '';

        const whyBox = document.getElementById('modalWhyBox');
        if (whyBox) {
            if (tile.why_it_matters) {
                whyBox.style.display = 'block';
                document.getElementById('modalWhyText').textContent = tile.why_it_matters;
            } else {
                whyBox.style.display = 'none';
            }
        }

        const impBar = document.getElementById('modalImportance');
        if (impBar) {
            document.getElementById('modalImpFill').className = `modal-importance-fill ${impClass}`;
            document.getElementById('modalImpFill').style.width = `${impPercent}%`;
            document.getElementById('modalImpLabel').textContent = `${importance}/10`;
        }

        document.getElementById('modalMeta').textContent = `${tile.source || 'Unknown'} • ${getTimeAgo(tile.published || tile.fetched_at)}`;
        document.getElementById('modalLink').href = tile.link || '#';

        const shareText = encodeURIComponent(`${tile.title}\n\nvia DailyAI`);
        const shareUrl = encodeURIComponent(tile.link || '');
        document.getElementById('modalShare').innerHTML = `
            <button class="share-btn share-twitter" onclick="window.open('https://twitter.com/intent/tweet?text=${shareText}&url=${shareUrl}','_blank','width=550,height=420')" title="Share on X">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
            </button>
            <button class="share-btn share-linkedin" onclick="window.open('https://www.linkedin.com/sharing/share-offsite/?url=${shareUrl}','_blank','width=550,height=420')" title="Share on LinkedIn">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
            </button>`;

        modalOverlay.classList.add('show');
        document.body.style.overflow = 'hidden';
    };

    function closeModal() {
        modalOverlay.classList.remove('show');
        document.body.style.overflow = '';
    }

    // ====================== SUBSCRIBE ======================
    async function onSubscribe(e) {
        e.preventDefault();
        const email = emailInput.value.trim();
        if (!email) return;

        const btn = document.getElementById('subscribeBtn');
        btn.disabled = true;
        btn.querySelector('.btn-text').textContent = 'Subscribing...';

        try {
            const resp = await fetch('/api/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email,
                    topics: selectedTopics.includes('all') ? [] : selectedTopics,
                    country: currentCountry,
                }),
            });
            const data = await resp.json();
            if (resp.ok) {
                showToast(`✅ ${data.message}`);
                emailInput.value = '';
                btn.querySelector('.btn-text').textContent = '✓ Subscribed!';
                setTimeout(() => { btn.querySelector('.btn-text').textContent = 'Subscribe'; }, 3000);
                fetchSubscriberCount();
            } else {
                showToast(`❌ ${data.error || 'Failed'}`);
                btn.querySelector('.btn-text').textContent = 'Subscribe';
            }
        } catch {
            showToast('❌ Network error');
            btn.querySelector('.btn-text').textContent = 'Subscribe';
        } finally { btn.disabled = false; }
    }

    async function fetchSubscriberCount() {
        try {
            const resp = await fetch('/api/subscribers/count');
            const data = await resp.json();
            if (data.count > 0 && subscriberCount) {
                subscriberCount.textContent = `${data.count} reader${data.count === 1 ? '' : 's'} subscribed`;
                subscriberCount.style.display = 'inline-block';
            }
        } catch {}
    }

    // ====================== UTILITIES ======================
    function getTimeAgo(dateStr) {
        if (!dateStr) return '';
        try {
            const d = new Date(dateStr), now = new Date(), ms = now - d;
            const m = Math.floor(ms / 60000), h = Math.floor(m / 60), dy = Math.floor(h / 24);
            if (m < 1) return 'Just now';
            if (m < 60) return `${m}m ago`;
            if (h < 24) return `${h}h ago`;
            if (dy < 7) return `${dy}d ago`;
            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        } catch { return ''; }
    }

    function showLoading() {
        tilesContainer.style.display = 'none';
        emptyState.style.display = 'none';
        loadingContainer.style.display = 'flex';
        startLoadingEmojis();
    }

    function startLoadingEmojis() {
        let idx = 0;
        const el = document.getElementById('morphEmoji');
        if (!el) return;
        loadingEmojiInterval = setInterval(() => {
            idx = (idx + 1) % LOADING_EMOJIS.length;
            el.textContent = LOADING_EMOJIS[idx];
        }, 1500);
    }

    function stopLoadingEmojis() {
        if (loadingEmojiInterval) {
            clearInterval(loadingEmojiInterval);
            loadingEmojiInterval = null;
        }
    }

    function showEmpty() { tilesContainer.style.display = 'none'; loadingContainer.style.display = 'none'; emptyState.style.display = 'flex'; }

    let toastEl = null, toastTimeout = null;
    function showToast(msg) {
        if (!toastEl) { toastEl = document.createElement('div'); toastEl.className = 'toast'; document.body.appendChild(toastEl); }
        clearTimeout(toastTimeout);
        toastEl.textContent = msg;
        toastEl.offsetHeight;
        toastEl.classList.add('show');
        toastTimeout = setTimeout(() => toastEl.classList.remove('show'), 3000);
    }

    function updateClock() {
        clockDisplay.textContent = new Date().toLocaleString('en-US', {
            hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, timeZoneName: 'short',
        });
    }

    function escapeHtml(str) { const d = document.createElement('div'); d.textContent = str; return d.innerHTML; }

    if ('serviceWorker' in navigator) navigator.serviceWorker.register('/static/sw.js').catch(() => {});

    document.addEventListener('DOMContentLoaded', init);
})();
