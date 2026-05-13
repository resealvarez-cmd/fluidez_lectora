const CACHE_NAME = 'fluidezia-v1';
const ASSETS = [
  './',
  './index.html',
  './src/styles.css',
  './src/api.js',
  './src/docente.js',
  './manifest.json'
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
  // Solo manejar peticiones GET a recursos propios
  if (event.request.method !== 'GET') return;
  
  event.respondWith(
    caches.open(CACHE_NAME).then(cache => {
      return cache.match(event.request).then(response => {
        const fetchPromise = fetch(event.request).then(networkResponse => {
          // Actualizar cache en segundo plano si la respuesta es válida
          if (networkResponse.ok) {
            cache.put(event.request, networkResponse.clone());
          }
          return networkResponse;
        });
        // Retornar respuesta de cache si existe, o esperar a la red
        return response || fetchPromise;
      });
    })
  );
});
