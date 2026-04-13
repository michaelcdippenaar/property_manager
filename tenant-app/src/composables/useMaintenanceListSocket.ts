import { onUnmounted } from 'vue'

/**
 * WebSocket composable for tenant maintenance issue list auto-refresh.
 *
 * Connects to /ws/maintenance/updates/ and calls `onUpdate` whenever an issue
 * is created or updated. Falls back to exponential-backoff reconnect on close.
 *
 * Usage:
 *   useMaintenanceListSocket(() => loadIssues())
 */
export function useMaintenanceListSocket(onUpdate: () => void) {
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectDelay = 1000
  let stopped = false

  function getWsUrl(): string {
    const token = localStorage.getItem('access_token') || ''
    const apiBase = (process.env.API_URL as string) || 'http://localhost:8000/api/v1'
    const host = new URL(apiBase).host
    const protocol = apiBase.startsWith('https') ? 'wss:' : 'ws:'
    return `${protocol}//${host}/ws/maintenance/updates/?token=${token}`
  }

  function connect() {
    if (stopped) return
    cleanup()

    try {
      ws = new WebSocket(getWsUrl())
    } catch {
      scheduleReconnect()
      return
    }

    ws.onopen = () => {
      reconnectDelay = 1000
    }

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.event === 'issue_created' || data.event === 'issue_updated') {
          onUpdate()
        }
      } catch { /* ignore parse errors */ }
    }

    ws.onclose = () => {
      if (!stopped) scheduleReconnect()
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function scheduleReconnect() {
    reconnectTimer = setTimeout(() => {
      reconnectDelay = Math.min(reconnectDelay * 2, 30_000)
      connect()
    }, reconnectDelay)
  }

  function cleanup() {
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
    if (ws) {
      ws.onopen = null; ws.onmessage = null; ws.onclose = null; ws.onerror = null
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close()
      }
      ws = null
    }
  }

  function stop() {
    stopped = true
    cleanup()
  }

  connect()
  onUnmounted(stop)
}
