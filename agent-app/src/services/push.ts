/**
 * Push notification service for the Klikk agent app (Quasar/Capacitor).
 *
 * Handles FCM (Android) + APNs (iOS) token registration using the
 * @capacitor/push-notifications plugin.
 *
 * Call ``initialisePush()`` once after a successful login.
 * Call ``revokePushToken()`` before clearing auth state on logout.
 *
 * Deep-link routing:
 *   Incoming notifications carry a ``data.screen`` key.  The ``addListeners``
 *   call translates that key to a Vue Router path and navigates on tap.
 *
 * POPIA:
 *   Token registration only happens after the user is authenticated.
 *   Tokens are revoked on logout (``revokePushToken``).
 */

import { Platform } from 'quasar'
import type { Router } from 'vue-router'

// Screen → route mapping for agent deep-links.
// Routes must correspond to defined paths in agent-app/src/router/index.ts.
// Where no dedicated detail page exists, we fall back to the closest list view.
const SCREEN_ROUTES: Record<string, (data: Record<string, string>) => string> = {
  // No lease detail page — navigate to the leases list
  lease_detail:       (_d) => '/leases',
  // No dedicated mandates page — pipeline is where mandate cards live
  mandate_detail:     (_d) => '/pipeline',
  // No maintenance detail page — navigate to the maintenance list
  maintenance_detail: (_d) => '/maintenance',
  // No payments/invoices page — fall back to today's task summary
  invoice_detail:     (_d) => '/today',
}

/**
 * Register for push notifications.  Call this on login (after tokens are set).
 *
 * @param registerToken   Async fn that POSTs token + platform to backend
 * @param router          Vue Router instance (for deep-link navigation)
 */
export async function initialisePush(
  registerToken: (token: string, platform: 'ios' | 'android') => Promise<void>,
  router: Router,
): Promise<void> {
  if (!Platform.is.capacitor) {
    // Browser / dev environment — Web Push handled separately in tenant app
    return
  }

  try {
    const { PushNotifications } = await import('@capacitor/push-notifications')

    // 1. Request permission (must come from user gesture in onboarding; here it
    //    is triggered immediately after login which counts as a user gesture).
    const permResult = await PushNotifications.requestPermissions()
    if (permResult.receive !== 'granted') {
      console.warn('[Push] Permission not granted:', permResult.receive)
      return
    }

    // 2. Register with FCM / APNs
    await PushNotifications.register()

    // 3. Capture the device token and send to backend
    await PushNotifications.addListener('registration', async (tokenData) => {
      const platform: 'ios' | 'android' = Platform.is.ios ? 'ios' : 'android'
      try {
        await registerToken(tokenData.value, platform)
        console.info('[Push] Token registered, platform:', platform)
      } catch (err) {
        console.error('[Push] Token registration failed:', err)
      }
    })

    // 4. Handle registration errors
    await PushNotifications.addListener('registrationError', (err) => {
      console.error('[Push] Registration error:', err)
    })

    // 5. Foreground notification received — show in-app (no native banner)
    await PushNotifications.addListener('pushNotificationReceived', (notification) => {
      console.info('[Push] Foreground notification:', notification.title)
      // The admin app currently shows a WebSocket toast; push foreground
      // messages are informational only. Future: integrate with Quasar Notify.
    })

    // 6. Notification tapped — deep-link to relevant screen
    await PushNotifications.addListener(
      'pushNotificationActionPerformed',
      (action) => {
        const data = (action.notification.data ?? {}) as Record<string, string>
        const screen = data.screen
        if (!screen) return
        const routeFn = SCREEN_ROUTES[screen]
        if (routeFn) {
          router.push(routeFn(data)).catch(() => {
            // Navigation guard may redirect — ignore
          })
        }
      },
    )
  } catch (err) {
    console.error('[Push] initialisePush failed:', err)
  }
}

/**
 * Remove all listeners and delete the push token from the backend.
 * Call before clearing auth state on logout.
 *
 * @param currentToken    The token string currently stored (from registration)
 * @param revokeToken     Async fn that sends DELETE /auth/push-token/ { token }
 */
export async function revokePushToken(
  currentToken: string | null,
  revokeToken: (token: string) => Promise<void>,
): Promise<void> {
  if (!Platform.is.capacitor) return

  try {
    const { PushNotifications } = await import('@capacitor/push-notifications')
    await PushNotifications.removeAllListeners()
  } catch {
    // Plugin may not be registered — silently ignore
  }

  if (currentToken) {
    try {
      await revokeToken(currentToken)
    } catch (err) {
      console.warn('[Push] Token revocation failed (continuing logout):', err)
    }
  }
}
