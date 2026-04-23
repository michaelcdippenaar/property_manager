/**
 * useClarity — Microsoft Clarity session-recording integration.
 *
 * Rules:
 *   1. The Clarity snippet is NEVER injected unless VITE_ENABLE_CLARITY === 'true'
 *      (env var is false/absent in dev and CI).
 *   2. Even when the env var is set, the snippet is only injected AFTER the user
 *      has explicitly accepted the POPIA consent banner.
 *   3. initClarity() is idempotent — calling it twice does nothing.
 *
 * Sensitive-field masking is handled at the component level via the
 * <MaskedInput> wrapper (admin/src/components/shared/MaskedInput.vue).
 * The canonical list of PII field names lives in piiFields.ts.
 * This composable does not touch the DOM beyond injecting the Clarity <script> tag.
 */

const CLARITY_ENABLED = import.meta.env.VITE_ENABLE_CLARITY === 'true'
const CLARITY_PROJECT_ID = import.meta.env.VITE_CLARITY_PROJECT_ID || ''

const CONSENT_KEY = 'klikk_clarity_consent' // 'accepted' | 'declined'

let _initialized = false

/** Returns whether the user has previously accepted Clarity recording. */
export function hasClarityConsent(): boolean {
  try {
    return localStorage.getItem(CONSENT_KEY) === 'accepted'
  } catch {
    return false
  }
}

/** Returns whether the user has previously declined (banner should not re-appear). */
export function hasClarityDecision(): boolean {
  try {
    const val = localStorage.getItem(CONSENT_KEY)
    return val === 'accepted' || val === 'declined'
  } catch {
    return false
  }
}

/** Persist the user's choice and, if accepted, inject the snippet. */
export function setClarityConsent(accepted: boolean): void {
  try {
    localStorage.setItem(CONSENT_KEY, accepted ? 'accepted' : 'declined')
  } catch {
    // localStorage unavailable — degrade gracefully
  }
  if (accepted) {
    initClarity()
  }
}

/**
 * Inject the Clarity snippet into <head>.  Safe to call multiple times — only
 * runs once.  Will silently no-op if:
 *   - VITE_ENABLE_CLARITY is not 'true', OR
 *   - no project ID is configured, OR
 *   - snippet was already injected.
 */
export function initClarity(): void {
  if (!CLARITY_ENABLED) return
  if (!CLARITY_PROJECT_ID) {
    console.warn('[useClarity] VITE_CLARITY_PROJECT_ID is not set — Clarity not loaded.')
    return
  }
  if (_initialized) return
  _initialized = true

  // Microsoft Clarity snippet (verbatim from Clarity setup guide, minified)
  // eslint-disable-next-line
  ;(function (c: any, l: any, a: any, r: any, i: any, t?: any, y?: any) {
    c[a] =
      c[a] ||
      function () {
        ;(c[a].q = c[a].q || []).push(arguments)
      }
    t = l.createElement(r)
    t.async = 1
    t.src = 'https://www.clarity.ms/tag/' + i
    y = l.getElementsByTagName(r)[0]
    y.parentNode.insertBefore(t, y)
  })(window, document, 'clarity', 'script', CLARITY_PROJECT_ID)
}

export function useClarity() {
  return {
    isEnabled: CLARITY_ENABLED,
    hasClarityConsent,
    hasClarityDecision,
    setClarityConsent,
    initClarity,
  }
}
