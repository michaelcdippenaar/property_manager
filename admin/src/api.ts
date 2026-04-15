import axios from 'axios'
import { apiBaseURL } from './lib/backendUrls'

const api = axios.create({
  baseURL: apiBaseURL(),
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Serialize refresh calls: with ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION
// on the backend, two concurrent 401s would each POST the same refresh token —
// the first rotates (and blacklists) it, the second then fails and boots the
// user to /login. Instead, the first 401 starts a refresh; every other 401 that
// arrives while it's in flight awaits the same promise and reuses the new token.
let refreshInFlight: Promise<string> | null = null

async function runRefresh(): Promise<string> {
  const refresh = localStorage.getItem('refresh_token')
  if (!refresh) throw new Error('no refresh token')
  const { data } = await axios.post(
    `${api.defaults.baseURL}/auth/token/refresh/`,
    { refresh }
  )
  localStorage.setItem('access_token', data.access)
  if (data.refresh) localStorage.setItem('refresh_token', data.refresh)
  return data.access
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && original && !original._retry) {
      original._retry = true
      if (!refreshInFlight) {
        refreshInFlight = runRefresh().finally(() => {
          refreshInFlight = null
        })
      }
      try {
        const access = await refreshInFlight
        original.headers.Authorization = `Bearer ${access}`
        return api(original)
      } catch {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
