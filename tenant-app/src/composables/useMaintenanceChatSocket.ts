import { ref, watch, onUnmounted } from 'vue'

export interface MaintenanceActivity {
  id: number
  activity_type: string
  message: string
  created_by_name?: string
  created_by_role?: string
  created_at: string
  file?: string | null
  file_url?: string
  is_system?: boolean
  metadata?: Record<string, unknown> | null
}

/**
 * WebSocket-first composable for maintenance issue chat.
 * Falls back to REST API polling (every 30s) when the WebSocket disconnects.
 *
 * @param issueId       Reactive getter returning the MaintenanceRequest ID (or null)
 * @param onHistory     Called once on WS connect with all existing activities
 * @param onNewActivity Called for each new activity (WS broadcast or poll delta)
 * @param apiPollFn     REST fallback: fetch activities → MaintenanceActivity[]
 * @param apiSendFn     REST fallback: send message when WS is down
 */
export function useMaintenanceChatSocket(
  issueId: () => number | null,
  onHistory: (activities: MaintenanceActivity[]) => void,
  onNewActivity: (activity: MaintenanceActivity) => void,
  apiPollFn?: (id: number) => Promise<MaintenanceActivity[]>,
  apiSendFn?: (id: number, message: string, activityType: string) => Promise<void>,
) {
  const connected = ref(false)
  const disconnected = ref(false)
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectDelay = 1000
  let stopped = false

  // Polling state
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let lastKnownActivityId = 0
  const POLL_INTERVAL = 30_000

  function getWsUrl(id: number): string {
    const token = localStorage.getItem('access_token') || ''
    const apiBase = (process.env.API_URL as string) || 'http://localhost:8000/api/v1'
    const host = new URL(apiBase).host
    const protocol = apiBase.startsWith('https') ? 'wss:' : 'ws:'
    return `${protocol}//${host}/ws/maintenance/${id}/activity/?token=${token}`
  }

  function startPolling() {
    if (pollTimer || !apiPollFn) return
    const id = issueId()
    if (!id) return

    pollTimer = setInterval(async () => {
      if (connected.value || stopped) { stopPolling(); return }
      try {
        const activities = await apiPollFn(id)
        // Emit only activities newer than what we've seen
        for (const a of activities) {
          if (a.id > lastKnownActivityId) {
            lastKnownActivityId = a.id
            onNewActivity(a)
          }
        }
      } catch { /* polling is best-effort */ }
    }, POLL_INTERVAL)
  }

  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  }

  function connect() {
    const id = issueId()
    if (!id || stopped) return
    cleanup()

    try {
      ws = new WebSocket(getWsUrl(id))
    } catch {
      disconnected.value = true
      startPolling()
      scheduleReconnect()
      return
    }

    ws.onopen = () => {
      connected.value = true
      disconnected.value = false
      reconnectDelay = 1000
      stopPolling()
    }

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'history') {
          const activities = data.activities ?? []
          // Track the latest ID for polling dedup
          for (const a of activities) {
            if (a.id > lastKnownActivityId) lastKnownActivityId = a.id
          }
          onHistory(activities)
        } else if (data.type === 'activity' && data.activity) {
          if (data.activity.id > lastKnownActivityId) {
            lastKnownActivityId = data.activity.id
          }
          onNewActivity(data.activity)
        }
      } catch { /* ignore parse errors */ }
    }

    ws.onclose = () => {
      connected.value = false
      disconnected.value = true
      if (!stopped) {
        startPolling()
        scheduleReconnect()
      }
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
    stopPolling()
  }

  /**
   * Send a message. Uses WebSocket when connected, falls back to REST API.
   * Returns true if sent successfully.
   */
  function send(message: string, activityType = 'note'): boolean {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ message, activity_type: activityType }))
      return true
    }
    // Fallback to REST API when WS is disconnected
    if (apiSendFn) {
      const id = issueId()
      if (id) {
        apiSendFn(id, message, activityType).catch(() => { /* best effort */ })
        return true
      }
    }
    return false
  }

  watch(issueId, (id) => {
    if (id) {
      stopped = false
      reconnectDelay = 1000
      lastKnownActivityId = 0
      connect()
    } else {
      cleanup()
      stopPolling()
    }
  }, { immediate: true })

  onUnmounted(stop)

  return { connected, disconnected, send, stop }
}
