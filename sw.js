// 한 번 본 파일은 오프라인에서도 쓸 수 있게 캐시한다 (네트워크 우선, 실패 시 캐시)
const CACHE = "word-cards-v2";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  e.respondWith(
    // no-cache: 브라우저 캐시 대신 서버에 확인해 새 버전을 바로 받는다 (바뀌지 않았으면 304라 가볍다)
    fetch(e.request, { cache: "no-cache" })
      .then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
        }
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});
