<template>
  <q-layout view="hHh lpR fFf">
    <q-header :elevated="!isIos" :class="headerClass">
      <q-toolbar>
        <q-btn flat round :icon="backIcon" :color="isIos ? 'primary' : 'white'" @click="$router.back()" />
        <q-toolbar-title :class="isIos ? 'text-primary text-weight-semibold' : 'text-white text-weight-medium'">
          {{ issue?.title ?? 'Repair Detail' }}
        </q-toolbar-title>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <q-page>
        <!-- Loading -->
        <div v-if="loading" class="flex flex-center" style="min-height: 300px">
          <q-spinner-dots :size="SPINNER_SIZE_PAGE" color="primary" />
        </div>

        <template v-else-if="issue">
          <!-- Issue meta card -->
          <div class="bg-white q-pa-md" style="border-bottom: 1px solid rgba(0,0,0,0.06)">
            <div class="row items-center q-gutter-sm">
              <StatusBadge :value="issue.status" />
              <StatusBadge :value="issue.priority" variant="priority" />
              <q-space />
              <div class="text-right">
                <div class="text-caption text-grey-5">Logged</div>
                <div class="text-caption text-weight-medium">{{ formatDate(issue.created_at) }}</div>
              </div>
            </div>
            <div class="text-caption text-grey-6 q-mt-xs">{{ issue.category }}</div>
          </div>

          <!-- Activity feed -->
          <div ref="scrollEl" class="q-pa-md" style="padding-bottom: 100px">
            <!-- Issue description -->
            <div class="text-center q-mb-sm">
              <span class="text-caption text-grey-5">Issue description</span>
            </div>
            <div class="chat-bubble-other q-mb-md" style="align-self: flex-start">
              <div>{{ issue.description }}</div>
            </div>

            <!-- Activities -->
            <template v-for="act in activities" :key="act.id">
              <!-- System message -->
              <div v-if="act.is_system || act.activity_type === 'status_change'" class="text-center q-my-sm">
                <q-chip size="sm" color="grey-2" text-color="grey-6">{{ act.message }}</q-chip>
              </div>
              <!-- User/agent message -->
              <div v-else class="column q-mb-sm" :class="isMyActivity(act) ? 'items-end' : 'items-start'">
                <div v-if="!isMyActivity(act)" class="text-caption text-grey-5 q-px-xs q-mb-xs">{{ act.created_by_name }}</div>
                <div :class="isMyActivity(act) ? 'chat-bubble-user' : 'chat-bubble-other'">
                  <div>{{ act.message }}</div>
                  <img v-if="act.file_url" :src="act.file_url" class="q-mt-sm rounded-borders" style="max-width: 200px" />
                </div>
                <div class="text-caption text-grey-4 q-px-xs" style="font-size: 10px">{{ formatTime(act.created_at) }}</div>
              </div>
            </template>

            <!-- WS connection indicator -->
            <div v-if="!wsConnected" class="text-center q-mt-sm">
              <span class="text-caption text-grey-5">Connecting...</span>
            </div>
          </div>

          <!-- Composer -->
          <div
            class="fixed-bottom bg-white q-pa-sm row items-end q-gutter-sm"
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
              placeholder="Write a message…"
              class="col"
              autogrow
              @keyup.enter.exact.prevent="sendActivityMessage"
            />
            <q-btn
              round
              flat
              icon="send"
              color="primary"
              :disable="!messageText.trim() && !pendingFile"
              @click="sendActivityMessage"
            />
          </div>
        </template>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { usePlatform } from '../composables/usePlatform'
import { useMaintenanceChatSocket } from '../composables/useMaintenanceChatSocket'
import type { MaintenanceActivity } from '../composables/useMaintenanceChatSocket'
import { useAuthStore } from '../stores/auth'
import StatusBadge from '../components/StatusBadge.vue'
import * as tenantApi from '../services/api'
import type { MaintenanceIssue } from '../services/api'
import { formatDate, formatTime } from '../utils/formatters'
import { SPINNER_SIZE_PAGE } from '../utils/designTokens'

const route = useRoute()
const auth  = useAuthStore()
const { isIos, backIcon, headerClass } = usePlatform()

const issueId = Number(route.params.id)

const issue       = ref<MaintenanceIssue | null>(null)
const loading     = ref(true)
const activities  = ref<MaintenanceActivity[]>([])
const seenIds     = new Set<number>()
const messageText = ref('')
const pendingFile = ref<File | null>(null)
const scrollEl    = ref<HTMLElement | null>(null)
const sending     = ref(false)

// ── Computed in component ─────────────────────────────────────────────────────
function isMyActivity(act: MaintenanceActivity) {
  return act.created_by_name === auth.user?.full_name
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

async function sendActivityMessage() {
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

    const res = await tenantApi.postActivity(issueId, form)
    addActivity(res.data as MaintenanceActivity)
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

onMounted(async () => {
  try {
    const res = await tenantApi.getIssue(issueId)
    issue.value = res.data
  } finally {
    loading.value = false
  }
})
</script>
