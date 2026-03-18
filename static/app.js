/**
 * DailyAI — Frontend App Logic
 * Handles country selection, topic filtering, news fetching, tile rendering,
 * share buttons, newsletter subscription, and auto-refresh.
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
    const topicBar = document.getElementById('topicBar');
    const subscribeForm = document.getElementById('subscribeForm');
    const emailInput = document.getElementById('emailInput');
    const subscriberCount = document.getElementById('subscriberCount');

    // --- State ---
    let currentCountry = localStorage.getItem('dailyai_country') || 'GLOBAL';
    let selectedTopics = JSON.parse(localStorage.getItem('dailyai_topics') || '["all"]');
    let allTiles = []; // unfiltered tiles from server
    let isLoading = false;
    let autoRefreshTimer = null;

    // --- Init ---
    function init() {
        // Restore saved country
        countrySelect.value = currentCountry;

        // Restore topic pills
        restoreTopicSelection();

        // Events
        countrySelect.addEventListener('change', onCountryChange);
        refreshBtn.addEventListener('click', onRefreshClick);

        // Topic pill clicks
        if (topicBar) {
            topicBar.addEventListener('click', onTopicClick);
        }

        // Subscribe form
        if (subscribeForm) {
            subscribeForm.addEventListener('submit', onSubscribe);
        }

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

        // Fetch subscriber count
        fetchSubscriberCount();

        // Auto-refresh every 5 minutes (server does hourly, but we poll)
        autoRefreshTimer = setInterval(() => loadNews(true), 5 * 60 * 1000);
    }

    // --- Topic Selection ---
    function restoreTopicSelection() {
        const pills = document.querySelectorAll('.topic-pill');
        pills.forEach(pill => {
            pill.classList.toggle('active', selectedTopics.includes(pill.dataset.topic));
        });
    }

    function onTopicClick(e) {
        const pill = e.target.closest('.topic-pill');
        if (!pill) return;

        const topic = pill.dataset.topic;

        if (topic === 'all') {
            // "All" deselects everything else
            selectedTopics = ['all'];
        } else {
            // Remove "all" if selecting a specific topic
            selectedTopics = selectedTopics.filter(t => t !== 'all');

            if (selectedTopics.includes(topic)) {
                selectedTopics = selectedTopics.filter(t => t !== topic);
            } else {
                selectedTopics.push(topic);
            }

            // If nothing selected, default back to "all"
            if (selectedTopics.length === 0) {
                selectedTopics = ['all'];
            }
        }

        // Save and update UI
        localStorage.setItem('dailyai_topics', JSON.stringify(selectedTopics));
        restoreTopicSelection();
        filterAndRenderTiles();
    }

    function filterAndRenderTiles() {
        if (selectedTopics.includes('all')) {
            renderTiles(allTiles);
        } else {
            const filtered = allTiles.filter(tile => {
                const tileTopic = (tile.topic || 'general').toLowerCase();
                const tileCategory = (tile.category || 'general').toLowerCase();
                return selectedTopics.includes(tileTopic) || selectedTopics.includes(tileCategory);
            });
            if (filtered.length > 0) {
                renderTiles(filtered);
            } else {
                renderTiles(allTiles); // fallback to show all if no match
                showToast('No stories match your topics — showing all');
            }
        }
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
                allTiles = data.tiles;
                filterAndRenderTiles();
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
            const topic = (tile.topic || 'general').toLowerCase();
            const importance = tile.importance || 5;
            const timeAgo = getTimeAgo(tile.published || tile.fetched_at);
            const link = tile.link || '#';
            const staggerDelay = i * 60;
            const whyItMatters = tile.why_it_matters || '';

            // Build importance dots
            const filledDots = Math.round(importance / 2);
            let dotsHtml = '';
            for (let d = 0; d < 5; d++) {
                if (d < filledDots) {
                    dotsHtml += `<span class="importance-dot ${importance >= 8 ? 'high' : 'active'}"></span>`;
                } else {
                    dotsHtml += `<span class="importance-dot"></span>`;
                }
            }

            // Share text
            const shareText = encodeURIComponent(`${tile.title}\n\n${whyItMatters || tile.summary || ''}\n\nvia DailyAI`);
            const shareUrl = encodeURIComponent(link);

            // Why it matters section
            const whyHtml = whyItMatters
                ? `<p class="tile-why">💡 ${escapeHtml(whyItMatters)}</p>`
                : '';

            return `
                <div class="news-tile" style="animation-delay: ${staggerDelay}ms" id="tile-${i}">
                    <a href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer" class="tile-link">
                        <span class="tile-index">${String(i + 1).padStart(2, '0')}</span>
                        <div class="tile-header">
                            <span class="tile-category ${category}">${escapeHtml(category)}</span>
                            <div class="tile-importance" title="Importance: ${importance}/10">
                                ${dotsHtml}
                            </div>
                        </div>
                        <h2 class="tile-title">${escapeHtml(tile.title)}</h2>
                        <p class="tile-summary">${escapeHtml(tile.summary || '')}</p>
                        ${whyHtml}
                        <div class="tile-footer">
                            <span class="tile-source">${escapeHtml(tile.source || 'Unknown')}</span>
                            <span class="tile-time">${timeAgo}</span>
                        </div>
                    </a>
                    <div class="tile-actions">
                        <button class="share-btn share-twitter" onclick="event.stopPropagation(); window.open('https://twitter.com/intent/tweet?text=${shareText}&url=${shareUrl}', '_blank', 'width=550,height=420')" title="Share on X/Twitter">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                        </button>
                        <button class="share-btn share-linkedin" onclick="event.stopPropagation(); window.open('https://www.linkedin.com/sharing/share-offsite/?url=${shareUrl}', '_blank', 'width=550,height=420')" title="Share on LinkedIn">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    // --- Subscribe ---
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
                    email: email,
                    topics: selectedTopics.includes('all') ? [] : selectedTopics,
                    country: currentCountry,
                }),
            });
            const data = await resp.json();

            if (resp.ok) {
                showToast(`✅ ${data.message}`);
                emailInput.value = '';
                btn.querySelector('.btn-text').textContent = '✓ Subscribed!';
                setTimeout(() => {
                    btn.querySelector('.btn-text').textContent = 'Subscribe';
                }, 3000);
                fetchSubscriberCount();
            } else {
                showToast(`❌ ${data.error || 'Subscription failed'}`);
                btn.querySelector('.btn-text').textContent = 'Subscribe';
            }
        } catch (err) {
            showToast('❌ Network error');
            btn.querySelector('.btn-text').textContent = 'Subscribe';
        } finally {
            btn.disabled = false;
        }
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
        clockDisplay.textContent = new Date().toLocaleString('en-US', {
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
