/**
 * Plausible Analytics — in-app event tracking for the Klikk Admin SPA
 *
 * Activation model (v2 — GTM-013)
 * --------------------------------
 * Previous versions relied on the marketing site injecting window.plausible
 * before the user reached the app. Users who navigate directly to
 * app.klikk.co.za (the majority of campaign signups) never received the
 * script and all conversion events were silently dropped.
 *
 * The SPA now loads plausible.js itself when VITE_PLAUSIBLE_DOMAIN is set.
 * Plausible self-hosted is cookieless and does not process personal information,
 * so no additional POPIA consent gate is required (see: DEC-001, 2026-04-22).
 *
 * POPIA compliance: no PI is passed in any event property. Props are limited
 * to anonymous plan names, boolean flags, and string labels from a fixed enum.
 *
 * Usage:
 *   import { trackEvent, setupPlausibleRouterHook } from '@/plugins/plausible'
 *   trackEvent('signup_completed', { plan: 'free' })
 *
 * Full event catalogue (mirrors the Plausible goal definitions):
 *   - signup_started          : sign-up page, form first-touched
 *   - signup_completed        : account created successfully
 *   - first_property_created  : first property saved by user
 *   - first_mandate_signed    : first mandate e-signed
 *   - first_lease_signed      : first lease e-signed (key value moment)
 *   - subscription_started    : successful upgrade to a paid plan
 *
 * See docs/marketing/attribution-dashboard.md for the full funnel definition.
 */

declare global {
  interface Window {
    plausible?: (eventName: string, options?: PlausibleOptions) => void & {
      q?: Array<[string, PlausibleOptions | undefined]>
    }
  }
}

interface PlausibleOptions {
  props?: Record<string, string | boolean | number>
  callback?: () => void
}

/** Named conversion events — add to this union as new goals are defined */
export type KlikkEvent =
  | 'signup_started'
  | 'signup_completed'
  | 'first_property_created'
  | 'first_mandate_signed'
  | 'first_lease_signed'
  | 'subscription_started'

/**
 * Emit a named event to Plausible.
 * Silently no-ops if window.plausible is not available.
 */
export function trackEvent(
  name: KlikkEvent,
  props?: PlausibleOptions['props'],
): void {
  if (typeof window.plausible !== 'function') return
  window.plausible(name, props ? { props } : undefined)
}

/**
 * Called once from main.ts after the Vue app is created.
 *
 * When VITE_PLAUSIBLE_DOMAIN is set (should be 'app.klikk.co.za' in
 * production):
 *   1. Install a stub queue so events fired before the script loads are buffered.
 *   2. Inject the plausible.js script tag pointing at self-hosted
 *      analytics.klikk.co.za. The script drains the queue automatically
 *      because plausible.js checks for window.plausible.q on startup.
 *
 * When VITE_PLAUSIBLE_DOMAIN is not set (dev / staging without analytics):
 *   — no-op. All trackEvent() calls are silently dropped.
 */
export function initPlausible(): void {
  if (typeof window === 'undefined') return

  const domain = import.meta.env.VITE_PLAUSIBLE_DOMAIN as string | undefined
  if (!domain) return

  // Install the stub queue. plausible.js will replace window.plausible with
  // the real function and replay anything buffered in .q on load.
  if (!window.plausible) {
    const queue: Array<[string, PlausibleOptions | undefined]> = []
    const stub = function (name: string, options?: PlausibleOptions) {
      queue.push([name, options])
    } as typeof window.plausible & { q: typeof queue }
    stub!.q = queue
    window.plausible = stub
  }

  // Inject the script tag. Uses the self-hosted Plausible instance at
  // analytics.klikk.co.za. The 'outbound-links' and 'custom-events'
  // extensions are bundled in the standard plausible.js build.
  const script = document.createElement('script')
  script.defer = true
  script.setAttribute('data-domain', domain)
  script.src = 'https://analytics.klikk.co.za/js/script.js'
  document.head.appendChild(script)
}

/**
 * Wire up a Vue Router afterEach hook so Plausible receives a pageview on
 * every SPA route change (required for SPAs — the script's built-in
 * history-based tracking does not fire on pushState without this call).
 *
 * Call once from main.ts, after router is created:
 *
 *   import type { Router } from 'vue-router'
 *   import { setupPlausibleRouterHook } from '@/plugins/plausible'
 *   setupPlausibleRouterHook(router)
 */
export function setupPlausibleRouterHook(router: { afterEach: (fn: () => void) => void }): void {
  const domain = import.meta.env.VITE_PLAUSIBLE_DOMAIN as string | undefined
  if (!domain) return

  router.afterEach(() => {
    if (typeof window.plausible === 'function') {
      window.plausible('pageview')
    }
  })
}
