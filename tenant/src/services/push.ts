/**
 * Klikk Tenant — Web Push subscription service.
 *
 * POPIA compliance:
 *   - The permission prompt is NEVER triggered on page load.
 *   - Call ``requestAndSubscribe`` only from a user-gesture handler
 *     (e.g. the POPIA opt-in banner "Enable notifications" button).
 *   - Subscription is revoked on logout via ``unsubscribePush``.
 *
 * Backend integration:
 *   The VAPID public key is read from the env var VITE_VAPID_PUBLIC_KEY.
 *   Subscriptions are stored on the backend at POST /auth/push-token/
 *   using platform = "web" with the serialised PushSubscription as the token.
 *
 * Usage:
 *   1. On login, call ``registerServiceWorker()`` — no permission prompt.
 *   2. From the POPIA opt-in banner, call ``requestAndSubscribe(postToken)``.
 *   3. On logout, call ``unsubscribePush(deleteToken)``.
 */

const SW_PATH = '/sw.js'

/** Return the VAPID public key from Vite env, or null if not configured. */
function getVapidKey(): ArrayBuffer | null {
  const raw = import.meta.env.VITE_VAPID_PUBLIC_KEY as string | undefined
  if (!raw) return null
  try {
    const base64 = raw.replace(/-/g, '+').replace(/_/g, '/')
    const binary = atob(base64)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
    return bytes.buffer
  } catch {
    console.warn('[Push] Invalid VAPID public key')
    return null
  }
}

/**
 * Register the service worker without requesting push permission.
 * Safe to call on every page load.
 */
export async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (!('serviceWorker' in navigator)) return null
  try {
    const reg = await navigator.serviceWorker.register(SW_PATH, { scope: '/' })
    return reg
  } catch (err) {
    console.error('[Push] Service worker registration failed:', err)
    return null
  }
}

/**
 * Request push permission and subscribe.
 * MUST be called from a user gesture (button click) — never on page load.
 *
 * @param postToken   Async fn that POSTs { token, platform: 'web' } to backend
 * @returns           'granted' | 'denied' | 'error'
 */
export async function requestAndSubscribe(
  postToken: (token: string, platform: 'web') => Promise<void>,
): Promise<'granted' | 'denied' | 'error'> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    console.warn('[Push] Web Push not supported in this browser.')
    return 'error'
  }

  const permission = await Notification.requestPermission()
  if (permission !== 'granted') {
    return 'denied'
  }

  const vapidKey = getVapidKey()
  if (!vapidKey) {
    console.warn('[Push] VITE_VAPID_PUBLIC_KEY not configured — subscription skipped.')
    return 'error'
  }

  try {
    let reg = await navigator.serviceWorker.getRegistration(SW_PATH)
    if (!reg) {
      reg = (await registerServiceWorker()) ?? undefined
    }
    if (!reg) return 'error'

    const existing = await reg.pushManager.getSubscription()
    const sub = existing ?? (await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: vapidKey,
    }))

    await postToken(JSON.stringify(sub.toJSON()), 'web')
    console.info('[Push] Web Push subscription registered')
    return 'granted'
  } catch (err) {
    console.error('[Push] Subscription failed:', err)
    return 'error'
  }
}

/**
 * Unsubscribe from Web Push and revoke the token from the backend.
 * Call on logout.
 *
 * @param deleteToken   Async fn that sends DELETE /auth/push-token/ { token }
 */
export async function unsubscribePush(
  deleteToken: (token: string) => Promise<void>,
): Promise<void> {
  if (!('serviceWorker' in navigator)) return
  try {
    const reg = await navigator.serviceWorker.getRegistration(SW_PATH)
    if (!reg) return
    const sub = await reg.pushManager.getSubscription()
    if (!sub) return
    const tokenStr = JSON.stringify(sub.toJSON())
    await sub.unsubscribe()
    await deleteToken(tokenStr)
    console.info('[Push] Web Push subscription revoked')
  } catch (err) {
    console.warn('[Push] Unsubscribe failed (continuing logout):', err)
  }
}
