import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

interface User {
  id: number
  email: string
  full_name: string
  role: string
}

interface AgencyInfo {
  id: number
  account_type: 'agency' | 'individual'
  name: string
  [key: string]: any
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const user = ref<User | null>(null)
  const agency = ref<AgencyInfo | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value)
  const STAFF_ROLES = ['agent', 'admin', 'agency_admin', 'estate_agent', 'managing_agent', 'accountant', 'viewer']
  const isAgent = computed(() => STAFF_ROLES.includes(user.value?.role ?? ''))
  const isSupplier = computed(() => user.value?.role === 'supplier')
  const isOwner = computed(() => user.value?.role === 'owner')
  const isTenant = computed(() => user.value?.role === 'tenant')
  const isAgency = computed(() => agency.value?.account_type === 'agency')

  /** Where to redirect after login based on role. */
  const homeRoute = computed(() => {
    if (isSupplier.value) return '/jobs'
    if (isOwner.value) return '/owner'
    const role = user.value?.role
    if (role === 'agency_admin') return '/agency'
    if (role === 'agent' || role === 'estate_agent' || role === 'managing_agent') return '/agent'
    return '/'
  })

  /**
   * Authenticate with email + password.
   * Returns the raw response data so the caller can inspect 2FA fields.
   * If the response contains full tokens (access + refresh), they are stored.
   */
  async function login(email: string, password: string): Promise<any> {
    const { data } = await api.post('/auth/login/', { email, password })
    // Only store tokens when the server actually issues them.
    // If two_fa_required or two_fa_hard_blocked, no tokens are present.
    if (data.access && data.refresh) {
      _setTokens(data)
    }
    return data
  }

  async function register(payload: {
    email: string
    password: string
    first_name: string
    last_name: string
    phone?: string
    account_type?: string
    agency_name?: string
    tos_document_id?: number | null
    privacy_document_id?: number | null
  }) {
    await api.post('/auth/register/', payload)
    await login(payload.email, payload.password)
  }

  /**
   * Authenticate with Google credential.
   * Returns raw response data (may include 2FA fields).
   */
  async function googleAuth(credential: string): Promise<any> {
    const { data } = await api.post('/auth/google/', { credential })
    if (data.access && data.refresh) {
      _setTokens(data)
    }
    return data
  }

  function _setTokens(data: { access: string; refresh: string; user: User }) {
    accessToken.value = data.access
    refreshToken.value = data.refresh
    user.value = data.user
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
  }

  async function logout() {
    // Blacklist refresh token on the server (best-effort)
    if (refreshToken.value) {
      try {
        await api.post('/auth/logout/', { refresh: refreshToken.value })
      } catch { /* ignore */ }
    }
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  async function fetchMe() {
    const { data } = await api.get('/auth/me/')
    user.value = data
    // Also fetch agency info for account type checks
    await fetchAgency()
  }

  async function fetchAgency() {
    try {
      const { data } = await api.get('/auth/agency/')
      agency.value = data && data.id ? data : null
    } catch {
      agency.value = null
    }
  }

  return {
    accessToken, user, agency, isAuthenticated,
    isAgent, isSupplier, isOwner, isTenant, isAgency, homeRoute,
    login, register, googleAuth, logout, fetchMe, fetchAgency, _setTokens,
  }
})
