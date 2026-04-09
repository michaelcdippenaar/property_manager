<template>
  <div class="space-y-4">

    <!-- Loading -->
    <div v-if="loading" class="flex items-center gap-2 text-sm text-gray-400 py-4">
      <Loader2 :size="15" class="animate-spin" />
      Loading signing status…
    </div>

    <template v-else-if="submission">

      <!-- Header -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span v-if="submission.status === 'completed'" class="inline-flex items-center gap-1.5 text-sm font-medium text-green-700">
            <CheckCircle2 :size="15" />
            Mandate fully signed
          </span>
          <span v-else-if="submission.status === 'declined'" class="inline-flex items-center gap-1.5 text-sm font-medium text-red-600">
            <XCircle :size="15" />
            Signing declined
          </span>
          <span v-else class="text-sm font-medium text-gray-700">
            Signing in progress
            <span class="text-gray-400 font-normal ml-1">{{ signedCount }} of {{ totalSigners }} signed</span>
          </span>
          <!-- Live indicator -->
          <span
            v-if="submission.status !== 'completed' && submission.status !== 'declined'"
            class="inline-flex items-center gap-1 text-[10px]"
            :class="wsConnected ? 'text-green-500' : 'text-gray-300'"
          >
            <span class="w-1.5 h-1.5 rounded-full" :class="wsConnected ? 'bg-green-400 animate-pulse' : 'bg-gray-300'" />
            {{ wsConnected ? 'Live' : '' }}
          </span>
        </div>

        <!-- Download signed mandate -->
        <button
          v-if="submission.status === 'completed'"
          class="btn-ghost text-xs flex items-center gap-1"
          @click="downloadSigned"
        >
          <Download :size="12" />
          Download signed mandate
        </button>
      </div>

      <!-- Progress bar -->
      <div v-if="submission.status !== 'completed' && submission.status !== 'declined' && totalSigners > 0" class="w-full bg-gray-100 rounded-full h-1.5">
        <div
          class="bg-green-500 h-1.5 rounded-full transition-all duration-500"
          :style="{ width: `${(signedCount / totalSigners) * 100}%` }"
        />
      </div>

      <!-- Signer timeline -->
      <div class="space-y-0">
        <div
          v-for="(signer, idx) in submission.signers"
          :key="signer.id || idx"
          class="relative pl-7 pb-5 last:pb-0"
        >
          <!-- Vertical line -->
          <div
            v-if="idx < submission.signers.length - 1"
            class="absolute left-[11px] top-6 bottom-0 w-px"
            :class="isSignerDone(signer) ? 'bg-green-300' : 'bg-gray-200'"
          />

          <!-- Status dot -->
          <div
            class="absolute left-0 top-0.5 w-6 h-6 rounded-full flex items-center justify-center border-2"
            :class="signerDotClass(signer)"
          >
            <CheckCircle2 v-if="isSignerDone(signer)" :size="14" class="text-green-600" />
            <XCircle v-else-if="isSignerDeclined(signer)" :size="14" class="text-red-500" />
            <Eye v-else-if="isSignerViewing(signer)" :size="12" class="text-blue-600" />
            <Clock v-else :size="12" class="text-gray-400" />
          </div>

          <!-- Signer info -->
          <div class="min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-sm font-medium text-gray-900">{{ signer.name || signer.email }}</span>
              <span class="text-[11px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500 capitalize">{{ signer.role }}</span>
            </div>
            <div class="text-xs mt-0.5" :class="signerNarrativeColor(signer)">
              {{ signerNarrative(signer) }}
            </div>

            <!-- Actions -->
            <div
              v-if="!isSignerDone(signer) && !isSignerDeclined(signer) && submission.status !== 'completed' && submission.status !== 'declined'"
              class="flex items-center gap-2 mt-2"
            >
              <button
                v-if="signer.id && signer.email"
                type="button"
                class="btn-ghost text-xs py-1 px-2.5 flex items-center gap-1"
                :disabled="actionLoadingId === signer.id"
                @click="sendReminder(signer)"
              >
                <Loader2 v-if="actionLoadingId === signer.id" :size="11" class="animate-spin" />
                <Mail v-else :size="11" />
                Send reminder
              </button>
              <button
                v-if="signer.id"
                type="button"
                class="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1 transition-colors"
                :disabled="copyingLinkId === signer.id"
                @click="copyPublicLink(signer)"
              >
                <Loader2 v-if="copyingLinkId === signer.id" :size="11" class="animate-spin" />
                <Link2 v-else :size="11" />
                Copy link
              </button>
            </div>
          </div>
        </div>
      </div>

    </template>

    <div v-else class="text-sm text-gray-400 py-2">No signing submission found.</div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { CheckCircle2, XCircle, Eye, Clock, Download, Mail, Link2, Loader2 } from 'lucide-vue-next'
import api from '../../api'
import { useESigningSocket } from '../../composables/useESigningSocket'
import { useToast } from '../../composables/useToast'

const props = defineProps<{ submissionId: number }>()
const { showToast } = useToast()

const loading         = ref(false)
const submission      = ref<any>(null)
const actionLoadingId = ref<number | null>(null)
const copyingLinkId   = ref<number | null>(null)

// ── Live WebSocket ──────────────────────────────────────── //
const { connected: wsConnected } = useESigningSocket(
  () => submission.value?.id ?? null,
  (event) => {
    if (!submission.value) return
    if (event.signers) submission.value.signers = event.signers
    if (event.type === 'submission_completed') {
      submission.value.status = 'completed'
      if (event.signed_pdf_url) submission.value.signed_pdf_url = event.signed_pdf_url
      load()
      emit('signed')
    } else if (event.type === 'signer_completed') {
      load()
    } else if (event.type === 'signer_declined') {
      submission.value.status = 'declined'
    }
  },
)

const emit = defineEmits<{ (e: 'signed'): void }>()

const signedCount = computed(() =>
  (submission.value?.signers ?? []).filter((s: any) =>
    ['completed', 'signed'].includes((s.status ?? '').toLowerCase())
  ).length
)
const totalSigners = computed(() => (submission.value?.signers ?? []).length)

// ── Signer status helpers ── //
function isSignerDone(s: any)     { return ['completed', 'signed'].includes((s.status ?? '').toLowerCase()) }
function isSignerDeclined(s: any) { return (s.status ?? '').toLowerCase() === 'declined' }
function isSignerViewing(s: any)  { return ['viewing', 'in_progress'].includes((s.status ?? '').toLowerCase()) }

function signerDotClass(s: any) {
  if (isSignerDone(s))     return 'border-green-400 bg-green-50'
  if (isSignerDeclined(s)) return 'border-red-400 bg-red-50'
  if (isSignerViewing(s))  return 'border-blue-400 bg-blue-50'
  return 'border-gray-200 bg-white'
}

function signerNarrative(s: any) {
  const st = (s.status ?? '').toLowerCase()
  if (st === 'completed' || st === 'signed') return 'Signed'
  if (st === 'declined') return 'Declined to sign'
  if (st === 'viewing' || st === 'in_progress') return 'Currently viewing document…'
  return 'Waiting for signing link to be opened'
}

function signerNarrativeColor(s: any) {
  if (isSignerDone(s))     return 'text-green-600'
  if (isSignerDeclined(s)) return 'text-red-500'
  if (isSignerViewing(s))  return 'text-blue-600'
  return 'text-gray-400'
}

// ── Data loading ── //
async function load() {
  loading.value = true
  try {
    const { data } = await api.get(`/esigning/submissions/${props.submissionId}/`)
    submission.value = data
  } catch {
    showToast('Failed to load signing status', 'error')
  } finally {
    loading.value = false
  }
}

// ── Actions ── //
async function sendReminder(signer: any) {
  actionLoadingId.value = signer.id
  try {
    await api.post(`/esigning/submissions/${props.submissionId}/resend/`, { signer_role: signer.role })
    showToast(`Reminder sent to ${signer.name || signer.email}`, 'success')
  } catch {
    showToast('Failed to send reminder', 'error')
  } finally {
    actionLoadingId.value = null
  }
}

async function copyPublicLink(signer: any) {
  copyingLinkId.value = signer.id
  try {
    const { data } = await api.post(`/esigning/submissions/${props.submissionId}/public-link/`, {
      signer_role: signer.role,
      public_app_origin: window.location.origin,
    })
    const path = (data.sign_path as string) || `/sign/${data.uuid}/`
    const full = (data.signing_url as string) || data.url || `${window.location.origin}${path}`
    await navigator.clipboard.writeText(full)
    showToast('Signing link copied to clipboard', 'success')
  } catch {
    showToast('Failed to copy link', 'error')
  } finally {
    copyingLinkId.value = null
  }
}

async function downloadSigned() {
  try {
    const { data } = await api.get(`/esigning/submissions/${props.submissionId}/download/`, {
      responseType: 'blob',
    })
    const url  = URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href  = url
    link.download = 'signed_mandate.pdf'
    link.click()
    URL.revokeObjectURL(url)
  } catch {
    showToast('Download failed', 'error')
  }
}

onMounted(load)
</script>
