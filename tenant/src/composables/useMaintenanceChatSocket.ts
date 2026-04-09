import { ref, watch, onUnmounted } from 'vue'

export interface MaintenanceActivity {
  id: number
  activity_type: string
  message: string
  created_by_name?: string
  created_at: string
  file_url?: string
  is_system?: boolean
}

export function useMaintenanceChatSocket(
  issueId: () => number | null,
  onHistory: (activities: MaintenanceActivity[]) => void,
  onNewActivity: (activity: MaintenanceActivity) => void,
) {
  const connected = ref(false)
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectDelay = 1000
  let stopped = false

  function getWsUrl(id: number): string {
    const token = localStorage.getItem('access_token') || ''
    const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
    const host = new URL(apiBase).host
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${host}/ws/maintenance/${id}/activity/?token=${token}`
  }

  function connect() {
    const id = issueId()
    if (!id || stopped) return
    cleanup()

    try {
      ws = new WebSocket(getWsUrl(id))
    } catch {
      scheduleReconnect()
      return
    }

    ws.onopen = () => {
      connected.value = true
      reconnectDelay = 1000
    }

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'history') {
          onHistory(data.activities ?? [])
        } else if (data.type === 'activity' && data.activity) {
          onNewActivity(data.activity)
        }
      } catch { /* ignore parse errors */ }
    }

    ws.onclose = () => {
      connected.value = false
      if (!stopped) scheduleReconnect()
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function scheduleReconnect() {
    if (stopped) return
    reconnectTimer = setTimeout(() => {
      reconnectDelay = Math.min(reconnectDelay * 2, 30000)
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
    connected.value = false
  }

  function stop() {
    stopped = true
    cleanup()
  }

  function send(message: string, activityType = 'note'): boolean {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ message, activity_type: activityType }))
      return true
    }
    return false
  }

  watch(issueId, (id) => {
    if (id) {
      stopped = false
      reconnectDelay = 1000
      connect()
    } else {
      cleanup()
    }
  }, { immediate: true })

  onUnmounted(stop)

  return { connected, send, stop }
}
