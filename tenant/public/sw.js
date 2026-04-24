/**
 * Klikk Tenant — Web Push Service Worker
 *
 * Handles background push events and shows native OS notifications.
 * Deep-link data keys (set by backend dispatch):
 *   screen        — logical tenant screen name
 *   <entity>_id   — primary key string for the target object
 *
 * Tenant screen → URL mapping:
 *   tenant_lease_detail       → /home/lease
 *   tenant_maintenance_detail → /issues/<maintenance_id>  (issues = maintenance)
 *   tenant_invoice_detail     → /home/dashboard  (no payments route yet)
 */

/* global self, clients */

self.addEventListener('push', (event) => {
  if (!event.data) return

  let payload
  try {
    payload = event.data.json()
  } catch {
    payload = { title: 'Klikk', body: event.data.text(), data: {} }
  }

  const title = payload.title || 'Klikk'
  const options = {
    body: payload.body || '',
    icon: '/favicon.svg',
    badge: '/favicon.svg',
    data: payload.data || {},
    vibrate: [100, 50, 100],
    tag: payload.data?.screen || 'klikk',
    renotify: true,
  }

  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()

  const data = event.notification.data || {}
  const screen = data.screen || ''

  // Paths must match tenant/src/router/index.ts exactly.
  // tenant_lease_detail  → /home/lease  (nested under AppShell at /home)
  // tenant_maintenance_detail → /issues/:id  (issues = maintenance in tenant)
  // tenant_invoice_detail → /home/dashboard  (no payments route yet)
  const urlMap = {
    tenant_lease_detail: '/home/lease',
    tenant_maintenance_detail: data.maintenance_id ? `/issues/${data.maintenance_id}` : '/home/dashboard',
    tenant_invoice_detail: '/home/dashboard',
  }

  const targetUrl = urlMap[screen] || '/'

  event.waitUntil(
    clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then((windowClients) => {
        // Focus existing window if possible
        for (const client of windowClients) {
          if ('focus' in client) {
            client.navigate(targetUrl)
            return client.focus()
          }
        }
        // Otherwise open a new window
        if (clients.openWindow) {
          return clients.openWindow(targetUrl)
        }
      }),
  )
})

self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (event) => event.waitUntil(clients.claim()))
