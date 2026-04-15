<template>
  <div class="space-y-5">
    <!-- Loading -->
    <div v-if="loading" class="card p-5 space-y-3 animate-pulse">
      <div class="h-3 bg-gray-100 rounded w-1/4"></div>
      <div class="h-5 bg-gray-100 rounded w-1/2"></div>
      <div class="h-3 bg-gray-100 rounded w-full"></div>
    </div>

    <!-- Not found -->
    <EmptyState
      v-else-if="!issue"
      title="Issue not found"
      :icon="AlertCircle"
    />

    <!-- Detail content -->
    <template v-else>
      <!-- Header -->
      <PageHeader
        :title="issue.title"
        :subtitle="issue.ticket_reference || `#${issue.id}`"
        :crumbs="[
          { label: 'Dashboard', to: '/' },
          { label: 'Maintenance', to: '/maintenance/issues' },
          { label: 'Issues', to: '/maintenance/issues' },
          { label: issue.ticket_reference || `#${issue.id}` },
        ]"
        back
      >
        <template #actions>
          <span :class="priorityBadge(issue.priority)">{{ issue.priority }}</span>
        </template>
      </PageHeader>

      <!-- Two-column layout: info left, chat right -->
      <div class="grid lg:grid-cols-[1fr_1fr] gap-5 items-start">

        <!-- Left column: details + quotes -->
        <div class="space-y-5 min-w-0">
          <!-- Description -->
          <div class="card px-5 py-4">
            <p class="text-sm text-gray-600 whitespace-pre-wrap">{{ issue.description || '—' }}</p>
          </div>

          <!-- Status -->
          <div class="card px-5 py-4">
            <label class="label text-xs">Status</label>
            <select
              :value="issue.status"
              @change="updateStatus(($event.target as HTMLSelectElement).value)"
              class="input text-sm"
            >
              <option v-for="s in statusOptions" :key="s" :value="s">{{ s.replace('_', ' ') }}</option>
            </select>
          </div>

          <!-- Supplier -->
          <div class="card px-5 py-4">
            <label class="label text-xs">Supplier</label>
            <select
              :value="issue.supplier ?? ''"
              @change="assignSupplier(($event.target as HTMLSelectElement).value)"
              class="input text-sm"
            >
              <option value="">Unassigned</option>
              <option v-for="s in suppliers" :key="s.id" :value="s.id">
                {{ s.display_name || s.name }}
              </option>
            </select>
          </div>

          <!-- Timestamps -->
          <div class="card px-5 py-4">
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span class="text-gray-400 text-xs">Created</span>
                <p class="text-gray-800">{{ formatDate(issue.created_at) }}</p>
              </div>
              <div>
                <span class="text-gray-400 text-xs">Updated</span>
                <p class="text-gray-800">{{ formatDate(issue.updated_at) }}</p>
              </div>
            </div>
          </div>

          <!-- Quotes -->
          <div class="card px-5 py-4">
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wide">Quotes</h3>
              <button
                v-if="issue.status === 'open' || issue.status === 'in_progress'"
                @click="getQuotes"
                :disabled="dispatching"
                class="text-xs text-navy hover:underline flex items-center gap-1"
              >
                <Send :size="12" />
                {{ dispatching ? 'Loading…' : 'Get Quotes' }}
              </button>
            </div>
            <div v-if="dispatchData" class="space-y-2">
              <div class="flex items-center gap-2 mb-2">
                <span :class="dispatchStatusBadge(dispatchData.status)">{{ dispatchData.status }}</span>
                <span class="text-xs text-gray-400">{{ dispatchData.quote_requests?.length || 0 }} supplier(s)</span>
              </div>
              <div v-for="qr in dispatchData.quote_requests" :key="qr.id"
                class="p-3 rounded-lg border border-gray-200 space-y-1"
                :class="qr.status === 'awarded' ? 'bg-success-50 border-success-100' : ''">
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
                  class="btn-success btn-sm mt-1"
                >
                  Award Job
                </button>
              </div>
              <p v-if="!dispatchData.quote_requests?.length" class="text-xs text-gray-400">No suppliers invited yet</p>
            </div>
            <p v-else class="text-xs text-gray-400">No dispatch yet — click "Get Quotes" to start</p>
          </div>
        </div>

        <!-- Right column: chat (pinned to viewport on desktop) -->
        <div class="card px-5 py-4 lg:sticky lg:top-5 flex flex-col overflow-hidden" style="height: calc(100vh - 11rem);">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wide">Support Chat</h3>
            <span class="text-xs text-gray-400">Type @agent to invoke AI</span>
          </div>
          <div
            ref="chatContainer"
            class="flex-1 min-h-[200px] overflow-y-auto border border-gray-100 rounded-lg p-3 space-y-2 bg-gray-50 mb-3"
          >
            <div v-if="chatLoading" class="text-xs text-gray-400 text-center py-4">Loading chat…</div>
            <div v-else-if="!chatMessages.length" class="text-xs text-gray-400 text-center py-4">
              No messages yet. Start the conversation below.
            </div>
            <template v-else>
              <div
                v-if="chatMessages.some(m => m.metadata?.chat_source === 'tenant_chat')"
                class="text-xs text-warning-700 bg-warning-50 border border-warning-100 rounded-md px-3 py-1.5 text-center mb-1"
              >
                Tenant conversation history from AI chat
              </div>
              <div
                v-for="(msg, idx) in chatMessages"
                :key="msg.id"
              >
                <div
                  v-if="idx > 0
                    && chatMessages[idx - 1]?.metadata?.chat_source === 'tenant_chat'
                    && msg.metadata?.chat_source !== 'tenant_chat'"
                  class="flex items-center gap-2 py-2"
                >
                  <div class="flex-1 border-t border-gray-200"></div>
                  <span class="text-micro text-gray-400 shrink-0">Ticket opened — live chat below</span>
                  <div class="flex-1 border-t border-gray-200"></div>
                </div>
                <div
                  class="text-sm rounded-lg p-2"
                  :class="[
                    msg.metadata?.source === 'ai_agent'
                      ? 'bg-navy/5 text-navy mr-4 border border-navy/10'
                      : msg.created_by_role === 'tenant'
                        ? 'bg-info-100 text-info-700 mr-4'
                        : 'bg-white text-gray-800 ml-4 border border-gray-200',
                    msg.metadata?.chat_source === 'tenant_chat' ? 'opacity-80' : '',
                  ]"
                >
                  <div class="text-xs font-semibold mb-0.5"
                    :class="msg.metadata?.source === 'ai_agent'
                      ? 'text-navy'
                      : msg.created_by_role === 'tenant'
                        ? 'text-info-600'
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

      </div>
    </template>

    <!-- Dispatch dialog -->
    <BaseModal :open="dispatchDialog" title="Dispatch to Suppliers" size="lg" @close="dispatchDialog = false">
      <template #header>
        <div>
          <h2 class="font-semibold text-gray-900">Get Quotes — {{ issue?.title }}</h2>
          <p class="text-xs text-gray-500 mt-0.5">Select suppliers to send quote requests to</p>
        </div>
      </template>

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
                class="px-1 py-0.5 bg-info-50 text-info-700 rounded text-micro">
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
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../api'
import { ArrowLeft, Send, Loader2, MapPin, AlertCircle } from 'lucide-vue-next'
import EmptyState from '../../components/EmptyState.vue'
import BaseModal from '../../components/BaseModal.vue'
import PageHeader from '../../components/PageHeader.vue'
import { useToast } from '../../composables/useToast'

const route = useRoute()
const toast = useToast()

const loading = ref(true)
const issue = ref<any | null>(null)
const suppliers = ref<any[]>([])
const statusOptions = ['open', 'in_progress', 'resolved', 'closed']

// Dispatch state
const dispatchData = ref<any | null>(null)
const dispatching = ref(false)
const dispatchDialog = ref(false)
const suggestions = ref<any[]>([])
const selectedSupplierIds = ref(new Set<number>())
const dispatchNotes = ref('')
const sending = ref(false)

// Chat state
const chatMessages = ref<any[]>([])
const chatLoading = ref(false)
const chatSending = ref(false)
const chatInput = ref('')
const chatContainer = ref<HTMLElement | null>(null)
let chatSocket: WebSocket | null = null

// ── Lifecycle ────────────────────────────────────────────────────────────────

onMounted(async () => {
  const id = Number(route.params.id)
  await Promise.all([loadIssue(id), loadSuppliers()])
  loading.value = false
})

onUnmounted(() => {
  disconnectChatSocket()
})

// ── Data loading ─────────────────────────────────────────────────────────────

async function loadIssue(id: number) {
  try {
    const { data } = await api.get(`/maintenance/${id}/`)
    issue.value = data
    // Load dispatch info
    try {
      const { data: dispatch } = await api.get(`/maintenance/${id}/dispatch/`)
      dispatchData.value = dispatch
    } catch { /* no dispatch yet */ }
    // Load chat + connect WebSocket
    await loadChat(id)
    connectChatSocket(id)
  } catch {
    issue.value = null
  }
}

async function loadSuppliers() {
  try {
    const { data } = await api.get('/maintenance/suppliers/', { params: { is_active: true } })
    suppliers.value = data.results ?? data
  } catch { /* ignore */ }
}

// ── Status & Supplier ────────────────────────────────────────────────────────

async function updateStatus(newStatus: string) {
  if (!issue.value) return
  await api.patch(`/maintenance/${issue.value.id}/`, { status: newStatus })
  issue.value = { ...issue.value, status: newStatus }
}

async function assignSupplier(supplierId: string) {
  if (!issue.value) return
  const value = supplierId ? Number(supplierId) : null
  await api.patch(`/maintenance/${issue.value.id}/`, { supplier: value })
  const sup = suppliers.value.find((s: any) => s.id === value)
  const name = sup ? (sup.display_name || sup.name) : null
  issue.value = { ...issue.value, supplier: value, supplier_name: name }
}

// ── Chat ─────────────────────────────────────────────────────────────────────

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

function getWsBase() {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL
  const apiUrl = import.meta.env.VITE_API_URL || ''
  if (apiUrl) {
    return apiUrl.replace(/^http/, 'ws').replace(/\/api\/v1\/?$/, '')
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}`
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
      if (!chatMessages.value.some((m: any) => m.id === data.activity.id)) {
        chatMessages.value.push(data.activity)
        scrollChatToBottom()
      }
    }
  }

  chatSocket.onerror = () => {
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
  if (!msg || chatSending.value || !issue.value) return

  chatSending.value = true
  chatInput.value = ''

  if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
    chatSocket.send(JSON.stringify({ message: msg, activity_type: 'note' }))
    chatSending.value = false
    return
  }

  try {
    const { data } = await api.post(`/maintenance/${issue.value.id}/activity/`, {
      message: msg,
      activity_type: 'note',
    })
    chatMessages.value.push(data)
    scrollChatToBottom()
  } catch (e: any) {
    toast.error('Failed to send message')
    chatInput.value = msg
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

// ── Dispatch ─────────────────────────────────────────────────────────────────

async function getQuotes() {
  if (!issue.value) return
  dispatching.value = true
  try {
    const { data } = await api.post(`/maintenance/${issue.value.id}/dispatch/`)
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
  if (!issue.value || !selectedSupplierIds.value.size) return
  sending.value = true
  try {
    const { data } = await api.post(`/maintenance/${issue.value.id}/dispatch/send/`, {
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
  if (!issue.value) return
  if (!confirm(`Award this job to ${qr.supplier_name} for R${qr.quote.amount}?`)) return
  const { data } = await api.post(`/maintenance/${issue.value.id}/dispatch/award/`, {
    quote_request_id: qr.id,
  })
  dispatchData.value = data
}

// ── Formatting ───────────────────────────────────────────────────────────────

function priorityBadge(p: string) {
  return { urgent: 'badge-red', high: 'badge-amber', medium: 'badge-blue', low: 'badge-green' }[p] ?? 'badge-gray'
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

function formatTime(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' })
    + ' ' + d.toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })
}
</script>
