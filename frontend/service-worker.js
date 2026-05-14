const CACHE_NAME = 'fluidezia-v1';
const ASSETS = [
  './',
  './index.html',
  './login.html',
  './estudiante.html',
  './src/styles.css',
  './src/api.js',
  './src/docente.js',
  './src/estudiante.js',
  './manifest.json',
  './assets/logo_profeic.png'
];

// Instalación: Cachear activos estáticos
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

// Activación: Limpiar caches antiguos
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
      );
    })
  );
});

// Estrategia: Stale-while-revalidate
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  
  event.respondWith(
    caches.open(CACHE_NAME).then(cache => {
      return cache.match(event.request).then(response => {
        const fetchPromise = fetch(event.request).then(networkResponse => {
          if (networkResponse.ok) {
            cache.put(event.request, networkResponse.clone());
          }
          return networkResponse;
        }).catch(() => {
          // Si falla la red, ya retornamos la cache abajo
        });
        return response || fetchPromise;
      });
    })
  );
});
