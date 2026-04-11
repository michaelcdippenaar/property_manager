<template>
  <q-layout view="hHh lpR fFf">
    <q-header :elevated="!isIos" :class="headerClass">
      <q-toolbar>
        <q-btn flat round :icon="backIcon" :color="isIos ? 'primary' : 'white'" @click="$router.back()" />
        <q-toolbar-title :class="isIos ? 'text-primary text-weight-semibold' : 'text-white text-weight-medium'">
          AI Assistant
        </q-toolbar-title>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <q-page class="column" style="min-height: 0">

        <!-- Messages -->
        <div ref="scrollEl" class="col overflow-auto q-pa-md" style="padding-bottom: 100px">
          <div v-if="pageLoading" class="flex flex-center q-pt-xl">
            <q-spinner-dots :size="SPINNER_SIZE_PAGE" color="primary" />
          </div>

          <template v-for="msg in messages" :key="msg.id">
            <!-- Skills card -->
            <div v-if="msg.type === 'skills'" class="q-mx-sm q-mb-sm">
              <q-card flat bordered class="bg-blue-1">
                <q-card-section class="q-pa-sm">
                  <div class="text-caption text-weight-bold text-info q-mb-xs">Skills used</div>
                  <div class="text-caption text-grey-8">{{ (msg.skills ?? []).join(', ') }}</div>
                </q-card-section>
              </q-card>
            </div>

            <!-- Confirm ticket card -->
            <div v-else-if="msg.type === 'confirm'" class="q-mx-sm q-mb-sm">
              <q-card flat bordered class="bg-orange-1">
                <q-card-section class="q-pa-sm">
                  <div class="text-subtitle2 text-warning q-mb-xs">Log a repair request?</div>
                  <div class="text-body2 text-grey-8">{{ msg.draft?.description }}</div>
                  <div class="row q-gutter-sm q-mt-sm">
                    <q-btn label="Yes, log it" color="warning" no-caps size="sm" class="col" @click="confirmTicket(msg)" />
                    <q-btn label="Not now" outline color="warning" no-caps size="sm" class="col" @click="dismissConfirm(msg)" />
                  </div>
                </q-card-section>
              </q-card>
            </div>

            <!-- Normal chat bubble -->
            <div v-else class="column q-mb-sm" :class="msg.role === 'user' ? 'items-end' : 'items-start'">
              <div :class="msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-other'">
                <div style="white-space: pre-wrap">{{ msg.content }}</div>
                <img v-if="msg.file_url" :src="msg.file_url" class="q-mt-sm rounded-borders" style="max-width: 200px" />
              </div>
              <div class="text-caption text-grey-4 q-px-xs" style="font-size: 10px">{{ formatTime(msg.created_at) }}</div>
            </div>
          </template>

          <!-- AI typing indicator -->
          <div v-if="aiTyping" class="row items-start q-gutter-sm">
            <div class="chat-bubble-other row items-center q-gutter-xs q-pa-sm">
              <span class="typing-dot" />
              <span class="typing-dot" />
              <span class="typing-dot" />
            </div>
          </div>
        </div>

        <!-- Composer -->
        <div
          class="bg-white q-pa-sm row items-end q-gutter-sm"
          style="border-top: 1px solid rgba(0,0,0,0.06); padding-bottom: calc(12px + env(safe-area-inset-bottom))"
        >
          <q-btn flat round icon="attach_file" color="grey-6" size="sm">
            <input
              type="file"
              accept="image/*,video/*"
              class="absolute-full cursor-pointer"
              style="opacity: 0"
              @change="onFileChange"
            />
          </q-btn>
          <q-input
            v-model="messageText"
            dense
            outlined
            rounded
            placeholder="Ask anything…"
            class="col"
            autogrow
            @keyup.enter.exact.prevent="handleSend"
          />
          <q-btn
            round
            flat
            icon="send"
            color="primary"
            :disable="!messageText.trim() || aiTyping"
            @click="handleSend"
          />
        </div>

      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePlatform } from '../composables/usePlatform'
import * as tenantApi from '../services/api'
import type { Message } from '../services/api'
import { formatTime } from '../utils/formatters'
import { SPINNER_SIZE_PAGE } from '../utils/designTokens'

const route  = useRoute()
const router = useRouter()
const { isIos, backIcon, headerClass } = usePlatform()

const convId = Number(route.params.id)

const messages    = ref<Message[]>([])
const pageLoading = ref(true)
const aiTyping    = ref(false)
const messageText = ref('')
const pendingFile = ref<File | null>(null)
const scrollEl    = ref<HTMLElement | null>(null)
let msgCounter    = -1

function scrollToBottom() {
  nextTick(() => {
    if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  })
}

function processAiResponse(data: Record<string, unknown>) {
  messages.value.push({
    id: msgCounter--,
    role: 'assistant',
    content: (data.content ?? data.response ?? '') as string,
    created_at: new Date().toISOString(),
  })

  // Skills card
  const skillsUsed = data.skills_used as { used?: boolean; preview?: string[] } | undefined
  if (skillsUsed?.used && skillsUsed?.preview?.length) {
    messages.value.push({
      id: msgCounter--,
      type: 'skills',
      skills: skillsUsed.preview,
      created_at: new Date().toISOString(),
    })
  }

  // Confirm ticket card
  if (data.interaction_type === 'maintenance' && !data.ticket_id && data.maintenance_draft) {
    messages.value.push({
      id: msgCounter--,
      type: 'confirm',
      draft: data.maintenance_draft as Record<string, unknown>,
      created_at: new Date().toISOString(),
    })
  }
}

async function handleSend() {
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

    const res = await tenantApi.sendMessage(convId, form)

    // Replace optimistic with real
    const idx = messages.value.findIndex(m => m.id === optimisticId)
    if (idx !== -1) messages.value.splice(idx, 1)

    processAiResponse(res.data as Record<string, unknown>)
  } catch {
    messages.value = messages.value.filter(m => m.id !== optimisticId)
    messageText.value = text
  } finally {
    aiTyping.value = false
    scrollToBottom()
  }
}

function confirmTicket(msg: Message) {
  dismissConfirm(msg)
  router.push({ name: 'report-issue', query: { title: (msg.draft as Record<string, string>)?.title ?? '', description: (msg.draft as Record<string, string>)?.description ?? '' } })
}

function dismissConfirm(msg: Message) {
  messages.value = messages.value.filter(m => m.id !== msg.id)
}

function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) pendingFile.value = file
}

onMounted(async () => {
  try {
    const res = await tenantApi.getConversation(convId)
    const msgs = res.data.messages ?? []
    messages.value = msgs.map((m: Message) => ({ ...m, type: undefined }))
    scrollToBottom()
  } finally {
    pageLoading.value = false
  }
})
</script>
