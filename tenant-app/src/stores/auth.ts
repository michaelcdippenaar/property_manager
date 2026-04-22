import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../boot/axios'

export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  full_name: string
  phone: string
  role: 'tenant' | 'agent' | 'admin' | 'supplier' | 'owner'
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken  = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const user         = ref<User | null>(null)

  // ── Computed (only isAuthenticated — all other getters live in components) ──
  const isAuthenticated = computed(() => !!accessToken.value)

  // ── Actions ───────────────────────────────────────────────────────────────

  function _setTokens(access: string, refresh: string) {
    accessToken.value  = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  async function login(email: string, password: string) {
    const { data } = await api.post('/auth/login/', { email, password })
    _setTokens(data.access, data.refresh)
    await fetchMe()
  }

  async function loginWithGoogle(credential: string) {
    const { data } = await api.post('/auth/google/', { credential })
    _setTokens(data.access, data.refresh)
    user.value = data.user
  }

  async function requestOtp(phone: string) {
    await api.post('/auth/otp/send/', { phone })
  }

  async function verifyOtp(phone: string, code: string) {
    const { data } = await api.post('/auth/otp/verify/', { phone, code })
    _setTokens(data.access, data.refresh)
    await fetchMe()
  }

  async function fetchMe() {
    const { data } = await api.get('/auth/me/')
    user.value = data.user ?? data
  }

  async function logout() {
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
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    }
  }

  async function registerPushToken(token: string, platform: 'ios' | 'android') {
    await api.post('/auth/push-token/', { token, platform })
  }

  return {
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    login,
    loginWithGoogle,
    requestOtp,
    verifyOtp,
    logout,
    fetchMe,
    registerPushToken,
  }
})
