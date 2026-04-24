import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../boot/axios'
import type { Router } from 'vue-router'

export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  full_name: string
  phone: string
  role: 'tenant' | 'agent' | 'admin' | 'supplier' | 'owner'
}

export interface Agency {
  id: number
  name: string
  email: string
  phone: string
  logo: string | null
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken  = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const user         = ref<User | null>(null)
  const agency       = ref<Agency | null>(null)
  // Last registered push token — needed so we can revoke it on logout
  const _pushToken   = ref<string | null>(localStorage.getItem('push_token'))

  /**
   * Set to true after a login response carries `two_fa_suggest_setup: true`.
   * The router guard and TwoFAEnrollPage read this to show the optional-setup
   * banner with a "Skip for now" button (owner role, DEC-018).
   */
  const suggestTwoFASetup = ref(false)

  // ── Computed ──────────────────────────────────────────────────────────────

  const isAuthenticated = computed(() => !!accessToken.value)

  const canAccessAgentApp = computed(() =>
    ['agent', 'admin'].includes(user.value?.role ?? ''),
  )

  const homeRoute = computed(() => {
    if (!user.value) return '/login'
    if (['agent', 'admin'].includes(user.value.role)) return '/dashboard'
    return '/login'
  })

  // ── Actions ───────────────────────────────────────────────────────────────

  function _setTokens(access: string, refresh: string) {
    accessToken.value  = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  /**
   * Authenticate with email + password.
   * Returns raw response data so the caller can handle 2FA fields.
   * Also sets `suggestTwoFASetup` when the server flags optional 2FA setup (owner role, DEC-018).
   */
  async function login(email: string, password: string): Promise<any> {
    const { data } = await api.post('/auth/login/', { email, password })
    if (data.access && data.refresh) {
      _setTokens(data.access, data.refresh)
      await fetchMe()
      suggestTwoFASetup.value = data.two_fa_suggest_setup === true
    }
    return data
  }

  /**
   * Authenticate with Google credential.
   * Returns raw response data so the caller can handle 2FA fields.
   */
  async function loginWithGoogle(credential: string): Promise<any> {
    const { data } = await api.post('/auth/google/', { credential })
    if (data.access && data.refresh) {
      _setTokens(data.access, data.refresh)
      user.value = data.user
      suggestTwoFASetup.value = data.two_fa_suggest_setup === true
    }
    return data
  }

  /**
   * Set tokens from a two_fa_token exchange (challenge or recovery).
   */
  function setTokensFromTwoFA(data: { access: string; refresh: string; user: any }) {
    _setTokens(data.access, data.refresh)
    user.value = data.user
  }

  async function fetchMe() {
    const { data } = await api.get('/auth/me/')
    user.value   = data.user ?? data
    agency.value = data.agency ?? null
  }

  /**
   * POST /auth/2fa/skip/ — owner role optional-2FA prompt: user chose not to enroll now.
   * Stamps `skipped_2fa_setup_at` on the backend so the prompt won't reappear until
   * the next first-login after the skip window expires (DEC-018).
   */
  async function skipTwoFASetup(): Promise<void> {
    await api.post('/auth/2fa/skip/')
    suggestTwoFASetup.value = false
  }

  async function logout() {
    // POPIA: revoke push token before clearing session
    if (_pushToken.value) {
      try {
        const { revokePushToken } = await import('../services/push')
        await revokePushToken(_pushToken.value, deregisterPushToken)
      } catch {
        // Non-fatal — proceed with logout
      }
    }
    try {
      if (refreshToken.value) {
        await api.post('/auth/logout/', { refresh: refreshToken.value })
      }
    } catch {
      // Ignore logout errors — clear state regardless
    } finally {
      accessToken.value  = null
      refreshToken.value = null
      user.value         = null
      agency.value       = null
      _pushToken.value   = null
      suggestTwoFASetup.value = false
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('push_token')
    }
  }

  async function registerPushToken(token: string, platform: 'ios' | 'android') {
    await api.post('/auth/push-token/', { token, platform })
    _pushToken.value = token
    localStorage.setItem('push_token', token)
  }

  async function deregisterPushToken(token: string) {
    await api.delete('/auth/push-token/', { data: { token } })
    _pushToken.value = null
    localStorage.removeItem('push_token')
  }

  /**
   * Initialise Capacitor push notifications after login.
   * Requires a Vue Router instance for deep-link navigation.
   */
  async function startPush(router: Router) {
    const { initialisePush } = await import('../services/push')
    await initialisePush(registerPushToken, router)
  }

  return {
    accessToken,
    refreshToken,
    user,
    agency,
    isAuthenticated,
    canAccessAgentApp,
    homeRoute,
    suggestTwoFASetup,
    login,
    loginWithGoogle,
    setTokensFromTwoFA,
    logout,
    fetchMe,
    skipTwoFASetup,
    registerPushToken,
    deregisterPushToken,
    startPush,
  }
})
