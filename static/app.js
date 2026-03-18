/**
 * DailyAI — Frontend App Logic
 * Handles country selection, news fetching, tile rendering, and auto-refresh.
 */

(function () {
    'use strict';

    // --- DOM Elements ---
    const countrySelect = document.getElementById('countrySelect');
    const tilesContainer = document.getElementById('tilesContainer');
    const loadingContainer = document.getElementById('loadingContainer');
    const emptyState = document.getElementById('emptyState');
    const updateBadge = document.getElementById('updateBadge');
    const refreshBtn = document.getElementById('refreshBtn');
    const clockDisplay = document.getElementById('clockDisplay');

    // --- State ---
    let currentCountry = localStorage.getItem('dailyai_country') || 'GLOBAL';
    let isLoading = false;
    let autoRefreshTimer = null;

    // --- Init ---
    function init() {
        // Restore saved country
        countrySelect.value = currentCountry;

        // Events
        countrySelect.addEventListener('change', onCountryChange);
        refreshBtn.addEventListener('click', onRefreshClick);

        // Track mouse for glow effect
        document.addEventListener('mousemove', (e) => {
            document.documentElement.style.setProperty('--mouse-x', e.clientX + 'px');
            document.documentElement.style.setProperty('--mouse-y', e.clientY + 'px');
        });

        // Start clock
        updateClock();
        setInterval(updateClock, 1000);

        // Load news
        loadNews();

        // Auto-refresh every 5 minutes (server does hourly, but we poll)
        autoRefreshTimer = setInterval(() => loadNews(true), 5 * 60 * 1000);
    }

    // --- Country Change ---
    function onCountryChange() {
        currentCountry = countrySelect.value;
        localStorage.setItem('dailyai_country', currentCountry);
        loadNews();
    }

    // --- Refresh Click ---
    async function onRefreshClick() {
        if (isLoading) return;
        refreshBtn.classList.add('spinning');
        showToast('Asking AI agent to refresh...');

        try {
            await fetch(`/api/refresh/${currentCountry}`, { method: 'POST' });
            await loadNews();
            showToast('✅ News refreshed!');
        } catch (err) {
            showToast('❌ Refresh failed');
        } finally {
            refreshBtn.classList.remove('spinning');
        }
    }

    // --- Load News ---
    window.loadNews = loadNews; // expose for retry button
    async function loadNews(silent = false) {
        if (isLoading) return;
        isLoading = true;

        if (!silent) {
            showLoading();
        }

        try {
            const resp = await fetch(`/api/news/${currentCountry}`);
            const data = await resp.json();

            if (data.tiles && data.tiles.length > 0) {
                renderTiles(data.tiles);
                updateBadge.textContent = `Updated: ${data.last_updated}`;
            } else {
                showEmpty();
                updateBadge.textContent = 'No data yet';
            }
        } catch (err) {
            console.error('Failed to load news:', err);
            if (!silent) showEmpty();
            updateBadge.textContent = 'Error loading';
        } finally {
            isLoading = false;
        }
    }

    // --- Render Tiles ---
    function renderTiles(tiles) {
        loadingContainer.style.display = 'none';
        emptyState.style.display = 'none';
        tilesContainer.style.display = 'grid';

        tilesContainer.innerHTML = tiles.map((tile, i) => {
            const category = (tile.category || 'general').toLowerCase();
            const importance = tile.importance || 5;
            const timeAgo = getTimeAgo(tile.published || tile.fetched_at);
            const link = tile.link || '#';
            const staggerDelay = i * 60;

            // Build importance dots (show 5 dots, filled based on importance/2)
            const filledDots = Math.round(importance / 2);
            let dotsHtml = '';
            for (let d = 0; d < 5; d++) {
                if (d < filledDots) {
                    dotsHtml += `<span class="importance-dot ${importance >= 8 ? 'high' : 'active'}"></span>`;
                } else {
                    dotsHtml += `<span class="importance-dot"></span>`;
                }
            }

            return `
                <a href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer"
                   class="news-tile" style="animation-delay: ${staggerDelay}ms"
                   id="tile-${i}">
                    <span class="tile-index">${String(i + 1).padStart(2, '0')}</span>
                    <div class="tile-header">
                        <span class="tile-category ${category}">${escapeHtml(category)}</span>
                        <div class="tile-importance" title="Importance: ${importance}/10">
                            ${dotsHtml}
                        </div>
                    </div>
                    <h2 class="tile-title">${escapeHtml(tile.title)}</h2>
                    <p class="tile-summary">${escapeHtml(tile.summary || '')}</p>
                    <div class="tile-footer">
                        <span class="tile-source">${escapeHtml(tile.source || 'Unknown')}</span>
                        <span class="tile-time">${timeAgo}</span>
                    </div>
                </a>
            `;
        }).join('');
    }

    // --- Time Ago ---
    function getTimeAgo(dateStr) {
        if (!dateStr) return '';
        try {
            const date = new Date(dateStr);
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHrs = Math.floor(diffMins / 60);
            const diffDays = Math.floor(diffHrs / 24);

            if (diffMins < 1) return 'Just now';
            if (diffMins < 60) return `${diffMins}m ago`;
            if (diffHrs < 24) return `${diffHrs}h ago`;
            if (diffDays < 7) return `${diffDays}d ago`;
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        } catch {
            return '';
        }
    }

    // --- Show/Hide States ---
    function showLoading() {
        tilesContainer.style.display = 'none';
        emptyState.style.display = 'none';
        loadingContainer.style.display = 'flex';
    }

    function showEmpty() {
        tilesContainer.style.display = 'none';
        loadingContainer.style.display = 'none';
        emptyState.style.display = 'flex';
    }

    // --- Toast ---
    let toastEl = null;
    let toastTimeout = null;
    function showToast(message) {
        if (!toastEl) {
            toastEl = document.createElement('div');
            toastEl.className = 'toast';
            document.body.appendChild(toastEl);
        }
        clearTimeout(toastTimeout);
        toastEl.textContent = message;
        // Force reflow
        toastEl.offsetHeight;
        toastEl.classList.add('show');
        toastTimeout = setTimeout(() => {
            toastEl.classList.remove('show');
        }, 3000);
    }

    // --- Clock ---
    function updateClock() {
        const now = new Date();
        clockDisplay.textContent = now.toLocaleString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
            timeZoneName: 'short',
        });
    }

    // --- Escape HTML ---
    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // --- Service Worker Registration (PWA) ---
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/sw.js').catch(() => {});
    }

    // --- Start ---
    document.addEventListener('DOMContentLoaded', init);
})();
