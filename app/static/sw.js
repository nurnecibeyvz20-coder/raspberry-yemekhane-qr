const CACHE_V = 'v1';
const SHELL = [
    '/static/style.css',
    '/static/logo.jpg',
    '/static/qrcode.min.js',
    '/static/icons/icon-192.png',
];

self.addEventListener('install', function (event) {
    event.waitUntil(
        caches.open(CACHE_V).then(function (cache) {
            return cache.addAll(SHELL);
        })
    );
});

self.addEventListener('activate', function (event) {
    event.waitUntil(
        caches.keys().then(function (keys) {
            return Promise.all(
                keys.filter(function (k) { return k !== CACHE_V; })
                    .map(function (k) { return caches.delete(k); })
            );
        })
    );
});

self.addEventListener('fetch', function (event) {
    if (event.request.url.includes('/static/')) {
        // static: cache-first, ağdan gelirse cache'e yaz
        event.respondWith(
            caches.match(event.request).then(function (hit) {
                if (hit) return hit;
                return fetch(event.request).then(function (resp) {
                    if (resp.ok) {
                        const kopya = resp.clone();
                        caches.open(CACHE_V).then(function (cache) {
                            cache.put(event.request, kopya);
                        });
                    }
                    return resp;
                });
            })
        );
        return;
    }
    // diğer her şey: network-only; offline navigasyonda basit yanıt
    event.respondWith(
        fetch(event.request).catch(function (err) {
            if (event.request.mode === 'navigate') {
                return new Response('<h1>Bağlantı yok</h1>', {
                    status: 503,
                    headers: { 'Content-Type': 'text/html; charset=utf-8' },
                });
            }
            throw err;
        })
    );
});
