/**
 * Sentry + Capacitor error monitoring boot file.
 *
 * Replaces the previous custom remote-log shipper with the official
 * @sentry/capacitor SDK so errors land in Sentry with full stack traces,
 * breadcrumbs, and device context (iOS/Android).
 *
 * Activation: set SENTRY_DSN in the build env (quasar.config.js exposes it
 * as process.env.SENTRY_DSN).  Leave blank to skip initialisation in dev.
 *
 * PII policy (POPIA): sendDefaultPii is false; beforeSend scrubs known PII keys.
 */

import { boot } from 'quasar/wrappers'
import * as Sentry from '@sentry/capacitor'
import * as SentryVue from '@sentry/vue'

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

export default boot(({ app }) => {
  const dsn = process.env.SENTRY_DSN as string | undefined
  if (!dsn) return

  Sentry.init(
    {
      app,
      dsn,
      environment: process.env.SENTRY_ENVIRONMENT ?? 'development',
      release: process.env.SENTRY_RELEASE,
      integrations: [
        SentryVue.browserTracingIntegration(),
      ],
      tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? 0.05),
      sendDefaultPii: false,
      beforeSend(event) {
        if (event.extra && typeof event.extra === 'object') {
          event.extra = scrubObj(event.extra as Record<string, unknown>)
        }
        return event
      },
    },
    SentryVue.init,
  )
})
