import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listMaintenanceRequests,
  updateMaintenanceRequest,
  type MaintenanceRequest,
  type MaintenanceActivity,
} from '../services/api'

function getWsBaseUrl(): string {
  const apiUrl = (process.env.API_URL as string) || 'http://localhost:8000'
  return apiUrl.replace(/^http/, 'ws').replace(/\/api\/v1\/?$/, '')
}

function getToken(): string {
  return localStorage.getItem('access_token') || ''
}

export const useMaintenanceStore = defineStore('maintenance', () => {
  // ── State ──────────────────────────────────────────────────────────────────
  const requests = ref<MaintenanceRequest[]>([])
  const activeRequestId = ref<number | null>(null)
  const activities = ref<MaintenanceActivity[]>([])
  const loading = ref(false)
  const loadingChat = ref(false)
  const listWsConnected = ref(false)
  const chatWsConnected = ref(false)

  let _listWs: WebSocket | null = null
  let _chatWs: WebSocket | null = null
  let _listReconnectTimer: ReturnType<typeof setTimeout> | null = null
  let _chatReconnectTimer: ReturnType<typeof setTimeout> | null = null
  let _listReconnectDelay = 1000
  let _chatReconnectDelay = 1000
  let _currentPropertyId: number | null = null

  // ── Getters ────────────────────────────────────────────────────────────────
  const activeRequest = computed(() =>
    requests.value.find((r) => r.id === activeRequestId.value) ?? null,
  )

  const openRequests = computed(() =>
    requests.value.filter((r) => r.status === 'open' || r.status === 'in_progress'),
  )

  const closedRequests = computed(() =>
    requests.value.filter((r) => r.status === 'resolved' || r.status === 'closed'),
  )

  const openCount = computed(() => openRequests.value.length)

  const urgentCount = computed(() =>
    requests.value.filter((r) => r.priority === 'urgent' || r.priority === 'high').length,
  )

  // ── Actions ────────────────────────────────────────────────────────────────

  async function fetchRequests(propertyId: number) {
    loading.value = true
    _currentPropertyId = propertyId
    try {
      const resp = await listMaintenanceRequests({ property: propertyId })
      requests.value = resp.results
    } finally {
      loading.value = false
    }
  }

  function selectRequest(id: number) {
    activeRequestId.value = id
    connectChatSocket(id)
  }

  function clearSelection() {
    // Mark messages as read when closing the chat
    if (activeRequestId.value != null) {
      const req = requests.value.find((r) => r.id === activeRequestId.value)
      const count = Math.max(activities.value.length, req?.activity_count || 0)
      localStorage.setItem(`maint_read_${activeRequestId.value}`, String(count))
    }
    activeRequestId.value = null
    activities.value = []
    _disconnectChat()
  }

  function unreadCount(req: MaintenanceRequest): number {
    const lastRead = parseInt(localStorage.getItem(`maint_read_${req.id}`) || '0', 10)
    return Math.max(0, (req.activity_count || 0) - lastRead)
  }

  // ── List WebSocket (real-time updates) ─────────────────────────────────────

  function connectListSocket() {
    _disconnectList()
    const url = `${getWsBaseUrl()}/ws/maintenance/updates/?token=${getToken()}`
    _listWs = new WebSocket(url)

    _listWs.onopen = () => {
      listWsConnected.value = true
      _listReconnectDelay = 1000
    }

    _listWs.onmessage = (event) => {
      const data = JSON.parse(event.data)
      // Re-fetch the list when an issue is created or updated for our property
      if (
        (data.event === 'issue_created' || data.event === 'issue_updated') &&
        _currentPropertyId
      ) {
        fetchRequests(_currentPropertyId)
      }
    }

    _listWs.onclose = (event) => {
      listWsConnected.value = false
      // Don't reconnect on intentional close (code 1000) or auth failure (4001)
      if (event.code !== 1000 && event.code !== 4001) {
        _listReconnectTimer = setTimeout(() => {
          _listReconnectDelay = Math.min(_listReconnectDelay * 2, 30000)
          connectListSocket()
        }, _listReconnectDelay)
      }
    }

    _listWs.onerror = () => {
      // onclose will fire after onerror — reconnect handled there
    }
  }

  // ── Chat WebSocket (per-issue activity feed) ───────────────────────────────

  function connectChatSocket(requestId: number) {
    _disconnectChat()
    loadingChat.value = true
    const url = `${getWsBaseUrl()}/ws/maintenance/${requestId}/activity/?token=${getToken()}`
    _chatWs = new WebSocket(url)

    _chatWs.onopen = () => {
      chatWsConnected.value = true
      _chatReconnectDelay = 1000
    }

    _chatWs.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.type === 'history') {
        // Initial history payload sent on connect
        activities.value = data.activities || []
        loadingChat.value = false
      } else if (data.type === 'activity') {
        // New activity broadcast
        const existing = activities.value.find((a) => a.id === data.activity?.id)
        if (!existing && data.activity) {
          activities.value.push(data.activity)
        }
      } else if (data.type === 'error') {
        console.warn('[maintenance-ws]', data.message)
      }
    }

    _chatWs.onclose = (event) => {
      chatWsConnected.value = false
      loadingChat.value = false
      if (event.code !== 1000 && event.code !== 4001 && activeRequestId.value === requestId) {
        _chatReconnectTimer = setTimeout(() => {
          _chatReconnectDelay = Math.min(_chatReconnectDelay * 2, 30000)
          connectChatSocket(requestId)
        }, _chatReconnectDelay)
      }
    }

    _chatWs.onerror = () => {
      // onclose handles reconnect
    }
  }

  function sendMessage(message: string, activityType = 'note') {
    if (!_chatWs || _chatWs.readyState !== WebSocket.OPEN) return
    _chatWs.send(JSON.stringify({ message, activity_type: activityType }))
  }

  async function updateStatus(id: number, status: MaintenanceRequest['status']) {
    const updated = await updateMaintenanceRequest(id, { status })
    const idx = requests.value.findIndex((r) => r.id === id)
    if (idx !== -1) requests.value[idx] = { ...requests.value[idx], ...updated }
  }

  // ── Cleanup ────────────────────────────────────────────────────────────────

  function _disconnectList() {
    if (_listReconnectTimer) {
      clearTimeout(_listReconnectTimer)
      _listReconnectTimer = null
    }
    if (_listWs) {
      _listWs.onclose = null // prevent reconnect
      _listWs.close()
      _listWs = null
    }
    listWsConnected.value = false
  }

  function _disconnectChat() {
    if (_chatReconnectTimer) {
      clearTimeout(_chatReconnectTimer)
      _chatReconnectTimer = null
    }
    if (_chatWs) {
      _chatWs.onclose = null
      _chatWs.close()
      _chatWs = null
    }
    chatWsConnected.value = false
  }

  function disconnect() {
    _disconnectList()
    _disconnectChat()
    activeRequestId.value = null
    activities.value = []
    requests.value = []
  }

  return {
    // State
    requests,
    activeRequestId,
    activities,
    loading,
    loadingChat,
    listWsConnected,
    chatWsConnected,
    // Getters
    activeRequest,
    openRequests,
    closedRequests,
    openCount,
    urgentCount,
    // Actions
    fetchRequests,
    selectRequest,
    clearSelection,
    unreadCount,
    connectListSocket,
    sendMessage,
    updateStatus,
    disconnect,
  }
})
