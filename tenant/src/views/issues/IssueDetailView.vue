<template>
  <div class="flex flex-col h-dvh overflow-hidden bg-surface">
    <AppHeader
      :title="issue?.title ?? 'Repair Detail'"
      show-back
      back-label="Repairs"
      :is-scrolled="isScrolled"
    />

    <!-- Loading state -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <Loader2 :size="28" class="text-navy/30 animate-spin" />
    </div>

    <template v-else-if="issue">
      <!-- Issue meta card -->
      <div class="bg-white border-b border-gray-100 px-5 py-3 flex items-center gap-3">
        <div>
          <p class="text-xs text-gray-500">{{ issue.category }}</p>
          <div class="flex items-center gap-2 mt-0.5">
            <StatusBadge :value="issue.status" />
            <StatusBadge :value="issue.priority" variant="priority" />
          </div>
        </div>
        <div class="ml-auto text-right">
          <p class="text-xs text-gray-400">Logged</p>
          <p class="text-xs font-medium text-gray-700">{{ formatDate(issue.created_at) }}</p>
        </div>
      </div>

      <!-- Activity feed -->
      <div
        ref="scrollEl"
        class="flex-1 overflow-y-auto px-4 py-4 space-y-3"
        style="padding-bottom: 88px"
        @scroll="onScroll"
      >
        <!-- Issue description bubble -->
        <div class="flex flex-col gap-1">
          <p class="text-xs text-gray-400 text-center mb-1">Issue description</p>
          <div class="chat-bubble-other self-start">
            <p>{{ issue.description }}</p>
          </div>
        </div>

        <!-- Activities -->
        <template v-for="act in activities" :key="act.id">
          <!-- System message -->
          <div v-if="act.is_system || act.activity_type === 'status_change'" class="text-center">
            <span class="text-xs text-gray-400 bg-gray-100 rounded-full px-3 py-1">{{ act.message }}</span>
          </div>
          <!-- User/agent message -->
          <div v-else class="flex flex-col gap-0.5" :class="isMyActivity(act) ? 'items-end' : 'items-start'">
            <p v-if="!isMyActivity(act)" class="text-xs text-gray-400 px-1">{{ act.created_by_name }}</p>
            <div :class="isMyActivity(act) ? 'chat-bubble-user' : 'chat-bubble-other'">
              <p>{{ act.message }}</p>
              <img v-if="act.file_url" :src="act.file_url" class="mt-2 rounded-lg max-w-[200px]" />
            </div>
            <p class="text-[10px] text-gray-400 px-1">{{ formatTime(act.created_at) }}</p>
          </div>
        </template>

        <!-- WS connection indicator -->
        <div class="text-center" v-if="!wsConnected">
          <span class="text-xs text-gray-400">Connecting...</span>
        </div>
      </div>

      <!-- Message composer -->
      <div class="bg-white border-t border-gray-100 px-4 py-3 flex items-end gap-2" style="padding-bottom: calc(0.75rem + env(safe-area-inset-bottom))">
        <label class="touchable w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center flex-shrink-0">
          <Paperclip :size="18" class="text-gray-500" />
          <input type="file" accept="image/*,video/*" class="hidden" @change="onFileChange" />
        </label>
        <div class="flex-1 bg-gray-100 rounded-2xl px-4 py-2.5 min-h-[40px] flex items-center">
          <textarea
            v-model="messageText"
            rows="1"
            placeholder="Write a message…"
            class="flex-1 bg-transparent outline-none resize-none text-sm text-gray-900 placeholder-gray-400"
            style="max-height: 100px"
            @input="autoResize"
          />
        </div>
        <button
          class="w-10 h-10 rounded-xl bg-navy flex items-center justify-center flex-shrink-0 ripple touchable"
          :disabled="!messageText.trim() && !pendingFile"
          :class="(!messageText.trim() && !pendingFile) ? 'opacity-40' : ''"
          @click="sendMessage"
        >
          <Send :size="18" class="text-white" />
        </button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { Loader2, Paperclip, Send } from 'lucide-vue-next'
import AppHeader from '../../components/AppHeader.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'
import { useMaintenanceChatSocket } from '../../composables/useMaintenanceChatSocket'
import type { MaintenanceActivity } from '../../composables/useMaintenanceChatSocket'

const route = useRoute()
const auth = useAuthStore()
const issueId = Number(route.params.id)

const issue = ref<any>(null)
const loading = ref(true)
const activities = ref<MaintenanceActivity[]>([])
const seenIds = new Set<number>()
const messageText = ref('')
const pendingFile = ref<File | null>(null)
const scrollEl = ref<HTMLElement | null>(null)
const isScrolled = ref(false)
const sending = ref(false)

function onScroll() {
  isScrolled.value = (scrollEl.value?.scrollTop ?? 0) > 20
}

function isMyActivity(act: MaintenanceActivity) {
  return act.created_by_name === auth.user?.full_name
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' })
}
function formatTime(d: string) {
  return new Date(d).toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' })
}

function addActivity(act: MaintenanceActivity) {
  if (seenIds.has(act.id)) return
  seenIds.add(act.id)
  activities.value.push(act)
  nextTick(() => {
    if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  })
}

const { connected: wsConnected, send: wsSend } = useMaintenanceChatSocket(
  () => issueId,
  (history) => {
    activities.value = []
    seenIds.clear()
    history.forEach(addActivity)
  },
  addActivity,
)

async function sendMessage() {
  if (!messageText.value.trim() && !pendingFile.value) return
  if (sending.value) return
  sending.value = true

  const text = messageText.value
  messageText.value = ''

  // Try WebSocket first (text only)
  if (!pendingFile.value && wsSend(text)) {
    sending.value = false
    return
  }

  // Fallback to REST (also handles file uploads)
  try {
    const form = new FormData()
    if (text) form.append('message', text)
    form.append('activity_type', 'note')
    if (pendingFile.value) form.append('file', pendingFile.value)
    pendingFile.value = null

    const res = await api.post(`/maintenance/${issueId}/activity/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    addActivity(res.data)
  } catch {
    messageText.value = text
  } finally {
    sending.value = false
  }
}

function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) pendingFile.value = file
}

function autoResize(e: Event) {
  const el = e.target as HTMLTextAreaElement
  el.style.height = 'auto'
  el.style.height = el.scrollHeight + 'px'
}

onMounted(async () => {
  try {
    const res = await api.get(`/maintenance/${issueId}/`)
    issue.value = res.data
  } finally {
    loading.value = false
  }
})
</script>
