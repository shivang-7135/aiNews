// DailyAI Service Worker — basic offline caching
const CACHE_NAME = 'dailyai-v1';
const PRECACHE = [
    '/',
    '/static/styles.css',
    '/static/app.js',
];

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
    // Network-first for API calls
    if (e.request.url.includes('/api/')) {
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

    // Cache-first for static assets
    e.respondWith(
        caches.match(e.request).then(cached => cached || fetch(e.request))
    );
});
