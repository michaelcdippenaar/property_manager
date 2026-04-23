<template>
  <div class="flex flex-col h-dvh overflow-hidden bg-surface">
    <AppHeader title="AI Assistant" show-back back-label="Chats" :is-scrolled="isScrolled" />

    <!-- Messages -->
    <div ref="scrollEl" class="flex-1 overflow-y-auto px-4 py-4 space-y-3" style="padding-bottom: 80px" @scroll="onScroll">
      <div v-if="loading" class="flex items-center justify-center pt-10">
        <Loader2 :size="28" class="text-navy/30 animate-spin" />
      </div>

      <!-- Welcome / empty state with POPIA disclosure -->
      <div v-else-if="messages.length === 0" class="flex flex-col items-center justify-center pt-16 px-6 text-center">
        <div class="w-14 h-14 bg-navy/5 rounded-2xl flex items-center justify-center mb-4">
          <Bot :size="26" class="text-navy/40" />
        </div>
        <p class="font-semibold text-gray-700 mb-1">Hi, I'm your AI assistant</p>
        <p class="text-sm text-gray-400 leading-relaxed mb-4">
          Ask me anything about your rental — maintenance, payments, your lease, or general queries.
        </p>
        <div class="bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 max-w-xs">
          <p class="text-xs text-gray-500 leading-relaxed">
            Messages you send here are processed by an AI service. Don't share ID numbers, bank details, or passport numbers — we'll redact them, but it's safer not to send them.
          </p>
        </div>
      </div>

      <template v-for="msg in messages" :key="msg.id">
        <!-- System / skill info card -->
        <div v-if="msg.type === 'skills'" class="mx-2">
          <div class="bg-info-50 border border-info-100 rounded-2xl px-4 py-3 text-xs text-info-700">
            <p class="font-semibold mb-1">Skills used</p>
            <p>{{ (msg.skills ?? []).join(', ') }}</p>
          </div>
        </div>

        <!-- Confirm ticket card -->
        <div v-else-if="msg.type === 'confirm'" class="mx-2">
          <div class="bg-warning-50 border border-warning-100 rounded-2xl px-4 py-3 space-y-3">
            <p class="text-sm font-semibold text-warning-700">Log a repair request?</p>
            <p class="text-sm text-warning-600">{{ msg.draft?.description }}</p>
            <div class="flex gap-2">
              <button class="flex-1 py-2 bg-warning-500 text-white rounded-xl text-sm font-medium touchable ripple" @click="confirmTicket(msg)">
                Yes, log it
              </button>
              <button class="flex-1 py-2 bg-white border border-warning-200 text-warning-700 rounded-xl text-sm font-medium touchable" @click="dismissConfirm(msg)">
                Not now
              </button>
            </div>
          </div>
        </div>

        <!-- Normal chat bubble -->
        <div v-else class="flex flex-col gap-0.5" :class="msg.role === 'user' ? 'items-end' : 'items-start'">
          <div :class="msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-other'">
            <p class="whitespace-pre-wrap">{{ msg.content }}</p>
            <img v-if="msg.file_url" :src="msg.file_url" class="mt-2 rounded-lg max-w-[200px]" />
          </div>
          <p class="text-[10px] text-gray-400 px-1">{{ formatTime(msg.created_at) }}</p>
        </div>
      </template>

      <!-- AI typing indicator -->
      <div v-if="aiTyping" class="flex items-start gap-2">
        <div class="chat-bubble-other flex items-center gap-1.5">
          <span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms" />
          <span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms" />
          <span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms" />
        </div>
      </div>
    </div>

    <!-- Composer -->
    <div class="bg-white border-t border-gray-100 px-4 py-3 flex items-end gap-2" style="padding-bottom: calc(0.75rem + env(safe-area-inset-bottom))">
      <label class="touchable w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center flex-shrink-0">
        <Paperclip :size="18" class="text-gray-500" />
        <input type="file" accept="image/*,video/*" class="hidden" @change="onFileChange" />
      </label>
      <div class="flex-1 bg-gray-100 rounded-2xl px-4 py-2.5 min-h-[40px] flex items-center">
        <textarea
          v-model="messageText"
          rows="1"
          placeholder="Ask anything…"
          class="flex-1 bg-transparent outline-none resize-none text-sm text-gray-900 placeholder-gray-400"
          style="max-height: 100px"
          @input="autoResize"
          @keyup.enter.exact.prevent="sendMessage"
        />
      </div>
      <button
        class="w-10 h-10 rounded-xl bg-navy flex items-center justify-center flex-shrink-0 ripple touchable"
        :disabled="!messageText.trim() || aiTyping"
        :class="(!messageText.trim() || aiTyping) ? 'opacity-40' : ''"
        @click="sendMessage"
      >
        <Send :size="18" class="text-white" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Bot, Loader2, Paperclip, Send } from 'lucide-vue-next'
import AppHeader from '../../components/AppHeader.vue'
import api from '../../api'
import { useToast } from '../../composables/useToast'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const convId = route.params.id

interface Message {
  id: number
  role?: string
  type?: string
  content?: string
  file_url?: string
  created_at: string
  skills?: string[]
  draft?: any
  interaction_type?: string
}

const messages = ref<Message[]>([])
const loading = ref(true)
const aiTyping = ref(false)
const messageText = ref('')
const pendingFile = ref<File | null>(null)
const scrollEl = ref<HTMLElement | null>(null)
const isScrolled = ref(false)
let msgCounter = -1

function onScroll() {
  isScrolled.value = (scrollEl.value?.scrollTop ?? 0) > 20
}

function scrollToBottom() {
  nextTick(() => {
    if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  })
}

function formatTime(d: string) {
  return new Date(d).toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' })
}

function processAiResponse(data: any) {
  // Add AI message
  messages.value.push({
    id: msgCounter--,
    role: 'assistant',
    content: data.content ?? data.response ?? '',
    created_at: new Date().toISOString(),
  })

  // Skills card
  if (data.skills_used?.used && data.skills_used?.preview?.length) {
    messages.value.push({
      id: msgCounter--,
      type: 'skills',
      skills: data.skills_used.preview,
      created_at: new Date().toISOString(),
    })
  }

  // Confirm ticket card
  if (data.interaction_type === 'maintenance' && !data.ticket_id && data.maintenance_draft) {
    messages.value.push({
      id: msgCounter--,
      type: 'confirm',
      draft: data.maintenance_draft,
      created_at: new Date().toISOString(),
    })
  }
}

async function sendMessage() {
  if (!messageText.value.trim() || aiTyping.value) return

  const text = messageText.value
  messageText.value = ''

  // Optimistic user message
  const optimisticId = msgCounter--
  messages.value.push({ id: optimisticId, role: 'user', content: text, created_at: new Date().toISOString() })
  scrollToBottom()
  aiTyping.value = true

  try {
    const form = new FormData()
    form.append('content', text)
    if (pendingFile.value) { form.append('file', pendingFile.value); pendingFile.value = null }

    const res = await api.post(`/tenant-portal/conversations/${convId}/messages/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    // Replace optimistic with real
    const idx = messages.value.findIndex(m => m.id === optimisticId)
    if (idx !== -1) messages.value.splice(idx, 1)

    processAiResponse(res.data)
  } catch {
    messages.value = messages.value.filter(m => m.id !== optimisticId)
    messageText.value = text
    toast.error('Failed to send message.')
  } finally {
    aiTyping.value = false
    scrollToBottom()
  }
}

async function confirmTicket(msg: Message) {
  dismissConfirm(msg)
  router.push({ name: 'report-issue', query: { title: msg.draft?.title ?? '', description: msg.draft?.description ?? '' } })
}

function dismissConfirm(msg: Message) {
  messages.value = messages.value.filter(m => m.id !== msg.id)
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
    const res = await api.get(`/tenant-portal/conversations/${convId}/`)
    const msgs = res.data.messages ?? []
    messages.value = msgs.map((m: any) => ({ ...m, type: undefined }))
    scrollToBottom()
  } finally {
    loading.value = false
  }
  // Pre-fill input from suggested prompt (passed via ?prefill= query param)
  if (route.query.prefill) {
    messageText.value = String(route.query.prefill)
  }
})
</script>
