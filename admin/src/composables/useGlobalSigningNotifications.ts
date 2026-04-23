/**
 * Global signing notification bus for the admin SPA.
 *
 * Connects to `ws://<host>/ws/esigning/notifications/` with JWT auth.
 * Broadcasts signing events to all parts of the app so a toast can be shown
 * regardless of which route the agent is currently viewing.
 *
 * Features:
 * - Auto-reconnects on disconnect with exponential back-off
 * - Deduplicates events by `event_id` — prevents double toasts when the agent
 *   also has the ESigningPanel open for the same submission
 * - Auto-stops when the user logs out (watches auth store)
 */
import { ref, watch, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useToast } from './useToast'

export interface SigningNotificationEvent {
  type: 'signer_completed' | 'submission_completed' | 'signer_declined' | string
  event_id: string
  submission_id: number
  signer_name: string
  doc_type: 'lease' | 'mandate' | 'document' | string
  doc_title: string
  property_address: string
  message: string
  panel_url?: string
}

/** Duration (ms) toasts for signing events are shown. Must be ≥ 6 000 per AC. */
const TOAST_DURATION_MS = 7000

/** Max event IDs kept in the dedup set (prevents unbounded memory growth). */
const DEDUP_CACHE_MAX = 200

// Module-level dedup cache shared across composable instances.
const seenEventIds = new Set<string>()

function _pruneDedup() {
  if (seenEventIds.size > DEDUP_CACHE_MAX) {
    // Drop the oldest ~50 entries
    const iter = seenEventIds.values()
    for (let i = 0; i < 50; i++) {
      const { value, done } = iter.next()
      if (done) break
      seenEventIds.delete(value)
    }
  }
}

function getWsUrl(): string {
  const token = localStorage.getItem('access_token') || ''
  const loc = window.location
  const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:'
  const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
  const host = new URL(apiBase).host
  return `${protocol}//${host}/ws/esigning/notifications/?token=${token}`
}

/**
 * Mount this composable once in `App.vue`.
 * It automatically connects when the user is authenticated and disconnects on logout.
 */
export function useGlobalSigningNotifications() {
  const toast = useToast()
  const connected = ref(false)

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectDelay = 1000
  let stopped = false

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
      connected.value = true
      reconnectDelay = 1000
    }

    ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data) as SigningNotificationEvent
        handleEvent(event)
      } catch {
        /* ignore malformed messages */
      }
    }

    ws.onclose = () => {
      connected.value = false
      if (!stopped) scheduleReconnect()
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function handleEvent(event: SigningNotificationEvent) {
    // Dedup by event_id to avoid double-toasting when ESigningPanel is also open
    if (event.event_id) {
      if (seenEventIds.has(event.event_id)) return
      seenEventIds.add(event.event_id)
      _pruneDedup()
    }

    const msg = event.message || buildFallbackMessage(event)
    const type = event.type

    if (type === 'submission_completed') {
      toast.show(msg, 'success', TOAST_DURATION_MS)
    } else if (type === 'signer_declined') {
      toast.show(msg, 'warning', TOAST_DURATION_MS)
    } else {
      // signer_completed and any future types
      toast.show(msg, 'info', TOAST_DURATION_MS)
    }
  }

  function buildFallbackMessage(event: SigningNotificationEvent): string {
    const name = event.signer_name || 'A signer'
    const docType = event.doc_type || 'document'
    if (event.type === 'submission_completed') {
      return `All parties signed the ${docType}`
    }
    if (event.type === 'signer_declined') {
      return `${name} declined to sign the ${docType}`
    }
    return `${name} signed the ${docType}`
  }

  function scheduleReconnect() {
    if (stopped) return
    reconnectTimer = setTimeout(() => {
      reconnectDelay = Math.min(reconnectDelay * 2, 30_000)
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

  // Connect when authenticated; disconnect on logout
  const authStore = useAuthStore()
  watch(
    () => authStore.isAuthenticated,
    (isAuth) => {
      if (isAuth) {
        stopped = false
        reconnectDelay = 1000
        connect()
      } else {
        stop()
      }
    },
    { immediate: true },
  )

  onUnmounted(stop)

  return { connected, stop }
}

/**
 * Mark an event ID as already seen from within a panel (e.g. ESigningPanel)
 * to prevent the global listener from showing a duplicate toast.
 */
export function markSigningEventSeen(eventId: string) {
  if (eventId) seenEventIds.add(eventId)
}
