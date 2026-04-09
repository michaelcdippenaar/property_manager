import { boot } from 'quasar/wrappers'
import axios, { type AxiosInstance } from 'axios'

declare module '@vue/runtime-core' {
  interface ComponentCustomProperties {
    $axios: AxiosInstance
    $api: AxiosInstance
  }
}

const api = axios.create({
  baseURL: (process.env.API_URL as string) || 'http://localhost:8000/api/v1',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── Request interceptor: inject Bearer token ──────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor: 401 → refresh → retry ──────────────────────────────
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem('refresh_token')

      if (refresh) {
        try {
          const { data } = await axios.post(
            `${api.defaults.baseURL}/auth/token/refresh/`,
            { refresh },
          )
          localStorage.setItem('access_token', data.access)
          if (data.refresh) {
            localStorage.setItem('refresh_token', data.refresh)
          }
          original.headers.Authorization = `Bearer ${data.access}`
          return api(original)
        } catch {
          // Refresh failed — clear tokens and redirect to login
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          // Use dynamic import to avoid circular dependency with router
          import('../router/index').then(({ default: router }) => {
            void router.push('/login')
          })
        }
      }
    }

    return Promise.reject(error)
  },
)

export default boot(({ app }) => {
  app.config.globalProperties.$axios = axios
  app.config.globalProperties.$api = api
})

export { api }
