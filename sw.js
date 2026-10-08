/* ClimateShield field pack - cache the whole shell so the form opens with no signal. */
var V = "cs-field-1";
var SHELL = ["./", "./index.html", "./anchors.js", "./manifest.webmanifest", "./icon.svg"];

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(V).then(function (c) {
    return c.addAll(SHELL);
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (ks) {
    return Promise.all(ks.filter(function (k) { return k !== V; })
                        .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener("fetch", function (e) {
  if (e.request.method !== "GET") return;
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then(function (hit) {
      return hit || fetch(e.request).then(function (resp) {
        if (resp.ok && new URL(e.request.url).origin === self.location.origin) {
          var cp = resp.clone();
          caches.open(V).then(function (c) { c.put(e.request, cp); });
        }
        return resp;
      }).catch(function () { return caches.match("./"); });
    })
  );
});
