// SAFE-Triage Hospital Lite — minimal offline service worker.
//
// Strategy: cache-first for the app shell + hashed asset bundles, network-first
// for navigations so an online user always gets the freshest HTML when possible
// but falls back to the cached shell when offline.
//
// The deterministic JS triage engine ships inside the bundled JS, so once the
// app shell is cached the entire ENTRY -> REVIEW -> HANDOFF workflow runs
// offline on an iPad / iPhone installed from the home screen.

const VERSION = 'st-hospital-lite-v1';
const SHELL_CACHE = `${VERSION}-shell`;
const RUNTIME_CACHE = `${VERSION}-runtime`;

const SHELL_URLS = [
    '/',
    '/index.html',
    '/manifest.webmanifest',
    '/app-icon.svg',
    '/icons/pwa/icon-192.png',
    '/icons/pwa/icon-512.png',
    '/icons/pwa/apple-touch-icon-180.png',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        (async () => {
            const cache = await caches.open(SHELL_CACHE);
            // Tolerate individual misses — don't fail install if one icon 404s.
            await Promise.all(
                SHELL_URLS.map((url) =>
                    cache.add(new Request(url, { cache: 'reload' })).catch(() => null),
                ),
            );
            self.skipWaiting();
        })(),
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        (async () => {
            const keys = await caches.keys();
            await Promise.all(
                keys
                    .filter((k) => !k.startsWith(VERSION))
                    .map((k) => caches.delete(k)),
            );
            await self.clients.claim();
        })(),
    );
});

self.addEventListener('fetch', (event) => {
    const req = event.request;
    if (req.method !== 'GET') return;

    const url = new URL(req.url);
    if (url.origin !== self.location.origin) return;

    // Navigations: network-first, falling back to cached shell.
    if (req.mode === 'navigate') {
        event.respondWith(
            (async () => {
                try {
                    const fresh = await fetch(req);
                    const cache = await caches.open(RUNTIME_CACHE);
                    cache.put(req, fresh.clone()).catch(() => {});
                    return fresh;
                } catch {
                    const cache = await caches.open(SHELL_CACHE);
                    const cachedRoot = (await cache.match('/')) || (await cache.match('/index.html'));
                    if (cachedRoot) return cachedRoot;
                    return new Response(
                        '<!doctype html><meta charset="utf-8"><title>SAFE-Triage offline</title>' +
                            '<style>body{font-family:system-ui;padding:2rem;color:#0f172a;background:#f1f5f9}</style>' +
                            '<h1>SAFE-Triage offline</h1><p>The app shell isn\'t cached yet. Reconnect once to install.</p>',
                        { headers: { 'Content-Type': 'text/html; charset=utf-8' }, status: 503 },
                    );
                }
            })(),
        );
        return;
    }

    // Hashed Vite assets: cache-first (immutable once cached).
    if (url.pathname.startsWith('/assets/')) {
        event.respondWith(
            (async () => {
                const cache = await caches.open(RUNTIME_CACHE);
                const hit = await cache.match(req);
                if (hit) return hit;
                try {
                    const fresh = await fetch(req);
                    if (fresh.ok) cache.put(req, fresh.clone()).catch(() => {});
                    return fresh;
                } catch {
                    return hit || Response.error();
                }
            })(),
        );
        return;
    }

    // Icons / static images / SW itself: cache-first with network update.
    if (
        url.pathname.startsWith('/icons/') ||
        url.pathname.startsWith('/images/') ||
        url.pathname === '/app-icon.svg' ||
        url.pathname === '/manifest.webmanifest'
    ) {
        event.respondWith(
            (async () => {
                const cache = await caches.open(SHELL_CACHE);
                const hit = await cache.match(req);
                const fetchAndUpdate = fetch(req)
                    .then((res) => {
                        if (res.ok) cache.put(req, res.clone()).catch(() => {});
                        return res;
                    })
                    .catch(() => hit);
                return hit || fetchAndUpdate;
            })(),
        );
    }
});
