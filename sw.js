// Doctor Plus PWA — Service Worker
const CACHE_VERSION = 'doctorplus-v2.1.0';

const CORE_ASSETS = [
  './index.html',
  './auth-system-3-1-1.html',
  './dashboard.html',
  './specialties.js',
  './manifest.json',
  './icon-192x192.png',
  './icon-512x512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_VERSION)
      .then(cache => Promise.all(
        CORE_ASSETS.map(url => cache.add(url).catch(err => console.warn('[SW] skip', url, err)))
      ))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(names => Promise.all(names.filter(n => n !== CACHE_VERSION).map(n => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (
    event.request.method !== 'GET' ||
    url.protocol.startsWith('chrome-extension') ||
    url.hostname.includes('supabase.co') ||
    url.hostname.includes('emailjs.com')
  ) { return; }

  event.respondWith(
    fetch(event.request)
      .then(response => {
        if (response.ok && url.origin === self.location.origin) {
          const clone = response.clone();
          caches.open(CACHE_VERSION).then(cache => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => caches.match(event.request)
        .then(cached => cached || caches.match('./auth-system-3-1-1.html')))
  );
});
