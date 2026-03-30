<template>
  <div class="space-y-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <p class="text-sm text-gray-500">Track, assign, and resolve maintenance requests across all properties.</p>
    </div>

    <!-- Tabs: Active / Archived -->
    <div class="flex items-center gap-0 border-b border-gray-200 -mb-1">
      <button
        class="px-4 py-2 text-sm font-medium transition-colors relative"
        :class="activeTab === 'active' ? 'text-navy' : 'text-gray-400 hover:text-gray-600'"
        @click="switchTab('active')"
      >
        Active
        <span v-if="activeTab === 'active'" class="absolute bottom-0 left-0 right-0 h-0.5 bg-navy rounded-full" />
      </button>
      <button
        class="px-4 py-2 text-sm font-medium transition-colors relative flex items-center gap-1.5"
        :class="activeTab === 'archived' ? 'text-navy' : 'text-gray-400 hover:text-gray-600'"
        @click="switchTab('archived')"
      >
        <Archive :size="13" />
        Archived
        <span v-if="activeTab === 'archived'" class="absolute bottom-0 left-0 right-0 h-0.5 bg-navy rounded-full" />
      </button>
    </div>

    <!-- Filter pills -->
    <FilterPills v-model="activeFilter" :options="filterOptions" @update:modelValue="loadRequests()" />

    <!-- Loading skeletons -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="i in 6" :key="i" class="card p-5 space-y-3 animate-pulse">
        <div class="h-3 bg-gray-100 rounded w-1/3"></div>
        <div class="h-4 bg-gray-100 rounded w-2/3"></div>
        <div class="h-3 bg-gray-100 rounded w-full"></div>
      </div>
    </div>

    <!-- Two-column layout: list + detail panel -->
    <div v-else class="grid gap-5" :class="selected ? 'xl:grid-cols-[minmax(0,0.75fr)_minmax(420px,1.25fr)]' : ''">

      <!-- Left: request cards -->
      <div class="space-y-3 min-w-0">
        <button
          v-for="req in requests"
          :key="req.id"
          type="button"
          class="w-full text-left rounded-xl border px-4 py-3 transition-all border-l-4"
          :class="[
            priorityBorderLeft(req.priority),
            selected?.id === req.id ? 'bg-slate-50 shadow-sm border-gray-300' : 'bg-white hover:bg-gray-50 hover:border-gray-300 border-gray-200',
          ]"
          @click="selectRequest(req)"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="text-xs font-mono text-gray-400">{{ req.ticket_reference || `#${req.id}` }}</span>
                <span class="font-medium text-gray-900 text-sm">{{ req.title }}</span>
              </div>
              <p class="text-xs text-gray-500 mt-1 line-clamp-1">{{ req.description }}</p>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <span :class="priorityBadge(req.priority)" class="text-micro">{{ req.priority }}</span>
              <span :class="statusBadge(req.status)" class="text-micro">{{ req.status?.replace('_', ' ') }}</span>
            </div>
          </div>
          <div class="flex items-center gap-3 mt-2 text-xs text-gray-400">
            <span class="flex items-center gap-1"><Clock :size="10" /> {{ formatDateTime(req.created_at) }}</span>
            <span v-if="req.tenant_name" class="flex items-center gap-1"><User :size="10" /> {{ req.tenant_name }}</span>
            <span v-if="req.supplier_name" class="flex items-center gap-1"><Truck :size="10" /> {{ req.supplier_name }}</span>
            <span v-if="req.activity_count" class="flex items-center gap-1"><MessageCircle :size="10" /> {{ req.activity_count }}</span>
          </div>
        </button>

        <div v-if="!requests.length" class="text-center text-gray-400 py-16">
          No maintenance requests for this filter
        </div>
      </div>

      <!-- Right: detail panel -->
      <div v-if="selected" class="min-w-0">
        <div class="card sticky top-5 min-h-[70vh] max-h-[calc(100vh-7rem)] overflow-hidden flex flex-col">

          <!-- Header -->
          <div class="px-5 py-4 border-b border-gray-100 space-y-3">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="text-xs font-mono text-gray-500">#{{ selected.id }}</div>
                <h2 class="text-base font-semibold text-gray-900 mt-1">{{ selected.title }}</h2>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <span :class="priorityBadge(selected.priority)">{{ selected.priority }}</span>
                <button @click="selected = null" class="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
                  <X :size="16" />
                </button>
              </div>
            </div>
          </div>

          <!-- Scrollable detail content -->
          <div class="flex-1 min-h-0 overflow-y-auto px-5 py-4 space-y-5">

            <!-- Description -->
            <p class="text-sm text-gray-600 whitespace-pre-wrap">{{ selected.description || '—' }}</p>

            <!-- Status + Supplier -->
            <div class="grid sm:grid-cols-2 gap-3">
              <div>
                <label class="label text-xs">Status</label>
                <select
                  :value="selected.status"
                  @change="updateStatus(selected, ($event.target as HTMLSelectElement).value)"
                  class="input text-sm"
                >
                  <option v-for="s in statusOptions" :key="s" :value="s">{{ s.replace('_', ' ') }}</option>
                </select>
              </div>
              <div>
                <label class="label text-xs">Supplier</label>
                <select
                  :value="selected.supplier ?? ''"
                  @change="assignSupplier(selected, ($event.target as HTMLSelectElement).value)"
                  class="input text-sm"
                >
                  <option value="">Unassigned</option>
                  <option v-for="s in suppliers" :key="s.id" :value="s.id">
                    {{ s.display_name || s.name }}
                  </option>
                </select>
              </div>
            </div>

            <!-- Info -->
            <div class="grid sm:grid-cols-2 gap-3 text-sm">
              <div>
                <span class="text-gray-400 text-xs">Created</span>
                <p class="text-gray-800">{{ formatDate(selected.created_at) }}</p>
              </div>
              <div>
                <span class="text-gray-400 text-xs">Updated</span>
                <p class="text-gray-800">{{ formatDate(selected.updated_at) }}</p>
              </div>
            </div>

            <!-- Issue Chat -->
            <div class="border-t border-gray-100 pt-4">
              <div class="flex items-center justify-between mb-3">
                <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wide">Support Chat</h3>
                <span class="text-xs text-gray-400">Type @agent to invoke AI</span>
              </div>
              <div
                ref="chatContainer"
                class="max-h-[50vh] min-h-[200px] overflow-y-auto border border-gray-100 rounded-lg p-3 space-y-2 bg-gray-50 mb-3"
              >
                <div v-if="chatLoading" class="text-xs text-gray-400 text-center py-4">Loading chat…</div>
                <div v-else-if="!chatMessages.length" class="text-xs text-gray-400 text-center py-4">
                  No messages yet. Start the conversation below.
                </div>
                <template v-else>
                  <!-- Historic tenant chat banner -->
                  <div
                    v-if="chatMessages.some(m => m.metadata?.chat_source === 'tenant_chat')"
                    class="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-md px-3 py-1.5 text-center mb-1"
                  >
                    Tenant conversation history from AI chat
                  </div>
                  <div
                    v-for="(msg, idx) in chatMessages"
                    :key="msg.id"
                  >
                    <!-- Divider between historic chat and live ticket messages -->
                    <div
                      v-if="idx > 0
                        && chatMessages[idx - 1]?.metadata?.chat_source === 'tenant_chat'
                        && msg.metadata?.chat_source !== 'tenant_chat'"
                      class="flex items-center gap-2 py-2"
                    >
                      <div class="flex-1 border-t border-gray-200" />
                      <span class="text-micro text-gray-400 shrink-0">Ticket opened — live chat below</span>
                      <div class="flex-1 border-t border-gray-200" />
                    </div>
                    <div
                      class="text-sm rounded-lg p-2"
                      :class="[
                        msg.metadata?.source === 'ai_agent'
                          ? 'bg-indigo-50 text-indigo-900 mr-4 border border-indigo-200'
                          : msg.created_by_role === 'tenant'
                            ? 'bg-blue-100 text-blue-900 mr-4'
                            : 'bg-white text-gray-800 ml-4 border border-gray-200',
                        msg.metadata?.chat_source === 'tenant_chat' ? 'opacity-80' : '',
                      ]"
                    >
                      <div class="text-xs font-semibold mb-0.5"
                        :class="msg.metadata?.source === 'ai_agent'
                          ? 'text-indigo-600'
                          : msg.created_by_role === 'tenant'
                            ? 'text-blue-600'
                            : 'text-gray-500'">
                        {{ msg.metadata?.source === 'ai_agent' ? 'AI Agent' : (msg.created_by_name || 'System') }}
                        <span class="font-normal text-gray-400 ml-1">{{ formatTime(msg.created_at) }}</span>
                      </div>
                      <div class="whitespace-pre-wrap">{{ msg.message }}</div>
                    </div>
                  </div>
                </template>
              </div>
              <div class="flex gap-2">
                <input
                  v-model="chatInput"
                  type="text"
                  class="input flex-1 text-sm"
                  placeholder="Type a message… (use @agent to invoke AI)"
                  :disabled="chatSending"
                  @keydown.enter="sendChatMessage"
                />
                <button
                  type="button"
                  class="btn-primary text-sm px-3"
                  :disabled="chatSending || !chatInput.trim()"
                  @click="sendChatMessage"
                >
                  <Send :size="14" />
                </button>
              </div>
            </div>

            <!-- Get Quotes section -->
            <div class="border-t border-gray-100 pt-4">
              <div class="flex items-center justify-between mb-3">
                <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wide">Quotes</h3>
                <button
                  v-if="selected.status === 'open' || selected.status === 'in_progress'"
                  @click="getQuotes(selected)"
                  :disabled="dispatching"
                  class="text-xs text-navy hover:underline flex items-center gap-1"
                >
                  <Send :size="12" />
                  {{ dispatching ? 'Loading…' : 'Get Quotes' }}
                </button>
              </div>

              <!-- Show existing dispatch quotes if any -->
              <div v-if="dispatchData" class="space-y-2">
                <div class="flex items-center gap-2 mb-2">
                  <span :class="dispatchStatusBadge(dispatchData.status)">{{ dispatchData.status }}</span>
                  <span class="text-xs text-gray-400">{{ dispatchData.quote_requests?.length || 0 }} supplier(s)</span>
                </div>
                <div v-for="qr in dispatchData.quote_requests" :key="qr.id"
                  class="p-3 rounded-lg border border-gray-200 space-y-1"
                  :class="qr.status === 'awarded' ? 'bg-green-50 border-green-200' : ''">
                  <div class="flex items-center justify-between">
                    <span class="text-sm font-medium text-gray-800">{{ qr.supplier_name }}</span>
                    <span :class="quoteStatusBadge(qr.status)" class="text-micro">{{ qr.status }}</span>
                  </div>
                  <div v-if="qr.quote" class="flex items-center gap-4 text-sm">
                    <span class="font-medium text-gray-900">R{{ Number(qr.quote.amount).toLocaleString() }}</span>
                    <span v-if="qr.quote.estimated_days" class="text-gray-500">{{ qr.quote.estimated_days }} days</span>
                    <span v-if="qr.quote.available_from" class="text-gray-500">from {{ qr.quote.available_from }}</span>
                  </div>
                  <div v-if="qr.quote?.description" class="text-xs text-gray-500">{{ qr.quote.description }}</div>
                  <button
                    v-if="qr.quote && qr.status === 'quoted' && dispatchData.status !== 'awarded'"
                    @click="awardQuote(qr)"
                    class="mt-1 px-3 py-1 text-xs font-medium text-white bg-green-600 rounded-lg hover:bg-green-700"
                  >
                    Award Job
                  </button>
                </div>
                <p v-if="!dispatchData.quote_requests?.length" class="text-xs text-gray-400">No suppliers invited yet</p>
              </div>
              <p v-else class="text-xs text-gray-400">No dispatch yet — click "Get Quotes" to start</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Dispatch dialog — ranked suppliers + select & send -->
    <BaseModal :open="dispatchDialog" title="Dispatch to Suppliers" size="lg" @close="dispatchDialog = false">
      <template #header>
        <div>
          <h2 class="font-semibold text-gray-900">Get Quotes — {{ selected?.title }}</h2>
          <p class="text-xs text-gray-500 mt-0.5">Select suppliers to send quote requests to</p>
        </div>
      </template>

      <!-- Supplier ranking -->
      <div class="space-y-2">
        <div v-for="(s, idx) in suggestions" :key="s.supplier_id"
          class="flex items-center gap-3 p-3 rounded-lg border transition-colors cursor-pointer"
          :class="selectedSupplierIds.has(s.supplier_id)
            ? 'border-navy bg-navy/5'
            : 'border-gray-200 hover:border-gray-300'"
          @click="toggleSupplierSelection(s.supplier_id)"
        >
          <input type="checkbox" :checked="selectedSupplierIds.has(s.supplier_id)"
            class="rounded" @click.stop="toggleSupplierSelection(s.supplier_id)" />
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="font-medium text-gray-900 text-sm">{{ s.supplier_name }}</span>
              <span class="text-xs text-gray-400">{{ s.supplier_city }}</span>
              <span v-if="idx === 0" class="badge-green text-micro">Best match</span>
            </div>
            <div class="flex items-center gap-3 mt-1 text-xs text-gray-500">
              <span v-if="s.reasons?.proximity?.distance_km" class="flex items-center gap-1">
                <MapPin :size="10" /> {{ s.reasons.proximity.distance_km }}km
              </span>
              <span v-for="t in s.trades?.slice(0, 3)" :key="t"
                class="px-1 py-0.5 bg-blue-50 text-blue-700 rounded text-micro">
                {{ t }}
              </span>
            </div>
          </div>
          <div class="text-right">
            <div class="text-sm font-mono font-medium text-navy">{{ s.score }}</div>
            <div class="text-micro text-gray-400">score</div>
          </div>
        </div>
      </div>

      <div v-if="!suggestions.length" class="text-center text-gray-400 py-8">
        No active suppliers found
      </div>

      <div class="mt-4">
        <label class="label">Notes to suppliers (optional)</label>
        <textarea v-model="dispatchNotes" class="input" rows="2" placeholder="Access instructions, urgency details…"></textarea>
      </div>

      <template #footer>
        <button class="btn-ghost" @click="dispatchDialog = false">Cancel</button>
        <button class="btn-primary" :disabled="!selectedSupplierIds.size || sending"
          @click="sendDispatch">
          <Loader2 v-if="sending" :size="14" class="animate-spin" />
          <Send v-else :size="14" />
          Send to {{ selectedSupplierIds.size }} supplier(s)
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import api from '../../api'
import { Clock, Truck, Send, X, Loader2, MapPin, Archive, MessageCircle, User } from 'lucide-vue-next'
import FilterPills from '../../components/FilterPills.vue'
import BaseModal from '../../components/BaseModal.vue'
import { useToast } from '../../composables/useToast'

const toast = useToast()

const loading = ref(true)
const activeFilter = ref('all')
const requests = ref<any[]>([])
const suppliers = ref<any[]>([])
const selected = ref<any | null>(null)
const dispatchData = ref<any | null>(null)
const statusOptions = ['open', 'in_progress', 'resolved', 'closed']

// Dispatch state
const dispatching = ref(false)
const dispatchDialog = ref(false)
const suggestions = ref<any[]>([])
const selectedSupplierIds = ref(new Set<number>())
const dispatchNotes = ref('')
const sending = ref(false)

// Issue chat state
const chatMessages = ref<any[]>([])
const chatLoading = ref(false)
const chatSending = ref(false)
const chatInput = ref('')
const chatContainer = ref<HTMLElement | null>(null)
let chatSocket: WebSocket | null = null
let listSocket: WebSocket | null = null

const activeTab = ref<'active' | 'archived'>('active')

const filterOptions = computed(() =>
  activeTab.value === 'archived'
    ? [{ label: 'All Closed', value: 'all' }]
    : [
        { label: 'All', value: 'all' },
        { label: 'Open', value: 'open' },
        { label: 'In Progress', value: 'in_progress' },
        { label: 'Resolved', value: 'resolved' },
      ]
)

function switchTab(tab: 'active' | 'archived') {
  activeTab.value = tab
  activeFilter.value = 'all'
  selected.value = null
  loadRequests()
}

onMounted(async () => {
  await Promise.all([loadRequests(), loadSuppliers()])
  connectListSocket()
})

function getWsBase() {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL
  const apiUrl = import.meta.env.VITE_API_URL || ''
  if (apiUrl) {
    // Derive WS URL from API URL (http://localhost:8000/api/v1 → ws://localhost:8000)
    return apiUrl.replace(/^http/, 'ws').replace(/\/api\/v1\/?$/, '')
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}`
}

function connectListSocket() {
  const host = getWsBase()
  const token = localStorage.getItem('access_token') || ''
  listSocket = new WebSocket(`${host}/ws/maintenance/updates/?token=${token}`)

  listSocket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.event === 'issue_created' || data.event === 'issue_updated') {
      // Auto-refresh the issue list
      loadRequests()
      // If currently viewing this issue, refresh its detail too
      if (selected.value?.id === data.request_id) {
        selectRequest(selected.value)
      }
    } else if (data.event === 'activity_created') {
      // If viewing the affected issue, reload its chat
      if (selected.value?.id === data.request_id) {
        loadChat(data.request_id)
      }
    }
  }

  listSocket.onerror = () => {
    console.warn('Maintenance list WebSocket failed')
  }

  // Reconnect on close
  listSocket.onclose = () => {
    setTimeout(() => {
      if (!listSocket || listSocket.readyState === WebSocket.CLOSED) {
        connectListSocket()
      }
    }, 5000)
  }
}

async function loadSuppliers() {
  try {
    const { data } = await api.get('/maintenance/suppliers/', { params: { is_active: true } })
    suppliers.value = data.results ?? data
  } catch { /* ignore */ }
}

async function loadRequests() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (activeTab.value === 'archived') {
      params.status = 'closed'
    } else if (activeFilter.value !== 'all') {
      params.status = activeFilter.value
    } else {
      params.exclude_status = 'closed'
    }
    const { data } = await api.get('/maintenance/', { params })
    requests.value = data.results ?? data
  } finally {
    loading.value = false
  }
}

async function selectRequest(req: any) {
  selected.value = { ...req }
  dispatchData.value = null
  // Try to load existing dispatch
  try {
    const { data } = await api.get(`/maintenance/${req.id}/dispatch/`)
    dispatchData.value = data
  } catch { /* no dispatch yet */ }
  // Load and connect to issue chat
  await loadChat(req.id)
  connectChatSocket(req.id)
}

async function loadChat(requestId: number) {
  chatLoading.value = true
  chatMessages.value = []
  try {
    const { data } = await api.get(`/maintenance/${requestId}/activity/`)
    chatMessages.value = Array.isArray(data) ? data : data.results ?? []
  } catch { /* no activities yet */ }
  chatLoading.value = false
  scrollChatToBottom()
}

function connectChatSocket(requestId: number) {
  disconnectChatSocket()
  const host = getWsBase()
  const token = localStorage.getItem('access_token') || ''
  chatSocket = new WebSocket(`${host}/ws/maintenance/${requestId}/activity/?token=${token}`)

  chatSocket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'history') {
      chatMessages.value = data.activities || []
      scrollChatToBottom()
    } else if (data.type === 'activity' && data.activity) {
      // Avoid duplicates
      if (!chatMessages.value.some((m: any) => m.id === data.activity.id)) {
        chatMessages.value.push(data.activity)
        scrollChatToBottom()
      }
    }
  }

  chatSocket.onerror = () => {
    // Fall back to REST polling if WebSocket fails
    console.warn('WebSocket connection failed, using REST fallback')
  }
}

function disconnectChatSocket() {
  if (chatSocket) {
    chatSocket.close()
    chatSocket = null
  }
}

async function sendChatMessage() {
  const msg = chatInput.value.trim()
  if (!msg || chatSending.value || !selected.value) return

  chatSending.value = true
  chatInput.value = ''

  // Try WebSocket first
  if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
    chatSocket.send(JSON.stringify({ message: msg, activity_type: 'note' }))
    chatSending.value = false
    return
  }

  // Fall back to REST
  try {
    const { data } = await api.post(`/maintenance/${selected.value.id}/activity/`, {
      message: msg,
      activity_type: 'note',
    })
    chatMessages.value.push(data)
    scrollChatToBottom()
  } catch (e: any) {
    toast.error('Failed to send message')
    chatInput.value = msg // Restore
  } finally {
    chatSending.value = false
  }
}

function scrollChatToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

function formatTime(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' })
    + ' ' + d.toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })
}

// Clean up WebSockets on unmount
onUnmounted(() => {
  disconnectChatSocket()
  if (listSocket) {
    listSocket.onclose = null  // Prevent reconnect
    listSocket.close()
    listSocket = null
  }
})

// Disconnect stale chat socket when selection changes
// (selectRequest() will open a new one — no need to reconnect here)
watch(() => selected.value?.id, (newId, oldId) => {
  if (oldId && newId !== oldId) {
    disconnectChatSocket()
  }
})

async function updateStatus(req: any, newStatus: string) {
  await api.patch(`/maintenance/${req.id}/`, { status: newStatus })
  req.status = newStatus
  selected.value = { ...req, status: newStatus }
  // Update in list too
  const idx = requests.value.findIndex((r: any) => r.id === req.id)
  if (idx >= 0) requests.value[idx].status = newStatus
}

async function assignSupplier(req: any, supplierId: string) {
  const value = supplierId ? Number(supplierId) : null
  await api.patch(`/maintenance/${req.id}/`, { supplier: value })
  const sup = suppliers.value.find((s: any) => s.id === value)
  const name = sup ? (sup.display_name || sup.name) : null
  selected.value = { ...req, supplier: value, supplier_name: name }
  const idx = requests.value.findIndex((r: any) => r.id === req.id)
  if (idx >= 0) {
    requests.value[idx].supplier = value
    requests.value[idx].supplier_name = name
  }
}

async function getQuotes(req: any) {
  dispatching.value = true
  try {
    const { data } = await api.post(`/maintenance/${req.id}/dispatch/`)
    dispatchData.value = data.dispatch
    suggestions.value = data.suggestions || []
    selectedSupplierIds.value = new Set(
      suggestions.value.slice(0, 3).map((s: any) => s.supplier_id)
    )
    dispatchNotes.value = ''
    dispatchDialog.value = true
  } finally {
    dispatching.value = false
  }
}

function toggleSupplierSelection(id: number) {
  if (selectedSupplierIds.value.has(id)) selectedSupplierIds.value.delete(id)
  else selectedSupplierIds.value.add(id)
}

async function sendDispatch() {
  if (!selected.value || !selectedSupplierIds.value.size) return
  sending.value = true
  try {
    const { data } = await api.post(`/maintenance/${selected.value.id}/dispatch/send/`, {
      supplier_ids: Array.from(selectedSupplierIds.value),
      notes: dispatchNotes.value,
    })
    dispatchData.value = data.dispatch
    dispatchDialog.value = false
    toast.success('Dispatch sent successfully')
  } catch {
    toast.error('Failed to dispatch')
  } finally {
    sending.value = false
  }
}

async function awardQuote(qr: any) {
  if (!selected.value) return
  if (!confirm(`Award this job to ${qr.supplier_name} for R${qr.quote.amount}?`)) return
  const { data } = await api.post(`/maintenance/${selected.value.id}/dispatch/award/`, {
    quote_request_id: qr.id,
  })
  dispatchData.value = data
  await loadRequests()
}

function priorityBadge(p: string) {
  return { urgent: 'badge-red', high: 'badge-amber', medium: 'badge-blue', low: 'badge-green' }[p] ?? 'badge-gray'
}

function priorityBorderLeft(p: string) {
  return {
    urgent: 'border-l-red-500',
    high: 'border-l-amber-400',
    medium: 'border-l-blue-400',
    low: 'border-l-green-400',
  }[p] ?? 'border-l-gray-300'
}

function statusBadge(s: string) {
  return { open: 'badge-blue', in_progress: 'badge-amber', resolved: 'badge-green', closed: 'badge-gray' }[s] ?? 'badge-gray'
}

function dispatchStatusBadge(s: string) {
  return { draft: 'badge-gray', sent: 'badge-blue', quoting: 'badge-amber', awarded: 'badge-green', cancelled: 'badge-gray' }[s] ?? 'badge-gray'
}

function quoteStatusBadge(s: string) {
  return { pending: 'badge-gray', viewed: 'badge-blue', quoted: 'badge-amber', declined: 'badge-red', awarded: 'badge-green', expired: 'badge-gray' }[s] ?? 'badge-gray'
}

function formatDate(iso: string) {
  return iso ? new Date(iso).toLocaleDateString('en-ZA') : '—'
}

function formatDateTime(iso: string) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('en-ZA') + ' ' + d.toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' })
}
</script>
