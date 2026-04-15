<template>
  <q-layout view="hHh lpR fFf">

    <!-- Header -->
    <q-header :elevated="!isIos" :class="headerClass">
      <q-toolbar>
        <q-btn flat round :icon="backIcon" :color="isIos ? 'primary' : 'white'" aria-label="Go back" @click="router.back()" />
        <q-toolbar-title :class="isIos ? 'text-primary text-weight-semibold' : 'text-white text-weight-medium'">
          <div class="ellipsis" style="max-width: 220px">{{ ticket?.title || 'Repair Chat' }}</div>
        </q-toolbar-title>
        <!-- Connection indicator -->
        <q-icon
          v-if="wsDisconnected"
          name="wifi_off"
          color="amber"
          size="20px"
          class="q-mr-sm"
        >
          <q-tooltip>Reconnecting… using offline mode</q-tooltip>
        </q-icon>
        <StatusBadge v-if="ticket" :value="ticket.status" />
      </q-toolbar>
    </q-header>

    <q-page-container>
      <q-page class="column">

        <!-- Loading -->
        <div v-if="loading" class="col column items-center justify-center">
          <q-spinner-dots :size="SPINNER_SIZE_PAGE" color="primary" />
        </div>

        <!-- Chat timeline -->
        <div v-else ref="chatContainer" class="col scroll q-pa-sm" style="overflow-y: auto">

          <!-- Meta bar (collapsible) -->
          <div v-if="ticket" class="text-center q-mb-sm">
            <q-chip
              dense
              clickable
              size="sm"
              color="grey-2"
              text-color="grey-7"
              :icon="metaExpanded ? 'expand_less' : 'expand_more'"
              @click="metaExpanded = !metaExpanded"
            >
              {{ ticket.category }} · {{ priorityLabel }}
            </q-chip>
            <q-slide-transition>
              <div v-show="metaExpanded" class="q-mt-xs text-caption text-grey-6 text-center">
                Created {{ formatDate(ticket.created_at) }}
                <span v-if="ticket.priority"> · Priority: {{ ticket.priority }}</span>
              </div>
            </q-slide-transition>
          </div>

          <!-- AI greeting (for new tickets with no history) -->
          <div v-if="showGreeting" class="row justify-start q-mb-sm">
            <div class="column" style="max-width: 80%">
              <div class="text-caption text-grey-5 q-ml-sm q-mb-xs">AI Assistant</div>
              <div class="chat-bubble-other">
                Ticket #{{ ticketId }} opened. Hi! What maintenance issue would you like to report? You can also send photos to help us assess the problem.
              </div>
            </div>
          </div>

          <!-- Activity messages -->
          <template v-for="activity in activities" :key="activity.id">

            <!-- System chip (status changes, supplier assigned, etc.) -->
            <div v-if="isSystemEvent(activity)" class="text-center q-my-xs">
              <q-chip dense size="sm" color="grey-2" text-color="grey-6" :icon="systemIcon(activity)">
                {{ activity.message }}
              </q-chip>
            </div>

            <!-- AI / assistant bubble -->
            <div v-else-if="isAiMessage(activity)" class="row justify-start q-mb-sm">
              <div class="column" style="max-width: 80%">
                <div class="text-caption text-grey-5 q-ml-sm q-mb-xs">AI Assistant</div>
                <div class="chat-bubble-other">{{ activity.message }}</div>
                <img v-if="activity.file" :src="fileUrl(activity.file)" class="chat-image q-mt-xs" @click="previewImage(activity.file)" />
                <div class="text-caption text-grey-4 q-ml-sm q-mt-xs">{{ formatTime(activity.created_at) }}</div>
              </div>
            </div>

            <!-- Tenant (current user) bubble -->
            <div v-else-if="isTenantMessage(activity)" class="row justify-end q-mb-sm">
              <div class="column items-end" style="max-width: 80%">
                <div v-if="stripAgentPrefix(activity.message)" class="chat-bubble-user">{{ stripAgentPrefix(activity.message) }}</div>
                <img v-if="activity.file" :src="fileUrl(activity.file)" class="chat-image q-mt-xs" @click="previewImage(activity.file)" />
                <div class="text-caption text-grey-4 q-mr-sm q-mt-xs">{{ formatTime(activity.created_at) }}</div>
              </div>
            </div>

            <!-- Other participant bubble (admin, agent, supplier) -->
            <div v-else class="row justify-start q-mb-sm">
              <div class="column" style="max-width: 80%">
                <div class="text-caption text-grey-5 q-ml-sm q-mb-xs">
                  {{ activity.created_by_name || 'Staff' }}
                  <q-badge v-if="activity.created_by_role" dense :label="activity.created_by_role" color="grey-4" class="q-ml-xs text-capitalize" />
                </div>
                <div class="chat-bubble-other chat-bubble-other--staff">{{ activity.message }}</div>
                <img v-if="activity.file" :src="fileUrl(activity.file)" class="chat-image q-mt-xs" @click="previewImage(activity.file)" />
                <div class="text-caption text-grey-4 q-ml-sm q-mt-xs">{{ formatTime(activity.created_at) }}</div>
              </div>
            </div>
          </template>

          <!-- Typing indicator -->
          <div v-if="waitingForAi" class="row justify-start q-mb-sm">
            <div class="chat-bubble-other">
              <div class="typing-dots">
                <span class="typing-dot" />
                <span class="typing-dot" />
                <span class="typing-dot" />
              </div>
            </div>
          </div>

          <!-- Scroll anchor -->
          <div ref="scrollAnchor" />
        </div>

        <!-- Close ticket suggestion -->
        <div v-if="showCloseSuggestion" class="q-px-sm q-pb-xs">
          <q-banner dense rounded class="bg-blue-1">
            <template #avatar>
              <q-icon name="check_circle" color="positive" />
            </template>
            <div class="text-body2">Issue resolved? Close this ticket.</div>
            <template #action>
              <q-btn flat no-caps dense color="positive" label="Close ticket" :loading="closingTicket" @click="closeTicket" />
              <q-btn flat no-caps dense color="grey" label="Not yet" @click="dismissCloseSuggestion" />
            </template>
          </q-banner>
        </div>

        <!-- Photo preview -->
        <div v-if="photoPreview" class="q-pa-sm" style="border-top: 0.5px solid rgba(0,0,0,0.1)">
          <div class="row items-center q-gutter-sm">
            <img :src="photoPreview" style="height: 64px; border-radius: 8px; object-fit: cover" />
            <q-btn flat round dense icon="close" size="sm" color="grey-6" @click="clearPhoto" />
          </div>
        </div>

        <!-- Composer -->
        <div class="composer-bar q-pa-sm">
          <input ref="fileInput" type="file" accept="image/*" capture="environment" style="display: none" @change="onPhotoSelected" />
          <q-input
            v-model="newMessage"
            dense
            outlined
            rounded
            placeholder="Type a message…"
            class="col"
            @keyup.enter="sendMessage"
          >
            <template #prepend>
              <q-btn round flat dense icon="photo_camera" color="grey-6" aria-label="Attach photo" @click="openPhotoPicker" />
            </template>
            <template #append>
              <q-btn round flat dense icon="send" color="primary" :disable="!canSend" :loading="sendingPhoto" aria-label="Send message" @click="sendMessage" />
            </template>
          </q-input>
        </div>

      </q-page>
    </q-page-container>

  </q-layout>
</template>

<script setup lang="ts">
defineOptions({ name: 'TicketChatPage' })

import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { usePlatform } from '../composables/usePlatform'
import { useMaintenanceChatSocket } from '../composables/useMaintenanceChatSocket'
import type { MaintenanceActivity } from '../composables/useMaintenanceChatSocket'
import StatusBadge from '../components/StatusBadge.vue'
import { SPINNER_SIZE_PAGE } from '../utils/designTokens'
import { formatDate, formatTime } from '../utils/formatters'
import * as tenantApi from '../services/api'
import type { MaintenanceIssue } from '../services/api'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const $q = useQuasar()
const { isIos, headerClass, backIcon } = usePlatform()

const ticketId = computed(() => Number(route.params.id) || null)
const ticket = ref<MaintenanceIssue | null>(null)
const loading = ref(true)
const activities = ref<MaintenanceActivity[]>([])
const newMessage = ref('')
const metaExpanded = ref(false)
const waitingForAi = ref(false)
const sendingPhoto = ref(false)
const chatContainer = ref<HTMLElement | null>(null)
const scrollAnchor = ref<HTMLElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const selectedPhoto = ref<File | null>(null)
const photoPreview = ref<string | null>(null)
const hasReceivedHistory = ref(false)
let classifyAttempted = false

const showGreeting = computed(() => hasReceivedHistory.value && activities.value.length === 0)
const priorityLabel = computed(() => ticket.value?.priority?.replace('_', ' ') || '')
const canSend = computed(() => newMessage.value.trim() || selectedPhoto.value)
const closingTicket = ref(false)
const closeSuggestionDismissed = ref(false)

// Detect if AI suggested closing (look for close/resolved keywords in recent AI messages)
const CLOSE_KEYWORDS = /\b(close this ticket|mark.*(resolved|closed)|issue.*(resolved|fixed)|would you like to close)\b/i
const showCloseSuggestion = computed(() => {
  if (closeSuggestionDismissed.value || closingTicket.value) return false
  if (!ticket.value || ticket.value.status === 'closed' || ticket.value.status === 'resolved') return false
  // Check last 3 AI messages for closure suggestion
  const recentAi = activities.value.filter(a => isAiMessage(a)).slice(-3)
  return recentAi.some(a => CLOSE_KEYWORDS.test(a.message))
})

// ── API polling/send callbacks for WS fallback ──────────────────────────────
async function apiFetchActivities(id: number): Promise<MaintenanceActivity[]> {
  const res = await tenantApi.listActivities(id)
  return res.data.results ?? (res.data as unknown as MaintenanceActivity[])
}

async function apiSendActivity(id: number, message: string, activityType: string): Promise<void> {
  const form = new FormData()
  form.append('message', message)
  form.append('activity_type', activityType)
  await tenantApi.postActivity(id, form)
}

// ── WebSocket ───────────────────────────────────────────────────────────────
const { connected: wsConnected, disconnected: wsDisconnected, send: wsSend } = useMaintenanceChatSocket(
  () => ticketId.value,
  (history) => {
    activities.value = history
    hasReceivedHistory.value = true
    scrollToBottom()
  },
  (activity) => {
    activities.value.push(activity)
    // If AI responded, stop typing indicator and attempt classification
    if (isAiMessage(activity)) {
      waitingForAi.value = false
      maybeClassify()
    }
    scrollToBottom()
  },
  apiFetchActivities,
  apiSendActivity,
)

// ── Message helpers ─────────────────────────────────────────────────────────
const AGENT_PREFIX_RE = /^@agent\s*/i

function stripAgentPrefix(msg: string): string {
  return msg.replace(AGENT_PREFIX_RE, '')
}

function isSystemEvent(a: MaintenanceActivity): boolean {
  const systemTypes = ['status_change', 'supplier_assigned', 'dispatch_sent', 'quote_received', 'job_awarded']
  return systemTypes.includes(a.activity_type)
}

function isAiMessage(a: MaintenanceActivity): boolean {
  return (
    a.metadata?.source === 'ai_agent' ||
    (a.activity_type === 'system' && !isSystemEvent(a)) ||
    (!a.created_by_name && a.activity_type === 'note' && !a.created_by_role)
  )
}

function isTenantMessage(a: MaintenanceActivity): boolean {
  if (auth.user?.id != null) {
    return a.created_by != null && Number(a.created_by) === Number(auth.user.id)
  }
  return a.created_by_role === 'tenant'
}

function systemIcon(a: MaintenanceActivity): string {
  const map: Record<string, string> = {
    status_change: 'swap_horiz',
    supplier_assigned: 'person_add',
    dispatch_sent: 'send',
    quote_received: 'request_quote',
    job_awarded: 'emoji_events',
  }
  return map[a.activity_type] || 'info'
}

// ── Photo handling ──────────────────────────────────────────────────────────
function openPhotoPicker() {
  fileInput.value?.click()
}

function onPhotoSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  selectedPhoto.value = file
  photoPreview.value = URL.createObjectURL(file)
  // Reset input so the same file can be re-selected
  input.value = ''
}

function clearPhoto() {
  if (photoPreview.value) URL.revokeObjectURL(photoPreview.value)
  selectedPhoto.value = null
  photoPreview.value = null
}

function fileUrl(file: string): string {
  if (file.startsWith('http')) return file
  const apiBase = (process.env.API_URL as string) || 'http://localhost:8000/api/v1'
  const origin = new URL(apiBase).origin
  return `${origin}${file}`
}

function previewImage(file: string) {
  $q.dialog({
    message: `<img src="${fileUrl(file)}" style="max-width:100%;border-radius:8px" />`,
    html: true,
    ok: { label: 'Close', flat: true },
  })
}

// ── Send ────────────────────────────────────────────────────────────────────
async function sendMessage() {
  const text = newMessage.value.trim()
  const photo = selectedPhoto.value

  if (!text && !photo) return

  // If we have a photo, send via REST (WebSocket can't do binary)
  if (photo && ticketId.value) {
    sendingPhoto.value = true
    const form = new FormData()
    form.append('message', text || '[Photo attached]')
    form.append('activity_type', 'note')
    form.append('file', photo)
    try {
      await tenantApi.postActivity(ticketId.value, form)
      newMessage.value = ''
      clearPhoto()
    } catch {
      $q.notify({ type: 'negative', message: 'Failed to send photo' })
    } finally {
      sendingPhoto.value = false
    }
    scrollToBottom()
    return
  }

  // Text-only: send via WebSocket
  // Only trigger AI when tenant explicitly mentions @agent
  wsSend(text, 'note')
  newMessage.value = ''
  scrollToBottom()
}

// ── Auto-classify ───────────────────────────────────────────────────────────
async function maybeClassify() {
  if (classifyAttempted || !ticket.value) return
  // Only classify once, after AI has responded at least once
  const userMessages = activities.value.filter(a => isTenantMessage(a))
  if (userMessages.length === 0) return
  classifyAttempted = true

  const description = userMessages.map(a => stripAgentPrefix(a.message)).join('\n')
  const title = stripAgentPrefix(userMessages[0].message).slice(0, 80)

  try {
    const res = await tenantApi.classifyIssue({ title, description })
    const cls = res.data
    if (cls.confidence > 0.3) {
      await tenantApi.updateIssue(ticket.value.id, {
        title,
        category: cls.category,
        priority: cls.priority,
      })
      // Refresh ticket data
      const updated = await tenantApi.getIssue(ticket.value.id)
      ticket.value = updated.data
    }
  } catch { /* classification is best-effort */ }
}

// ── Close ticket ───────────────────────────────────────────────────────────
async function closeTicket() {
  if (!ticket.value) return
  closingTicket.value = true
  try {
    await tenantApi.updateIssue(ticket.value.id, { status: 'closed' })
    ticket.value = { ...ticket.value, status: 'closed' }
    $q.notify({ type: 'positive', message: 'Ticket closed' })
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to close ticket' })
  } finally {
    closingTicket.value = false
  }
}

function dismissCloseSuggestion() {
  closeSuggestionDismissed.value = true
}

// ── Scroll ──────────────────────────────────────────────────────────────────
function scrollToBottom() {
  nextTick(() => {
    scrollAnchor.value?.scrollIntoView({ behavior: 'smooth' })
  })
}

// ── Load ticket ─────────────────────────────────────────────────────────────
onMounted(async () => {
  if (!ticketId.value) { loading.value = false; return }
  try {
    const res = await tenantApi.getIssue(ticketId.value)
    ticket.value = res.data
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to load ticket details.', icon: 'error' })
  }
  loading.value = false
})

// Scroll when activities change
watch(() => activities.value.length, () => scrollToBottom())
</script>

<style scoped lang="scss">
.chat-image {
  max-width: 200px;
  max-height: 200px;
  border-radius: var(--klikk-radius-card);
  object-fit: cover;
  cursor: pointer;
  border: 1px solid var(--klikk-border);
}

.composer-bar {
  position: sticky;
  bottom: 0;
  z-index: 10;
  border-top: 0.5px solid var(--klikk-border);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding-bottom: max(8px, env(safe-area-inset-bottom, 0px));
}

// Staff / admin bubble — subtle navy-tinted background.
// Uses info token surface rather than a raw hex literal.
.chat-bubble-other--staff {
  background: var(--klikk-info-50);
}
</style>
