const CACHE_VERSION = 'vetsync-pwa-v9';
const APP_SHELL_CACHE = `${CACHE_VERSION}-shell`;
const RUNTIME_CACHE = `${CACHE_VERSION}-runtime`;
const DB_NAME = 'VetCareOfflineDB';
const DB_VERSION = 1;
const STORE_NAME = 'offline_bookings';

const APP_SHELL = [
  '/',
  '/offline',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/js/push-notifications.js',
  '/static/manifest.json',
  '/static/images/pwa-icon-192.png',
  '/static/images/pwa-icon-512.png',
  '/static/images/vet-dog.png',
  '/static/images/kitten.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(APP_SHELL_CACHE).then(async (cache) => {
      await Promise.allSettled(APP_SHELL.map((asset) => cache.add(asset)));
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => ![APP_SHELL_CACHE, RUNTIME_CACHE].includes(key))
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== 'GET') {
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(networkFirstPage(request));
    return;
  }

  if (url.origin === self.location.origin && isStaticAsset(url.pathname)) {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }

  if (url.origin === self.location.origin && url.pathname.startsWith('/api/')) {
    event.respondWith(networkOnly(request));
  }
});

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-offline-bookings') {
    event.waitUntil(syncOfflineBookings());
  }
});

self.addEventListener('push', (event) => {
  let data = {
    title: 'VetSync Update',
    body: 'You have a new update from VetSync.',
    icon: '/static/images/pwa-icon-192.png',
    data: { url: '/dashboard' },
  };

  try {
    if (event.data) {
      data = { ...data, ...event.data.json() };
    }
  } catch (error) {
    console.error('Push data parse error:', error);
  }

  const options = {
    body: data.body,
    icon: data.icon || '/static/images/pwa-icon-192.png',
    badge: '/static/images/pwa-icon-192.png',
    data: data.data || { url: '/dashboard' },
    vibrate: [100, 50, 100],
    actions: [{ action: 'view', title: 'View Update' }],
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
      .then(() => {
        // Broadcast to all open tabs so they can show an in-app popup
        return self.clients.matchAll({ type: 'window', includeUncontrolled: true })
          .then(windowClients => {
            windowClients.forEach(client => {
              client.postMessage({
                type: 'PUSH_NOTIFICATION',
                title: data.title,
                body: data.body,
                url: data.data.url
              });
            });
          });
      })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const requestedUrl = event.notification.data && event.notification.data.url
    ? event.notification.data.url
    : '/dashboard';
  const urlToOpen = new URL(requestedUrl, self.location.origin).href;

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url === urlToOpen && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
      return undefined;
    })
  );
});

async function networkFirstPage(request) {
  try {
    const response = await fetch(request);
    const cache = await caches.open(RUNTIME_CACHE);
    cache.put(request, response.clone());
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    return cached || caches.match('/offline');
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(RUNTIME_CACHE);
  const cached = await cache.match(request);
  const network = fetch(request)
    .then((response) => {
      if (response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => cached);

  return cached || network;
}

async function networkOnly(request) {
  try {
    return await fetch(request);
  } catch (error) {
    return new Response(JSON.stringify({ error: 'offline' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

function isStaticAsset(pathname) {
  return pathname.startsWith('/static/') || pathname === '/manifest.json';
}

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
      }
    };

    request.onsuccess = (event) => resolve(event.target.result);
    request.onerror = (event) => reject(event.target.error);
  });
}

async function getOfflineBookings() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, 'readonly');
    const store = transaction.objectStore(STORE_NAME);
    const request = store.getAll();
    request.onsuccess = () => resolve(request.result || []);
    request.onerror = () => reject(request.error);
  });
}

async function deleteOfflineBooking(id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, 'readwrite');
    const request = transaction.objectStore(STORE_NAME).delete(id);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

async function syncOfflineBookings() {
  const bookings = await getOfflineBookings();

  for (const booking of bookings) {
    const formData = new FormData();
    Object.entries(booking).forEach(([key, value]) => {
      if (key !== 'id') {
        formData.append(key, value);
      }
    });

    try {
      const response = await fetch('/book', {
        method: 'POST',
        body: formData,
        credentials: 'include',
      });

      if (response.ok || response.redirected || response.status === 400) {
        await deleteOfflineBooking(booking.id);
      }
    } catch (error) {
      return;
    }
  }
}
