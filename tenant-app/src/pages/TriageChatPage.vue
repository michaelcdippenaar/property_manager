<template>
  <q-layout view="hHh lpR fFf">

    <!-- Header -->
    <q-header :elevated="!isIos" :class="headerClass">
      <q-toolbar>
        <q-btn flat round :icon="backIcon" :color="isIos ? 'primary' : 'white'" aria-label="Go back" @click="goBack" />
        <q-toolbar-title :class="isIos ? 'text-primary text-weight-semibold' : 'text-white text-weight-medium'">
          <div class="ellipsis" style="max-width: 220px">{{ headerTitle }}</div>
        </q-toolbar-title>
        <q-chip
          v-if="linkedTicketId"
          dense
          clickable
          size="sm"
          color="positive"
          text-color="white"
          icon="confirmation_number"
          @click="goToTicket"
        >
          Ticket #{{ linkedTicketId }}
        </q-chip>
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

          <!-- AI greeting -->
          <div class="row justify-start q-mb-sm">
            <div class="column" style="max-width: 80%">
              <div class="text-caption text-grey-5 q-ml-sm q-mb-xs">AI Assistant</div>
              <div class="chat-bubble-other">
                Hi! I'm your AI maintenance assistant. What issue would you like to report? You can also send photos to help us assess the problem.
              </div>
            </div>
          </div>

          <!-- Messages -->
          <template v-for="msg in messages" :key="msg.id">

            <!-- System chip (ticket created, etc.) -->
            <div v-if="msg.role === 'system'" class="text-center q-my-xs">
              <q-chip dense size="sm" color="positive" text-color="white" icon="confirmation_number">
                {{ msg.content }}
              </q-chip>
            </div>

            <!-- AI bubble -->
            <div v-else-if="msg.role === 'assistant'" class="row justify-start q-mb-sm">
              <div class="column" style="max-width: 80%">
                <div class="text-caption text-grey-5 q-ml-sm q-mb-xs">AI Assistant</div>
                <div class="chat-bubble-other">{{ msg.content }}</div>
                <img v-if="msg.attachment_url" :src="msg.attachment_url" class="chat-image q-mt-xs" @click="previewImage(msg.attachment_url!)" />
                <div class="text-caption text-grey-4 q-ml-sm q-mt-xs">{{ formatTime(msg.created_at || '') }}</div>
              </div>
            </div>

            <!-- User bubble -->
            <div v-else class="row justify-end q-mb-sm">
              <div class="column items-end" style="max-width: 80%">
                <div v-if="msg.content" class="chat-bubble-user">{{ msg.content }}</div>
                <img v-if="msg.attachment_url" :src="msg.attachment_url" class="chat-image q-mt-xs" @click="previewImage(msg.attachment_url!)" />
                <div class="text-caption text-grey-4 q-mr-sm q-mt-xs">{{ formatTime(msg.created_at || '') }}</div>
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

        <!-- Photo preview -->
        <div v-if="photoPreview" class="q-pa-sm" style="border-top: 0.5px solid rgba(0,0,0,0.1)">
          <div class="row items-center q-gutter-sm">
            <img :src="photoPreview" style="height: 64px; border-radius: 8px; object-fit: cover" />
            <q-btn flat round dense icon="close" size="sm" color="grey-6" @click="clearPhoto" />
          </div>
        </div>

        <!-- Ticket created banner -->
        <div v-if="linkedTicketId" class="q-px-sm q-pb-xs">
          <q-banner dense rounded class="bg-positive text-white">
            <template #avatar>
              <q-icon name="check_circle" />
            </template>
            Ticket #{{ linkedTicketId }} created. You can continue chatting here or
            <a class="text-white text-weight-bold cursor-pointer" style="text-decoration: underline" @click="goToTicket">view the ticket</a>.
          </q-banner>
        </div>

        <!-- Fallback: AI identified issue but couldn't create ticket (no linked unit) -->
        <div v-else-if="reportSuggested" class="q-px-sm q-pb-xs">
          <q-banner dense rounded class="bg-warning text-white">
            <template #avatar>
              <q-icon name="warning" />
            </template>
            <div class="text-body2 text-weight-medium q-mb-xs">We couldn't auto-log this repair</div>
            <div class="text-caption q-mb-sm" style="opacity: 0.9">Your account isn't linked to a unit yet. Contact your property manager to link your account, or submit the form below.</div>
            <q-btn
              dense
              unelevated
              no-caps
              label="Report manually"
              color="white"
              text-color="warning"
              size="sm"
              @click="openManualReport"
            />
          </q-banner>
        </div>

        <!-- Composer -->
        <div class="composer-bar q-pa-sm">
          <input ref="fileInput" type="file" accept="image/*" capture="environment" style="display: none" @change="onPhotoSelected" />
          <q-input
            v-model="newMessage"
            dense
            outlined
            rounded
            placeholder="Describe your issue..."
            class="col"
            @keyup.enter="sendMessage"
          >
            <template #prepend>
              <q-btn round flat dense icon="photo_camera" color="grey-6" aria-label="Attach photo" @click="openPhotoPicker" />
            </template>
            <template #append>
              <q-btn round flat dense icon="send" color="primary" :disable="!canSend" :loading="waitingForAi" aria-label="Send message" @click="sendMessage" />
            </template>
          </q-input>
        </div>

      </q-page>
    </q-page-container>

  </q-layout>
</template>

<script setup lang="ts">
defineOptions({ name: 'TriageChatPage' })

import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { usePlatform } from '../composables/usePlatform'
import { SPINNER_SIZE_PAGE } from '../utils/designTokens'
import { formatTime } from '../utils/formatters'
import * as tenantApi from '../services/api'
import type { ConversationMessage } from '../services/api'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()
const { isIos, headerClass, backIcon } = usePlatform()

const convId = computed(() => Number(route.params.convId) || null)
const loading = ref(true)
const messages = ref<(ConversationMessage & { role: string })[]>([])
const newMessage = ref('')
const waitingForAi = ref(false)
const linkedTicketId = ref<number | null>(null)
const reportSuggested = ref(false)
const conversationTitle = ref('New Request')
const scrollAnchor = ref<HTMLElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const selectedPhoto = ref<File | null>(null)
const photoPreview = ref<string | null>(null)

const headerTitle = computed(() => conversationTitle.value || 'New Request')
const canSend = computed(() => (newMessage.value.trim() || selectedPhoto.value) && !waitingForAi.value)

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
  input.value = ''
}

function clearPhoto() {
  if (photoPreview.value) URL.revokeObjectURL(photoPreview.value)
  selectedPhoto.value = null
  photoPreview.value = null
}

function previewImage(url: string) {
  $q.dialog({
    message: `<img src="${url}" style="max-width:100%;border-radius:8px" />`,
    html: true,
    ok: { label: 'Close', flat: true },
  })
}

// ── Send message ────────────────────────────────────────────────────────────
async function sendMessage() {
  const text = newMessage.value.trim()
  const photo = selectedPhoto.value
  if (!text && !photo) return
  if (!convId.value) return

  // Build request
  let payload: FormData | { content: string }
  if (photo) {
    const form = new FormData()
    form.append('content', text || '[Photo attached]')
    form.append('file', photo)
    payload = form
  } else {
    payload = { content: text }
  }

  // Optimistic: add user message to timeline
  const userMsg: ConversationMessage & { role: string } = {
    id: Date.now(),
    role: 'user',
    content: text || '[Photo attached]',
    attachment_url: photoPreview.value,
    attachment_kind: photo ? 'image' : '',
    created_at: new Date().toISOString(),
  }
  messages.value.push(userMsg)
  newMessage.value = ''
  const hadPhoto = !!photo
  if (hadPhoto) clearPhoto()
  waitingForAi.value = true
  scrollToBottom()

  try {
    const res = await tenantApi.sendConversationMessage(convId.value, payload)
    const data = res.data

    // Update user message with server attachment URL if photo was uploaded
    if (hadPhoto && data.user_message.attachment_url) {
      userMsg.attachment_url = data.user_message.attachment_url
    }

    // Add AI response
    messages.value.push({
      ...data.ai_message,
      created_at: data.ai_message.created_at || new Date().toISOString(),
    })

    // Update conversation title
    if (data.conversation.title && data.conversation.title !== 'New conversation') {
      conversationTitle.value = data.conversation.title
    }

    // Check if a maintenance ticket was created
    if (data.maintenance_request && !linkedTicketId.value) {
      linkedTicketId.value = data.maintenance_request.id
      reportSuggested.value = false
      messages.value.push({
        id: Date.now() + 1,
        role: 'system',
        content: `Ticket #${data.maintenance_request.id} created — ${data.maintenance_request.title}`,
        attachment_url: null,
        attachment_kind: '',
        created_at: new Date().toISOString(),
      })
    } else if (data.maintenance_report_suggested && !linkedTicketId.value) {
      reportSuggested.value = true
    }
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to send message. Please try again.' })
    // Remove the optimistic user message on failure
    messages.value.pop()
  } finally {
    waitingForAi.value = false
    scrollToBottom()
  }
}

// ── Navigation ──────────────────────────────────────────────────────────────
function goBack() {
  router.push('/repairs')
}

function goToTicket() {
  if (linkedTicketId.value) {
    router.push(`/repairs/ticket/${linkedTicketId.value}`)
  }
}

function openManualReport() {
  // Navigate to repairs page — tenant can use the FAB there to start a new request
  // or contact their property manager directly
  $q.dialog({
    title: 'Contact your property manager',
    message: 'Your account isn\'t linked to a unit yet. Please ask your property manager to link your account so repairs can be logged automatically. In the meantime, contact them directly to report this issue.',
    ok: { label: 'Go to Repairs', color: 'primary', unelevated: true },
    cancel: { label: 'Stay here', flat: true },
  }).onOk(() => {
    router.push('/repairs')
  })
}

// ── Scroll ──────────────────────────────────────────────────────────────────
function scrollToBottom() {
  nextTick(() => {
    scrollAnchor.value?.scrollIntoView({ behavior: 'smooth' })
  })
}

// ── Load existing conversation ──────────────────────────────────────────────
onMounted(async () => {
  if (!convId.value) { loading.value = false; return }
  try {
    const res = await tenantApi.getConversation(convId.value)
    const conv = res.data
    if (conv.title && conv.title !== 'New conversation') {
      conversationTitle.value = conv.title
    }
    if (conv.maintenance_request_id) {
      linkedTicketId.value = conv.maintenance_request_id
    }
    // Load existing messages
    if (conv.messages && conv.messages.length > 0) {
      messages.value = conv.messages.map(m => ({
        ...m,
        created_at: m.created_at || new Date().toISOString(),
      }))
    }
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to load conversation.', icon: 'error' })
  }
  loading.value = false
  scrollToBottom()
})
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
</style>
