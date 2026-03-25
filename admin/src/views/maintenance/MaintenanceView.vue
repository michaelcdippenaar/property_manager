<template>
  <div class="flex gap-5" style="height: calc(100vh - 8rem)">

    <!-- ── Left: request list ───────────────────────────────────────────── -->
    <div class="flex flex-col gap-4 min-w-0" style="flex: 0 0 50%">
      <div class="flex items-center justify-between">
        <h1 class="text-base font-semibold text-gray-900">Maintenance</h1>
        <span class="text-xs text-gray-400">{{ requests.length }} requests</span>
      </div>

      <div class="flex gap-1.5 flex-wrap">
        <button
          v-for="f in filters"
          :key="f.value"
          @click="activeFilter = f.value; loadRequests()"
          class="px-2.5 py-1 rounded-full text-xs font-medium transition-colors"
          :class="activeFilter === f.value
            ? 'bg-navy text-white'
            : 'bg-white border border-gray-200 text-gray-600 hover:border-gray-300'"
        >{{ f.label }}</button>
      </div>

      <!-- Skeleton -->
      <div v-if="loading" class="space-y-2">
        <div v-for="i in 5" :key="i" class="card p-4 space-y-2 animate-pulse">
          <div class="h-3 bg-gray-100 rounded w-1/3"></div>
          <div class="h-4 bg-gray-100 rounded w-2/3"></div>
          <div class="h-3 bg-gray-100 rounded w-full"></div>
        </div>
      </div>

      <!-- Cards -->
      <div v-else class="space-y-2 overflow-y-auto flex-1 pr-1">
        <div
          v-for="req in requests"
          :key="req.id"
          @click="select(req)"
          class="card p-4 cursor-pointer transition-all"
          :class="selected?.id === req.id ? 'ring-2 ring-navy bg-navy/5' : 'hover:shadow-md'"
        >
          <div class="flex items-start justify-between gap-2 mb-2">
            <span :class="priorityBadge(req.priority)" class="text-xs">{{ req.priority }}</span>
            <span class="text-xs px-1.5 py-0.5 rounded font-medium" :class="statusClass(req.status)">
              {{ req.status.replace('_', ' ') }}
            </span>
          </div>
          <div class="text-sm font-medium text-gray-900 leading-snug line-clamp-2 mb-1.5">{{ req.title }}</div>
          <div class="flex items-center gap-1.5 text-xs text-gray-400">
            <Clock :size="11" />
            {{ formatDate(req.created_at) }}
            <span v-if="req.supplier_name" class="text-gray-300">·</span>
            <span v-if="req.supplier_name" class="truncate">{{ req.supplier_name }}</span>
          </div>
        </div>
        <div v-if="!requests.length" class="text-center text-gray-400 py-12 text-sm">No requests for this filter</div>
      </div>
    </div>

    <!-- ── Right: detail + chat panel ──────────────────────────────────── -->
    <div class="flex-1 min-w-0 flex flex-col overflow-hidden">
      <div v-if="!selected" class="flex flex-col items-center justify-center h-full text-gray-400 gap-3">
        <Wrench :size="36" class="text-gray-200" />
        <p class="text-sm">Select a request to view details</p>
      </div>

      <div v-else class="card flex-1 flex flex-col overflow-hidden min-h-0">

        <!-- Top bar -->
        <div class="flex items-start justify-between gap-4 px-6 py-4 border-b border-gray-100 flex-shrink-0">
          <div class="space-y-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span :class="priorityBadge(selected.priority)">{{ selected.priority }}</span>
              <span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="statusClass(selected.status)">
                {{ selected.status.replace('_', ' ') }}
              </span>
              <!-- WS status dot -->
              <span
                class="w-1.5 h-1.5 rounded-full ml-1"
                :class="wsConnected ? 'bg-green-400' : 'bg-gray-300'"
                :title="wsConnected ? 'Live' : 'Connecting…'"
              ></span>
            </div>
            <h2 class="text-sm font-semibold text-gray-900">{{ selected.title }}</h2>
          </div>
          <select
            :value="selected.status"
            @change="updateStatus(selected, ($event.target as HTMLSelectElement).value)"
            class="text-xs border border-gray-200 rounded-lg px-2 py-1.5 text-gray-600 bg-white outline-none focus:ring-1 focus:ring-navy/30 flex-shrink-0"
          >
            <option v-for="s in statusOptions" :key="s" :value="s">{{ s.replace('_', ' ') }}</option>
          </select>
        </div>

        <!-- Scrollable body: meta + dispatch (max 45% height, scrollable) -->
        <div class="px-6 py-4 space-y-4 border-b border-gray-100 overflow-y-auto" style="max-height: 45%">
          <!-- Meta grid -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <div class="text-xs text-gray-400">Reported</div>
              <div class="text-sm font-medium text-gray-700">{{ formatDate(selected.created_at) }}</div>
            </div>
            <div>
              <div class="text-xs text-gray-400">Last updated</div>
              <div class="text-sm font-medium text-gray-700">{{ formatDate(selected.updated_at) }}</div>
            </div>
            <div>
              <div class="text-xs text-gray-400">Unit</div>
              <div class="text-sm font-medium text-gray-700">Unit {{ selected.unit }}</div>
            </div>
            <div>
              <div class="text-xs text-gray-400">Assigned supplier</div>
              <div class="text-sm font-medium text-gray-700">{{ selected.supplier_name || 'Unassigned' }}</div>
            </div>
          </div>

          <!-- Description -->
          <div>
            <div class="text-xs text-gray-400 mb-1">Description</div>
            <p class="text-sm text-gray-700 leading-relaxed">{{ selected.description || '—' }}</p>
          </div>

          <!-- Image -->
          <div v-if="selected.image">
            <img :src="selected.image" class="rounded-lg max-h-40 object-cover border border-gray-100" />
          </div>

          <!-- Dispatch -->
          <div>
            <div class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Dispatch</div>
            <div v-if="loadingDispatch" class="text-xs text-gray-400 animate-pulse">Loading…</div>
            <div v-else-if="dispatch" class="space-y-2">
              <div class="flex items-center gap-2">
                <span
                  class="text-xs px-2 py-0.5 rounded-full font-medium"
                  :class="dispatch.status === 'awarded' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'"
                >{{ dispatch.status }}</span>
                <span class="text-xs text-gray-400">by {{ dispatch.dispatched_by_name }}</span>
              </div>
              <div v-if="dispatch.quote_requests?.length" class="space-y-1.5">
                <div
                  v-for="qr in dispatch.quote_requests"
                  :key="qr.id"
                  class="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2"
                >
                  <div>
                    <div class="text-xs font-medium text-gray-800">{{ qr.supplier_name }}</div>
                    <div class="text-xs text-gray-400">{{ qr.supplier_city }}</div>
                  </div>
                  <div class="text-right">
                    <span
                      class="text-xs px-1.5 py-0.5 rounded font-medium"
                      :class="qr.status === 'accepted' ? 'bg-green-100 text-green-700' : qr.status === 'declined' ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-600'"
                    >{{ qr.status }}</span>
                    <div v-if="qr.quote" class="text-xs font-semibold text-navy">R{{ Number(qr.quote.amount).toLocaleString() }}</div>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="flex items-center gap-1.5 text-xs text-gray-400">
              <AlertCircle :size="12" />No dispatch created yet
            </div>
          </div>
        </div>

        <!-- ── Bottom tabs: Chat | AI Agent ───────────────────────────── -->
        <div class="flex flex-col flex-1 min-h-0">
          <!-- Tab bar -->
          <div class="flex border-b border-gray-100 flex-shrink-0">
            <button
              v-for="tab in ['chat', 'agent']"
              :key="tab"
              @click="activeTab = tab"
              class="flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors"
              :class="activeTab === tab
                ? 'border-navy text-navy'
                : 'border-transparent text-gray-400 hover:text-gray-600'"
            >
              <MessageSquare v-if="tab === 'chat'" :size="12" />
              <Bot v-else :size="12" />
              {{ tab === 'chat' ? 'Chat' : 'AI Agent' }}
              <span v-if="tab === 'chat' && !wsConnected" class="w-1.5 h-1.5 rounded-full bg-gray-300"></span>
              <span v-if="tab === 'chat' && wsConnected" class="w-1.5 h-1.5 rounded-full bg-green-400"></span>
            </button>
          </div>

          <!-- ── CHAT TAB ─────────────────────────────────────────── -->
          <template v-if="activeTab === 'chat'">
            <div ref="threadRef" class="flex-1 overflow-y-auto px-4 py-4 space-y-2">
              <div v-if="!wsConnected && !activities.length" class="text-xs text-gray-400 animate-pulse text-center py-4">Connecting…</div>

              <template v-for="item in activities" :key="item.id">
                <div v-if="item.activity_type !== 'note'" class="flex justify-center my-1">
                  <span class="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 font-medium">
                    {{ item.created_by_name || 'System' }} · {{ item.activity_type.replace(/_/g, ' ') }} · {{ formatTime(item.created_at) }}
                  </span>
                </div>
                <div v-else class="flex gap-2" :class="isTenant(item) ? 'flex-row' : 'flex-row-reverse'">
                  <div
                    class="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5"
                    :class="isTenant(item) ? 'bg-gray-200 text-gray-600' : 'bg-navy text-white'"
                  >{{ avatarInitials(item.created_by_name) }}</div>
                  <div class="max-w-[72%] space-y-0.5" :class="isTenant(item) ? '' : 'items-end flex flex-col'">
                    <div class="text-[10px] text-gray-400 px-1" :class="isTenant(item) ? '' : 'text-right'">
                      {{ item.created_by_name || 'System' }}
                      <span v-if="item.created_by_role" class="ml-1 opacity-60">({{ item.created_by_role }})</span>
                    </div>
                    <div
                      class="px-3 py-2 rounded-2xl text-sm leading-relaxed break-words"
                      :class="isTenant(item) ? 'bg-gray-100 text-gray-800 rounded-tl-sm' : 'bg-navy text-white rounded-tr-sm'"
                    >{{ item.message }}</div>
                    <div class="text-[10px] text-gray-400 px-1" :class="isTenant(item) ? '' : 'text-right'">{{ formatTime(item.created_at) }}</div>
                  </div>
                </div>
              </template>

              <div v-if="wsConnected && !activities.length" class="text-xs text-gray-400 text-center py-6">No messages yet — start the conversation.</div>
            </div>

            <div class="px-4 py-3 border-t border-gray-100 flex-shrink-0 flex gap-2 items-end">
              <textarea
                v-model="newMessage"
                @keydown.enter.exact.prevent="sendMessage"
                placeholder="Type a note… (Enter to send)"
                rows="1"
                class="flex-1 text-sm border border-gray-200 rounded-xl px-3 py-2 outline-none focus:ring-1 focus:ring-navy/30 bg-white resize-none leading-relaxed"
                style="min-height: 38px; max-height: 100px"
              />
              <button
                @click="sendMessage"
                :disabled="!newMessage.trim() || !wsConnected"
                class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-navy text-white text-xs font-medium disabled:opacity-40 hover:bg-navy/90 transition-colors flex-shrink-0"
              >
                <Send :size="13" />
              </button>
            </div>
          </template>

          <!-- ── AI AGENT TAB ─────────────────────────────────────── -->
          <template v-else>
            <div ref="agentThreadRef" class="flex-1 overflow-y-auto px-4 py-4 space-y-3">
              <div v-if="!agentMessages.length" class="flex flex-col items-center justify-center h-full text-center py-8">
                <div class="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center mb-3">
                  <Bot :size="20" class="text-indigo-500" />
                </div>
                <p class="text-xs font-semibold text-gray-700 mb-1">AI Maintenance Agent</p>
                <p class="text-[11px] text-gray-400 max-w-[200px] leading-relaxed">Ask about this issue — the agent sees the full chat history and property context.</p>
                <div class="flex flex-col gap-1.5 mt-4 w-full max-w-[220px]">
                  <button
                    v-for="q in agentQuickPrompts"
                    :key="q"
                    @click="sendAgentMessage(q)"
                    class="text-[11px] text-left px-3 py-2 rounded-lg border border-gray-200 bg-white text-gray-600 hover:border-indigo-300 hover:text-indigo-600 transition-colors"
                  >{{ q }}</button>
                </div>
              </div>

              <div v-for="(msg, i) in agentMessages" :key="i" class="flex gap-2" :class="msg.role === 'user' ? 'flex-row-reverse' : ''">
                <div
                  class="w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                  :class="msg.role === 'user' ? 'bg-navy' : 'bg-indigo-100'"
                >
                  <Bot v-if="msg.role === 'assistant'" :size="12" class="text-indigo-600" />
                  <User v-else :size="12" class="text-white" />
                </div>
                <div
                  class="max-w-[80%] px-3 py-2 rounded-xl text-sm leading-relaxed"
                  :class="msg.role === 'user'
                    ? 'bg-navy text-white rounded-tr-sm'
                    : 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm shadow-sm'"
                  v-html="renderMarkdown(msg.content)"
                />
              </div>

              <div v-if="agentThinking" class="flex gap-2">
                <div class="w-6 h-6 rounded-lg bg-indigo-100 flex items-center justify-center flex-shrink-0">
                  <Bot :size="12" class="text-indigo-600" />
                </div>
                <div class="bg-white border border-gray-200 rounded-xl rounded-tl-sm px-3 py-2.5 shadow-sm">
                  <div class="flex gap-1">
                    <span class="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce" style="animation-delay:0ms"/>
                    <span class="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce" style="animation-delay:150ms"/>
                    <span class="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce" style="animation-delay:300ms"/>
                  </div>
                </div>
              </div>
            </div>

            <div class="px-4 py-3 border-t border-gray-100 flex-shrink-0 flex gap-2 items-end">
              <textarea
                v-model="agentInput"
                @keydown.enter.exact.prevent="sendAgentMessage()"
                placeholder="Ask the AI agent about this issue…"
                rows="1"
                class="flex-1 text-sm border border-gray-200 rounded-xl px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-300 bg-white resize-none leading-relaxed"
                style="min-height: 38px; max-height: 100px"
              />
              <button
                @click="sendAgentMessage()"
                :disabled="!agentInput.trim() || agentThinking"
                class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-indigo-600 text-white text-xs font-medium disabled:opacity-40 hover:bg-indigo-700 transition-colors flex-shrink-0"
              >
                <Send :size="13" />
              </button>
            </div>
          </template>

        </div>

      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'
import { Clock, Wrench, AlertCircle, Send, MessageSquare, Bot, User } from 'lucide-vue-next'

const auth = useAuthStore()

const loading = ref(true)
const loadingDispatch = ref(false)
const activeFilter = ref('all')
const requests = ref<any[]>([])
const selected = ref<any | null>(null)
const dispatch = ref<any | null>(null)
const activities = ref<any[]>([])
const newMessage = ref('')
const threadRef = ref<HTMLElement | null>(null)
const wsConnected = ref(false)
let ws: WebSocket | null = null

const activeTab = ref<'chat' | 'agent'>('chat')
const agentMessages = ref<{ role: 'user' | 'assistant'; content: string }[]>([])
const agentInput = ref('')
const agentThinking = ref(false)
const agentThreadRef = ref<HTMLElement | null>(null)
const agentQuickPrompts = [
  'Summarise this issue',
  'What priority should this be?',
  'Suggest a reply to the tenant',
  'Which supplier should I assign?',
]

const statusOptions = ['open', 'in_progress', 'resolved', 'closed']
const filters = [
  { label: 'All', value: 'all' },
  { label: 'Open', value: 'open' },
  { label: 'In Progress', value: 'in_progress' },
  { label: 'Resolved', value: 'resolved' },
  { label: 'Archived', value: 'closed' },
]

onMounted(() => loadRequests())
onBeforeUnmount(() => closeWs())

async function loadRequests() {
  loading.value = true
  try {
    const params: Record<string, string> = activeFilter.value !== 'all'
      ? { status: activeFilter.value }
      : { exclude_status: 'closed' }
    const { data } = await api.get('/maintenance/', { params })
    requests.value = data.results ?? data
    if (requests.value.length && !selected.value) select(requests.value[0])
  } finally {
    loading.value = false
  }
}

async function select(req: any) {
  selected.value = req
  dispatch.value = null
  activities.value = []
  agentMessages.value = []
  wsConnected.value = false
  closeWs()

  loadingDispatch.value = true
  try {
    const { data } = await api.get(`/maintenance/${req.id}/dispatch/`)
    dispatch.value = data
  } catch { dispatch.value = null }
  finally { loadingDispatch.value = false }

  openWs(req.id)
}

function openWs(requestId: number) {
  const token = auth.accessToken
  const wsUrl = `ws://127.0.0.1:8000/ws/maintenance/${requestId}/activity/?token=${token}`
  ws = new WebSocket(wsUrl)

  ws.onopen = () => { wsConnected.value = true }

  ws.onmessage = async (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'history') {
      activities.value = data.activities
    } else if (data.type === 'activity') {
      activities.value.push(data.activity)
    }
    await nextTick()
    scrollToBottom()
  }

  ws.onclose = () => { wsConnected.value = false }
  ws.onerror = () => { wsConnected.value = false }
}

function closeWs() {
  if (ws) { ws.close(); ws = null }
}

function sendMessage() {
  if (!newMessage.value.trim() || !ws || ws.readyState !== WebSocket.OPEN) return
  ws.send(JSON.stringify({ activity_type: 'note', message: newMessage.value.trim() }))
  newMessage.value = ''
}

function scrollToBottom() {
  if (threadRef.value) threadRef.value.scrollTop = threadRef.value.scrollHeight
}

async function updateStatus(req: any, newStatus: string) {
  await api.patch(`/maintenance/${req.id}/`, { status: newStatus })
  req.status = newStatus
  if (selected.value?.id === req.id) selected.value = { ...req, status: newStatus }
}

async function sendAgentMessage(text?: string) {
  const content = text || agentInput.value.trim()
  if (!content || agentThinking.value) return
  agentMessages.value.push({ role: 'user', content })
  agentInput.value = ''
  agentThinking.value = true
  await nextTick()
  if (agentThreadRef.value) agentThreadRef.value.scrollTop = agentThreadRef.value.scrollHeight

  try {
    const { data } = await api.post('/maintenance/agent-assist/chat/', {
      message: content,
      maintenance_request_id: selected.value?.id,
      history: agentMessages.value.slice(0, -1),
    })
    agentMessages.value.push({ role: 'assistant', content: data.reply })
  } catch (e: any) {
    agentMessages.value.push({ role: 'assistant', content: '_Error reaching AI agent. Please try again._' })
  } finally {
    agentThinking.value = false
    await nextTick()
    if (agentThreadRef.value) agentThreadRef.value.scrollTop = agentThreadRef.value.scrollHeight
  }
}

function renderMarkdown(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n\n/g, '</p><p class="mt-1">')
    .replace(/\n/g, '<br/>')
    .replace(/^/, '<p>')
    .replace(/$/, '</p>')
}

function isTenant(item: any) {
  return item.created_by_role === 'tenant'
}

function avatarInitials(name: string | null) {
  if (!name) return 'SY'
  return name.split(' ').map((w: string) => w[0]).join('').slice(0, 2).toUpperCase()
}

function priorityBadge(p: string) {
  return { urgent: 'badge-red', high: 'badge-amber', medium: 'badge-blue', low: 'badge-green' }[p] ?? 'badge-gray'
}

function statusClass(s: string) {
  return {
    open: 'bg-blue-50 text-blue-700',
    in_progress: 'bg-amber-50 text-amber-700',
    resolved: 'bg-green-50 text-green-700',
    closed: 'bg-gray-100 text-gray-500',
  }[s] ?? 'bg-gray-100 text-gray-500'
}

function activityTypeClass(t: string) {
  return {
    status_change: 'bg-blue-50 text-blue-600',
    supplier_assigned: 'bg-purple-50 text-purple-600',
    dispatch_sent: 'bg-amber-50 text-amber-600',
    quote_received: 'bg-teal-50 text-teal-600',
    job_awarded: 'bg-green-50 text-green-700',
    system: 'bg-gray-100 text-gray-500',
  }[t] ?? 'bg-gray-100 text-gray-500'
}

function formatDate(iso: string) {
  return iso ? new Date(iso).toLocaleDateString('en-ZA') : '—'
}

function formatTime(iso: string) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('en-ZA') + ' ' + d.toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' })
}
</script>
