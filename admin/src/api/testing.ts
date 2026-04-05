import api from '../api'

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '')

export const testingApi = {
  // Dashboard
  getHealth: () => api.get('/test-hub/health/'),
  getSnapshot: () => api.get('/test-hub/health/'),  // health endpoint returns module stats

  // Module live stats (real pytest collection)
  getModuleStats: (module: string) => api.get(`/test-hub/module/${module}/`),

  // Runs
  getRuns: (params?: { module?: string; tier?: string }) =>
    api.get('/test-hub/runs/', { params }),
  triggerRun: (module?: string, tier?: string) =>
    api.post('/test-hub/runs/trigger/', { module, tier }),

  // Live streaming run (SSE)
  streamRunUrl: (module?: string) => {
    const token = localStorage.getItem('access_token') || ''
    const params = new URLSearchParams({ token })
    if (module) params.set('module', module)
    return `${API_BASE}/test-hub/runs/stream/?${params}`
  },

  // Issues
  getIssues: (params?: { module?: string; status?: string }) =>
    api.get('/test-hub/issues/', { params }),

  // Self-check
  getSelfCheck: () => api.get('/test-hub/selfcheck/'),
  runSelfCheck: () => api.post('/test-hub/selfcheck/'),

  // RAG
  getRAGStatus: () => api.get('/test-hub/rag-status/'),
  reindexRAG: (module?: string) => api.post('/test-hub/rag-reindex/', { module }),

  // Frontend (Vitest) tests
  getFrontendStats: () => api.get('/test-hub/frontend/stats/'),
  streamFrontendRunUrl: () => {
    const token = localStorage.getItem('access_token') || ''
    const params = new URLSearchParams({ token })
    return `${API_BASE}/test-hub/runs/stream-frontend/?${params}`
  },
}
