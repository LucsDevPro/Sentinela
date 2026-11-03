// Service worker mínimo: guarda só a "casca" do app (a página e os ícones) pra abrir rápido.
// NUNCA guarda dados nem respostas do Worker (PIN, decisões, contestações): só pedidos GET
// do próprio site, e sempre tenta a rede primeiro.
const CASCA = "sentinela-casca-v1";
const ARQUIVOS = ["validar.html", "manifest.webmanifest", "assets/icone-192.png", "assets/icone-512.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CASCA).then(c => c.addAll(ARQUIVOS)).catch(() => {})); self.skipWaiting(); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CASCA).map(k => caches.delete(k))))); self.clients.claim(); });
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin) return;       // Worker/API: nunca interceptar
  const caminho = u.pathname.split("/").pop() || "";
  if (!ARQUIVOS.some(a => a.endsWith(caminho)) || caminho === "") return;     // dados (data/*.json) sempre da rede
  e.respondWith(fetch(e.request).then(r => { const cp = r.clone(); caches.open(CASCA).then(c => c.put(e.request, cp)); return r; })
    .catch(() => caches.match(e.request)));
});
