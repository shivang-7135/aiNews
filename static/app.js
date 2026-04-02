// DailyAI v3.0 — Scroll-first feed, onboarding, auto-dismiss streak
const API_URL = '/api/articles';
const FEED_CACHE_PREFIX = 'dailyai_feed_cache_v4';
const BRIEF_CACHE_PREFIX = 'dailyai_brief_cache_v2';
const FEED_CACHE_TTL_MS = 25 * 60 * 1000;
const BRIEF_CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000;
const MAX_FEED_ITEMS = 30;
const MAX_FEED_SUMMARY_WORDS = 50;
const RELEASE_VERSION = document.documentElement.dataset.releaseVersion || 'dev';
const VERSION_POLL_MS = 45 * 1000;
const BUILD_MARKER_KEY = 'dailyai_last_loaded_build';
const CACHE_SCHEMA_KEY = 'dailyai_cache_schema_v2';
const TOPIC_AFFINITY_KEY = 'dailyai_topic_affinity_v1';
const FEED_PAGE_SIZE = 15;


(function () {
    'use strict';

    const I18N = {
        en: {
            htmlLang: 'en',
            pageTitle: 'DailyAI - AI Decisions in 60 Seconds',
            pageDescription: 'DailyAI turns AI headlines into clear decisions, impact, and next actions.',
            onboardingTitle: 'Welcome to DailyAI',
            onboardingDesc: 'From AI headlines to action in under 60 seconds.',
            onboardingFeatureSwipe: 'Scroll fast, save what matters, ignore the noise.',
            onboardingFeatureLanguage: 'Use top bar to switch language instantly.',
            onboardingFeatureCountry: 'Use top bar country to localize your feed.',
            onboardingFeatureRead: 'Tap a card to see confidence, impact, and a role-based next step.',
            onboardingFeatureCache: 'Stories are cached locally for faster loading and fewer API calls.',
            onboardingCacheNote: 'Start in General mode, then switch Decision Lens anytime from the menu.',
            onboardingStart: 'Start with Scroll ↕',
            onboardingScroll: 'Start Exploring',
            navDiscover: 'Discover',
            navSaved: 'Saved Articles',
            languageTitle: '🌐 Language',
            regionTitle: '🌍 Region',
            lensTitle: '🎯 Decision Lens',
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
            sidebarHint: 'Stay in the loop, not in a doomscroll spiral.',
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
            settingsNav: 'Settings',
            appearanceTitle: '🌓 Appearance',
            themeSwitchToLight: 'Switch to Light Theme',
            themeSwitchToDark: 'Switch to Dark Theme',
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
            noSavedSub: 'Tap Save on any card to keep it here.',
            savedAppear: 'Saved articles appear after loading the feed.',
            swipeLabelSave: 'SAVE',
            swipeLabelSkip: 'SKIP',
            sortedLatest: '🕐 Sorted by latest',
            sortedRelevance: '⚡ Sorted by relevance',
            switchedTo: 'Switched to {name}',
            roleToast: 'Lens: {name}',
            lensActive: 'Lens: {name}',
            roleGeneral: 'General',
            roleFounder: 'Founder',
            roleDeveloper: 'Developer',
            roleStudent: 'Student',
            roleMarketer: 'Marketer',
            confidence: 'Confidence',
            confidenceHigh: 'High',
            confidenceMedium: 'Medium',
            confidenceLow: 'Low',
            impact: 'Impact',
            impactImmediate: 'Immediate',
            impactWatchlist: 'Watchlist',
            confidenceHint: 'Confidence estimates how reliable this story is based on source quality and corroboration.',
            impactHint: 'Impact estimates how soon this story could affect most people or teams.',
            decisionExplainer: 'How to read this: Confidence reflects source reliability; Impact reflects practical urgency.',
            doNext: 'Do this next',
            actionFounder: 'Map business impact for your team and shortlist one pilot this week.',
            actionDeveloper: 'Review technical implications and test one implementation path today.',
            actionStudent: 'Note one key concept and save this story for your learning revision.',
            actionMarketer: 'Extract one user-facing angle and draft a short communication test.',
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
            unsaveAction: '🗑 Unsave',
            addedSaved: '✓ Added to saved articles',
            removedSaved: 'Removed from saved',
            expandView: 'Expand View',
            collapseView: 'Compact View',
            loadingBrief: 'Generating detailed brief...',
            briefUnavailable: 'Detailed brief is not available yet. Please try again.',
            publishedAt: 'Published',
            updatedAt: 'Updated',
            whatsNewTitle: 'How DailyAI Helps You Decide',
            whatsNewBody: 'Every story now gives confidence, impact, and what to do next:',
            whatsNewAcknowledge: 'Start Exploring',
            streakLine: '🔥 Day {count} reading streak',
            streakBadge: '🔥 Day {count} reading DailyAI',
            shareAction: '📤 Share',
            sharedSuccess: 'Link copied to clipboard',
            readToday: '{count} stories read today',
            heroDismiss: 'Start Reading →',
            installPromptTitle: 'Add DailyAI to Home Screen',
            installPromptSub: 'Get instant AI news — no app store needed',
            installPromptBtn: 'Install',
            trustSignalText: 'AI-curated from 50+ sources · Updated every hour',
            pulseTitle: 'Market Pulse',
            pulseStories: '{count} stories',
            pulseFresh: 'Fresh: {time}',
            relatedStories: 'Related stories',
            swipeDiscoverHint: 'Swipe left or right to move across stories',
        },
        hi: {
            htmlLang: 'hi',
            pageTitle: 'DailyAI - 60 सेकंड में AI निर्णय',
            pageDescription: 'DailyAI AI हेडलाइन्स को स्पष्ट निर्णय, प्रभाव और अगले कदम में बदलता है।',
            onboardingTitle: 'DailyAI में आपका स्वागत है',
            onboardingDesc: 'AI हेडलाइन्स से एक्शन तक, 60 सेकंड के अंदर।',
            onboardingFeatureSwipe: 'तेज़ी से स्क्रॉल करें, काम की चीज़ सेव करें, बाकी शोर छोड़ दें।',
            onboardingFeatureLanguage: 'टॉप बार से भाषा तुरंत बदलें।',
            onboardingFeatureCountry: 'फीड को स्थानीय बनाने के लिए टॉप बार से देश बदलें।',
            onboardingFeatureRead: 'कार्ड पर टैप करके विश्वसनीयता, प्रभाव और भूमिका-आधारित अगला कदम देखें।',
            onboardingFeatureCache: 'स्टोरीज़ लोकल कैश में सेव होती हैं, इसलिए लोडिंग तेज और API कॉल कम होती हैं।',
            onboardingCacheNote: 'शुरुआत General मोड में करें, फिर मेन्यू से कभी भी Decision Lens बदलें।',
            onboardingStart: 'स्क्रॉल से शुरू करें ↕',
            onboardingScroll: 'एक्सप्लोर शुरू करें',
            navDiscover: 'खोजें',
            navSaved: 'सेव्ड लेख',
            languageTitle: '🌐 भाषा',
            regionTitle: '🌍 क्षेत्र',
            lensTitle: '🎯 निर्णय लेंस',
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
            sidebarHint: 'अपडेट रहो, doomscroll spiral में मत फंसो।',
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
            settingsNav: 'सेटिंग्स',
            appearanceTitle: '🌓 थीम',
            themeSwitchToLight: 'लाइट थीम पर जाएं',
            themeSwitchToDark: 'डार्क थीम पर जाएं',
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
            noSavedSub: 'लेख सेव करने के लिए कार्ड पर Save दबाएं।',
            savedAppear: 'फीड लोड होने के बाद सेव्ड लेख यहां दिखेंगे।',
            swipeLabelSave: 'सेव',
            swipeLabelSkip: 'स्किप',
            sortedLatest: '🕐 नवीनतम के अनुसार क्रमबद्ध',
            sortedRelevance: '⚡ प्रासंगिकता के अनुसार क्रमबद्ध',
            switchedTo: '{name} पर स्विच किया गया',
            roleToast: 'लेंस: {name}',
            lensActive: 'लेंस: {name}',
            roleGeneral: 'जनरल',
            roleFounder: 'फाउंडर',
            roleDeveloper: 'डेवलपर',
            roleStudent: 'स्टूडेंट',
            roleMarketer: 'मार्केटर',
            confidence: 'विश्वसनीयता',
            confidenceHigh: 'उच्च',
            confidenceMedium: 'मध्यम',
            confidenceLow: 'कम',
            impact: 'प्रभाव',
            impactImmediate: 'तुरंत',
            impactWatchlist: 'नज़र रखें',
            confidenceHint: 'विश्वसनीयता बताती है कि स्रोत और पुष्टि के आधार पर खबर कितनी भरोसेमंद है।',
            impactHint: 'प्रभाव बताता है कि यह खबर कितनी जल्दी ज़्यादातर लोगों या टीमों को प्रभावित कर सकती है।',
            decisionExplainer: 'इसे ऐसे समझें: विश्वसनीयता स्रोत की भरोसेमंदी बताती है; प्रभाव वास्तविक तात्कालिकता दिखाता है।',
            doNext: 'अगला कदम',
            actionFounder: 'टीम के लिए बिज़नेस प्रभाव मैप करें और इस सप्ताह एक पायलट तय करें।',
            actionDeveloper: 'तकनीकी असर देखें और आज एक इम्प्लीमेंटेशन पथ टेस्ट करें।',
            actionStudent: 'एक मुख्य सीख नोट करें और इस स्टोरी को रिविज़न के लिए सेव करें।',
            actionMarketer: 'एक यूज़र-फेसिंग एंगल निकालें और छोटा कम्युनिकेशन टेस्ट बनाएं।',
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
            unsaveAction: '🗑 हटाएं',
            addedSaved: '✓ सेव्ड लेखों में जोड़ा गया',
            removedSaved: 'सेव्ड से हटाया गया',
            expandView: 'व्यू बढ़ाएं',
            collapseView: 'कॉम्पैक्ट व्यू',
            loadingBrief: 'विस्तृत विवरण तैयार किया जा रहा है...',
            briefUnavailable: 'विस्तृत विवरण अभी उपलब्ध नहीं है। कृपया फिर कोशिश करें।',
            publishedAt: 'प्रकाशित',
            updatedAt: 'अपडेट किया गया',
            whatsNewTitle: 'DailyAI आपके निर्णय कैसे बेहतर करता है',
            whatsNewBody: 'अब हर स्टोरी में विश्वसनीयता, प्रभाव और अगला कदम मिलता है:',
            whatsNewAcknowledge: 'शुरू करें',
            streakLine: '🔥 दिन {count} पढ़ने की स्ट्रीक',
            streakBadge: '🔥 दिन {count} DailyAI पढ़ना',
            shareAction: '📤 शेयर',
            sharedSuccess: 'लिंक कॉपी हो गया',
            readToday: 'आज {count} खबरें पढ़ीं',
            heroDismiss: 'पढ़ना शुरू करें →',
            installPromptTitle: 'DailyAI को होम स्क्रीन पर जोड़ें',
            installPromptSub: 'तुरंत AI खबर पाएं — ऐप स्टोर की जरूरत नहीं',
            installPromptBtn: 'इंस्टॉल करें',
            trustSignalText: '50+ स्रोतों से AI द्वारा चयनित · हर घंटे अपडेट',
            pulseTitle: 'मार्केट पल्स',
            pulseStories: '{count} खबरें',
            pulseFresh: 'ताज़ा: {time}',
            relatedStories: 'मिलती-जुलती खबरें',
            swipeDiscoverHint: 'खबरों के बीच जाने के लिए बाएं या दाएं स्वाइप करें',
        },
        de: {
            htmlLang: 'de',
            pageTitle: 'DailyAI - KI-Entscheidungen in 60 Sekunden',
            pageDescription: 'DailyAI macht aus KI-Schlagzeilen klare Entscheidungen, Wirkung und nächste Schritte.',
            onboardingTitle: 'Willkommen bei DailyAI',
            onboardingDesc: 'Von KI-Headlines zu konkreten Aktionen in unter 60 Sekunden.',
            onboardingFeatureSwipe: 'Schnell scrollen, Relevantes speichern, den Rest ignorieren.',
            onboardingFeatureLanguage: 'Sprache direkt oben in der Leiste wechseln.',
            onboardingFeatureCountry: 'Land oben umstellen, um den Feed zu lokalisieren.',
            onboardingFeatureRead: 'Auf eine Karte tippen, um Sicherheit, Wirkung und den nächsten Schritt zu sehen.',
            onboardingFeatureCache: 'Stories werden lokal zwischengespeichert für schnelleres Laden und weniger API-Aufrufe.',
            onboardingCacheNote: 'Starte im allgemeinen Modus und wechsle den Entscheidungsfokus später im Menü.',
            onboardingStart: 'Mit Scrollen starten ↕',
            onboardingScroll: 'Jetzt entdecken',
            navDiscover: 'Entdecken',
            navSaved: 'Gespeicherte Artikel',
            languageTitle: '🌐 Sprache',
            regionTitle: '🌍 Region',
            lensTitle: '🎯 Entscheidungsfokus',
            sortBy: 'Sortieren nach',
            sortRelevance: '⚡ Relevanz',
            sortLatest: '🕐 Neueste',
            digestTitle: '📬 Täglicher Digest',
            digestDesc: 'Der tägliche Digest kommt bald.',
            readersSubscribed: 'Leser abonniert',
            emailPlaceholder: 'you@email.com',
            subscribe: 'Abonnieren',
            subscribing: 'Wird abonniert...',
            done: '✓ Fertig!',
            sidebarHint: 'Bleib up to date, nicht im Doomscroll-Strudel.',
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
            settingsNav: 'Einstellungen',
            appearanceTitle: '🌓 Design',
            themeSwitchToLight: 'Zum hellen Design wechseln',
            themeSwitchToDark: 'Zum dunklen Design wechseln',
            viewDiscover: 'Entdecken',
            viewSaved: 'Gespeichert',
            forYou: 'Für dich',
            topStories: 'Top-Storys',
            techScience: 'Technik & Wissenschaft',
            aiModels: 'KI-Modelle',
            tools: 'Tools',
            research: 'Forschung',
            business: 'Business',
            hintSkip: '← Überspringen',
            hintSave: 'Speichern →',
            emptyCaughtUp: 'Du bist auf dem neuesten Stand!',
            emptySub: 'Ziehe nach unten oder wechsle Tabs für mehr Storys.',
            reloadFeed: 'Feed neu laden ↻',
            noStories: 'Noch keine Storys',
            noStoriesSub: 'Zum Aktualisieren nach unten ziehen.',
            noSavedTitle: 'Noch keine gespeicherten Artikel',
            noSavedSub: 'Tippe auf Speichern bei einer Karte, um sie hier abzulegen.',
            savedAppear: 'Gespeicherte Artikel erscheinen nach dem Laden des Feeds.',
            swipeLabelSave: 'SPEICHERN',
            swipeLabelSkip: 'SKIP',
            sortedLatest: '🕐 Nach Neueste sortiert',
            sortedRelevance: '⚡ Nach Relevanz sortiert',
            switchedTo: 'Gewechselt zu {name}',
            roleToast: 'Fokus: {name}',
            lensActive: 'Fokus: {name}',
            roleGeneral: 'Allgemein',
            roleFounder: 'Gründer',
            roleDeveloper: 'Entwickler',
            roleStudent: 'Student',
            roleMarketer: 'Marketing',
            confidence: 'Sicherheit',
            confidenceHigh: 'Hoch',
            confidenceMedium: 'Mittel',
            confidenceLow: 'Niedrig',
            impact: 'Wirkung',
            impactImmediate: 'Sofort',
            impactWatchlist: 'Beobachten',
            confidenceHint: 'Sicherheit schätzt ein, wie verlässlich die Story laut Quelle und Bestätigungen ist.',
            impactHint: 'Wirkung schätzt ein, wie schnell die Story die meisten Menschen oder Teams betreffen könnte.',
            decisionExplainer: 'So liest du es: Sicherheit zeigt die Quellenzuverlässigkeit; Wirkung zeigt die praktische Dringlichkeit.',
            doNext: 'Nächster Schritt',
            actionFounder: 'Business-Auswirkung für dein Team einordnen und diese Woche einen Pilot wählen.',
            actionDeveloper: 'Technische Folgen prüfen und heute einen Umsetzungsweg testen.',
            actionStudent: 'Einen Kernpunkt notieren und Story für die Lern-Wiederholung speichern.',
            actionMarketer: 'Einen nutzerorientierten Winkel ableiten und einen kurzen Messaging-Test planen.',
            languageToast: 'Sprache: {name}',
            languageRefreshNotice: 'Sprache wurde geändert. Bitte Seite neu laden.',
            languageReloadTitle: 'Sprache aktualisiert',
            languageReloadPrompt: 'Sprache wurde geändert. Jetzt neu laden für das beste Erlebnis?',
            languageReloadNow: 'Jetzt neu laden',
            languageReloadLaterAction: 'Später',
            languageReloadLater: 'Sprache wurde geändert. Du kannst jederzeit neu laden für eine vollständige Aktualisierung.',
            subscribedToast: 'Abonniert! 🎉',
            subscribedOk: 'Abonniert!',
            networkError: 'Netzwerkfehler',
            failed: 'Fehlgeschlagen',
            saveToast: 'Gespeichert! 🔖',
            readOriginal: 'Original lesen →',
            saveAction: '🔖 Speichern',
            savedAction: '✓ Gespeichert',
            unsaveAction: '🗑 Entfernen',
            addedSaved: '✓ Zu gespeicherten Artikeln hinzugefügt',
            removedSaved: 'Aus Gespeichert entfernt',
            expandView: 'Ansicht vergrößern',
            collapseView: 'Kompakte Ansicht',
            loadingBrief: 'Ausführlicher Brief wird erstellt...',
            briefUnavailable: 'Ausführlicher Brief ist noch nicht verfügbar. Bitte erneut versuchen.',
            publishedAt: 'Veröffentlicht',
            updatedAt: 'Aktualisiert',
            whatsNewTitle: 'So hilft DailyAI bei Entscheidungen',
            whatsNewBody: 'Jede Story zeigt jetzt Sicherheit, Wirkung und den nächsten Schritt:',
            whatsNewAcknowledge: 'Los gehts',
            streakLine: '🔥 Tag {count} Lesestreak',
            streakBadge: '🔥 Tag {count} DailyAI gelesen',
            shareAction: '📤 Teilen',
            sharedSuccess: 'Link kopiert',
            readToday: 'Heute {count} Storys gelesen',
            heroDismiss: 'Jetzt lesen →',
            installPromptTitle: 'DailyAI zum Startbildschirm',
            installPromptSub: 'Sofortige KI-News holen — kein App Store nötig',
            installPromptBtn: 'Installieren',
            trustSignalText: 'KI-kuratiert aus 50+ Quellen · Stündlich aktualisiert',
            pulseTitle: 'Marktimpuls',
            pulseStories: '{count} Storys',
            pulseFresh: 'Neu: {time}',
            relatedStories: 'Aehnliche Storys',
            swipeDiscoverHint: 'Nach links oder rechts wischen, um Storys zu wechseln',
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

        setText('#languageSectionTitle', t('languageTitle'));
        setText('#regionSectionTitle', t('regionTitle'));
        setText('#roleSectionTitle', t('lensTitle'));
        setText('#appearanceSectionTitle', t('appearanceTitle'));
        setText('#sortSectionTitle', t('sortBy'));
        setText('#refreshSectionTitle', t('refreshSectionTitle'));
        setText('#digestSectionTitle', t('digestTitle'));
        
        setText('#heroDismiss', t('heroDismiss'));
        setText('#installPromptTitle', t('installPromptTitle'));
        setText('#installPromptSub', t('installPromptSub'));
        setText('#installPromptBtn', t('installPromptBtn'));
        setText('#trustSignalText', t('trustSignalText'));
        updateProgressRing();

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
        const versionLabel = $('appVersionLabel');
        if (versionLabel) versionLabel.textContent = getBuildFooterText();

        const savedBtn = $('savedBtn');
        if (savedBtn) savedBtn.setAttribute('aria-label', t('viewSaved'));
        const bottomSettingsBtn_el = $('bottomSettingsBtn');
        if (bottomSettingsBtn_el) bottomSettingsBtn_el.setAttribute('aria-label', t('settingsNav'));
        setText('#bottomSettingsLabel', t('settingsNav'));
        setText('#bottomDiscoverLabel', t('viewDiscover'));
        setText('#bottomSavedLabel', t('viewSaved'));

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
        'AI Models': 'linear-gradient(135deg, #0f2027, #203a43, #2c5364)',
        'Tools': 'linear-gradient(135deg, #1a1a2e, #16213e, #0f3460)',
        'Research': 'linear-gradient(135deg, #0d0d0d, #1a1a2e, #16213e)',
        'Top Stories': 'linear-gradient(135deg, #1f1c2c, #928dab)',
        'Business': 'linear-gradient(135deg, #141e30, #243b55)',
        'Tech & Science': 'linear-gradient(135deg, #0f2027, #203a43, #2c5364)',
    };
    const TOPIC_PLACEHOLDER_IMAGES = {
        'AI Models': [
            'https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1676299081847-824916de030a?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1686191128892-3d19f2d7d53f?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1620712943543-bcc4688e7485?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1655720828018-edd2daec9349?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1697577418970-95d99b5a55cf?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1710993267928-e78e6d293048?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1684369175833-4b445ad6bfb5?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1680538400916-608e118e5e67?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1696429199683-0154c4dfa944?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1712002641088-9d76f9080889?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1633356122544-f134324a6cee?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1555255707-c07966088b7b?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1580894894513-541e068a3e2b?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1617791160505-cb03e tried-96fa?auto=format&fit=crop&w=800&q=80',
        ],
        'Top Stories': [
            'https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1495020689067-958852a7765e?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1585829365295-ab7cd400c167?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1503023345310-bd7c1de61c7d?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1558618666-fcd25c85f82e?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1478720568477-152d9b164e26?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1528819622765-d6bcf132f793?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1555949963-ff9fe0c870eb?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=800&q=80',
        ],
        'Tech & Science': [
            'https://images.unsplash.com/photo-1532094349884-543bc11b234d?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1518152006812-edab29b069ac?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1507413245164-6160d8298b31?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1573164713714-d95e436ab8d6?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1535223289827-42f1e9919769?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1614064641938-3bbee52942c7?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1559757175-5700dde675bc?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1517976487492-5750f3195933?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1636690513351-0af1763f6571?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1561557944-6e7860d1a7eb?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1580894908361-967195033215?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1624953587687-daf255b6b80a?auto=format&fit=crop&w=800&q=80',
        ],
        'Business': [
            'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1579532537598-459ecdaf39cc?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1591696205602-2f950c417cb9?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1551135049-8a33b5883817?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1559526324-4b87b5e36e44?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1504868584819-f8e8b4b6d7e3?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1642790106117-e829e14a795f?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1553835973-dec43bfddbeb?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1444653614773-995cb1ef9efa?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=800&q=80',
        ],
        'Tools': [
            'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1515879218367-8466d910aaa4?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1461749280684-dccba630e2f6?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1629654297299-c8506221ca97?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1618477247222-acbdb0e159b3?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1551650975-87deedd944c3?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1504639725590-34d0984388bd?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1603468620905-8de7d86b781e?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1618401471353-b98afee0b2eb?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1605379399642-870262d3d051?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1542831371-29b0f74f9713?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1544256718-3bcf237f3974?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1633356122102-3fe601e05bd2?auto=format&fit=crop&w=800&q=80',
        ],
        'Research': [
            'https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1576086213369-97a306d36557?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1614935151651-0bea6508db6b?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1530973428-5bf2db2e4d71?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1628595351029-c2bf17511435?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1507668077129-56e32842fceb?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1529079018732-bdef9ab517a1?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1636466497217-26a8cbeaf0aa?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1544383835-bda2bc66a55d?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1607988795691-3d0147b43231?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1585435465945-bef5a93f8849?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=800&q=80',
            'https://images.unsplash.com/photo-1655720828018-edd2daec9349?auto=format&fit=crop&w=800&q=80',
        ],
    };

    // Keyword-to-image map for content-relevant fallback images
    const KEYWORD_IMAGE_MAP = [
        { keywords: ['robot', 'robotics', 'humanoid', 'boston dynamics'], img: 'https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['chip', 'semiconductor', 'nvidia', 'gpu', 'processor', 'hardware'], img: 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['regulation', 'law', 'act', 'policy', 'governance', 'government', 'eu', 'congress'], img: 'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['startup', 'funding', 'billion', 'million', 'valuation', 'raise', 'invest', 'venture'], img: 'https://images.unsplash.com/photo-1559526324-4b87b5e36e44?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['openai', 'chatgpt', 'gpt'], img: 'https://images.unsplash.com/photo-1676299081847-824916de030a?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['google', 'gemini', 'deepmind', 'alphabet'], img: 'https://images.unsplash.com/photo-1573804633927-bfcbcd909acd?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['apple', 'siri', 'iphone', 'mac'], img: 'https://images.unsplash.com/photo-1611532736597-de2d4265fba3?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['microsoft', 'copilot', 'azure', 'bing'], img: 'https://images.unsplash.com/photo-1633419461186-7d40a38105ec?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['meta', 'facebook', 'llama', 'instagram', 'zuckerberg'], img: 'https://images.unsplash.com/photo-1636114673156-052a83459fc4?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['autonomous', 'self-driving', 'car', 'vehicle', 'tesla', 'waymo'], img: 'https://images.unsplash.com/photo-1549317661-bd32c8ce0afe?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['healthcare', 'medical', 'drug', 'patient', 'doctor', 'diagnosis', 'health'], img: 'https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['education', 'student', 'school', 'university', 'teacher', 'learning'], img: 'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['climate', 'energy', 'solar', 'environment', 'green', 'carbon', 'sustainability'], img: 'https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['security', 'cyber', 'hack', 'privacy', 'deepfake', 'threat', 'attack'], img: 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['space', 'nasa', 'satellite', 'rocket', 'launch', 'orbit', 'mars'], img: 'https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['data', 'database', 'analytics', 'cloud', 'aws', 'server'], img: 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['open source', 'linux', 'github', 'developer', 'code'], img: 'https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['image', 'video', 'generate', 'art', 'creative', 'dall-e', 'midjourney', 'diffusion'], img: 'https://images.unsplash.com/photo-1634017839464-5c339afa60d0?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['china', 'chinese', 'beijing', 'baidu'], img: 'https://images.unsplash.com/photo-1547981609-4b6bfe67ca0b?auto=format&fit=crop&w=800&q=80' },
        { keywords: ['benchmark', 'test', 'score', 'performance', 'comparison'], img: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=800&q=80' },
    ];

    const TOPIC_LOCAL_FALLBACK_IMAGES = {
        'AI Models': '/static/topic-covers/ai-models.svg',
        'Top Stories': '/static/topic-covers/top-stories.svg',
        'Tech & Science': '/static/topic-covers/tech-science.svg',
        'Business': '/static/topic-covers/business.svg',
        'Tools': '/static/topic-covers/tools.svg',
        'Research': '/static/topic-covers/research.svg',
    };

    const COUNTRY_FLAGS = {
        'US': '🇺🇸', 'GB': '🇬🇧', 'IN': '🇮🇳', 'DE': '🇩🇪', 'FR': '🇫🇷', 'CA': '🇨🇦',
        'AU': '🇦🇺', 'JP': '🇯🇵', 'KR': '🇰🇷', 'CN': '🇨🇳', 'BR': '🇧🇷', 'SG': '🇸🇬',
        'AE': '🇦🇪', 'IL': '🇮🇱', 'GLOBAL': '🌐',
    };
    const AVATAR_COLORS = ['#aca3ff', '#6f5fea', '#ff9eca', '#00D2FF', '#8b5cf6', '#6C5CE7', '#ff6e84', '#5948d3'];
    const FALLBACK_ARTICLES = [
        { id: 'fb-1', headline: 'OpenAI Announces GPT-5 with Multimodal Reasoning', summary: 'OpenAI has unveiled GPT-5, featuring advanced multimodal reasoning capabilities that can process text, images, and audio simultaneously.', why_it_matters: 'A major leap in AI capability, potentially transforming multiple industries.', topic: 'AI Models', source_name: 'TechCrunch', source_avatar_url: null, image_url: null, article_url: '#', published_at: new Date().toISOString(), updated_at: new Date().toISOString() },
        { id: 'fb-2', headline: 'EU Finalizes AI Act Implementation Timeline', summary: 'The European Union has released the final implementation timeline for the AI Act, giving companies 12 months to comply.', why_it_matters: 'Companies worldwide must adapt their AI products to meet these regulations.', topic: 'Top Stories', source_name: 'Reuters', source_avatar_url: null, image_url: null, article_url: '#', published_at: new Date().toISOString(), updated_at: new Date().toISOString() },
        { id: 'fb-3', headline: 'New Open-Source LLM Surpasses Commercial Models', summary: 'A new open-source language model has outperformed leading commercial models on multiple benchmarks.', why_it_matters: 'Open-source AI is closing the gap, democratizing access to powerful tools.', topic: 'Research', source_name: 'ArXiv', source_avatar_url: null, image_url: null, article_url: '#', published_at: new Date().toISOString(), updated_at: new Date().toISOString() },
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
    function getCookieValue(name) {
        const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const match = document.cookie.match(new RegExp(`(?:^|; )${escaped}=([^;]*)`));
        return match ? decodeURIComponent(match[1]) : '';
    }
    function getApiPostHeaders() {
        const headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
        };
        const csrfToken = getCookieValue('dailyai_csrf');
        if (csrfToken) headers['X-CSRF-Token'] = csrfToken;
        return headers;
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

    function readTopicAffinity() {
        try {
            const parsed = JSON.parse(localStorage.getItem(TOPIC_AFFINITY_KEY) || '{}');
            return (parsed && typeof parsed === 'object') ? parsed : {};
        } catch {
            return {};
        }
    }

    function writeTopicAffinity(data) {
        try {
            localStorage.setItem(TOPIC_AFFINITY_KEY, JSON.stringify(data));
        } catch {
            // Best-effort personalization persistence.
        }
    }

    function updateTopicAffinity(topic, action) {
        const normalizedTopic = String(topic || '').trim();
        if (!normalizedTopic) return;

        const deltas = {
            tap: 0.8,
            read: 1.2,
            save: 2.2,
            skip: -0.9,
        };
        const delta = deltas[action] || 0;
        if (!delta) return;

        const affinity = readTopicAffinity();
        const prev = Number(affinity[normalizedTopic]) || 0;
        const next = Math.max(-8, Math.min(18, prev + delta));
        affinity[normalizedTopic] = Number(next.toFixed(2));
        writeTopicAffinity(affinity);
    }

    function rankAndDiversifyForYou(articles) {
        const affinity = readTopicAffinity();
        const now = Date.now();
        const scored = (articles || []).map((article) => {
            const topic = String(article.topic || '').trim();
            const importanceScore = Number(article.importance || 0);
            const topicAffinity = Number(affinity[topic] || 0);
            const publishedMs = new Date(article.published_at || article.updated_at || 0).getTime() || 0;
            const ageHours = Math.max(0, (now - publishedMs) / (1000 * 60 * 60));
            const freshnessBoost = Math.max(0, 4 - ageHours * 0.15);
            const score = importanceScore + (topicAffinity * 0.9) + freshnessBoost;
            return { article, score };
        }).sort((a, b) => b.score - a.score);

        const picked = [];
        const perSourceCap = 2;
        const sourceCount = {};
        for (const item of scored) {
            const source = String(item.article.source_name || 'unknown');
            const used = Number(sourceCount[source] || 0);
            if (used >= perSourceCap) continue;
            picked.push(item.article);
            sourceCount[source] = used + 1;
            if (picked.length >= MAX_FEED_ITEMS) break;
        }

        return picked;
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
    let currentTheme = localStorage.getItem('dailyai_theme') || 'dark';
    let syncCode = localStorage.getItem('dailyai_sync_code') || '';
    let consentGiven = localStorage.getItem('dailyai_consent') === '1';
    let currentSheetArticleId = '';
    let feedOffset = 0;
    let hasMoreFeed = true;
    let isLoadingMoreFeed = false;

    // ---- DOM ----
    const $ = id => document.getElementById(id);
    const appShell = $('appShell');
    const bootLoader = $('bootLoader');
    const swipeStack = $('swipeStack');
    const swipeContainer = $('swipeContainer');
    const scrollFeed = $('scrollFeed');
    const swipeEmpty = $('swipeEmpty');
    const feed = $('feed');
    const bottomSettingsBtn = $('bottomSettingsBtn');
    const bottomDiscoverBtn = $('bottomDiscoverBtn');
    const filterTabs = $('filterTabs');
    const sidebar = $('sidebar');
    const sidebarBackdrop = $('sidebarBackdrop');
    const sheetBackdrop = $('sheetBackdrop');
    const bottomSheet = $('bottomSheet');
    const sheetContent = $('sheetContent');
    const toastEl = $('toast');
    const viewTitle = $('viewTitle');
    const countrySelect = $('countrySelect');
    const languageSelect = $('languageSelect');
    const themeTogglePill = $('themeTogglePill');
    const modeToggle = $('modeToggle');
    const refreshNewsBtn = $('sidebarRefreshBtn');
    const langReloadBackdrop = $('langReloadBackdrop');
    const langReloadNowBtn = $('langReloadNowBtn');
    const langReloadLaterBtn = $('langReloadLaterBtn');
    const whatsNewBackdrop = $('whatsNewBackdrop');
    const whatsNewOkBtn = $('whatsNewOkBtn');
    const whatsNewList = $('whatsNewList');

    if (!['en', 'de'].includes(currentLanguage)) {
        currentLanguage = 'en';
        localStorage.setItem('dailyai_language', currentLanguage);
    }
    const ALLOWED_COUNTRIES = ['US', 'GB', 'DE', 'IN', 'GLOBAL'];
    if (!ALLOWED_COUNTRIES.includes(currentCountry)) {
        currentCountry = 'GLOBAL';
        localStorage.setItem('dailyai_country', currentCountry);
    }

    // ====================== MARKET-FIT UPGRADE ======================
    let deferredPrompt;
    function updateProgressRing() {
        const today = new Date().toDateString();
        let count = parseInt(localStorage.getItem('dailyai_read_count') || '0', 10);
        if (localStorage.getItem('dailyai_read_date') !== today) count = 0;
        
        const max = 10;
        const progress = Math.min(count / max, 1);
        const circumference = 97.4;
        const offset = circumference - (progress * circumference);
        
        const fillEl = document.querySelector('.progress-ring-fill');
        if (fillEl) fillEl.style.strokeDashoffset = offset;
        
        const countEl = document.querySelector('.progress-count');
        if (countEl) countEl.textContent = count;
        
        const ringRow = document.querySelector('.reading-progress');
        if (ringRow) {
            ringRow.setAttribute('aria-label', t('readToday', { count }));
            ringRow.title = t('readToday', { count });
        }
    }

    function trackReadArticle() {
        const today = new Date().toDateString();
        let lastDate = localStorage.getItem('dailyai_read_date');
        let count = parseInt(localStorage.getItem('dailyai_read_count') || '0', 10);
        if (lastDate !== today) {
            count = 0;
            localStorage.setItem('dailyai_read_date', today);
        }
        if (count < 10) {
            count++;
            localStorage.setItem('dailyai_read_count', count);
            updateProgressRing();
        }
    }

    function initMarketFitFeatures() {
        const heroBanner = document.getElementById('heroBanner');
        if (heroBanner) heroBanner.style.display = 'none';

        // PWA Install Prompt
        const promptEl = document.getElementById('installPrompt');
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            if (promptEl && !localStorage.getItem('dailyai_install_dismissed')) {
                setTimeout(() => promptEl.style.display = 'flex', 8000); // 8s delay

                document.getElementById('installPromptBtn')?.addEventListener('click', async () => {
                    promptEl.style.display = 'none';
                    if (deferredPrompt) {
                        deferredPrompt.prompt();
                        const { outcome } = await deferredPrompt.userChoice;
                        deferredPrompt = null;
                        if (outcome === 'accepted') localStorage.setItem('dailyai_install_dismissed', '1');
                    }
                });
                document.getElementById('installPromptClose')?.addEventListener('click', () => {
                    promptEl.style.display = 'none';
                    localStorage.setItem('dailyai_install_dismissed', '1');
                });
            }
        });

        updateProgressRing();
    }

    // ====================== INIT ======================
    async function init() {
        if (!['dark', 'light'].includes(currentTheme)) {
            currentTheme = 'dark';
        }
        applyTheme(currentTheme);

        // Sidebar
        bottomSettingsBtn?.addEventListener('click', openSidebar);
        $('sidebarClose').addEventListener('click', closeSidebar);
        sidebarBackdrop.addEventListener('click', closeSidebar);

        // Sidebar nav
        $('navDiscover')?.addEventListener('click', () => switchView('discover'));
        $('navSaved')?.addEventListener('click', () => switchView('saved'));
        bottomDiscoverBtn?.addEventListener('click', () => switchView('discover'));
        $('savedBtn')?.addEventListener('click', () => switchView('saved'));

        // Sort
        $('sortGroup').addEventListener('click', onSortClick);

        // Country
        countrySelect.addEventListener('change', onCountryChange);

        // Language
        languageSelect.addEventListener('change', onLanguageChange);


        // Theme — stopPropagation prevents topBar's scroll-to-top from firing
        themeTogglePill?.addEventListener('click', (e) => {
            e.stopPropagation();
            onThemeToggle();
        });
        // Also support keyboard for accessibility
        themeTogglePill?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); onThemeToggle(); }
        });

        // Newsletter
        $('subscribeForm').addEventListener('submit', onSubscribe);

        // Filter tabs
        filterTabs.addEventListener('click', onTabClick);

        // Mode toggle (legacy; hidden in current UX)
        modeToggle?.addEventListener('click', toggleFeedMode);

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
        updateSavedCount();
        restoreSort();
        restoreFeedMode();
        loadLanguages();
        loadCountries();
        fetchSubscriberCount();
        setupServiceWorker();
        startVersionWatcher();
        initSyncRestore();
        initConsentBanner();
        updateSyncCodeUI();

        initMarketFitFeatures();

        // Onboarding check
        if (!localStorage.getItem('dailyai_onboarded')) {
            showOnboarding();
        } else if (!syncCode) {
            // Already onboarded but no sync code — show topic picker
            showTopicOnboarding();
        }

        // Pull to refresh & TopBar tap-to-top
        setupPullToRefresh();

        // Load feed
        showSkeleton();
        fetchArticles(currentTopic);
    }

    function setupPullToRefresh() {
        let touchstartY = 0;
        let isPulling = false;
        const scrollEls = [$('scrollFeed'), $('feed')];
        const fab = $('scrollTopFab');

        scrollEls.forEach(el => {
            if (!el) return;

            // Toggle FAB visibility on scroll
            el.addEventListener('scroll', () => {
                if (fab) {
                    if (el.scrollTop > 300) {
                        fab.classList.add('show');
                    } else {
                        fab.classList.remove('show');
                    }
                }
            }, { passive: true });

            el.addEventListener('touchstart', e => {
                if (el.scrollTop <= 0) {
                    touchstartY = e.touches[0].clientY;
                    isPulling = true;
                } else {
                    isPulling = false;
                }
            }, { passive: true });

            el.addEventListener('touchmove', e => {
                if (!isPulling) return;
                const y = e.touches[0].clientY;
                if (y < touchstartY) isPulling = false;
            }, { passive: true });

            el.addEventListener('touchend', e => {
                if (!isPulling) return;
                const y = e.changedTouches[0].clientY;
                if (y - touchstartY > 80) {
                    refreshNewsNow();
                }
                isPulling = false;
            }, { passive: true });
        });

        const scrollToTop = () => {
            scrollEls.forEach(el => {
                if (el && el.style.display !== 'none' && el.scrollTop > 0) {
                    el.scrollTo({ top: 0, behavior: 'smooth' });
                }
            });
        };

        const titleEl = $('viewTitle');
        titleEl?.addEventListener('click', scrollToTop);
        $('scrollTopFab')?.addEventListener('click', scrollToTop);
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
            const cacheSchema = String(localStorage.getItem(CACHE_SCHEMA_KEY) || '').trim();
            const needsSchemaReset = cacheSchema !== CACHE_SCHEMA_KEY;
            const needsBuildReset = !previousBuild || previousBuild !== RELEASE_VERSION;

            if (needsSchemaReset || needsBuildReset) {
                await clearClientCaches({ includeServiceWorkers: true });
                localStorage.setItem(CACHE_SCHEMA_KEY, CACHE_SCHEMA_KEY);
                localStorage.setItem(BUILD_MARKER_KEY, RELEASE_VERSION);

                // Reload only when coming from a previous known build to guarantee fresh script state.
                if (previousBuild && previousBuild !== RELEASE_VERSION) {
                    location.reload();
                    return true;
                }
            }
            localStorage.setItem(CACHE_SCHEMA_KEY, CACHE_SCHEMA_KEY);
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
        let currentStep = 0;
        const steps = overlay.querySelectorAll('.onboard-step');
        const dots = overlay.querySelectorAll('.onboard-dot');
        const nextBtn = $('onboardNext');

        function goToStep(idx) {
            steps.forEach(s => s.classList.remove('active'));
            dots.forEach(d => d.classList.remove('active'));
            steps[idx]?.classList.add('active');
            dots[idx]?.classList.add('active');
            currentStep = idx;
            if (idx === steps.length - 1) {
                nextBtn.textContent = 'Get Started';
            } else {
                nextBtn.textContent = 'Next';
            }
        }

        nextBtn?.addEventListener('click', () => {
            if (currentStep < steps.length - 1) {
                goToStep(currentStep + 1);
            } else {
                dismissOnboarding(overlay, 'scroll');
            }
        });

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

        // Show topic onboarding if no sync code yet
        if (!syncCode) {
            setTimeout(() => showTopicOnboarding(), 500);
        }
    }

    // ====================== TOPIC ONBOARDING ======================
    async function showTopicOnboarding() {
        const backdrop = $('topicOnboardBackdrop');
        if (!backdrop) return;

        let existingTopics = [];
        const isUpdate = !!syncCode;

        if (isUpdate) {
            try {
                const resp = await fetch(`/api/profile/${encodeURIComponent(syncCode)}`);
                if (resp.ok) {
                    const data = await resp.json();
                    existingTopics = data.profile?.preferred_topics || [];
                }
            } catch (e) {
                console.warn('Could not load existing topics', e);
            }
        }

        backdrop.style.display = 'flex';
        const selected = new Set(existingTopics);

        // Clean up old listeners by cloning
        let goBtn = $('topicOnboardGo');
        const newGoBtn = goBtn.cloneNode(true);
        goBtn.parentNode.replaceChild(newGoBtn, goBtn);
        goBtn = newGoBtn;

        goBtn.style.display = ''; // Ensure it's not hidden from a previous run
        goBtn.textContent = isUpdate ? 'Update Topics' : 'Build My Feed';
        goBtn.disabled = selected.size < 2;

        const grid = backdrop.querySelector('.topic-pill-grid');
        grid.style.display = 'flex';
        if (isUpdate) {
            $('topicOnboardSync').style.display = 'none';
            backdrop.querySelector('.topic-onboard-sub').textContent = 'Update your personalized feed';
        }

        const pills = backdrop.querySelectorAll('.topic-pill');
        pills.forEach(pill => {
            const topic = pill.dataset.topic;
            // clone pill to remove old listeners
            const newPill = pill.cloneNode(true);
            pill.parentNode.replaceChild(newPill, pill);

            if (selected.has(topic)) {
                newPill.classList.add('selected');
            } else {
                newPill.classList.remove('selected');
            }

            newPill.addEventListener('click', () => {
                const t = newPill.dataset.topic;
                if (selected.has(t)) {
                    selected.delete(t);
                    newPill.classList.remove('selected');
                } else {
                    selected.add(t);
                    newPill.classList.add('selected');
                }
                goBtn.disabled = selected.size < 2;
            });
        });

        goBtn.addEventListener('click', async () => {
            goBtn.disabled = true;
            goBtn.textContent = isUpdate ? 'Updating...' : 'Creating...';
            try {
                const url = isUpdate ? `/api/profile/${encodeURIComponent(syncCode)}` : '/api/profile/new';
                const method = isUpdate ? 'PUT' : 'POST';
                const resp = await fetch(url, {
                    method: method,
                    headers: getApiPostHeaders(),
                    body: JSON.stringify({
                        preferred_topics: Array.from(selected),
                        country: currentCountry,
                        language: currentLanguage,
                    }),
                });
                const data = await resp.json();

                if (!isUpdate && data.profile && data.profile.sync_code) {
                    syncCode = data.profile.sync_code;
                    localStorage.setItem('dailyai_sync_code', syncCode);
                    updateSyncCodeUI();
                }

                if (isUpdate) {
                    backdrop.style.display = 'none';
                    showToast('Topics updated!');
                } else {
                    // First time: show sync code
                    $('topicSyncCode').textContent = syncCode;
                    $('topicOnboardSync').style.display = '';
                    goBtn.style.display = 'none';
                    grid.style.display = 'none';
                    backdrop.querySelector('.topic-onboard-sub').textContent = 'Your personalized feed is ready!';
                }

                // Re-fetch articles with personalization
                fetchArticles(currentTopic, { forceRefresh: true });

            } catch (e) {
                goBtn.textContent = isUpdate ? 'Update Topics' : 'Build My Feed';
                goBtn.disabled = false;
                showToast(isUpdate ? 'Could not update topics.' : 'Could not create profile. Try again.');
            }
        });

        // Copy sync code buttons (ensure attached only once if possible, but safe to re-attach if not cloned)
        // They aren't cloned here so we rely on multiple clicks just doing the same thing, 
        // but let's avoid duplicates for Done
        const doneBtn = $('topicOnboardDone');
        if (doneBtn) {
            const newDone = doneBtn.cloneNode(true);
            doneBtn.parentNode.replaceChild(newDone, doneBtn);
            newDone.addEventListener('click', () => {
                backdrop.style.display = 'none';
            });
        }

        const copyBtn = $('topicSyncCopy');
        if (copyBtn) {
            const newCopy = copyBtn.cloneNode(true);
            copyBtn.parentNode.replaceChild(newCopy, copyBtn);
            newCopy.addEventListener('click', () => copySyncCode());
        }
    }

    function copySyncCode() {
        if (!syncCode) return;
        navigator.clipboard?.writeText(syncCode).then(() => {
            showToast('Sync code copied!');
        }).catch(() => {
            showToast(syncCode);
        });
    }

    function updateSyncCodeUI() {
        const sidebarDisplay = $('syncSidebarDisplay');
        const sidebarCode = $('sidebarSyncCode');
        if (syncCode && sidebarDisplay && sidebarCode) {
            sidebarCode.textContent = syncCode;
            sidebarDisplay.style.display = '';
        }
    }

    // ====================== SYNC RESTORE ======================
    function initSyncRestore() {
        const restoreBtn = $('syncRestoreBtn');
        const restoreInput = $('syncRestoreInput');
        const restoreStatus = $('syncRestoreStatus');
        if (!restoreBtn || !restoreInput) return;

        restoreBtn.addEventListener('click', async () => {
            const code = restoreInput.value.trim();
            if (!code) return;
            restoreBtn.disabled = true;
            try {
                const resp = await fetch(`/api/profile/${encodeURIComponent(code)}`);
                if (resp.status === 404) {
                    if (restoreStatus) restoreStatus.textContent = 'Profile not found';
                    restoreBtn.disabled = false;
                    return;
                }
                const data = await resp.json();
                if (data.profile) {
                    syncCode = data.profile.sync_code;
                    localStorage.setItem('dailyai_sync_code', syncCode);
                    if (restoreStatus) restoreStatus.textContent = `Restored as ${syncCode}`;
                    updateSyncCodeUI();
                    fetchArticles(currentTopic, { forceRefresh: true });
                    showToast(`Welcome back, ${syncCode}!`);
                }
            } catch {
                if (restoreStatus) restoreStatus.textContent = 'Restore failed';
            }
            restoreBtn.disabled = false;
        });

        $('sidebarSyncCopy')?.addEventListener('click', () => copySyncCode());

        // Change Topics — re-open the topic picker
        $('changeTopicsBtn')?.addEventListener('click', () => {
            closeSidebar();
            showTopicOnboarding();
        });
    }

    // ====================== SIGNAL TRACKING ======================
    function recordSignal(articleId, action, topic) {
        if (topic) updateTopicAffinity(topic, action);
        if (!syncCode || !topic) return;
        fetch(`/api/profile/${encodeURIComponent(syncCode)}/signal`, {
            method: 'POST',
            headers: getApiPostHeaders(),
            body: JSON.stringify({ article_id: articleId, action, topic }),
        }).catch(() => { /* fire-and-forget */ });
    }

    // ====================== CONSENT BANNER ======================
    function initConsentBanner() {
        if (consentGiven || localStorage.getItem('dailyai_consent') === '0') return;
        const banner = $('consentBanner');
        if (!banner) return;
        banner.style.display = '';

        $('consentAccept')?.addEventListener('click', () => {
            consentGiven = true;
            localStorage.setItem('dailyai_consent', '1');
            banner.style.display = 'none';
        });
        $('consentDecline')?.addEventListener('click', () => {
            localStorage.setItem('dailyai_consent', '0');
            banner.style.display = 'none';
        });
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
        if (!modeToggle) return;
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
        feedMode = 'scroll';
        swipeContainer.style.display = 'none';
        scrollFeed.style.display = '';
        renderScrollFeed();
    }

    // ====================== SCROLL FEED (InShorts) ======================
    let cardObserver = null;

    function setupCardObserver() {
        if (cardObserver) cardObserver.disconnect();
        cardObserver = new IntersectionObserver((entries) => {
            entries.forEach((entry, idx) => {
                if (entry.isIntersecting) {
                    const card = entry.target;
                    const delay = Math.min(idx * 80, 400);
                    setTimeout(() => card.classList.add('card-visible'), delay);
                    cardObserver.unobserve(card);
                }
            });
        }, { root: scrollFeed, threshold: 0.1 });
    }

    function renderScrollFeed() {
        scrollFeed.innerHTML = '';
        const articles = getFilteredArticles();
        if (articles.length === 0) {
            scrollFeed.innerHTML = `<div style="padding:60px 20px;text-align:center;"><p style="font-size:48px;margin-bottom:12px;">📰</p><p style="font-size:16px;font-weight:600;">${t('noStories')}</p><p style="font-size:14px;color:var(--text3);margin-top:4px;">${t('noStoriesSub')}</p></div>`;
            return;
        }

        setupCardObserver();

        articles.forEach(article => {
            const card = createScrollCard(article);
            scrollFeed.appendChild(card);
            if (cardObserver) cardObserver.observe(card);
        });

        // Page counter
        const counter = $('scrollPageCounter');
        const currentPageEl = $('scrollCurrentPage');
        const totalPagesEl = $('scrollTotalPages');
        if (counter && currentPageEl && totalPagesEl) {
            totalPagesEl.textContent = articles.length;
            currentPageEl.textContent = '1';
            counter.style.display = '';
            counter.classList.add('visible');

            // Update page on scroll
            scrollFeed.onscroll = () => {
                const cards = scrollFeed.querySelectorAll('.scroll-card');
                if (!cards.length) return;
                const scrollTop = scrollFeed.scrollTop;
                const cardH = cards[0].offsetHeight + 12; // margin
                const idx = Math.round(scrollTop / cardH);
                currentPageEl.textContent = Math.min(idx + 1, articles.length);

                const nearBottom = scrollFeed.scrollHeight - (scrollFeed.scrollTop + scrollFeed.clientHeight) < 420;
                if (nearBottom) loadMoreFeedIfNeeded();
            };
        }
    }

    function applyTheme(theme) {
        currentTheme = theme === 'light' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', currentTheme);
        localStorage.setItem('dailyai_theme', currentTheme);
        // Pill toggle updates itself via CSS :root[data-theme] selectors
    }

    function onThemeToggle() {
        applyTheme(currentTheme === 'light' ? 'dark' : 'light');
    }

    function limitWords(text, maxWords = MAX_FEED_SUMMARY_WORDS) {
        const words = String(text || '').trim().split(/\s+/).filter(Boolean);
        if (words.length <= maxWords) return String(text || '');
        return `${words.slice(0, maxWords).join(' ')}...`;
    }



    function getReadingTimeMarkup(article) {
        // Average silent reading speed is ~250 wpm. Using character count approx (1000 chars ~ 1 min)
        const chars = (article.headline || '').length + (article.summary || '').length + (article.why_it_matters || '').length || 800;
        const mins = Math.max(1, Math.ceil(chars / 800));
        return `<div class="card-reading-time">${mins} min read</div>`;
    }

    function getCardBadges(article) {
        let badgesHtml = '';
        if (article.importance >= 9) {
            badgesHtml += `<div class="card-badge-trending">Trending</div>`;
        } else if (article.importance >= 8) {
            const pubDate = new Date(article.published_at || article.updated_at || new Date());
            const hoursOld = (new Date() - pubDate) / (1000 * 60 * 60);
            if (hoursOld < 12) badgesHtml += `<div class="card-badge-breaking">Breaking</div>`;
        }
        return badgesHtml;
    }

    function createScrollCard(article) {
        const card = document.createElement('div');
        card.className = 'scroll-card';
        card.dataset.id = article.id;
        // Set importance as data attribute for CSS-driven glow effects
        if (article.importance) card.dataset.importance = String(article.importance);
        const avatarColor = AVATAR_COLORS[hashCode(article.source_name) % AVATAR_COLORS.length];
        const initial = (article.source_name || 'D')[0].toUpperCase();
        const importanceHtml = article.importance ? `<div class="relevance-badge">🔥 ${article.importance}/10</div>` : '';
        const tapToReadHtml = `<p class="tap-to-read">✨ Tap to generate AI brief...</p>`;
        const whyHtml = article.why_it_matters ? `<div class="card-why">💡 ${esc(article.why_it_matters)}</div>` : '';
        const topicTag = article.topic ? `<span class="card-topic-tag">${esc(article.topic)}</span>` : '';
        const rawImg = article.image_url
            ? `<img src="${esc(article.image_url)}" alt="" class="card-image" loading="lazy" onerror="this.onerror=null; this.src='${esc(getTopicFallbackCoverUrl(article.topic))}';">`
            : buildTopicCoverImg(article);
        const imgHtml = `<div class="card-image-wrap">${topicTag}${rawImg}</div>`;

        const badgesHtml = getCardBadges(article);
        const readingTimeHtml = getReadingTimeMarkup(article);

        const isSaved = !!bookmarks[article.id];
        card.innerHTML = `
            ${imgHtml}
            <div class="card-body">
                ${badgesHtml}
                ${readingTimeHtml}
                <h2 class="card-headline">${esc(article.headline)}</h2>
                ${importanceHtml}
                ${tapToReadHtml}
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
        if (currentTopic === 'For You') {
            return (allArticles || []).slice(0, MAX_FEED_ITEMS);
        }
        const filtered = (allArticles || []).filter(
            a => (a.topic || '').toLowerCase() === currentTopic.toLowerCase()
        );
        return filtered.slice(0, MAX_FEED_ITEMS);
    }

    function renderMarketPulse(articles) {
        const pulseEl = $('marketPulse');
        if (!pulseEl) return;

        const topicCounts = {};
        for (const article of (articles || [])) {
            const topic = String(article.topic || 'Top Stories').trim();
            topicCounts[topic] = Number(topicCounts[topic] || 0) + 1;
        }
        const topTopics = Object.entries(topicCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 3);

        if (topTopics.length === 0) {
            pulseEl.style.display = 'none';
            pulseEl.innerHTML = '';
            return;
        }

        const newestArticle = (articles || [])
            .map((article) => new Date(article.published_at || article.updated_at || 0).getTime() || 0)
            .sort((a, b) => b - a)[0] || Date.now();
        const freshness = getTimeAgo(new Date(newestArticle).toISOString());

        pulseEl.style.display = 'flex';
        pulseEl.innerHTML = `
            <div class="market-pulse-header">
                <span class="market-pulse-title">${esc(t('pulseTitle'))}</span>
                <span class="market-pulse-fresh">${esc(t('pulseFresh', { time: freshness }))}</span>
            </div>
            <div class="market-pulse-topics">
                ${topTopics.map(([topic, count]) => `
                    <button class="market-pulse-chip" data-topic="${esc(topic)}" type="button">
                        <span class="chip-topic">${esc(topic)}</span>
                        <span class="chip-count">${esc(t('pulseStories', { count }))}</span>
                    </button>
                `).join('')}
            </div>
        `;

        pulseEl.querySelectorAll('.market-pulse-chip').forEach((chip) => {
            chip.addEventListener('click', () => {
                const targetTopic = chip.dataset.topic;
                if (!targetTopic) return;
                const tab = Array.from(document.querySelectorAll('.filter-pill')).find(
                    (pill) => String(pill.dataset.topic || '').toLowerCase() === String(targetTopic).toLowerCase()
                );
                if (tab) tab.click();
            });
        });
    }

    function getTopicCoverUrl(topic, seed = '') {
        const list = TOPIC_PLACEHOLDER_IMAGES[topic] || TOPIC_PLACEHOLDER_IMAGES['Top Stories'];
        if (!Array.isArray(list) || list.length === 0) return TOPIC_PLACEHOLDER_IMAGES['Top Stories'][0];
        const idx = Math.abs(hashCode(String(seed || topic || 'default'))) % list.length;
        return list[idx];
    }

    function getTopicFallbackCoverUrl(topic) {
        return TOPIC_LOCAL_FALLBACK_IMAGES[topic] || TOPIC_LOCAL_FALLBACK_IMAGES['Top Stories'];
    }

    function getKeywordImage(headline) {
        if (!headline) return null;
        const lower = headline.toLowerCase();
        for (const entry of KEYWORD_IMAGE_MAP) {
            for (const kw of entry.keywords) {
                if (lower.includes(kw)) return entry.img;
            }
        }
        return null;
    }

    function buildTopicCoverImg(article) {
        const topic = article.topic || 'Top Stories';
        const headline = article.headline || '';
        // 1st: Try keyword-based content-relevant image
        const keywordImg = getKeywordImage(headline);
        if (keywordImg) {
            const fallbackUrl = getTopicFallbackCoverUrl(topic);
            return `<img src="${esc(keywordImg)}" alt="${esc(headline)}" class="card-image" loading="lazy" onerror="this.onerror=null;this.src='${esc(fallbackUrl)}'">`;
        }
        // 2nd: Pick from expanded topic pool using unique seed
        const seed = `${article.id || ''}|${headline}|${article.source_name || ''}`;
        const coverUrl = getTopicCoverUrl(topic, seed);
        const fallbackUrl = getTopicFallbackCoverUrl(topic);
        return `<img src="${esc(coverUrl)}" alt="${esc(headline)}" class="card-image" loading="lazy" onerror="this.onerror=null;this.src='${esc(fallbackUrl)}'">`;
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
                opt.textContent = `${flag} ${String(code).toUpperCase()}`;
                opt.title = translateCountryName(code, name);
                if (code === currentCountry) opt.selected = true;
                countrySelect.appendChild(opt);
            }
            updateTopBarCountry();
        } catch { /* fallback: keep default */ }
    }

    async function loadLanguages() {
        const fallback = { en: 'English', de: 'Deutsch' };
        const allowedLangs = new Set(['en', 'de']);
        try {
            const resp = await fetch('/api/languages');
            const data = await resp.json();
            const apiLanguages = data.languages || fallback;
            const languages = Object.fromEntries(
                Object.entries(apiLanguages).filter(([code]) => allowedLangs.has(code))
            );
            languageSelect.innerHTML = '';
            for (const [code, name] of Object.entries(languages)) {
                const opt = document.createElement('option');
                opt.value = code;
                opt.textContent = String(name);
                opt.title = name;
                if (code === currentLanguage) opt.selected = true;
                languageSelect.appendChild(opt);
            }
            if (!Object.keys(languages).length) {
                for (const [code, name] of Object.entries(fallback)) {
                    const opt = document.createElement('option');
                    opt.value = code;
                    opt.textContent = String(name);
                    opt.title = name;
                    if (code === currentLanguage) opt.selected = true;
                    languageSelect.appendChild(opt);
                }
            }
        } catch {
            languageSelect.innerHTML = '';
            for (const [code, name] of Object.entries(fallback)) {
                const opt = document.createElement('option');
                opt.value = code;
                opt.textContent = String(name);
                opt.title = name;
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
        const name = translateCountryName(currentCountry, currentCountry);
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
                headers: getApiPostHeaders(),
            });
        } catch {
            // Ignore refresh failures and fallback to normal article fetch.
        }

        await fetchArticles(currentTopic, { forceRefresh: true });
        const localizedLabel = {
            en: { en: 'English', de: 'Deutsch' },
            de: { en: 'Englisch', de: 'Deutsch' },
        };
        const name = (localizedLabel[currentLanguage] && localizedLabel[currentLanguage][currentLanguage]) || currentLanguage;
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
        // Superseded by animated onboarding guide — no-op
        return;
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
        const compactCode = currentCountry === 'GLOBAL' ? 'GLB' : String(currentCountry).toUpperCase();
        const countryBadge = document.getElementById('topBarCountry');
        if (countryBadge) {
            countryBadge.textContent = `${flag} ${compactCode}`;
            countryBadge.setAttribute('title', displayName);
            countryBadge.setAttribute('aria-label', displayName);
        }

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
        bottomSettingsBtn?.classList.add('active');
    }
    function closeSidebar() {
        sidebar.classList.remove('show');
        sidebarBackdrop.classList.remove('show');
        bottomSettingsBtn?.classList.remove('active');
    }

    // ====================== VIEW SWITCH ======================
    function switchView(view) {
        currentView = view;
        closeSidebar();
        document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));
        bottomDiscoverBtn?.classList.toggle('active', view === 'discover');
        $('savedBtn')?.classList.toggle('active', view === 'saved');
        if (view === 'discover') {
            $('navDiscover')?.classList.add('active');
            viewTitle.textContent = t('viewDiscover');
            filterTabs.style.display = '';
            feed.style.display = 'none';
            if (modeToggle) modeToggle.style.display = 'none';
            renderFeed();
        } else {
            $('navSaved')?.classList.add('active');
            viewTitle.textContent = t('viewSaved');
            filterTabs.style.display = 'none';
            swipeContainer.style.display = 'none';
            scrollFeed.style.display = 'none';
            const counter = $('scrollPageCounter');
            if (counter) { counter.style.display = 'none'; counter.classList.remove('visible'); }
            feed.style.display = '';
            if (modeToggle) modeToggle.style.display = 'none';
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
        feed.querySelectorAll('.saved-unsave-btn').forEach((btn) => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                const cardEl = btn.closest('.feed-card');
                await unsaveArticle(id, { sourceEl: btn, cardEl, rerenderSaved: true });
            });
        });
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
        const importanceHtml = article.importance ? `<div class="relevance-badge">🔥 ${article.importance}/10</div>` : '';
        const tapToReadHtml = `<p class="tap-to-read">✨ Tap to generate AI brief...</p>`;
        const whyHtml = article.why_it_matters ? `<div class="card-why">💡 ${esc(article.why_it_matters)}</div>` : '';
        const topicTag = article.topic ? `<span class="card-topic-tag">${esc(article.topic)}</span>` : '';
        const rawImg = article.image_url
            ? `<img src="${esc(article.image_url)}" alt="" class="card-image" loading="lazy" onerror="this.onerror=null; this.src='${esc(getTopicFallbackCoverUrl(article.topic))}';">`
            : buildTopicCoverImg(article);
        const imgHtml = `<div class="card-image-wrap">${topicTag}${rawImg}</div>`;

        const badgesHtml = getCardBadges(article);
        const readingTimeHtml = getReadingTimeMarkup(article);

        return `<div class="feed-card" data-id="${esc(article.id)}" style="animation-delay:${i * 50}ms">
            ${imgHtml}
            <div class="card-body">
                ${badgesHtml}
                ${readingTimeHtml}
                <h2 class="card-headline">${esc(article.headline)}</h2>
                ${importanceHtml}
                ${tapToReadHtml}
                ${whyHtml}
                <div class="card-footer">
                    <div class="card-source"><div class="source-avatar" style="background:${avatarColor}">${initial}</div><span class="source-name">${esc(article.source_name)}</span></div>
                    <button class="saved-unsave-btn" data-id="${esc(article.id)}">${esc(t('unsaveAction'))}</button>
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
                method: 'POST', headers: getApiPostHeaders(),
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
        const { forceRefresh = false, append = false } = options;
        const param = topic === 'For You' ? 'all' : topic;
        const cacheKey = getFeedCacheKey(param, currentCountry, currentLanguage);
        if (!append && !forceRefresh) {
            const cachedArticles = readCacheEntry(cacheKey, FEED_CACHE_TTL_MS);
            if (cachedArticles && cachedArticles.length > 0) {
                allArticles = cachedArticles;
                feedOffset = cachedArticles.length;
                hasMoreFeed = cachedArticles.length >= FEED_PAGE_SIZE;
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
            const effectiveOffset = append ? feedOffset : 0;
            let url = `${API_URL}?topic=${encodeURIComponent(param)}&country=${encodeURIComponent(currentCountry)}&language=${encodeURIComponent(currentLanguage)}&offset=${effectiveOffset}&limit=${FEED_PAGE_SIZE}`;
            if (syncCode) url += `&sync_code=${encodeURIComponent(syncCode)}`;
            const resp = await Promise.race([fetch(url), timeout]);
            const data = await resp.json();
            const batch = (data.articles && data.articles.length > 0) ? data.articles : [];
            if (!append) {
                allArticles = batch.length > 0 ? batch : FALLBACK_ARTICLES;
                feedOffset = batch.length;
            } else if (batch.length > 0) {
                const seenIds = new Set(allArticles.map(a => a.id));
                const merged = batch.filter(a => !seenIds.has(a.id));
                allArticles = allArticles.concat(merged);
                feedOffset = allArticles.length;
            }
            hasMoreFeed = Boolean(data.has_more);

            if (!append && batch.length > 0) {
                writeCacheEntry(cacheKey, batch);
                if (param === 'all') hydrateTopicCachesFromAll(batch);
            }
        } catch {
            if (!append) {
                const staleArticles = readCacheEntry(cacheKey, FEED_CACHE_TTL_MS, true);
                allArticles = (staleArticles && staleArticles.length > 0) ? staleArticles : FALLBACK_ARTICLES;
                feedOffset = allArticles.length;
                hasMoreFeed = false;
            }
        }
        sortArticles();
        swipeCardIndex = 0;
        swipeEmpty.style.display = 'none';
        if (append && scrollFeed && scrollFeed.style.display !== 'none') {
            const prevTop = scrollFeed.scrollTop;
            renderScrollFeed();
            requestAnimationFrame(() => {
                scrollFeed.scrollTop = prevTop;
            });
        } else {
            renderFeed();
        }
        setGlobalLoading(false);
    }

    async function loadMoreFeedIfNeeded() {
        if (isLoadingMoreFeed || !hasMoreFeed || currentView !== 'discover') return;
        isLoadingMoreFeed = true;
        try {
            await fetchArticles(currentTopic, { append: true });
        } finally {
            isLoadingMoreFeed = false;
        }
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
                headers: getApiPostHeaders(),
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
        const topicTag = article.topic ? `<span class="card-topic-tag">${esc(article.topic)}</span>` : '';
        const rawImg = article.image_url
            ? `<img src="${esc(article.image_url)}" alt="" class="card-image" loading="lazy" onerror="this.onerror=null; this.src='${esc(getTopicFallbackCoverUrl(article.topic))}';">`
            : buildTopicCoverImg(article);
        const imgHtml = `<div class="card-image-wrap">${topicTag}${rawImg}</div>`;
        const importanceHtml = article.importance ? `<div class="relevance-badge">🔥 ${article.importance}/10</div>` : '';
        const tapToReadHtml = `<p class="tap-to-read">✨ Tap to generate AI brief...</p>`;
        const badgesHtml = getCardBadges(article);
        const readingTimeHtml = getReadingTimeMarkup(article);

        card.innerHTML = `
            <div class="swipe-label swipe-label-save">${t('swipeLabelSave')}</div>
            <div class="swipe-label swipe-label-skip">${t('swipeLabelSkip')}</div>
            ${imgHtml}
            <div class="card-body">
                ${badgesHtml}
                ${readingTimeHtml}
                <h2 class="card-headline">${esc(article.headline)}</h2>
                ${importanceHtml}
                ${tapToReadHtml}
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
            recordSignal(article.id, 'save', article.topic || article.category || '');
        }
        if (dir < 0 && article) {
            recordSignal(article.id, 'skip', article.topic || article.category || '');
        }
        swipeCardIndex++;
        setTimeout(() => renderSwipeStack(), 350);
    }
    function updateSavedCount() {
        const count = Object.keys(bookmarks).length;
        const savedCountEl = $('savedCount');
        if (savedCountEl) savedCountEl.textContent = count;
        const savedBtn = $('savedBtn');
        if (savedBtn) savedBtn.classList.toggle('has-saved', count > 0);
    }

    function saveArticle(article) {
        if (!article?.id) return;
        bookmarks[article.id] = article;
        localStorage.setItem('dailyai_bookmarks', JSON.stringify(bookmarks));
        updateSavedCount();
        recordSignal(article.id, 'save', article.topic || article.category || '');
    }

    function showDustbinThrow(sourceEl) {
        if (!sourceEl) return Promise.resolve();
        return new Promise((resolve) => {
            const sourceRect = sourceEl.getBoundingClientRect();
            const dustbin = document.createElement('div');
            dustbin.className = 'dustbin-indicator';
            dustbin.textContent = '🗑️';

            const token = document.createElement('div');
            token.className = 'unsave-fly-token';
            token.textContent = '🔖';
            token.style.left = `${sourceRect.left + sourceRect.width / 2}px`;
            token.style.top = `${sourceRect.top + sourceRect.height / 2}px`;

            document.body.appendChild(dustbin);
            document.body.appendChild(token);

            requestAnimationFrame(() => {
                token.classList.add('animate');
                dustbin.classList.add('show');
            });

            setTimeout(() => {
                token.remove();
                dustbin.remove();
                resolve();
            }, 520);
        });
    }

    async function unsaveArticle(articleId, options = {}) {
        if (!articleId || !bookmarks[articleId]) return;
        const { sourceEl = null, cardEl = null, rerenderSaved = true } = options;

        if (cardEl) {
            cardEl.classList.add('feed-card-unsaving');
        }
        await showDustbinThrow(sourceEl || cardEl);

        delete bookmarks[articleId];
        localStorage.setItem('dailyai_bookmarks', JSON.stringify(bookmarks));
        updateSavedCount();
        showToast(t('removedSaved'));

        if (rerenderSaved && currentView === 'saved') {
            renderSavedList();
        }
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
        currentSheetArticleId = String(article.id || '');
        recordSignal(article.id || '', 'tap', article.topic || article.category || '');
        trackReadArticle();
        
        const whyHtml = article.why_it_matters ? `<div class="sheet-why">💡 ${esc(article.why_it_matters)}</div>` : '';
        const isSaved = !!bookmarks[article.id];
        sheetContent.innerHTML = `
            <div class="sheet-headline-row">
                <h2 class="sheet-headline">${esc(article.headline)}</h2>
            </div>
            <div class="sheet-brief-wrap" id="sheetBriefWrap">
                <div class="sheet-brief-loading" id="sheetBriefLoading">
                    <p class="sheet-brief" style="margin-bottom:6px;">${esc(t('loadingBrief'))}</p>
                    <div class="line w60"></div>
                    <div class="line w95"></div>
                    <div class="line w88"></div>
                    <div class="line w90"></div>
                    <div class="line w80"></div>
                    <div class="line w92"></div>
                </div>
                <p class="sheet-brief" id="sheetBrief" style="display:none;"></p>
            </div>
            ${whyHtml}
            <p class="sheet-swipe-hint">${esc(t('swipeDiscoverHint'))}</p>
            <section class="sheet-related" id="sheetRelated"></section>
            <p class="sheet-meta">${esc(article.source_name)} • ${esc(t('publishedAt'))}: ${esc(getShortDate(article.published_at || article.updated_at))} • ${esc(getExactTimestamp(article.updated_at || article.published_at, 'updatedAt'))}</p>
        `;

        const actionsHtml = `
            <div class="sheet-actions">
                <button class="sheet-link sheet-link-share" id="sheetShareBtn" aria-label="${t('shareAction')}" title="${t('shareAction')}">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"></path>
                        <polyline points="16 6 12 2 8 6"></polyline>
                        <line x1="12" y1="2" x2="12" y2="15"></line>
                    </svg>
                </button>
                <button class="sheet-link sheet-link-secondary" id="sheetSaveBtn">${isSaved ? t('unsaveAction') : t('saveAction')}</button>
                <a href="${esc(article.article_url)}" target="_blank" rel="noopener noreferrer" class="sheet-link">${t('readOriginal')}</a>
                <p class="save-feedback" id="sheetSaveFeedback" style="display:none;">${t('addedSaved')}</p>
            </div>
        `;

        const existingActions = bottomSheet.querySelector('.sheet-actions');
        if (existingActions) existingActions.remove();
        bottomSheet.insertAdjacentHTML('beforeend', actionsHtml);

        const shareBtn = $('sheetShareBtn');
        shareBtn?.addEventListener('click', async () => {
            const shareData = {
                title: 'DailyAI: ' + article.headline,
                text: article.summary,
                url: article.article_url
            };
            try {
                if (navigator.share) await navigator.share(shareData);
                else {
                    await navigator.clipboard.writeText(shareData.url);
                    showToast(t('sharedSuccess'));
                }
            } catch (e) { console.error('Share failed', e); }
        });

        const saveFromSheet = (id) => {
            const a = allArticles.find(x => x.id === id) || article;
            if (a) saveArticle(a);
        };
        const saveBtn = $('sheetSaveBtn');
        const saveFeedback = $('sheetSaveFeedback');
        saveBtn?.addEventListener('click', async () => {
            const currentlySaved = !!bookmarks[article.id];
            if (currentlySaved) {
                await unsaveArticle(article.id, { sourceEl: saveBtn, rerenderSaved: currentView === 'saved' });
                saveBtn.textContent = t('saveAction');
                if (saveFeedback) {
                    saveFeedback.textContent = t('removedSaved') || 'Removed from saved';
                    saveFeedback.style.display = 'block';
                }
            } else {
                saveFromSheet(article.id);
                saveBtn.textContent = t('unsaveAction');
                if (saveFeedback) {
                    saveFeedback.textContent = t('addedSaved');
                    saveFeedback.style.display = 'block';
                }
                showToast(t('saveToast'));
            }
        });

        loadDetailedBrief(article);
        renderRelatedStories(article);
        attachSheetSwipeNavigation();
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
            briefEl.innerHTML = formatBriefContent(cachedBrief);
            if (briefWrap) briefWrap.scrollTop = 0;
            return;
        }

        try {
            const resp = await fetch('/api/articles/brief', {
                method: 'POST',
                headers: getApiPostHeaders(),
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
                briefEl.innerHTML = formatBriefContent(data.brief);
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

    function getStorySimilarityScore(baseArticle, candidate) {
        if (!baseArticle || !candidate || baseArticle.id === candidate.id) return -1;
        let score = 0;
        if ((baseArticle.topic || '').toLowerCase() === (candidate.topic || '').toLowerCase()) score += 4;
        if ((baseArticle.source_name || '').toLowerCase() === (candidate.source_name || '').toLowerCase()) score += 1.5;

        const tokenize = (text) => String(text || '')
            .toLowerCase()
            .replace(/[^a-z0-9\s]/g, ' ')
            .split(/\s+/)
            .filter((w) => w.length > 3);

        const aTokens = new Set(tokenize(baseArticle.headline));
        const bTokens = new Set(tokenize(candidate.headline));
        let overlap = 0;
        aTokens.forEach((token) => {
            if (bTokens.has(token)) overlap += 1;
        });
        score += Math.min(overlap, 5);

        const publishedMs = new Date(candidate.published_at || candidate.updated_at || 0).getTime() || 0;
        const ageHours = Math.max(0, (Date.now() - publishedMs) / (1000 * 60 * 60));
        score += Math.max(0, 3 - ageHours * 0.2);
        return score;
    }

    function renderRelatedStories(baseArticle) {
        const relatedEl = $('sheetRelated');
        if (!relatedEl) return;

        const related = (allArticles || [])
            .map((candidate) => ({
                candidate,
                score: getStorySimilarityScore(baseArticle, candidate),
            }))
            .filter((entry) => entry.score > 0)
            .sort((a, b) => b.score - a.score)
            .slice(0, 6)
            .map((entry) => entry.candidate);

        if (!related.length) {
            relatedEl.innerHTML = '';
            return;
        }

        relatedEl.innerHTML = `
            <p class="sheet-related-title">${esc(t('relatedStories'))}</p>
            <div class="sheet-related-rail">
                ${related.map((article) => `
                    <button class="sheet-related-card" data-id="${esc(article.id)}" type="button">
                        <span class="related-topic">${esc(article.topic || 'Top Stories')}</span>
                        <span class="related-headline">${esc(article.headline || '')}</span>
                        <span class="related-time">${esc(getTimeAgo(article.published_at || article.updated_at))}</span>
                    </button>
                `).join('')}
            </div>
        `;

        relatedEl.querySelectorAll('.sheet-related-card').forEach((button) => {
            button.addEventListener('click', () => {
                const articleId = button.dataset.id;
                const article = (allArticles || []).find((entry) => String(entry.id) === String(articleId));
                if (article) openSheet(article);
            });
        });
    }

    function getCurrentFeedArticles() {
        if (currentView !== 'discover') return [];
        if (currentTopic === 'For You') return allArticles || [];
        return (allArticles || []).filter(
            (article) => String(article.topic || '').toLowerCase() === String(currentTopic || '').toLowerCase()
        );
    }

    function openAdjacentStoryFromSheet(direction) {
        const stories = getCurrentFeedArticles();
        if (!stories.length || !currentSheetArticleId) return;
        const index = stories.findIndex((article) => String(article.id) === currentSheetArticleId);
        if (index < 0) return;
        const targetIndex = index + direction;
        if (targetIndex < 0 || targetIndex >= stories.length) return;
        openSheet(stories[targetIndex]);
    }

    function attachSheetSwipeNavigation() {
        const contentEl = $('sheetContent');
        if (!contentEl) return;
        const existingCleanup = contentEl._sheetSwipeCleanup;
        if (typeof existingCleanup === 'function') existingCleanup();

        let startX = 0;
        let startY = 0;
        const onTouchStart = (event) => {
            const touch = event.touches && event.touches[0];
            if (!touch) return;
            startX = touch.clientX;
            startY = touch.clientY;
        };
        const onTouchEnd = (event) => {
            const touch = event.changedTouches && event.changedTouches[0];
            if (!touch) return;
            const deltaX = touch.clientX - startX;
            const deltaY = touch.clientY - startY;
            if (Math.abs(deltaX) < 75) return;
            if (Math.abs(deltaY) > Math.abs(deltaX) * 0.7) return;
            if (deltaX < 0) openAdjacentStoryFromSheet(1);
            if (deltaX > 0) openAdjacentStoryFromSheet(-1);
        };

        contentEl.addEventListener('touchstart', onTouchStart, { passive: true });
        contentEl.addEventListener('touchend', onTouchEnd, { passive: true });
        contentEl._sheetSwipeCleanup = () => {
            contentEl.removeEventListener('touchstart', onTouchStart);
            contentEl.removeEventListener('touchend', onTouchEnd);
            contentEl._sheetSwipeCleanup = null;
        };
    }

    function closeSheet() {
        const contentEl = $('sheetContent');
        const existingCleanup = contentEl && contentEl._sheetSwipeCleanup;
        if (typeof existingCleanup === 'function') existingCleanup();
        currentSheetArticleId = '';
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
            const locale = currentLanguage === 'de' ? 'de-DE' : 'en-US';
            if (m < 1) return currentLanguage === 'de' ? 'Gerade eben' : 'Just now';
            if (m < 60) return currentLanguage === 'de' ? `vor ${m} Min` : `${m}m ago`;
            const h = Math.floor(m / 60);
            if (h < 24) return currentLanguage === 'de' ? `vor ${h} Std` : `${h}h ago`;
            const dy = Math.floor(h / 24);
            if (dy < 7) return currentLanguage === 'de' ? `vor ${dy} Tg` : `${dy}d ago`;
            return d.toLocaleDateString(locale, { month: 'short', day: 'numeric' });
        } catch { return ''; }
    }
    function getExactTimestamp(dateStr, labelKey = 'updatedAt') {
        if (!dateStr) return `${t(labelKey)}: -`;
        try {
            const d = new Date(dateStr);
            if (Number.isNaN(d.getTime())) return `${t(labelKey)}: -`;
            const locale = currentLanguage === 'de' ? 'de-DE' : 'en-US';
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
            const locale = currentLanguage === 'de' ? 'de-DE' : 'en-US';
            return d.toLocaleDateString(locale, { month: 'short', day: 'numeric' });
        } catch {
            return '-';
        }
    }
    function formatBriefContent(text) {
        const escaped = esc(text || '');
        const withBold = escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        return withBold
            .split(/\n{2,}/)
            .map((block) => `<p>${block.replace(/\n/g, '<br>')}</p>`)
            .join('');
    }
    function hashCode(str) { let h = 0; for (let i = 0; i < (str || '').length; i++) { h = ((h << 5) - h) + str.charCodeAt(i); h |= 0; } return Math.abs(h); }
    function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

    // ====================== SESSION ANALYTICS ======================
    const _sessionStats = { taps: 0, saves: 0, reads: 0, skips: 0, briefs_opened: 0, time_spent_seconds: 0, session_count: 1 };
    const _sessionStart = Date.now();

    function trackAction(action) {
        if (action === 'tap') _sessionStats.taps++;
        else if (action === 'save') _sessionStats.saves++;
        else if (action === 'read' || action === 'brief') { _sessionStats.reads++; _sessionStats.briefs_opened++; }
        else if (action === 'skip') _sessionStats.skips++;
    }

    function flushAnalytics() {
        if (!syncCode) return;
        _sessionStats.time_spent_seconds = Math.round((Date.now() - _sessionStart) / 1000);
        const payload = JSON.stringify(_sessionStats);
        // Prefer sendBeacon for page unload, fetch otherwise
        if (navigator.sendBeacon) {
            navigator.sendBeacon(`/api/profile/${encodeURIComponent(syncCode)}/analytics`, new Blob([payload], { type: 'application/json' }));
        } else {
            fetch(`/api/profile/${encodeURIComponent(syncCode)}/analytics`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload, keepalive: true
            }).catch(() => { });
        }
    }

    // Flush analytics every 2 minutes
    setInterval(() => { if (syncCode) flushAnalytics(); }, 2 * 60 * 1000);
    // Flush on page unload
    window.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') flushAnalytics(); });
    window.addEventListener('pagehide', flushAnalytics);

    document.addEventListener('DOMContentLoaded', init);
})();
