// DailyAI v3.0 — Swipe + Scroll mode, Onboarding, Auto-dismiss streak
const API_URL = '/api/articles';

(function () {
    'use strict';

    // ---- Config ----
    const TOPIC_GRADIENTS = {
        'AI Models':      'linear-gradient(135deg, #0f2027, #203a43, #2c5364)',
        'Tools':          'linear-gradient(135deg, #1a1a2e, #16213e, #0f3460)',
        'Research':       'linear-gradient(135deg, #0d0d0d, #1a1a2e, #16213e)',
        'Top Stories':    'linear-gradient(135deg, #1f1c2c, #928dab)',
        'Business':       'linear-gradient(135deg, #141e30, #243b55)',
        'Tech & Science': 'linear-gradient(135deg, #0f2027, #203a43, #2c5364)',
    };
    const TOPIC_EMOJIS = {
        'AI Models': '🤖', 'Tools': '🔧', 'Research': '🔬',
        'Top Stories': '⚡', 'Business': '💼', 'Tech & Science': '🧬',
    };
    const COUNTRY_FLAGS = {
        'US':'🇺🇸','GB':'🇬🇧','IN':'🇮🇳','DE':'🇩🇪','FR':'🇫🇷','CA':'🇨🇦',
        'AU':'🇦🇺','JP':'🇯🇵','KR':'🇰🇷','CN':'🇨🇳','BR':'🇧🇷','SG':'🇸🇬',
        'AE':'🇦🇪','IL':'🇮🇱','GLOBAL':'🌐',
    };
    const AVATAR_COLORS = ['#6366f1','#2dd4a0','#f59e0b','#ef4444','#8b5cf6','#3b82f6','#ec4899','#14b8a6'];
    const FALLBACK_ARTICLES = [
        { id:'fb-1', headline:'OpenAI Announces GPT-5 with Multimodal Reasoning', summary:'OpenAI has unveiled GPT-5, featuring advanced multimodal reasoning capabilities that can process text, images, and audio simultaneously.', why_it_matters:'A major leap in AI capability, potentially transforming multiple industries.', topic:'AI Models', source_name:'TechCrunch', source_avatar_url:null, image_url:null, article_url:'#', published_at:new Date().toISOString() },
        { id:'fb-2', headline:'EU Finalizes AI Act Implementation Timeline', summary:'The European Union has released the final implementation timeline for the AI Act, giving companies 12 months to comply.', why_it_matters:'Companies worldwide must adapt their AI products to meet these regulations.', topic:'Top Stories', source_name:'Reuters', source_avatar_url:null, image_url:null, article_url:'#', published_at:new Date().toISOString() },
        { id:'fb-3', headline:'New Open-Source LLM Surpasses Commercial Models', summary:'A new open-source language model has outperformed leading commercial models on multiple benchmarks.', why_it_matters:'Open-source AI is closing the gap, democratizing access to powerful tools.', topic:'Research', source_name:'ArXiv', source_avatar_url:null, image_url:null, article_url:'#', published_at:new Date().toISOString() },
    ];

    // ---- State ----
    let allArticles = [];
    let currentTopic = 'For You';
    let currentCountry = localStorage.getItem('dailyai_country') || 'GLOBAL';
    let currentSort = localStorage.getItem('dailyai_sort') || 'relevance';
    let currentView = 'discover';
    let feedMode = localStorage.getItem('dailyai_mode') || 'swipe'; // 'swipe' or 'scroll'
    let bookmarks = JSON.parse(localStorage.getItem('dailyai_bookmarks') || '{}');
    let swipeCardIndex = 0;
    let isDragging = false, startX = 0, startY = 0, deltaX = 0;

    // ---- DOM ----
    const $ = id => document.getElementById(id);
    const swipeStack = $('swipeStack');
    const swipeContainer = $('swipeContainer');
    const scrollFeed = $('scrollFeed');
    const swipeEmpty = $('swipeEmpty');
    const feed = $('feed');
    const filterTabs = $('filterTabs');
    const sidebar = $('sidebar');
    const sidebarBackdrop = $('sidebarBackdrop');
    const sheetBackdrop = $('sheetBackdrop');
    const bottomSheet = $('bottomSheet');
    const sheetContent = $('sheetContent');
    const toastEl = $('toast');
    const streakBadge = $('streakBadge');
    const viewTitle = $('viewTitle');
    const topBarCountry = $('topBarCountry');
    const countrySelect = $('countrySelect');
    const modeToggle = $('modeToggle');

    // ====================== INIT ======================
    function init() {
        // Sidebar
        $('menuBtn').addEventListener('click', openSidebar);
        $('sidebarClose').addEventListener('click', closeSidebar);
        sidebarBackdrop.addEventListener('click', closeSidebar);

        // Sidebar nav
        $('navDiscover').addEventListener('click', () => switchView('discover'));
        $('navSaved').addEventListener('click', () => switchView('saved'));
        $('savedBtn').addEventListener('click', () => switchView(currentView === 'saved' ? 'discover' : 'saved'));

        // Sort
        $('sortGroup').addEventListener('click', onSortClick);

        // Country
        countrySelect.addEventListener('change', onCountryChange);

        // Newsletter
        $('subscribeForm').addEventListener('submit', onSubscribe);

        // Filter tabs
        filterTabs.addEventListener('click', onTabClick);

        // Mode toggle
        modeToggle.addEventListener('click', toggleFeedMode);

        // Reload
        $('reloadBtn').addEventListener('click', () => {
            swipeCardIndex = 0;
            swipeEmpty.style.display = 'none';
            renderFeed();
        });

        // Bottom sheet
        sheetBackdrop.addEventListener('click', closeSheet);
        document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeSheet(); closeSidebar(); } });
        let sheetTouchStartY = 0;
        bottomSheet.addEventListener('touchstart', e => { sheetTouchStartY = e.touches[0].clientY; }, { passive: true });
        bottomSheet.addEventListener('touchmove', e => {
            if (e.touches[0].clientY - sheetTouchStartY > 80) closeSheet();
        }, { passive: true });

        // Init
        showStreak();
        updateSavedCount();
        restoreSort();
        restoreFeedMode();
        loadCountries();
        fetchSubscriberCount();

        // Onboarding check
        if (!localStorage.getItem('dailyai_onboarded')) {
            showOnboarding();
        }

        // Load feed
        showSkeleton();
        fetchArticles(currentTopic);
    }

    // ====================== ONBOARDING ======================
    function showOnboarding() {
        const overlay = $('onboardingOverlay');
        overlay.style.display = 'flex';

        $('onboardStart').addEventListener('click', () => {
            dismissOnboarding(overlay, 'swipe');
        });
        $('onboardScroll').addEventListener('click', () => {
            dismissOnboarding(overlay, 'scroll');
        });

        // Also dismiss on background tap
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) dismissOnboarding(overlay, feedMode);
        });
    }

    function dismissOnboarding(overlay, mode) {
        localStorage.setItem('dailyai_onboarded', '1');
        overlay.classList.add('hide');
        setTimeout(() => { overlay.style.display = 'none'; }, 400);

        if (mode !== feedMode) {
            feedMode = mode;
            localStorage.setItem('dailyai_mode', feedMode);
            restoreFeedMode();
            renderFeed();
        }
    }

    // ====================== FEED MODE ======================
    function toggleFeedMode() {
        feedMode = feedMode === 'swipe' ? 'scroll' : 'swipe';
        localStorage.setItem('dailyai_mode', feedMode);
        restoreFeedMode();
        renderFeed();
        showToast(feedMode === 'scroll' ? '↕ Scroll mode' : '👆 Swipe mode');
    }

    function restoreFeedMode() {
        if (feedMode === 'scroll') {
            modeToggle.textContent = '👆 Swipe';
            modeToggle.classList.add('active');
        } else {
            modeToggle.textContent = '↕ Scroll';
            modeToggle.classList.remove('active');
        }
    }

    function renderFeed() {
        if (currentView !== 'discover') return;
        if (feedMode === 'scroll') {
            swipeContainer.style.display = 'none';
            scrollFeed.style.display = '';
            renderScrollFeed();
        } else {
            scrollFeed.style.display = 'none';
            swipeContainer.style.display = '';
            renderSwipeStack();
        }
    }

    // ====================== SCROLL FEED (InShorts) ======================
    function renderScrollFeed() {
        scrollFeed.innerHTML = '';
        const articles = getFilteredArticles();
        if (articles.length === 0) {
            scrollFeed.innerHTML = '<div style="padding:60px 20px;text-align:center;"><p style="font-size:48px;margin-bottom:12px;">📰</p><p style="font-size:16px;font-weight:600;">No stories yet</p><p style="font-size:14px;color:var(--text3);margin-top:4px;">Pull down to refresh.</p></div>';
            return;
        }
        articles.forEach(article => {
            const card = createScrollCard(article);
            scrollFeed.appendChild(card);
        });
    }

    function createScrollCard(article) {
        const card = document.createElement('div');
        card.className = 'scroll-card';
        card.dataset.id = article.id;
        const gradient = TOPIC_GRADIENTS[article.topic] || TOPIC_GRADIENTS['Top Stories'];
        const emoji = TOPIC_EMOJIS[article.topic] || '⚡';
        const avatarColor = AVATAR_COLORS[hashCode(article.source_name) % AVATAR_COLORS.length];
        const initial = (article.source_name || 'D')[0].toUpperCase();
        const whyHtml = article.why_it_matters ? `<div class="card-why">💡 ${esc(article.why_it_matters)}</div>` : '';
        const imgHtml = article.image_url
            ? `<img src="${esc(article.image_url)}" alt="" class="card-image" loading="lazy">`
            : `<div class="card-image-placeholder" style="background:${gradient}">${emoji}</div>`;

        const isSaved = !!bookmarks[article.id];
        card.innerHTML = `
            ${imgHtml}
            <div class="card-body">
                <h2 class="card-headline">${esc(article.headline)}</h2>
                <p class="card-summary">${esc(article.summary)}</p>
                ${whyHtml}
                <div class="card-footer">
                    <div class="card-source"><div class="source-avatar" style="background:${avatarColor}">${initial}</div><span class="source-name">${esc(article.source_name)}</span></div>
                    <span class="card-time">${getTimeAgo(article.published_at)}</span>
                </div>
            </div>
        `;
        card.addEventListener('click', () => openSheet(article));
        return card;
    }

    function getFilteredArticles() {
        if (currentTopic === 'For You') return allArticles;
        return allArticles.filter(a => (a.topic || '').toLowerCase() === currentTopic.toLowerCase());
    }

    // ====================== COUNTRIES ======================
    async function loadCountries() {
        try {
            const resp = await fetch('/api/countries');
            const data = await resp.json();
            const countries = data.countries || {};
            countrySelect.innerHTML = '';
            for (const [code, name] of Object.entries(countries)) {
                const flag = COUNTRY_FLAGS[code] || '🏳️';
                const opt = document.createElement('option');
                opt.value = code;
                opt.textContent = `${flag} ${name}`;
                if (code === currentCountry) opt.selected = true;
                countrySelect.appendChild(opt);
            }
            updateTopBarCountry();
        } catch { /* fallback: keep default */ }
    }

    function onCountryChange() {
        currentCountry = countrySelect.value;
        localStorage.setItem('dailyai_country', currentCountry);
        updateTopBarCountry();
        closeSidebar();
        showSkeleton();
        fetchArticles(currentTopic);
        const name = countrySelect.options[countrySelect.selectedIndex]?.textContent || currentCountry;
        showToast(`Switched to ${name}`);
    }

    function updateTopBarCountry() {
        const flag = COUNTRY_FLAGS[currentCountry] || '🏳️';
        const opt = countrySelect.options[countrySelect.selectedIndex];
        const name = opt ? opt.textContent.replace(/^.\s*/, '') : currentCountry;
        topBarCountry.textContent = `${flag} ${name}`;
    }

    // ====================== SUBSCRIBER COUNT ======================
    async function fetchSubscriberCount() {
        try {
            const resp = await fetch('/api/subscribers/count');
            const data = await resp.json();
            const count = data.count || 0;
            if (count > 0) {
                $('subCountVal').textContent = count.toLocaleString();
                $('subCountWrap').style.display = 'block';
            }
        } catch { /* silently ignore */ }
    }

    // ====================== SIDEBAR ======================
    function openSidebar() {
        sidebar.classList.add('show');
        sidebarBackdrop.classList.add('show');
    }
    function closeSidebar() {
        sidebar.classList.remove('show');
        sidebarBackdrop.classList.remove('show');
    }

    // ====================== VIEW SWITCH ======================
    function switchView(view) {
        currentView = view;
        closeSidebar();
        document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));
        if (view === 'discover') {
            $('navDiscover').classList.add('active');
            viewTitle.textContent = 'Discover';
            filterTabs.style.display = '';
            feed.style.display = 'none';
            $('savedBtn').classList.remove('has-saved');
            modeToggle.style.display = '';
            renderFeed();
        } else {
            $('navSaved').classList.add('active');
            viewTitle.textContent = 'Saved';
            filterTabs.style.display = 'none';
            swipeContainer.style.display = 'none';
            scrollFeed.style.display = 'none';
            feed.style.display = '';
            $('savedBtn').classList.add('has-saved');
            modeToggle.style.display = 'none';
            renderSavedList();
        }
    }

    function renderSavedList() {
        const savedIds = Object.keys(bookmarks);
        if (savedIds.length === 0) {
            feed.innerHTML = '<div style="padding:60px 20px;text-align:center;"><p style="font-size:48px;margin-bottom:12px;">🔖</p><p style="font-size:16px;font-weight:600;">No saved articles yet</p><p style="font-size:14px;color:var(--text3);margin-top:4px;">Swipe right on cards to save them here.</p></div>';
            return;
        }
        const saved = allArticles.filter(a => bookmarks[a.id]);
        const storedSaved = Object.values(bookmarks).filter(v => typeof v === 'object' && v.headline);
        const combined = [...saved];
        for (const s of storedSaved) {
            if (!combined.find(c => c.id === s.id)) combined.push(s);
        }
        if (combined.length === 0) {
            feed.innerHTML = '<div style="padding:60px 20px;text-align:center;"><p style="font-size:14px;color:var(--text3);">Saved articles appear after loading the feed.</p></div>';
            return;
        }
        feed.innerHTML = combined.map((a, i) => createFeedCardHTML(a, i)).join('');
        feed.querySelectorAll('.feed-card').forEach(card => {
            card.addEventListener('click', () => {
                const article = combined.find(a => a.id === card.dataset.id);
                if (article) openSheet(article);
            });
        });
    }

    function createFeedCardHTML(article, i) {
        const gradient = TOPIC_GRADIENTS[article.topic] || TOPIC_GRADIENTS['Top Stories'];
        const emoji = TOPIC_EMOJIS[article.topic] || '⚡';
        const avatarColor = AVATAR_COLORS[hashCode(article.source_name) % AVATAR_COLORS.length];
        const initial = (article.source_name || 'D')[0].toUpperCase();
        const whyHtml = article.why_it_matters ? `<div class="card-why">💡 ${esc(article.why_it_matters)}</div>` : '';
        const imgHtml = article.image_url
            ? `<img src="${esc(article.image_url)}" alt="" class="card-image" loading="lazy">`
            : `<div class="card-image-placeholder" style="background:${gradient}">${emoji}</div>`;
        return `<div class="feed-card" data-id="${esc(article.id)}" style="animation-delay:${i*50}ms">
            ${imgHtml}
            <div class="card-body">
                <h2 class="card-headline">${esc(article.headline)}</h2>
                <p class="card-summary">${esc(article.summary)}</p>
                ${whyHtml}
                <div class="card-footer">
                    <div class="card-source"><div class="source-avatar" style="background:${avatarColor}">${initial}</div><span class="source-name">${esc(article.source_name)}</span></div>
                    <span class="card-time">${getTimeAgo(article.published_at)}</span>
                </div>
            </div>
        </div>`;
    }

    // ====================== SORT ======================
    function restoreSort() {
        document.querySelectorAll('.sort-option').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.sort === currentSort);
        });
    }
    function onSortClick(e) {
        const btn = e.target.closest('.sort-option');
        if (!btn || btn.dataset.sort === currentSort) return;
        currentSort = btn.dataset.sort;
        localStorage.setItem('dailyai_sort', currentSort);
        restoreSort();
        sortArticles();
        swipeCardIndex = 0;
        renderFeed();
        closeSidebar();
        showToast(currentSort === 'time' ? '🕐 Sorted by latest' : '⚡ Sorted by relevance');
    }
    function sortArticles() {
        if (currentSort === 'time') {
            allArticles.sort((a, b) => new Date(b.published_at || 0) - new Date(a.published_at || 0));
        }
    }

    // ====================== NEWSLETTER ======================
    async function onSubscribe(e) {
        e.preventDefault();
        const email = $('emailInput').value.trim();
        if (!email) return;
        const btn = $('subscribeBtn');
        btn.disabled = true; btn.textContent = 'Subscribing...';
        try {
            const resp = await fetch('/api/subscribe', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, topics: [], country: currentCountry }),
            });
            const data = await resp.json();
            if (resp.ok) {
                $('subStatus').textContent = '✅ ' + (data.message || 'Subscribed!');
                $('emailInput').value = '';
                btn.textContent = '✓ Done!';
                showToast('Subscribed! 🎉');
                fetchSubscriberCount();
                setTimeout(() => { btn.textContent = 'Subscribe'; }, 3000);
            } else {
                $('subStatus').textContent = '❌ ' + (data.error || 'Failed');
                btn.textContent = 'Subscribe';
            }
        } catch {
            $('subStatus').textContent = '❌ Network error';
            btn.textContent = 'Subscribe';
        } finally { btn.disabled = false; }
    }

    // ====================== FETCH ======================
    async function fetchArticles(topic) {
        const param = topic === 'For You' ? 'all' : topic;
        const timeout = new Promise((_, reject) => setTimeout(() => reject('timeout'), 8000));
        try {
            const resp = await Promise.race([
                fetch(`${API_URL}?topic=${encodeURIComponent(param)}&country=${encodeURIComponent(currentCountry)}`),
                timeout,
            ]);
            const data = await resp.json();
            allArticles = (data.articles && data.articles.length > 0) ? data.articles : FALLBACK_ARTICLES;
        } catch {
            allArticles = FALLBACK_ARTICLES;
        }
        sortArticles();
        swipeCardIndex = 0;
        swipeEmpty.style.display = 'none';
        renderFeed();
    }

    // ====================== TABS ======================
    function onTabClick(e) {
        const pill = e.target.closest('.filter-pill');
        if (!pill || pill.classList.contains('active')) return;
        document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        currentTopic = pill.dataset.topic;
        showSkeleton();
        fetchArticles(currentTopic);
    }

    // ====================== SWIPE STACK ======================
    function renderSwipeStack() {
        swipeStack.innerHTML = '';
        const remaining = allArticles.slice(swipeCardIndex);
        if (remaining.length === 0) {
            swipeEmpty.style.display = 'flex';
            return;
        }
        const visible = remaining.slice(0, 3);
        visible.forEach((article) => {
            const card = createSwipeCard(article);
            swipeStack.appendChild(card);
        });
        const topCard = swipeStack.firstElementChild;
        if (topCard) attachSwipeListeners(topCard);
    }

    function createSwipeCard(article) {
        const card = document.createElement('div');
        card.className = 'swipe-card';
        card.dataset.id = article.id;
        const gradient = TOPIC_GRADIENTS[article.topic] || TOPIC_GRADIENTS['Top Stories'];
        const emoji = TOPIC_EMOJIS[article.topic] || '⚡';
        const avatarColor = AVATAR_COLORS[hashCode(article.source_name) % AVATAR_COLORS.length];
        const initial = (article.source_name || 'D')[0].toUpperCase();
        const whyHtml = article.why_it_matters ? `<div class="card-why">💡 ${esc(article.why_it_matters)}</div>` : '';
        const imgHtml = article.image_url
            ? `<img src="${esc(article.image_url)}" alt="" class="card-image" loading="lazy">`
            : `<div class="card-image-placeholder" style="background:${gradient}">${emoji}</div>`;
        card.innerHTML = `
            <div class="swipe-label swipe-label-save">SAVE</div>
            <div class="swipe-label swipe-label-skip">SKIP</div>
            ${imgHtml}
            <div class="card-body">
                <h2 class="card-headline">${esc(article.headline)}</h2>
                <p class="card-summary">${esc(article.summary)}</p>
                ${whyHtml}
                <div class="card-footer">
                    <div class="card-source"><div class="source-avatar" style="background:${avatarColor}">${initial}</div><span class="source-name">${esc(article.source_name)}</span></div>
                    <span class="card-time">${getTimeAgo(article.published_at)}</span>
                </div>
            </div>
        `;
        card.addEventListener('click', () => { if (Math.abs(deltaX) < 5) openSheet(article); });
        return card;
    }

    // ====================== SWIPE ENGINE ======================
    function attachSwipeListeners(card) {
        card.addEventListener('touchstart', onPointerDown, { passive: true });
        card.addEventListener('touchmove', onPointerMove, { passive: false });
        card.addEventListener('touchend', onPointerUp, { passive: true });
        card.addEventListener('mousedown', onPointerDown);
    }
    function onPointerDown(e) {
        isDragging = true; deltaX = 0;
        const p = e.touches ? e.touches[0] : e;
        startX = p.clientX; startY = p.clientY;
        if (!e.touches) { document.addEventListener('mousemove', onPointerMove); document.addEventListener('mouseup', onPointerUp); }
    }
    function onPointerMove(e) {
        if (!isDragging) return;
        const p = e.touches ? e.touches[0] : e;
        deltaX = p.clientX - startX;
        const deltaY = p.clientY - startY;
        if (Math.abs(deltaY) > Math.abs(deltaX) && Math.abs(deltaX) < 20) return;
        if (e.cancelable) e.preventDefault();
        const card = swipeStack.firstElementChild;
        if (!card) return;
        card.style.transform = `translateX(${deltaX}px) rotate(${deltaX * 0.08}deg)`;
        card.style.transition = 'none';
        const t = 40;
        const saveL = card.querySelector('.swipe-label-save');
        const skipL = card.querySelector('.swipe-label-skip');
        saveL.style.opacity = deltaX > t ? Math.min((deltaX - t) / 60, 1) : 0;
        skipL.style.opacity = deltaX < -t ? Math.min((-deltaX - t) / 60, 1) : 0;
    }
    function onPointerUp() {
        isDragging = false;
        document.removeEventListener('mousemove', onPointerMove);
        document.removeEventListener('mouseup', onPointerUp);
        const card = swipeStack.firstElementChild;
        if (!card) return;
        if (deltaX > 80) { flyOut(card, 1); }
        else if (deltaX < -80) { flyOut(card, -1); }
        else {
            card.classList.add('animating');
            card.style.transform = '';
            card.querySelector('.swipe-label-save').style.opacity = 0;
            card.querySelector('.swipe-label-skip').style.opacity = 0;
            setTimeout(() => card.classList.remove('animating'), 400);
        }
    }
    function flyOut(card, dir) {
        const article = allArticles[swipeCardIndex];
        card.classList.add('animating');
        card.style.transform = `translateX(${dir * 500}px) rotate(${dir * 30}deg)`;
        card.style.opacity = '0';
        if (dir > 0 && article) {
            bookmarks[article.id] = article;
            localStorage.setItem('dailyai_bookmarks', JSON.stringify(bookmarks));
            showToast('Saved! 🔖');
            updateSavedCount();
        }
        swipeCardIndex++;
        setTimeout(() => renderSwipeStack(), 350);
    }
    function updateSavedCount() {
        const count = Object.keys(bookmarks).length;
        $('savedCount').textContent = count;
        if (count > 0) $('savedBtn').classList.add('has-saved');
    }

    // ====================== SKELETON ======================
    function showSkeleton() {
        swipeStack.innerHTML = `
            <div class="skeleton-card">
                <div class="skeleton-image"></div>
                <div class="skeleton-body">
                    <div class="skeleton-line w80"></div>
                    <div class="skeleton-line w60"></div>
                    <div class="skeleton-line w40"></div>
                </div>
            </div>`;
    }

    // ====================== BOTTOM SHEET ======================
    function openSheet(article) {
        const whyHtml = article.why_it_matters ? `<div class="sheet-why">💡 ${esc(article.why_it_matters)}</div>` : '';
        const isSaved = !!bookmarks[article.id];
        sheetContent.innerHTML = `
            <h2 class="sheet-headline">${esc(article.headline)}</h2>
            <p class="sheet-summary">${esc(article.summary)}</p>
            ${whyHtml}
            <p class="sheet-meta">${esc(article.source_name)} • ${getTimeAgo(article.published_at)}</p>
            <div style="display:flex;gap:10px;flex-wrap:wrap;">
                <a href="${esc(article.article_url)}" target="_blank" rel="noopener noreferrer" class="sheet-link">Read original →</a>
                <button class="sheet-link" style="border:1px solid var(--accent);background:none;color:var(--accent);cursor:pointer;" onclick="this.closest('.sheet-content').querySelector('.save-feedback').style.display='block';${isSaved ? '' : `window._saveFromSheet('${esc(article.id)}')`}">${isSaved ? '✓ Saved' : '🔖 Save'}</button>
            </div>
            <p class="save-feedback" style="display:none;margin-top:8px;font-size:12px;color:var(--accent);">✓ Added to saved articles</p>
        `;
        // Expose save function
        window._saveFromSheet = (id) => {
            const a = allArticles.find(x => x.id === id);
            if (a) {
                bookmarks[a.id] = a;
                localStorage.setItem('dailyai_bookmarks', JSON.stringify(bookmarks));
                updateSavedCount();
            }
        };
        sheetBackdrop.classList.add('show');
        bottomSheet.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
    function closeSheet() {
        sheetBackdrop.classList.remove('show');
        bottomSheet.classList.remove('show');
        document.body.style.overflow = '';
    }

    // ====================== STREAK ======================
    function showStreak() {
        const today = new Date().toISOString().slice(0, 10);
        const lastDay = localStorage.getItem('dailyai_streak_day');
        let streak = parseInt(localStorage.getItem('dailyai_streak_count') || '0', 10);
        if (lastDay !== today) {
            const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
            streak = (lastDay === yesterday) ? streak + 1 : 1;
            localStorage.setItem('dailyai_streak_day', today);
            localStorage.setItem('dailyai_streak_count', String(streak));
        }
        // Show in sidebar
        $('sidebarStreak').textContent = `🔥 Day ${streak} reading streak`;
        // Show floating badge — auto-dismiss after 4 seconds
        if (!sessionStorage.getItem('dailyai_streak_dismissed') && streak >= 1) {
            streakBadge.textContent = `🔥 Day ${streak} reading DailyAI`;
            streakBadge.style.display = 'block';
            // Fade in after animation delay
            setTimeout(() => streakBadge.classList.add('visible'), 600);
            // Auto fade out after 4 seconds
            setTimeout(() => {
                streakBadge.classList.add('fade-out');
                sessionStorage.setItem('dailyai_streak_dismissed', '1');
                setTimeout(() => { streakBadge.style.display = 'none'; }, 1000);
            }, 4000);
        }
    }

    // ====================== TOAST ======================
    let toastTimeout = null;
    function showToast(msg) {
        clearTimeout(toastTimeout);
        toastEl.textContent = msg;
        toastEl.classList.add('show');
        toastTimeout = setTimeout(() => toastEl.classList.remove('show'), 2000);
    }

    // ====================== UTILS ======================
    function getTimeAgo(dateStr) {
        if (!dateStr) return '';
        try {
            const d = new Date(dateStr), now = new Date();
            const m = Math.floor((now - d) / 60000);
            if (m < 1) return 'Just now';
            if (m < 60) return `${m}m ago`;
            const h = Math.floor(m / 60);
            if (h < 24) return `${h}h ago`;
            const dy = Math.floor(h / 24);
            if (dy < 7) return `${dy}d ago`;
            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        } catch { return ''; }
    }
    function hashCode(str) { let h=0; for(let i=0;i<(str||'').length;i++){h=((h<<5)-h)+str.charCodeAt(i);h|=0;} return Math.abs(h); }
    function esc(s) { const d=document.createElement('div'); d.textContent=s||''; return d.innerHTML; }

    document.addEventListener('DOMContentLoaded', init);
})();
