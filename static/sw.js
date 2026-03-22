// DailyAI Service Worker — deployment-aware caching
const SW_VERSION = new URL(self.location.href).searchParams.get('v') || 'dev';
const CACHE_NAME = `dailyai-${SW_VERSION}`;
const PRECACHE = ['/'];

self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(PRECACHE))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (e) => {
    const url = new URL(e.request.url);

    // Network-first for API calls
    if (url.pathname.startsWith('/api/')) {
        e.respondWith(
            fetch(e.request)
                .then(resp => {
                    const clone = resp.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
                    return resp;
                })
                .catch(() => caches.match(e.request))
        );
        return;
    }

    // Network-first for page navigations to avoid stale HTML after deploy.
    if (e.request.mode === 'navigate') {
        e.respondWith(
            fetch(e.request)
                .then(resp => {
                    const clone = resp.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
                    return resp;
                })
                .catch(() => caches.match(e.request))
        );
        return;
    }

    // Network-first for static assets; cache fallback for resilience.
    e.respondWith(
        fetch(e.request)
            .then(resp => {
                const clone = resp.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
                return resp;
            })
            .catch(() => caches.match(e.request))
    );
});
