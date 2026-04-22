import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export interface User {
  id: number
  email: string
  full_name: string
  role: string
  phone?: string
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value)
  const isTenant = computed(() => user.value?.role === 'tenant')

  /**
   * Authenticate with email + password.
   * Returns raw response data so the caller can handle 2FA fields.
   * Tokens are only stored when the server actually issues them.
   */
  async function login(email: string, password: string): Promise<any> {
    const { data } = await api.post('/auth/login/', { email, password })
    if (data.access && data.refresh) {
      _setTokens(data)
    }
    return data
  }

  async function requestOtp(phone: string) {
    await api.post('/auth/otp/request/', { phone })
  }

  async function verifyOtp(phone: string, code: string) {
    const { data } = await api.post('/auth/otp/verify/', { phone, code })
    _setTokens(data)
  }

  function _setTokens(data: { access: string; refresh: string; user: User }) {
    accessToken.value = data.access
    refreshToken.value = data.refresh
    user.value = data.user
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
  }

  async function logout() {
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
  }

  return {
    accessToken, user, isAuthenticated, isTenant,
    login, requestOtp, verifyOtp, logout, fetchMe, _setTokens,
  }
})
