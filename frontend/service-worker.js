const CACHE_NAME = 'fluidezia-v2';
const ASSETS = [
  './',
  'index.html',
  'login.html',
  'estudiante.html',
  'src/styles.css',
  'src/api.js',
  'src/docente.js',
  'src/estudiante.js',
  'manifest.json',
  'assets/logo_profeic.png'
];

// Instalación: Cachear activos estáticos y forzar activación inmediata
self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS))
  );
});

// Activación: Limpiar caches antiguos para no quedarse con versiones rotas
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
      ).then(() => self.clients.claim());
    })
  );
});

// Estrategia: Stale-while-revalidate ignorando parámetros de búsqueda (?v=30)
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request, { ignoreSearch: true }).then(response => {
      const fetchPromise = fetch(event.request).then(networkResponse => {
        if (networkResponse.ok) {
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, networkResponse.clone());
          });
        }
        return networkResponse;
      }).catch(() => {
        // Fallar silenciosamente si estamos sin conexión
      });
      return response || fetchPromise;
    })
  );
});