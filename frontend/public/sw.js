// Offline shell: cache the app files; API calls always go to the network
// (the app keeps its own cache of verdicts for products already scanned).
// Works under any base path (/app/ with Docker, / on Vercel).
const CACHE = "dawacheck-v2";
const SCOPE = new URL(self.registration.scope).pathname; // e.g. "/app/" or "/"
const isApi = (p) => p.startsWith("/api/") || /^\/(scan|bill|mix-check|claims|dose|spray-log|passport|rotation|sos|weather-window|report|radar|health|products|crops|offline-pack|i18n|explain|uploads|fpo|jobs|metrics|admin)\b/.test(p.slice(SCOPE.length - 1));

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll([SCOPE, `${SCOPE}icon.svg`, `${SCOPE}manifest.webmanifest`])));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== self.location.origin || !url.pathname.startsWith(SCOPE) || isApi(url.pathname)) return;
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return res;
      })
      .catch(() => caches.match(e.request).then((r) => r || caches.match(SCOPE)))
  );
});
