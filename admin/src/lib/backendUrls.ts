/**
 * Dev: Vite proxies `/api` → Django so the SPA can use same-origin `/api/v1`
 * (avoids CORS and works when only 5173 is used in the browser).
 * Production / overrides: set `VITE_API_URL`.
 */
export function apiBaseURL(): string {
  const fromEnv = import.meta.env.VITE_API_URL as string | undefined
  if (fromEnv) return fromEnv
  if (import.meta.env.DEV) return '/api/v1'
  return 'http://127.0.0.1:8000/api/v1'
}
