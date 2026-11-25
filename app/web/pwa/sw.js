// Lane A · A5 — service worker for the installable app (served at /sw.js so its scope is the whole site).
// Only GET navigations get an offline fallback. The share-target POST is left to the browser so the
// shared file goes straight to the server.
const SHELL = 'cbs-shell-v1'
const OFFLINE = '/offline'

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SHELL).then((c) => c.addAll([OFFLINE, '/static/icons/icon-192.png'])))
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) if (key !== SHELL) await caches.delete(key)
    await self.clients.claim()
  })())
})

self.addEventListener('fetch', (event) => {
  const req = event.request
  if (req.method !== 'GET') return
  if (req.mode === 'navigate') event.respondWith(fetch(req).catch(() => caches.match(OFFLINE)))
})
