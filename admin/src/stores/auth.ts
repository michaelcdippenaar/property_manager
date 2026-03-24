import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

interface User {
  id: number
  email: string
  full_name: string
  role: string
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value)
  const isAgent = computed(() => ['agent', 'admin'].includes(user.value?.role ?? ''))
  const isSupplier = computed(() => user.value?.role === 'supplier')
  const isOwner = computed(() => user.value?.role === 'owner')
  const isTenant = computed(() => user.value?.role === 'tenant')

  /** Where to redirect after login based on role. */
  const homeRoute = computed(() => {
    if (isSupplier.value) return '/jobs'
    if (isOwner.value) return '/owner'
    return '/'
  })

  async function login(email: string, password: string) {
    const { data } = await api.post('/auth/login/', { email, password })
    accessToken.value = data.access
    refreshToken.value = data.refresh
    user.value = data.user
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
  }

  function logout() {
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
    accessToken, user, isAuthenticated,
    isAgent, isSupplier, isOwner, isTenant, homeRoute,
    login, logout, fetchMe,
  }
})
