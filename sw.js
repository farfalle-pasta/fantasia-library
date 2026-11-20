// Fantasia Library(トップページ)の service worker
// ・トップページ関係は「通信優先、ダメならキャッシュ」→ 更新がすぐ届き、オフラインでも開ける
// ・ゲーム本体(games/<名前>/index.html など)は、各ゲーム自身の sw.js が担当するのでここでは触らない
const CACHE = 'museum-v1';
const SHELL = ['./', './index.html', './style.css', './app.js', './games.json',
               './manifest.webmanifest', './icons/icon-192.png', './icons/favicon.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith('museum-') && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  // ゲームのフォルダの中は触らない(展示用の画像 thumb.* だけ例外)
  const GAMES = new URL('games/', self.registration.scope).pathname;
  if (url.pathname.startsWith(GAMES) && !/\/thumb\.[a-z]+$/i.test(url.pathname)) return;

  e.respondWith(
    fetch(req)
      .then((res) => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() => caches.match(req, { ignoreSearch: true }).then((hit) => hit || caches.match('./index.html')))
  );
});
