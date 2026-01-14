/**
 * Service Worker for U.S. Department of the Treasury
 * Provides offline caching and performance improvements
 */

const CACHE_VERSION = 'treasury-v1';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const PAGES_CACHE = `${CACHE_VERSION}-pages`;
const IMAGES_CACHE = `${CACHE_VERSION}-images`;

// Static assets to cache immediately
const STATIC_ASSETS = [
  '/',
  '/news/press-releases/',
  '/css/treasury.css',
  '/js/treasury.js',
  '/images/treasury-seal.svg',
  '/images/treasury-seal.webp',
  '/images/treasury-seal-green.webp',
  '/images/favicon.png'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name.startsWith('treasury-') && !name.startsWith(CACHE_VERSION))
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Only handle same-origin requests
  if (url.origin !== location.origin) {
    return;
  }
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Strategy based on resource type
  if (isStaticAsset(url.pathname)) {
    // Cache-first for static assets
    event.respondWith(cacheFirst(request, STATIC_CACHE));
  } else if (isImage(url.pathname)) {
    // Cache-first for images
    event.respondWith(cacheFirst(request, IMAGES_CACHE));
  } else if (isHTMLPage(request)) {
    // Network-first for HTML pages (stale-while-revalidate)
    event.respondWith(networkFirst(request, PAGES_CACHE));
  }
});

// Cache-first strategy
async function cacheFirst(request, cacheName) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }
  
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('[SW] Fetch failed:', error);
    return new Response('Offline', { status: 503 });
  }
}

// Network-first strategy with cache fallback
async function networkFirst(request, cacheName) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache');
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    // Return offline page
    return caches.match('/');
  }
}

// Helper functions
function isStaticAsset(pathname) {
  return /\.(css|js|woff2?|ttf|eot)$/i.test(pathname);
}

function isImage(pathname) {
  return /\.(png|jpg|jpeg|gif|svg|webp|ico)$/i.test(pathname);
}

function isHTMLPage(request) {
  return request.headers.get('accept')?.includes('text/html');
}
