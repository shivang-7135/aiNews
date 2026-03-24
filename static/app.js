// DailyAI v3.0 — Swipe + Scroll mode, Onboarding, Auto-dismiss streak
const API_URL = '/api/articles';
const FEED_CACHE_PREFIX = 'dailyai_feed_cache_v2';
const BRIEF_CACHE_PREFIX = 'dailyai_brief_cache_v1';
const FEED_CACHE_TTL_MS = 25 * 60 * 1000;
const BRIEF_CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000;
const RELEASE_VERSION = document.documentElement.dataset.releaseVersion || 'dev';
const VERSION_POLL_MS = 45 * 1000;
const BUILD_MARKER_KEY = 'dailyai_last_loaded_build';
const APP_FUNCTIONALITY_GUIDE = {
    en: [
        'Swipe right to save and left to skip stories you do not need.',
        'Open Menu to change language, country, sort order, and refresh news.',
        'Tap any card to open detailed reading view with source link.',
        'Use Expand View inside article panel for more comfortable reading.',
        'Your feed is cached, so repeat opens are faster and lighter on data.',
    ],
    hi: [
        'पसंदीदा खबरें सेव करने के लिए दाएं स्वाइप करें और छोड़ने के लिए बाएं स्वाइप करें।',
        'Menu से भाषा, देश, सॉर्ट और Refresh News कंट्रोल करें।',
        'किसी भी कार्ड पर टैप करके विस्तृत पढ़ने वाला व्यू और source लिंक खोलें।',
        'अच्छी पढ़ाई के लिए आर्टिकल पैनल में Expand View का उपयोग करें।',
        'फीड कैश में सेव रहती है, इसलिए अगली बार ऐप तेज खुलेगा।',
    ],
    de: [
        'Nach rechts wischen speichert Stories, nach links werden sie uebersprungen.',
        'Im Menu kannst du Sprache, Land, Sortierung und News aktualisieren steuern.',
        'Tippe auf eine Karte fuer die Detailansicht mit Originalquelle.',
        'Nutze Expand View im Artikelbereich fuer angenehmes Lesen.',
        'Der Feed wird lokal zwischengespeichert und laedt beim naechsten Mal schneller.',
    ],
};

(function () {
    'use strict';

    const I18N = {
        en: {
            htmlLang: 'en',
            pageTitle: 'DailyAI - Discover AI News',
            pageDescription: 'DailyAI - AI news, curated daily. No login required.',
            onboardingTitle: 'Welcome to DailyAI',
            onboardingDesc: 'Discover what you can do in one place.',
            onboardingFeatureSwipe: 'Swipe right to save and left to skip.',
            onboardingFeatureLanguage: 'Change language from the sidebar.',
            onboardingFeatureCountry: 'Change country to localize your feed.',
            onboardingFeatureRead: 'Tap a card to read a detailed brief.',
            onboardingFeatureCache: 'Stories are cached locally for faster loading and fewer API calls.',
            onboardingCacheNote: 'Use Refresh News from the menu whenever you want fresh data.',
            onboardingStart: 'Start with Scroll ↕',
            onboardingScroll: 'Start with Swipe 👆',
            navDiscover: 'Discover',
            navSaved: 'Saved Articles',
            languageTitle: '🌐 Language',
            regionTitle: '🌍 Region',
            sortBy: 'Sort by',
            sortRelevance: '⚡ Relevance',
            sortLatest: '🕐 Latest',
            digestTitle: '📬 Daily Digest',
            digestDesc: 'Daily digest is coming soon.',
            readersSubscribed: 'readers subscribed',
            emailPlaceholder: 'you@email.com',
            subscribe: 'Subscribe',
            subscribing: 'Subscribing...',
            done: '✓ Done!',
            sidebarHint: 'Swipe right to save - Left to skip',
            noLogin: 'v3.0 - No login required',
            modeScroll: '↕ Scroll',
            modeSwipe: '👆 Swipe',
            modeTitle: 'Switch view mode',
            refreshNews: 'Refresh News',
            refreshSectionTitle: '🔄 Refresh',
            refreshingNews: 'Refreshing news...',
            refreshDone: 'News refreshed',
            refreshFailed: 'Refresh failed',
            loadingFeed: 'Loading latest stories...',
            topBarGlobal: '🌐 Global',
            viewDiscover: 'Discover',
            viewSaved: 'Saved',
            forYou: 'For You',
            topStories: 'Top Stories',
            techScience: 'Tech & Science',
            aiModels: 'AI Models',
            tools: 'Tools',
            research: 'Research',
            business: 'Business',
            hintSkip: '← Skip',
            hintSave: 'Save →',
            emptyCaughtUp: "You're all caught up!",
            emptySub: 'Pull down or switch tabs for more stories.',
            reloadFeed: 'Reload feed ↻',
            noStories: 'No stories yet',
            noStoriesSub: 'Pull down to refresh.',
            noSavedTitle: 'No saved articles yet',
            noSavedSub: 'Swipe right on cards to save them here.',
            savedAppear: 'Saved articles appear after loading the feed.',
            swipeLabelSave: 'SAVE',
            swipeLabelSkip: 'SKIP',
            sortedLatest: '🕐 Sorted by latest',
            sortedRelevance: '⚡ Sorted by relevance',
            switchedTo: 'Switched to {name}',
            languageToast: 'Language: {name}',
            languageRefreshNotice: 'Language changed. Please refresh the page.',
            languageReloadTitle: 'Language Updated',
            languageReloadPrompt: 'Language changed. Reload now for the best experience?',
            languageReloadNow: 'Reload Now',
            languageReloadLaterAction: 'Later',
            languageReloadLater: 'Language changed. You can reload anytime for a full refresh.',
            subscribedToast: 'Subscribed! 🎉',
            subscribedOk: 'Subscribed!',
            networkError: 'Network error',
            failed: 'Failed',
            saveToast: 'Saved! 🔖',
            readOriginal: 'Read original →',
            saveAction: '🔖 Save',
            savedAction: '✓ Saved',
            addedSaved: '✓ Added to saved articles',
            expandView: 'Expand View',
            collapseView: 'Compact View',
            loadingBrief: 'Generating detailed brief...',
            briefUnavailable: 'Detailed brief is not available yet. Please try again.',
            publishedAt: 'Published',
            updatedAt: 'Updated',
            whatsNewTitle: 'How to Use DailyAI',
            whatsNewBody: 'Quick guide to use the app better:',
            whatsNewAcknowledge: 'Start Exploring',
            streakLine: '🔥 Day {count} reading streak',
            streakBadge: '🔥 Day {count} reading DailyAI',
        },
        hi: {
            htmlLang: 'hi',
            pageTitle: 'DailyAI - AI समाचार खोजें',
            pageDescription: 'DailyAI - रोज़ाना चुनी हुई AI खबरें। लॉगिन की जरूरत नहीं।',
            onboardingTitle: 'DailyAI में आपका स्वागत है',
            onboardingDesc: 'एक ही जगह पर सभी फीचर्स समझें।',
            onboardingFeatureSwipe: 'सेव करने के लिए दाईं और स्किप के लिए बाईं ओर स्वाइप करें।',
            onboardingFeatureLanguage: 'साइडबार से भाषा बदलें।',
            onboardingFeatureCountry: 'अपनी फीड को स्थानीय बनाने के लिए देश बदलें।',
            onboardingFeatureRead: 'विस्तृत विवरण पढ़ने के लिए किसी कार्ड पर टैप करें।',
            onboardingFeatureCache: 'स्टोरीज़ लोकल कैश में सेव होती हैं, इसलिए लोडिंग तेज और API कॉल कम होती हैं।',
            onboardingCacheNote: 'नई खबरों के लिए मेन्यू में Refresh News का उपयोग करें।',
            onboardingStart: 'स्क्रॉल से शुरू करें ↕',
            onboardingScroll: 'स्वाइप से शुरू करें 👆',
            navDiscover: 'खोजें',
            navSaved: 'सेव्ड लेख',
            languageTitle: '🌐 भाषा',
            regionTitle: '🌍 क्षेत्र',
            sortBy: 'क्रमबद्ध करें',
            sortRelevance: '⚡ प्रासंगिकता',
            sortLatest: '🕐 नवीनतम',
            digestTitle: '📬 दैनिक डाइजेस्ट',
            digestDesc: 'डेली डाइजेस्ट जल्द आ रहा है।',
            readersSubscribed: 'पाठक सदस्य हैं',
            emailPlaceholder: 'you@email.com',
            subscribe: 'सदस्य बनें',
            subscribing: 'सदस्यता ली जा रही है...',
            done: '✓ हो गया!',
            sidebarHint: 'सेव करने के लिए दाएं स्वाइप करें - स्किप के लिए बाएं',
            noLogin: 'v3.0 - लॉगिन आवश्यक नहीं',
            modeScroll: '↕ स्क्रॉल',
            modeSwipe: '👆 स्वाइप',
            modeTitle: 'व्यू मोड बदलें',
            refreshNews: 'समाचार रिफ्रेश करें',
            refreshSectionTitle: '🔄 रिफ्रेश',
            refreshingNews: 'समाचार रिफ्रेश हो रहे हैं...',
            refreshDone: 'समाचार रिफ्रेश हो गए',
            refreshFailed: 'रिफ्रेश असफल',
            loadingFeed: 'ताज़ा खबरें लोड हो रही हैं...',
            topBarGlobal: '🌐 ग्लोबल',
            viewDiscover: 'खोजें',
            viewSaved: 'सेव्ड',
            forYou: 'आपके लिए',
            topStories: 'मुख्य खबरें',
            techScience: 'टेक और साइंस',
            aiModels: 'AI मॉडल्स',
            tools: 'टूल्स',
            research: 'रिसर्च',
            business: 'बिज़नेस',
            hintSkip: '← स्किप',
            hintSave: 'सेव →',
            emptyCaughtUp: 'आपने सब देख लिया!',
            emptySub: 'और खबरों के लिए नीचे खींचें या टैब बदलें।',
            reloadFeed: 'फीड फिर लोड करें ↻',
            noStories: 'अभी कोई स्टोरी नहीं',
            noStoriesSub: 'रिफ्रेश करने के लिए नीचे खींचें।',
            noSavedTitle: 'अभी कोई सेव्ड लेख नहीं',
            noSavedSub: 'लेख सेव करने के लिए कार्ड पर दाईं ओर स्वाइप करें।',
            savedAppear: 'फीड लोड होने के बाद सेव्ड लेख यहां दिखेंगे।',
            swipeLabelSave: 'सेव',
            swipeLabelSkip: 'स्किप',
            sortedLatest: '🕐 नवीनतम के अनुसार क्रमबद्ध',
            sortedRelevance: '⚡ प्रासंगिकता के अनुसार क्रमबद्ध',
            switchedTo: '{name} पर स्विच किया गया',
            languageToast: 'भाषा: {name}',
            languageRefreshNotice: 'भाषा बदल गई है। कृपया पेज रिफ्रेश करें।',
            languageReloadTitle: 'भाषा अपडेट हुई',
            languageReloadPrompt: 'भाषा बदल गई है। बेहतर अनुभव के लिए अभी रीलोड करें?',
            languageReloadNow: 'अभी रीलोड करें',
            languageReloadLaterAction: 'बाद में',
            languageReloadLater: 'भाषा बदल गई है। पूर्ण रिफ्रेश के लिए आप कभी भी रीलोड कर सकते हैं।',
            subscribedToast: 'सदस्यता सफल! 🎉',
            subscribedOk: 'सदस्यता सफल!',
            networkError: 'नेटवर्क त्रुटि',
            failed: 'असफल',
            saveToast: 'सेव किया गया! 🔖',
            readOriginal: 'मूल लेख पढ़ें →',
            saveAction: '🔖 सेव करें',
            savedAction: '✓ सेव्ड',
            addedSaved: '✓ सेव्ड लेखों में जोड़ा गया',
            expandView: 'व्यू बढ़ाएं',
            collapseView: 'कॉम्पैक्ट व्यू',
            loadingBrief: 'विस्तृत विवरण तैयार किया जा रहा है...',
            briefUnavailable: 'विस्तृत विवरण अभी उपलब्ध नहीं है। कृपया फिर कोशिश करें।',
            publishedAt: 'प्रकाशित',
            updatedAt: 'अपडेट किया गया',
            whatsNewTitle: 'DailyAI कैसे उपयोग करें',
            whatsNewBody: 'ऐप को बेहतर तरीके से उपयोग करने के लिए त्वरित गाइड:',
            whatsNewAcknowledge: 'शुरू करें',
            streakLine: '🔥 दिन {count} पढ़ने की स्ट्रीक',
            streakBadge: '🔥 दिन {count} DailyAI पढ़ना',
        },
        de: {
            htmlLang: 'de',
            pageTitle: 'DailyAI - KI-News entdecken',
            pageDescription: 'DailyAI - taeglich kuratierte KI-News. Kein Login erforderlich.',
            onboardingTitle: 'Willkommen bei DailyAI',
            onboardingDesc: 'Alle Funktionen auf einen Blick.',
            onboardingFeatureSwipe: 'Nach rechts wischen zum Speichern, nach links zum Ueberspringen.',
            onboardingFeatureLanguage: 'Sprache in der Seitenleiste wechseln.',
            onboardingFeatureCountry: 'Land wechseln, um den Feed zu lokalisieren.',
            onboardingFeatureRead: 'Auf eine Karte tippen, um einen detaillierten Brief zu lesen.',
            onboardingFeatureCache: 'Stories werden lokal zwischengespeichert fuer schnelleres Laden und weniger API-Aufrufe.',
            onboardingCacheNote: 'Mit "News aktualisieren" im Menue holst du frische Daten.',
            onboardingStart: 'Mit Scrollen starten ↕',
            onboardingScroll: 'Mit Wischen starten 👆',
            navDiscover: 'Entdecken',
            navSaved: 'Gespeicherte Artikel',
            languageTitle: '🌐 Sprache',
            regionTitle: '🌍 Region',
            sortBy: 'Sortieren nach',
            sortRelevance: '⚡ Relevanz',
            sortLatest: '🕐 Neueste',
            digestTitle: '📬 Taeglicher Digest',
            digestDesc: 'Der taegliche Digest kommt bald.',
            readersSubscribed: 'Leser abonniert',
            emailPlaceholder: 'you@email.com',
            subscribe: 'Abonnieren',
            subscribing: 'Wird abonniert...',
            done: '✓ Fertig!',
            sidebarHint: 'Nach rechts zum Speichern - nach links zum Ueberspringen',
            noLogin: 'v3.0 - Kein Login erforderlich',
            modeScroll: '↕ Scrollen',
            modeSwipe: '👆 Wischen',
            modeTitle: 'Ansichtsmodus wechseln',
            refreshNews: 'News aktualisieren',
            refreshSectionTitle: '🔄 Aktualisieren',
            refreshingNews: 'News werden aktualisiert...',
            refreshDone: 'News aktualisiert',
            refreshFailed: 'Aktualisierung fehlgeschlagen',
            loadingFeed: 'Neueste Meldungen werden geladen...',
            topBarGlobal: '🌐 Global',
            viewDiscover: 'Entdecken',
            viewSaved: 'Gespeichert',
            forYou: 'Fuer dich',
            topStories: 'Top-Storys',
            techScience: 'Technik & Wissenschaft',
            aiModels: 'KI-Modelle',
            tools: 'Tools',
            research: 'Forschung',
            business: 'Business',
            hintSkip: '← Ueberspringen',
            hintSave: 'Speichern →',
            emptyCaughtUp: 'Du bist auf dem neuesten Stand!',
            emptySub: 'Ziehe nach unten oder wechsle Tabs fuer mehr Storys.',
            reloadFeed: 'Feed neu laden ↻',
            noStories: 'Noch keine Storys',
            noStoriesSub: 'Zum Aktualisieren nach unten ziehen.',
            noSavedTitle: 'Noch keine gespeicherten Artikel',
            noSavedSub: 'Wische nach rechts auf Karten, um sie hier zu speichern.',
            savedAppear: 'Gespeicherte Artikel erscheinen nach dem Laden des Feeds.',
            swipeLabelSave: 'SPEICHERN',
            swipeLabelSkip: 'SKIP',
            sortedLatest: '🕐 Nach Neueste sortiert',
            sortedRelevance: '⚡ Nach Relevanz sortiert',
            switchedTo: 'Gewechselt zu {name}',
            languageToast: 'Sprache: {name}',
            languageRefreshNotice: 'Sprache wurde geaendert. Bitte Seite neu laden.',
            languageReloadTitle: 'Sprache aktualisiert',
            languageReloadPrompt: 'Sprache wurde geaendert. Jetzt neu laden fuer das beste Erlebnis?',
            languageReloadNow: 'Jetzt neu laden',
            languageReloadLaterAction: 'Spaeter',
            languageReloadLater: 'Sprache wurde geaendert. Du kannst jederzeit neu laden fuer eine vollstaendige Aktualisierung.',
            subscribedToast: 'Abonniert! 🎉',
            subscribedOk: 'Abonniert!',
            networkError: 'Netzwerkfehler',
            failed: 'Fehlgeschlagen',
            saveToast: 'Gespeichert! 🔖',
            readOriginal: 'Original lesen →',
            saveAction: '🔖 Speichern',
            savedAction: '✓ Gespeichert',
            addedSaved: '✓ Zu gespeicherten Artikeln hinzugefuegt',
            expandView: 'Ansicht vergroessern',
            collapseView: 'Kompakte Ansicht',
            loadingBrief: 'Ausfuehrlicher Brief wird erstellt...',
            briefUnavailable: 'Ausfuehrlicher Brief ist noch nicht verfuegbar. Bitte erneut versuchen.',
            publishedAt: 'Veroeffentlicht',
            updatedAt: 'Aktualisiert',
            whatsNewTitle: 'So nutzt du DailyAI',
            whatsNewBody: 'Kurzanleitung fuer die beste Nutzung:',
            whatsNewAcknowledge: 'Los gehts',
            streakLine: '🔥 Tag {count} Lesestreak',
            streakBadge: '🔥 Tag {count} DailyAI gelesen',
        },
    };

    function t(key, vars = {}) {
        const dict = I18N[currentLanguage] || I18N.en;
        const fallback = I18N.en;
        let text = dict[key] || fallback[key] || key;
        Object.entries(vars).forEach(([k, v]) => {
            text = text.replaceAll(`{${k}}`, String(v));
        });
        return text;
    }

    function applyTranslations() {
        document.documentElement.lang = t('htmlLang');
        document.title = t('pageTitle');

        const metaDesc = document.querySelector('meta[name="description"]');
        if (metaDesc) metaDesc.setAttribute('content', t('pageDescription'));

        const setText = (selector, value) => {
            const el = document.querySelector(selector);
            if (el) el.textContent = value;
        };
        setText('.onboard-title', t('onboardingTitle'));
        setText('.onboard-desc', t('onboardingDesc'));
        setText('#onboardFeatureSwipe', t('onboardingFeatureSwipe'));
        setText('#onboardFeatureLanguage', t('onboardingFeatureLanguage'));
        setText('#onboardFeatureCountry', t('onboardingFeatureCountry'));
        setText('#onboardFeatureRead', t('onboardingFeatureRead'));
        setText('#onboardFeatureCache', t('onboardingFeatureCache'));
        setText('#onboardCacheNote', t('onboardingCacheNote'));
        setText('#onboardStart', t('onboardingStart'));
        setText('#onboardScroll', t('onboardingScroll'));
        setText('#langReloadTitle', t('languageReloadTitle'));
        setText('#langReloadBody', t('languageReloadPrompt'));
        setText('#langReloadNowBtn', t('languageReloadNow'));
        setText('#langReloadLaterBtn', t('languageReloadLaterAction'));
        setText('#whatsNewTitle', t('whatsNewTitle'));
        setText('#whatsNewBody', t('whatsNewBody'));
        setText('#whatsNewOkBtn', t('whatsNewAcknowledge'));
        setText('#bootLoaderText', t('loadingFeed'));

        const navDiscover = $('navDiscover');
        if (navDiscover) navDiscover.innerHTML = `<span class="sidebar-icon">🏠</span> ${t('navDiscover')}`;
        const navSaved = $('navSaved');
        if (navSaved) navSaved.innerHTML = `<span class="sidebar-icon">🔖</span> ${t('navSaved')}<span class="sidebar-badge" id="savedCount">${Object.keys(bookmarks).length}</span>`;

        const sidebarTitles = document.querySelectorAll('.sidebar-section-title');
        if (sidebarTitles[0]) sidebarTitles[0].textContent = t('languageTitle');
        if (sidebarTitles[1]) sidebarTitles[1].textContent = t('regionTitle');
        if (sidebarTitles[2]) sidebarTitles[2].textContent = t('sortBy');
        if (sidebarTitles[3]) sidebarTitles[3].textContent = t('refreshSectionTitle');
        if (sidebarTitles[4]) sidebarTitles[4].textContent = t('digestTitle');

        setText('.sidebar-desc', t('digestDesc'));
        setText('#sidebarRefreshBtn', t('refreshNews'));
        setText('#subscribeBtn', t('subscribe'));
        const emailInput = $('emailInput');
        if (emailInput) emailInput.setAttribute('placeholder', t('emailPlaceholder'));

        const subWrap = $('subCountWrap');
        if (subWrap && subWrap.style.display !== 'none') {
            subWrap.innerHTML = `<span id="subCountVal">${$('subCountVal')?.textContent || '0'}</span> ${t('readersSubscribed')}`;
        }

        const footerLines = document.querySelectorAll('.sidebar-footer p');
        if (footerLines[0]) footerLines[0].textContent = t('sidebarHint');
        if (footerLines[2]) footerLines[2].textContent = getBuildFooterText();

        const savedBtn = $('savedBtn');
        if (savedBtn) savedBtn.setAttribute('aria-label', t('viewSaved'));
        const menuBtn = $('menuBtn');
        if (menuBtn) menuBtn.setAttribute('aria-label', t('navDiscover'));

        const modeBtn = $('modeToggle');
        if (modeBtn) modeBtn.setAttribute('title', t('modeTitle'));

        const refreshBtn = $('sidebarRefreshBtn');
        if (refreshBtn) {
            refreshBtn.setAttribute('title', t('refreshNews'));
            refreshBtn.setAttribute('aria-label', t('refreshNews'));
        }

        const pills = document.querySelectorAll('.filter-pill');
        pills.forEach((pill) => {
            const topic = pill.dataset.topic || '';
            const map = {
                'For You': t('forYou'),
                'Top Stories': t('topStories'),
                'Tech & Science': t('techScience'),
                'AI Models': t('aiModels'),
                'Tools': t('tools'),
                'Research': t('research'),
                'Business': t('business'),
            };
            if (map[topic]) pill.textContent = map[topic];
        });

        setText('.hint-left', t('hintSkip'));
        setText('.hint-right', t('hintSave'));
        setText('.empty-title', t('emptyCaughtUp'));
        setText('.empty-sub', t('emptySub'));
        setText('#reloadBtn', t('reloadFeed'));

        switchView(currentView);
        restoreSort();
        restoreFeedMode();
        showStreak();
    }

    function getBuildFooterText() {
        const safeVersion = String(RELEASE_VERSION || 'dev').trim();
        const shortVersion = safeVersion.length > 10 ? safeVersion.slice(0, 10) : safeVersion;
        const noLoginText = t('noLogin').replace(/^v\d+\.\d+\s*-\s*/, '');
        return `Build ${shortVersion} - ${noLoginText}`;
    }

    function translateCountryName(code, name) {
        const COUNTRY_LABELS = {
            en: { GLOBAL: 'Global / Worldwide' },
            hi: {
                US: 'संयुक्त राज्य अमेरिका', GB: 'यूनाइटेड किंगडम', IN: 'भारत', DE: 'जर्मनी', FR: 'फ्रांस',
                CA: 'कनाडा', AU: 'ऑस्ट्रेलिया', JP: 'जापान', KR: 'दक्षिण कोरिया', CN: 'चीन',
                BR: 'ब्राज़ील', SG: 'सिंगापुर', AE: 'यूएई', IL: 'इज़राइल', GLOBAL: 'ग्लोबल / विश्वव्यापी',
            },
            de: {
                US: 'Vereinigte Staaten', GB: 'Vereinigtes Koenigreich', IN: 'Indien', DE: 'Deutschland', FR: 'Frankreich',
                CA: 'Kanada', AU: 'Australien', JP: 'Japan', KR: 'Suedkorea', CN: 'China',
                BR: 'Brasilien', SG: 'Singapur', AE: 'VAE', IL: 'Israel', GLOBAL: 'Global / Weltweit',
            },
        };
        return (COUNTRY_LABELS[currentLanguage] && COUNTRY_LABELS[currentLanguage][code]) || name;
    }

    // ---- Config ----
    const TOPIC_GRADIENTS = {
        'AI Models':      'linear-gradient(135deg, #0f2027, #203a43, #2c5364)',
        'Tools':          'linear-gradient(135deg, #1a1a2e, #16213e, #0f3460)',
        'Research':       'linear-gradient(135deg, #0d0d0d, #1a1a2e, #16213e)',
        'Top Stories':    'linear-gradient(135deg, #1f1c2c, #928dab)',
        'Business':       'linear-gradient(135deg, #141e30, #243b55)',
        'Tech & Science': 'linear-gradient(135deg, #0f2027, #203a43, #2c5364)',
    };
    const TOPIC_PLACEHOLDER_IMAGES = {
        'AI Models': [
            'https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=1200&q=80',
            'https://images.unsplash.com/photo-1676299081847-824916de030a?auto=format&fit=crop&w=1200&q=80',
            'https://images.unsplash.com/photo-1686191128892-3d19f2d7d53f?auto=format&fit=crop&w=1200&q=80',
        ],
        'Top Stories': [
            'https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80',
            'https://images.unsplash.com/photo-1495020689067-958852a7765e?auto=format&fit=crop&w=1200&q=80',
            'https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?auto=format&fit=crop&w=1200&q=80',
        ],
        'Tech & Science': [
            'https://images.unsplash.com/photo-1532094349884-543bc11b234d?auto=format&fit=crop&w=1200&q=80',
            'https://images.unsplash.com/photo-1518152006812-edab29b069ac?auto=format&fit=crop&w=1200&q=80',
            'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80',
        ],
        'Business': [
            'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1200&q=80',
            'https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=1200&q=80',
            'https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?auto=format&fit=crop&w=1200&q=80',
        ],
        'Tools': [
            'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80',
            'https://images.unsplash.com/photo-1515879218367-8466d910aaa4?auto=format&fit=crop&w=1200&q=80',
            'https://images.unsplash.com/photo-1461749280684-dccba630e2f6?auto=format&fit=crop&w=1200&q=80',
        ],
        'Research': [
            'https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?auto=format&fit=crop&w=1200&q=80',
            'https://images.unsplash.com/photo-1576086213369-97a306d36557?auto=format&fit=crop&w=1200&q=80',
            'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80',
        ],
    };
    const TOPIC_LOCAL_FALLBACK_IMAGES = {
        'AI Models': '/static/topic-covers/ai-models.svg',
        'Top Stories': '/static/topic-covers/top-stories.svg',
        'Tech & Science': '/static/topic-covers/tech-science.svg',
        'Business': '/static/topic-covers/business.svg',
        'Tools': '/static/topic-covers/tools.svg',
        'Research': '/static/topic-covers/research.svg',
    };
    const COUNTRY_FLAGS = {
        'US':'🇺🇸','GB':'🇬🇧','IN':'🇮🇳','DE':'🇩🇪','FR':'🇫🇷','CA':'🇨🇦',
        'AU':'🇦🇺','JP':'🇯🇵','KR':'🇰🇷','CN':'🇨🇳','BR':'🇧🇷','SG':'🇸🇬',
        'AE':'🇦🇪','IL':'🇮🇱','GLOBAL':'🌐',
    };
    const AVATAR_COLORS = ['#6366f1','#2dd4a0','#f59e0b','#ef4444','#8b5cf6','#3b82f6','#ec4899','#14b8a6'];
    const FALLBACK_ARTICLES = [
        { id:'fb-1', headline:'OpenAI Announces GPT-5 with Multimodal Reasoning', summary:'OpenAI has unveiled GPT-5, featuring advanced multimodal reasoning capabilities that can process text, images, and audio simultaneously.', why_it_matters:'A major leap in AI capability, potentially transforming multiple industries.', topic:'AI Models', source_name:'TechCrunch', source_avatar_url:null, image_url:null, article_url:'#', published_at:new Date().toISOString(), updated_at:new Date().toISOString() },
        { id:'fb-2', headline:'EU Finalizes AI Act Implementation Timeline', summary:'The European Union has released the final implementation timeline for the AI Act, giving companies 12 months to comply.', why_it_matters:'Companies worldwide must adapt their AI products to meet these regulations.', topic:'Top Stories', source_name:'Reuters', source_avatar_url:null, image_url:null, article_url:'#', published_at:new Date().toISOString(), updated_at:new Date().toISOString() },
        { id:'fb-3', headline:'New Open-Source LLM Surpasses Commercial Models', summary:'A new open-source language model has outperformed leading commercial models on multiple benchmarks.', why_it_matters:'Open-source AI is closing the gap, democratizing access to powerful tools.', topic:'Research', source_name:'ArXiv', source_avatar_url:null, image_url:null, article_url:'#', published_at:new Date().toISOString(), updated_at:new Date().toISOString() },
    ];

    function getFeedCacheKey(topicParam, country, language) {
        return `${FEED_CACHE_PREFIX}:${country}:${language}:${(topicParam || 'all').toLowerCase()}`;
    }
    function getBriefCacheKey(article) {
        const fingerprint = `${article.id || ''}|${article.article_url || ''}|${article.headline || ''}|${currentLanguage}`;
        return `${BRIEF_CACHE_PREFIX}:${hashCode(fingerprint)}`;
    }
    function readCacheEntry(cacheKey, ttlMs, allowExpired = false) {
        try {
            const raw = localStorage.getItem(cacheKey);
            if (!raw) return null;
            const parsed = JSON.parse(raw);
            if (!parsed || typeof parsed.savedAt !== 'number') return null;
            const isExpired = Date.now() - parsed.savedAt > ttlMs;
            if (isExpired && !allowExpired) return null;
            return parsed.data;
        } catch {
            return null;
        }
    }
    function writeCacheEntry(cacheKey, data) {
        try {
            localStorage.setItem(cacheKey, JSON.stringify({ savedAt: Date.now(), data }));
        } catch {
            // Cache writes can fail on storage limits; app should continue without breaking.
        }
    }
    function hydrateTopicCachesFromAll(articles) {
        const topics = new Set((articles || []).map(a => (a.topic || '').trim()).filter(Boolean));
        topics.forEach((topicName) => {
            const topicArticles = (articles || []).filter(a => (a.topic || '').toLowerCase() === topicName.toLowerCase());
            if (topicArticles.length > 0) {
                const topicCacheKey = getFeedCacheKey(topicName, currentCountry, currentLanguage);
                writeCacheEntry(topicCacheKey, topicArticles);
            }
        });
    }

    // ---- State ----
    let allArticles = [];
    let currentTopic = 'For You';
    let currentCountry = localStorage.getItem('dailyai_country') || 'GLOBAL';
    let currentLanguage = localStorage.getItem('dailyai_language') || 'en';
    let currentSort = localStorage.getItem('dailyai_sort') || 'relevance';
    let currentView = 'discover';
    let feedMode = localStorage.getItem('dailyai_mode') || 'scroll'; // 'swipe' or 'scroll'
    let bookmarks = JSON.parse(localStorage.getItem('dailyai_bookmarks') || '{}');
    let swipeCardIndex = 0;
    let isDragging = false, startX = 0, startY = 0, deltaX = 0;
    let versionPollTimer = null;

    // ---- DOM ----
    const $ = id => document.getElementById(id);
    const appShell = $('appShell');
    const bootLoader = $('bootLoader');
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
    const languageSelect = $('languageSelect');
    const modeToggle = $('modeToggle');
    const refreshNewsBtn = $('sidebarRefreshBtn');
    const langReloadBackdrop = $('langReloadBackdrop');
    const langReloadNowBtn = $('langReloadNowBtn');
    const langReloadLaterBtn = $('langReloadLaterBtn');
    const whatsNewBackdrop = $('whatsNewBackdrop');
    const whatsNewOkBtn = $('whatsNewOkBtn');
    const whatsNewList = $('whatsNewList');

    // ====================== INIT ======================
    async function init() {
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

        // Language
        languageSelect.addEventListener('change', onLanguageChange);

        // Newsletter
        $('subscribeForm').addEventListener('submit', onSubscribe);

        // Filter tabs
        filterTabs.addEventListener('click', onTabClick);

        // Mode toggle
        modeToggle.addEventListener('click', toggleFeedMode);

        // Reload
        $('reloadBtn').addEventListener('click', refreshNewsNow);
        refreshNewsBtn?.addEventListener('click', refreshNewsNow);

        // Bottom sheet
        sheetBackdrop.addEventListener('click', closeSheet);
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') {
                closeSheet();
                closeSidebar();
                closeLanguageReloadModal();
                closeWhatsNewModal();
            }
        });
        let sheetTouchStartY = 0;
        bottomSheet.addEventListener('touchstart', e => { sheetTouchStartY = e.touches[0].clientY; }, { passive: true });
        bottomSheet.addEventListener('touchmove', e => {
            if (e.touches[0].clientY - sheetTouchStartY > 80) closeSheet();
        }, { passive: true });

        langReloadNowBtn?.addEventListener('click', () => location.reload());
        langReloadLaterBtn?.addEventListener('click', () => {
            closeLanguageReloadModal();
            showToast(t('languageReloadLater'));
        });
        langReloadBackdrop?.addEventListener('click', (e) => {
            if (e.target === langReloadBackdrop) {
                closeLanguageReloadModal();
                showToast(t('languageReloadLater'));
            }
        });

        whatsNewOkBtn?.addEventListener('click', closeWhatsNewModal);
        whatsNewBackdrop?.addEventListener('click', (e) => {
            if (e.target === whatsNewBackdrop) closeWhatsNewModal();
        });

        // Init
        const reloadedForBuildUpdate = await enforceBuildResetIfNeeded();
        if (reloadedForBuildUpdate) return;

        setGlobalLoading(true);

        applyTranslations();
        showWhatsNewIfNeeded();
        showStreak();
        updateSavedCount();
        restoreSort();
        restoreFeedMode();
        loadLanguages();
        loadCountries();
        fetchSubscriberCount();
        setupServiceWorker();
        startVersionWatcher();

        // Onboarding check
        if (!localStorage.getItem('dailyai_onboarded')) {
            showOnboarding();
        }

        // Load feed
        showSkeleton();
        fetchArticles(currentTopic);
    }

    function setupServiceWorker() {
        if (!('serviceWorker' in navigator)) return;
        window.addEventListener('load', () => {
            navigator.serviceWorker.register(`/static/sw.js?v=${encodeURIComponent(RELEASE_VERSION)}`).catch(() => {
                // Service worker registration is optional; continue app flow.
            });
        });
    }

    function startVersionWatcher() {
        if (versionPollTimer) clearInterval(versionPollTimer);
        versionPollTimer = setInterval(checkForDeploymentUpdate, VERSION_POLL_MS);
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) checkForDeploymentUpdate();
        });
        checkForDeploymentUpdate();
    }

    async function checkForDeploymentUpdate() {
        try {
            const resp = await fetch('/api/version', { cache: 'no-store' });
            if (!resp.ok) return;
            const data = await resp.json();
            const latestVersion = String(data.version || '').trim();
            if (!latestVersion || latestVersion === RELEASE_VERSION) return;

            const markerKey = 'dailyai_last_auto_reload_version';
            if (sessionStorage.getItem(markerKey) === latestVersion) return;
            sessionStorage.setItem(markerKey, latestVersion);

            await clearClientCaches({ includeServiceWorkers: true });
            try {
                localStorage.setItem(BUILD_MARKER_KEY, latestVersion);
            } catch {
                // Ignore storage write failures.
            }
            location.reload();
        } catch {
            // Ignore version check failures; next poll will retry.
        }
    }

    async function enforceBuildResetIfNeeded() {
        try {
            const previousBuild = String(localStorage.getItem(BUILD_MARKER_KEY) || '').trim();
            if (previousBuild && previousBuild !== RELEASE_VERSION) {
                await clearClientCaches({ includeServiceWorkers: true });
                localStorage.setItem(BUILD_MARKER_KEY, RELEASE_VERSION);
                location.reload();
                return true;
            }
            localStorage.setItem(BUILD_MARKER_KEY, RELEASE_VERSION);
        } catch {
            // Ignore localStorage failures and continue.
        }
        return false;
    }

    async function clearClientCaches(options = {}) {
        const includeServiceWorkers = Boolean(options.includeServiceWorkers);
        try {
            const keysToDelete = [];
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (!key) continue;
                if (key.startsWith(FEED_CACHE_PREFIX) || key.startsWith(BRIEF_CACHE_PREFIX)) {
                    keysToDelete.push(key);
                }
            }
            keysToDelete.forEach((key) => localStorage.removeItem(key));
        } catch {
            // Best effort cache cleanup.
        }

        if ('caches' in window) {
            try {
                const cacheKeys = await caches.keys();
                await Promise.all(cacheKeys.map((key) => caches.delete(key)));
            } catch {
                // Ignore cache API cleanup errors.
            }
        }

        if (includeServiceWorkers && 'serviceWorker' in navigator) {
            try {
                const registrations = await navigator.serviceWorker.getRegistrations();
                await Promise.all(registrations.map((reg) => reg.unregister()));
            } catch {
                // Ignore SW unregister errors.
            }
        }
    }

    // ====================== ONBOARDING ======================
    function showOnboarding() {
        const overlay = $('onboardingOverlay');
        overlay.style.display = 'flex';

        $('onboardStart').addEventListener('click', () => {
            dismissOnboarding(overlay, 'scroll');
        });
        $('onboardScroll').addEventListener('click', () => {
            dismissOnboarding(overlay, 'swipe');
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
        showToast(feedMode === 'scroll' ? t('modeScroll') : t('modeSwipe'));
    }

    function restoreFeedMode() {
        if (feedMode === 'scroll') {
            modeToggle.textContent = t('modeSwipe');
            modeToggle.classList.add('active');
        } else {
            modeToggle.textContent = t('modeScroll');
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
            scrollFeed.innerHTML = `<div style="padding:60px 20px;text-align:center;"><p style="font-size:48px;margin-bottom:12px;">📰</p><p style="font-size:16px;font-weight:600;">${t('noStories')}</p><p style="font-size:14px;color:var(--text3);margin-top:4px;">${t('noStoriesSub')}</p></div>`;
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
        const avatarColor = AVATAR_COLORS[hashCode(article.source_name) % AVATAR_COLORS.length];
        const initial = (article.source_name || 'D')[0].toUpperCase();
        const whyHtml = article.why_it_matters ? `<div class="card-why">💡 ${esc(article.why_it_matters)}</div>` : '';
        const imgHtml = article.image_url
            ? `<img src="${esc(article.image_url)}" alt="" class="card-image" loading="lazy">`
            : buildTopicCoverImg(article);

        const isSaved = !!bookmarks[article.id];
        card.innerHTML = `
            ${imgHtml}
            <div class="card-body">
                <h2 class="card-headline">${esc(article.headline)}</h2>
                <p class="card-summary">${esc(article.summary)}</p>
                ${whyHtml}
                <div class="card-footer">
                    <div class="card-source"><div class="source-avatar" style="background:${avatarColor}">${initial}</div><span class="source-name">${esc(article.source_name)}</span></div>
                    <span class="card-time">${getCardTimeMarkup(article)}</span>
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

    function getTopicCoverUrl(topic, seed = '') {
        const list = TOPIC_PLACEHOLDER_IMAGES[topic] || TOPIC_PLACEHOLDER_IMAGES['Top Stories'];
        if (!Array.isArray(list) || list.length === 0) return TOPIC_PLACEHOLDER_IMAGES['Top Stories'][0];
        const idx = hashCode(String(seed || topic || 'default')) % list.length;
        return list[idx];
    }

    function getTopicFallbackCoverUrl(topic) {
        return TOPIC_LOCAL_FALLBACK_IMAGES[topic] || TOPIC_LOCAL_FALLBACK_IMAGES['Top Stories'];
    }

    function buildTopicCoverImg(article) {
        const topic = article.topic || 'Top Stories';
        const seed = `${article.id || ''}|${article.headline || ''}|${article.source_name || ''}`;
        const coverUrl = getTopicCoverUrl(topic, seed);
        const fallbackUrl = getTopicFallbackCoverUrl(topic);
        return `<img src="${esc(coverUrl)}" alt="${esc(topic)}" class="card-image" loading="lazy" onerror="this.onerror=null;this.src='${esc(fallbackUrl)}'">`;
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
                opt.textContent = `${flag} ${translateCountryName(code, name)}`;
                if (code === currentCountry) opt.selected = true;
                countrySelect.appendChild(opt);
            }
            updateTopBarCountry();
        } catch { /* fallback: keep default */ }
    }

    async function loadLanguages() {
        const fallback = { en: 'English', hi: 'Hindi', de: 'German' };
        try {
            const resp = await fetch('/api/languages');
            const data = await resp.json();
            const languages = data.languages || fallback;
            languageSelect.innerHTML = '';
            for (const [code, name] of Object.entries(languages)) {
                const opt = document.createElement('option');
                opt.value = code;
                const localizedLabel = {
                    en: { en: 'English', hi: 'Hindi', de: 'German' },
                    hi: { en: 'अंग्रेजी', hi: 'हिंदी', de: 'जर्मन' },
                    de: { en: 'Englisch', hi: 'Hindi', de: 'Deutsch' },
                };
                opt.textContent = (localizedLabel[currentLanguage] && localizedLabel[currentLanguage][code]) || name;
                if (code === currentLanguage) opt.selected = true;
                languageSelect.appendChild(opt);
            }
        } catch {
            languageSelect.innerHTML = '';
            for (const [code, name] of Object.entries(fallback)) {
                const opt = document.createElement('option');
                opt.value = code;
                opt.textContent = name;
                if (code === currentLanguage) opt.selected = true;
                languageSelect.appendChild(opt);
            }
        }
    }

    function onCountryChange() {
        currentCountry = countrySelect.value;
        localStorage.setItem('dailyai_country', currentCountry);
        updateTopBarCountry();
        closeSidebar();
        showSkeleton();
        fetchArticles(currentTopic);
        const name = countrySelect.options[countrySelect.selectedIndex]?.textContent || currentCountry;
        showToast(t('switchedTo', { name }));
    }

    async function onLanguageChange() {
        currentLanguage = languageSelect.value || 'en';
        localStorage.setItem('dailyai_language', currentLanguage);

        // Apply key title labels immediately for instant visual feedback.
        document.documentElement.lang = t('htmlLang');
        document.title = t('pageTitle');
        if (viewTitle) {
            viewTitle.textContent = currentView === 'saved' ? t('viewSaved') : t('viewDiscover');
        }

        applyTranslations();

        closeLanguageReloadModal();
        loadCountries();
        loadLanguages();
        closeSidebar();
        showSkeleton();

        // Regenerate country feed in selected language so card headlines also switch.
        try {
            await fetch(`/api/refresh/${encodeURIComponent(currentCountry)}?language=${encodeURIComponent(currentLanguage)}`, {
                method: 'POST',
            });
        } catch {
            // Ignore refresh failures and fallback to normal article fetch.
        }

        await fetchArticles(currentTopic, { forceRefresh: true });
        const name = languageSelect.options[languageSelect.selectedIndex]?.textContent || currentLanguage;
        showToast(t('languageToast', { name }));
        setTimeout(() => showToast(t('languageRefreshNotice'), 4800), 350);
    }

    function openLanguageReloadModal() {
        if (!langReloadBackdrop) return;
        langReloadBackdrop.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    function closeLanguageReloadModal() {
        if (!langReloadBackdrop) return;
        langReloadBackdrop.style.display = 'none';
        if (!bottomSheet.classList.contains('show') && whatsNewBackdrop?.style.display !== 'flex') {
            document.body.style.overflow = '';
        }
    }

    function showWhatsNewIfNeeded() {
        if (!whatsNewBackdrop || !whatsNewList) return;
        const seenKey = 'dailyai_seen_guide_v1';
        if (localStorage.getItem(seenKey) === '1') return;

        const highlights = APP_FUNCTIONALITY_GUIDE[currentLanguage] || APP_FUNCTIONALITY_GUIDE.en;
        whatsNewList.innerHTML = highlights
            .map((item, index) => `<li style="animation-delay:${index * 80}ms">${esc(item)}</li>`)
            .join('');
        whatsNewBackdrop.style.display = 'flex';
        whatsNewBackdrop.classList.add('show');
        document.body.style.overflow = 'hidden';
        localStorage.setItem(seenKey, '1');
    }

    function closeWhatsNewModal() {
        if (!whatsNewBackdrop) return;
        whatsNewBackdrop.classList.remove('show');
        whatsNewBackdrop.style.display = 'none';
        if (!bottomSheet.classList.contains('show') && langReloadBackdrop?.style.display !== 'flex') {
            document.body.style.overflow = '';
        }
    }

    function updateTopBarCountry() {
        const flag = COUNTRY_FLAGS[currentCountry] || '🏳️';
        const displayName = translateCountryName(currentCountry, currentCountry);
        topBarCountry.textContent = flag;
        topBarCountry.setAttribute('title', displayName);
        topBarCountry.setAttribute('aria-label', displayName);
    }

    // ====================== SUBSCRIBER COUNT ======================
    async function fetchSubscriberCount() {
        try {
            const resp = await fetch('/api/subscribers/count');
            const data = await resp.json();
            const count = data.count || 0;
            if (count > 0) {
                const subCountWrap = $('subCountWrap');
                subCountWrap.innerHTML = `<span id="subCountVal">${count.toLocaleString()}</span> ${t('readersSubscribed')}`;
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
            viewTitle.textContent = t('viewDiscover');
            filterTabs.style.display = '';
            feed.style.display = 'none';
            $('savedBtn').classList.remove('has-saved');
            modeToggle.style.display = '';
            renderFeed();
        } else {
            $('navSaved').classList.add('active');
            viewTitle.textContent = t('viewSaved');
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
            feed.innerHTML = `<div style="padding:60px 20px;text-align:center;"><p style="font-size:48px;margin-bottom:12px;">🔖</p><p style="font-size:16px;font-weight:600;">${t('noSavedTitle')}</p><p style="font-size:14px;color:var(--text3);margin-top:4px;">${t('noSavedSub')}</p></div>`;
            return;
        }
        const saved = allArticles.filter(a => bookmarks[a.id]);
        const storedSaved = Object.values(bookmarks).filter(v => typeof v === 'object' && v.headline);
        const combined = [...saved];
        for (const s of storedSaved) {
            if (!combined.find(c => c.id === s.id)) combined.push(s);
        }
        if (combined.length === 0) {
            feed.innerHTML = `<div style="padding:60px 20px;text-align:center;"><p style="font-size:14px;color:var(--text3);">${t('savedAppear')}</p></div>`;
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
        const avatarColor = AVATAR_COLORS[hashCode(article.source_name) % AVATAR_COLORS.length];
        const initial = (article.source_name || 'D')[0].toUpperCase();
        const whyHtml = article.why_it_matters ? `<div class="card-why">💡 ${esc(article.why_it_matters)}</div>` : '';
        const imgHtml = article.image_url
            ? `<img src="${esc(article.image_url)}" alt="" class="card-image" loading="lazy">`
            : buildTopicCoverImg(article);
        return `<div class="feed-card" data-id="${esc(article.id)}" style="animation-delay:${i*50}ms">
            ${imgHtml}
            <div class="card-body">
                <h2 class="card-headline">${esc(article.headline)}</h2>
                <p class="card-summary">${esc(article.summary)}</p>
                ${whyHtml}
                <div class="card-footer">
                    <div class="card-source"><div class="source-avatar" style="background:${avatarColor}">${initial}</div><span class="source-name">${esc(article.source_name)}</span></div>
                    <span class="card-time">${getCardTimeMarkup(article)}</span>
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
        showToast(currentSort === 'time' ? t('sortedLatest') : t('sortedRelevance'));
    }
    function sortArticles() {
        if (currentSort === 'time') {
            allArticles.sort((a, b) => new Date(b.published_at || b.updated_at || 0) - new Date(a.published_at || a.updated_at || 0));
        }
    }

    // ====================== NEWSLETTER ======================
    async function onSubscribe(e) {
        e.preventDefault();
        const email = $('emailInput').value.trim();
        if (!email) return;
        const btn = $('subscribeBtn');
        btn.disabled = true; btn.textContent = t('subscribing');
        try {
            const resp = await fetch('/api/subscribe', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, topics: [], country: currentCountry, language: currentLanguage }),
            });
            const data = await resp.json();
            if (resp.ok) {
                $('subStatus').textContent = '✅ ' + (data.message || t('subscribedOk'));
                $('emailInput').value = '';
                btn.textContent = t('done');
                showToast(t('subscribedToast'));
                fetchSubscriberCount();
                setTimeout(() => { btn.textContent = t('subscribe'); }, 3000);
            } else {
                $('subStatus').textContent = '❌ ' + (data.error || t('failed'));
                btn.textContent = t('subscribe');
            }
        } catch {
            $('subStatus').textContent = '❌ ' + t('networkError');
            btn.textContent = t('subscribe');
        } finally { btn.disabled = false; }
    }

    // ====================== FETCH ======================
    async function fetchArticles(topic, options = {}) {
        const { forceRefresh = false } = options;
        const param = topic === 'For You' ? 'all' : topic;
        const cacheKey = getFeedCacheKey(param, currentCountry, currentLanguage);
        if (!forceRefresh) {
            const cachedArticles = readCacheEntry(cacheKey, FEED_CACHE_TTL_MS);
            if (cachedArticles && cachedArticles.length > 0) {
                allArticles = cachedArticles;
                sortArticles();
                swipeCardIndex = 0;
                swipeEmpty.style.display = 'none';
                renderFeed();
                setGlobalLoading(false);
                return;
            }
        }
        const timeout = new Promise((_, reject) => setTimeout(() => reject('timeout'), 8000));
        try {
            const resp = await Promise.race([
                fetch(`${API_URL}?topic=${encodeURIComponent(param)}&country=${encodeURIComponent(currentCountry)}&language=${encodeURIComponent(currentLanguage)}`),
                timeout,
            ]);
            const data = await resp.json();
            allArticles = (data.articles && data.articles.length > 0) ? data.articles : FALLBACK_ARTICLES;
            if (data.articles && data.articles.length > 0) {
                writeCacheEntry(cacheKey, data.articles);
                if (param === 'all') hydrateTopicCachesFromAll(data.articles);
            }
        } catch {
            const staleArticles = readCacheEntry(cacheKey, FEED_CACHE_TTL_MS, true);
            allArticles = (staleArticles && staleArticles.length > 0) ? staleArticles : FALLBACK_ARTICLES;
        }
        sortArticles();
        swipeCardIndex = 0;
        swipeEmpty.style.display = 'none';
        renderFeed();
        setGlobalLoading(false);
    }

    async function refreshNewsNow() {
        if (refreshNewsBtn?.dataset.loading === '1') return;
        if (refreshNewsBtn) {
            refreshNewsBtn.dataset.loading = '1';
            refreshNewsBtn.classList.add('loading');
            refreshNewsBtn.disabled = true;
        }
        showToast(t('refreshingNews'));
        showSkeleton();
        try {
            const resp = await fetch(`/api/refresh/${encodeURIComponent(currentCountry)}?language=${encodeURIComponent(currentLanguage)}`, {
                method: 'POST',
            });
            if (!resp.ok) throw new Error('refresh_failed');
            await fetchArticles(currentTopic, { forceRefresh: true });
            showToast(t('refreshDone'));
        } catch {
            await fetchArticles(currentTopic);
            showToast(t('refreshFailed'));
        } finally {
            if (refreshNewsBtn) {
                refreshNewsBtn.dataset.loading = '0';
                refreshNewsBtn.classList.remove('loading');
                refreshNewsBtn.disabled = false;
            }
        }
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
        const avatarColor = AVATAR_COLORS[hashCode(article.source_name) % AVATAR_COLORS.length];
        const initial = (article.source_name || 'D')[0].toUpperCase();
        const whyHtml = article.why_it_matters ? `<div class="card-why">💡 ${esc(article.why_it_matters)}</div>` : '';
        const imgHtml = article.image_url
            ? `<img src="${esc(article.image_url)}" alt="" class="card-image" loading="lazy">`
            : buildTopicCoverImg(article);
        card.innerHTML = `
            <div class="swipe-label swipe-label-save">${t('swipeLabelSave')}</div>
            <div class="swipe-label swipe-label-skip">${t('swipeLabelSkip')}</div>
            ${imgHtml}
            <div class="card-body">
                <h2 class="card-headline">${esc(article.headline)}</h2>
                <p class="card-summary">${esc(article.summary)}</p>
                ${whyHtml}
                <div class="card-footer">
                    <div class="card-source"><div class="source-avatar" style="background:${avatarColor}">${initial}</div><span class="source-name">${esc(article.source_name)}</span></div>
                    <span class="card-time">${getCardTimeMarkup(article)}</span>
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
            showToast(t('saveToast'));
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
        setGlobalLoading(true);
        swipeStack.innerHTML = `
            <div class="skeleton-card">
                <div class="skeleton-image"></div>
                <div class="skeleton-body">
                    <div class="skeleton-line w80"></div>
                    <div class="skeleton-line w60"></div>
                    <div class="skeleton-line w40"></div>
                </div>
            </div>`;
        scrollFeed.innerHTML = swipeStack.innerHTML;
        feed.innerHTML = swipeStack.innerHTML;
    }

    function setGlobalLoading(isLoading) {
        if (!bootLoader) return;
        bootLoader.classList.toggle('visible', Boolean(isLoading));
    }

    // ====================== BOTTOM SHEET ======================
    function openSheet(article) {
        const whyHtml = article.why_it_matters ? `<div class="sheet-why">💡 ${esc(article.why_it_matters)}</div>` : '';
        const isSaved = !!bookmarks[article.id];
        sheetContent.innerHTML = `
            <div class="sheet-headline-row">
                <h2 class="sheet-headline">${esc(article.headline)}</h2>
                <button class="sheet-link sheet-expand-btn sheet-expand-inline" id="sheetExpandBtn" aria-label="${bottomSheet.classList.contains('expanded') ? esc(t('collapseView')) : esc(t('expandView'))}" title="${bottomSheet.classList.contains('expanded') ? esc(t('collapseView')) : esc(t('expandView'))}">
                    <span class="sheet-expand-icon" aria-hidden="true">${bottomSheet.classList.contains('expanded') ? '⤡' : '⤢'}</span>
                </button>
            </div>
            <p class="sheet-summary">${esc(article.summary)}</p>
            <div class="sheet-brief-wrap" id="sheetBriefWrap">
                <div class="sheet-brief-loading" id="sheetBriefLoading">
                    <p class="sheet-brief" style="margin-bottom:4px;">${esc(t('loadingBrief'))}</p>
                    <div class="line w95"></div>
                    <div class="line w88"></div>
                    <div class="line w90"></div>
                    <div class="line w80"></div>
                    <div class="line w92"></div>
                </div>
                <p class="sheet-brief" id="sheetBrief" style="display:none;"></p>
            </div>
            ${whyHtml}
            <p class="sheet-meta">${esc(article.source_name)} • ${esc(t('publishedAt'))}: ${esc(getShortDate(article.published_at || article.updated_at))} • ${esc(getExactTimestamp(article.updated_at || article.published_at, 'updatedAt'))}</p>
        `;

        const actionsHtml = `
            <div class="sheet-actions">
                <a href="${esc(article.article_url)}" target="_blank" rel="noopener noreferrer" class="sheet-link">${t('readOriginal')}</a>
                <button class="sheet-link" style="border:1px solid var(--accent);background:none;color:var(--accent);cursor:pointer;" onclick="this.closest('.sheet-actions').querySelector('.save-feedback').style.display='block';${isSaved ? '' : `window._saveFromSheet('${esc(article.id)}')`}">${isSaved ? t('savedAction') : t('saveAction')}</button>
                <p class="save-feedback" style="display:none;">${t('addedSaved')}</p>
            </div>
        `;

        const existingActions = bottomSheet.querySelector('.sheet-actions');
        if (existingActions) existingActions.remove();
        bottomSheet.insertAdjacentHTML('beforeend', actionsHtml);
        const expandBtn = $('sheetExpandBtn');
        expandBtn?.addEventListener('click', () => toggleSheetExpanded(expandBtn));
        // Expose save function
        window._saveFromSheet = (id) => {
            const a = allArticles.find(x => x.id === id);
            if (a) {
                bookmarks[a.id] = a;
                localStorage.setItem('dailyai_bookmarks', JSON.stringify(bookmarks));
                updateSavedCount();
            }
        };

        loadDetailedBrief(article);
        sheetBackdrop.classList.add('show');
        bottomSheet.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    async function loadDetailedBrief(article) {
        const briefEl = $('sheetBrief');
        const loadingEl = $('sheetBriefLoading');
        const briefWrap = $('sheetBriefWrap');
        if (!briefEl) return;

        const briefCacheKey = getBriefCacheKey(article);
        const cachedBrief = readCacheEntry(briefCacheKey, BRIEF_CACHE_TTL_MS);
        if (cachedBrief) {
            if (loadingEl) loadingEl.style.display = 'none';
            briefEl.style.display = 'block';
            briefEl.textContent = cachedBrief;
            if (briefWrap) briefWrap.scrollTop = 0;
            return;
        }

        try {
            const resp = await fetch('/api/articles/brief', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: article.headline || '',
                    source: article.source_name || '',
                    link: article.article_url || '',
                    summary: article.summary || '',
                    why_it_matters: article.why_it_matters || '',
                    topic: article.topic || 'general',
                    language: currentLanguage,
                }),
            });
            const data = await resp.json();
            if (resp.ok && data.brief) {
                if (loadingEl) loadingEl.style.display = 'none';
                briefEl.style.display = 'block';
                briefEl.textContent = data.brief;
                writeCacheEntry(briefCacheKey, data.brief);
                if (briefWrap) briefWrap.scrollTop = 0;
            } else {
                if (loadingEl) loadingEl.style.display = 'none';
                briefEl.style.display = 'block';
                briefEl.textContent = t('briefUnavailable');
            }
        } catch {
            if (loadingEl) loadingEl.style.display = 'none';
            briefEl.style.display = 'block';
            briefEl.textContent = t('briefUnavailable');
        }
    }
    function closeSheet() {
        sheetBackdrop.classList.remove('show');
        sheetBackdrop.classList.remove('focused');
        bottomSheet.classList.remove('show');
        bottomSheet.classList.remove('expanded');
        appShell?.classList.remove('focus-mode');
        const existingActions = bottomSheet.querySelector('.sheet-actions');
        if (existingActions) existingActions.remove();
        document.body.style.overflow = '';
    }

    function toggleSheetExpanded(buttonEl) {
        bottomSheet.classList.toggle('expanded');
        const isExpanded = bottomSheet.classList.contains('expanded');
        sheetBackdrop.classList.toggle('focused', isExpanded);
        appShell?.classList.toggle('focus-mode', isExpanded);
        if (buttonEl) {
            buttonEl.setAttribute('aria-label', isExpanded ? t('collapseView') : t('expandView'));
            buttonEl.setAttribute('title', isExpanded ? t('collapseView') : t('expandView'));
            const icon = buttonEl.querySelector('.sheet-expand-icon');
            if (icon) icon.textContent = isExpanded ? '⤡' : '⤢';
        }
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
        $('sidebarStreak').textContent = t('streakLine', { count: streak });
        // Show floating badge — auto-dismiss after 4 seconds
        if (!sessionStorage.getItem('dailyai_streak_dismissed') && streak >= 1) {
            streakBadge.textContent = t('streakBadge', { count: streak });
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
    function showToast(msg, duration = 2000) {
        clearTimeout(toastTimeout);
        toastEl.textContent = msg;
        toastEl.classList.add('show');
        toastTimeout = setTimeout(() => toastEl.classList.remove('show'), duration);
    }

    // ====================== UTILS ======================
    function getTimeAgo(dateStr) {
        if (!dateStr) return '';
        try {
            const d = new Date(dateStr), now = new Date();
            const m = Math.floor((now - d) / 60000);
            const locale = currentLanguage === 'de' ? 'de-DE' : currentLanguage === 'hi' ? 'hi-IN' : 'en-US';
            if (m < 1) return currentLanguage === 'de' ? 'Gerade eben' : currentLanguage === 'hi' ? 'अभी' : 'Just now';
            if (m < 60) return currentLanguage === 'de' ? `vor ${m} Min` : currentLanguage === 'hi' ? `${m} मिनट पहले` : `${m}m ago`;
            const h = Math.floor(m / 60);
            if (h < 24) return currentLanguage === 'de' ? `vor ${h} Std` : currentLanguage === 'hi' ? `${h} घंटे पहले` : `${h}h ago`;
            const dy = Math.floor(h / 24);
            if (dy < 7) return currentLanguage === 'de' ? `vor ${dy} Tg` : currentLanguage === 'hi' ? `${dy} दिन पहले` : `${dy}d ago`;
            return d.toLocaleDateString(locale, { month: 'short', day: 'numeric' });
        } catch { return ''; }
    }
    function getExactTimestamp(dateStr, labelKey = 'updatedAt') {
        if (!dateStr) return `${t(labelKey)}: -`;
        try {
            const d = new Date(dateStr);
            if (Number.isNaN(d.getTime())) return `${t(labelKey)}: -`;
            const locale = currentLanguage === 'de' ? 'de-DE' : currentLanguage === 'hi' ? 'hi-IN' : 'en-US';
            const formatted = d.toLocaleString(locale, {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            });
            return `${t(labelKey)}: ${formatted}`;
        } catch {
            return `${t(labelKey)}: -`;
        }
    }
    function getCardTimeMarkup(article) {
        const relative = esc(getTimeAgo(article.published_at || article.updated_at));
        const exact = esc(getExactTimestamp(article.published_at || article.updated_at, 'publishedAt'));
        return `<span class="card-time-relative">${relative}</span><span class="card-time-exact">${exact}</span>`;
    }
    function getShortDate(dateStr) {
        if (!dateStr) return '-';
        try {
            const d = new Date(dateStr);
            if (Number.isNaN(d.getTime())) return '-';
            const locale = currentLanguage === 'de' ? 'de-DE' : currentLanguage === 'hi' ? 'hi-IN' : 'en-US';
            return d.toLocaleDateString(locale, { month: 'short', day: 'numeric' });
        } catch {
            return '-';
        }
    }
    function hashCode(str) { let h=0; for(let i=0;i<(str||'').length;i++){h=((h<<5)-h)+str.charCodeAt(i);h|=0;} return Math.abs(h); }
    function esc(s) { const d=document.createElement('div'); d.textContent=s||''; return d.innerHTML; }

    document.addEventListener('DOMContentLoaded', init);
})();
