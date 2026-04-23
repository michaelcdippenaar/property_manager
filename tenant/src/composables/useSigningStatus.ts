/**
 * useSigningStatus
 *
 * Composable that handles detecting signing completion after the tenant opens
 * the external signing tab.
 *
 * Two detection mechanisms run in parallel:
 *   1. Web: `window.postMessage` from the signing page (same-session opener signal).
 *   2. Web: polling the /esigning/submissions/ endpoint every POLL_INTERVAL ms
 *      (max POLL_MAX_ATTEMPTS × POLL_INTERVAL duration) while the tab is open.
 *   3. Native (Capacitor): `browserFinished` event from @capacitor/browser.
 *
 * Usage:
 *   const { startSigningWatch, stopSigningWatch, signedAt } = useSigningStatus()
 *   startSigningWatch(leaseId, signerEmail)
 *   // ... user opens tab ...
 *   watch(signedAt, (v) => { if (v) handleSigned() })
 */

import { ref } from 'vue'
import { Capacitor } from '@capacitor/core'
import api from '../api'

const POLL_INTERVAL = 5_000   // 5 seconds
const POLL_MAX_ATTEMPTS = 24  // 2 minutes max

export function useSigningStatus() {
  const signedAt = ref<string | null>(null)  // ISO timestamp set when signing detected
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let pollAttempts = 0
  let _leaseId: number | null = null
  let _signerEmail: string | null = null

  // Message listener for web postMessage signal
  function onMessage(event: MessageEvent) {
    if (event.data?.type === 'klikk_lease_signed') {
      _markSigned()
    }
  }

  function _markSigned() {
    if (signedAt.value) return  // already handled
    signedAt.value = new Date().toISOString()
    stopSigningWatch()
  }

  async function _checkSubmissionStatus() {
    if (!_leaseId || !_signerEmail) return
    try {
      const subsRes = await api.get('/esigning/submissions/', { params: { lease: _leaseId } })
      const subs = subsRes.data.results ?? subsRes.data
      const tenantHasSigned = subs.some((s: any) =>
        s.signers?.some(
          (sg: any) => sg.email === _signerEmail && sg.status !== 'pending'
        )
      )
      if (tenantHasSigned) {
        _markSigned()
      }
    } catch { /* non-fatal — continue polling */ }
  }

  async function startSigningWatch(leaseId: number, signerEmail: string) {
    _leaseId = leaseId
    _signerEmail = signerEmail
    signedAt.value = null
    pollAttempts = 0

    if (Capacitor.isNativePlatform()) {
      // On native, rely on browserFinished event
      try {
        const { Browser } = await import('@capacitor/browser')
        Browser.addListener('browserFinished', async () => {
          // Tab closed — check status once (user may have signed before closing)
          await _checkSubmissionStatus()
        })
      } catch { /* Browser plugin not available */ }
    } else {
      // On web, listen for postMessage from the signing tab
      window.addEventListener('message', onMessage)

      // Also start a polling loop
      pollTimer = setInterval(async () => {
        pollAttempts++
        await _checkSubmissionStatus()
        if (pollAttempts >= POLL_MAX_ATTEMPTS) {
          stopSigningWatch()
        }
      }, POLL_INTERVAL)
    }
  }

  function stopSigningWatch() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    window.removeEventListener('message', onMessage)
    // Remove Capacitor listener on native
    if (Capacitor.isNativePlatform()) {
      import('@capacitor/browser').then(({ Browser }) => {
        Browser.removeAllListeners().catch(() => {})
      }).catch(() => {})
    }
  }

  return { signedAt, startSigningWatch, stopSigningWatch }
}
