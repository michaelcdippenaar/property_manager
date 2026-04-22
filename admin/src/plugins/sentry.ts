/**
 * Sentry initialisation for the Klikk Admin SPA.
 *
 * Activated only when VITE_SENTRY_DSN is set in the build environment.
 * Source maps are uploaded by CI via @sentry/vite-plugin (see vite.config.ts).
 *
 * PII policy (POPIA):
 *   - send_default_pii is NOT enabled
 *   - beforeSend strips any id_number / passport / bank_account keys from extras
 */

import * as Sentry from '@sentry/vue'
import type { App } from 'vue'
import type { Router } from 'vue-router'

const PII_KEY_PATTERN = /id_number|id_no|passport|bank_account|account_number|card_number|cvv|pin/i

function scrubObj(obj: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(obj)) {
    if (PII_KEY_PATTERN.test(k)) {
      out[k] = '[Filtered]'
    } else if (v && typeof v === 'object' && !Array.isArray(v)) {
      out[k] = scrubObj(v as Record<string, unknown>)
    } else {
      out[k] = v
    }
  }
  return out
}

export function initSentry(app: App, router: Router): void {
  const dsn = import.meta.env.VITE_SENTRY_DSN as string | undefined
  if (!dsn) return

  Sentry.init({
    app,
    dsn,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT ?? 'development',
    release: import.meta.env.VITE_APP_RELEASE as string | undefined,
    integrations: [
      Sentry.browserTracingIntegration({ router }),
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE ?? 0.05),
    replaysSessionSampleRate: 0.0,   // off by default; PM can enable for debugging
    replaysOnErrorSampleRate: 0.5,
    sendDefaultPii: false,
    beforeSend(event) {
      if (event.extra && typeof event.extra === 'object') {
        event.extra = scrubObj(event.extra as Record<string, unknown>)
      }
      return event
    },
  })
}
