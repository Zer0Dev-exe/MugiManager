// Service worker de MugiManager: guarda la web para abrirla rápido y sin conexión.
// Las llamadas a la API nunca se guardan en caché (saldo, rutas y avisos deben ser actuales).
const CACHE = "mugimanager-v15";
const APP_SHELL = [
  "./",
  "index.html",
  "css/mugi_style.css?v=14.0",
  "js/config.js?v=14.0",
  "js/app.js?v=14.0",
  "img/logo.svg",
  "img/icon-192.png",
  "manifest.webmanifest"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== self.location.origin) return;

  // Red primero; si no hay conexión, la copia guardada
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
