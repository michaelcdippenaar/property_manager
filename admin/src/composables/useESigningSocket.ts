/**
 * Composable for real-time e-signing status updates via WebSocket.
 *
 * Connects to `ws://<host>/ws/esigning/<submissionPk>/` with JWT auth.
 * Receives events from the backend poller or webhook handler:
 *   - signer_viewed, signer_completed, signer_declined
 *   - submission_completed
 *
 * Auto-reconnects on disconnect with exponential backoff.
 */
import { ref, watch, onUnmounted } from 'vue'

export interface ESigningEvent {
  type: string
  submission_id?: number
  signers?: any[]
  signed_pdf_url?: string
  [key: string]: any
}

export function useESigningSocket(
  submissionPk: () => number | string | null | undefined,
  onEvent: (event: ESigningEvent) => void,
) {
  const connected = ref(false)
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectDelay = 1000
  let stopped = false

  function getWsUrl(pk: number | string): string {
    const token = localStorage.getItem('access_token') || ''
    const loc = window.location
    const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:'
    // In dev, the API runs on port 8000 while the SPA is on 5173
    const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
    const host = new URL(apiBase).host
    return `${protocol}//${host}/ws/esigning/${pk}/?token=${token}`
  }

  function connect() {
    const pk = submissionPk()
    if (!pk || stopped) return

    cleanup()

    try {
      ws = new WebSocket(getWsUrl(pk))
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
        const data = JSON.parse(e.data) as ESigningEvent
        onEvent(data)
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
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.onopen = null
      ws.onmessage = null
      ws.onclose = null
      ws.onerror = null
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

  // Auto-connect when submissionPk changes
  watch(submissionPk, (pk) => {
    if (pk) {
      stopped = false
      reconnectDelay = 1000
      connect()
    } else {
      cleanup()
    }
  }, { immediate: true })

  onUnmounted(stop)

  return { connected, stop }
}
