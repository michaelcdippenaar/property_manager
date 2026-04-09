<template>
  <div class="space-y-4">

    <!-- Loading -->
    <div v-if="loading" class="flex items-center gap-2 text-sm text-gray-400 py-4">
      <Loader2 :size="15" class="animate-spin" />
      Loading…
    </div>

    <!-- ── Active submission: signing timeline ── -->
    <template v-else-if="latestSub">

      <!-- Header with progress -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span v-if="latestSub.status === 'completed'" class="inline-flex items-center gap-1.5 text-sm font-medium text-green-700">
            <CheckCircle2 :size="15" />
            Lease fully signed
          </span>
          <span v-else-if="latestSub.status === 'declined'" class="inline-flex items-center gap-1.5 text-sm font-medium text-red-600">
            <XCircle :size="15" />
            Signing declined
          </span>
          <span v-else class="text-sm font-medium text-gray-700">
            Signing progress
            <span class="text-gray-400 font-normal ml-1">{{ signedCount }} of {{ totalSigners }} signed</span>
          </span>
          <!-- Live connection indicator -->
          <span
            v-if="latestSub.status !== 'completed' && latestSub.status !== 'declined'"
            class="inline-flex items-center gap-1 text-[10px]"
            :class="wsConnected ? 'text-green-500' : 'text-gray-300'"
            :title="wsConnected ? 'Live updates active' : 'Reconnecting…'"
          >
            <span class="w-1.5 h-1.5 rounded-full" :class="wsConnected ? 'bg-green-400 animate-pulse' : 'bg-gray-300'" />
            {{ wsConnected ? 'Live' : '' }}
          </span>
        </div>
        <a
          v-if="latestSub.signed_pdf_url || latestSub.status === 'completed'"
          href="#"
          @click.prevent="downloadSignedPdf"
          class="btn-ghost text-xs flex items-center gap-1"
        >
          <Download :size="12" />
          Download signed PDF
        </a>
      </div>

      <!-- Progress bar -->
      <div v-if="latestSub.status !== 'completed' && latestSub.status !== 'declined'" class="w-full bg-gray-100 rounded-full h-1.5">
        <div
          class="bg-green-500 h-1.5 rounded-full transition-all duration-500"
          :style="{ width: `${(signedCount / totalSigners) * 100}%` }"
        />
      </div>

      <!-- Signer timeline -->
      <div class="space-y-0">
        <div
          v-for="(signer, idx) in latestSub.signers"
          :key="signer.id || idx"
          class="relative pl-7 pb-5 last:pb-0"
        >
          <!-- Vertical line -->
          <div
            v-if="idx < latestSub.signers.length - 1"
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
              <span class="text-[11px] text-gray-400">{{ signer.role }}</span>
            </div>

            <!-- Status narrative -->
            <div class="text-xs mt-0.5" :class="signerNarrativeColor(signer)">
              {{ signerNarrative(signer) }}
            </div>

            <!-- Action: only for unsigned signers on active submissions -->
            <div
              v-if="!isSignerDone(signer) && !isSignerDeclined(signer) && latestSub.status !== 'completed' && latestSub.status !== 'declined'"
              class="flex items-center gap-2 mt-2"
            >
              <button
                v-if="signer.id && signer.email"
                type="button"
                class="btn-ghost text-xs py-1 px-2.5 flex items-center gap-1"
                :disabled="actionLoadingId === signer.id"
                @click="sendReminder(latestSub.id, signer)"
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
                @click="copyPublicLink(latestSub.id, signer)"
              >
                <Loader2 v-if="copyingLinkId === signer.id" :size="11" class="animate-spin" />
                <Link2 v-else :size="11" />
                Copy link
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Landlord can sign — shown when all tenants have signed -->
      <div
        v-if="landlordCanSign"
        class="flex items-center gap-3 px-4 py-3 bg-blue-50 border border-blue-200 rounded-xl mt-2"
      >
        <div class="flex-1 min-w-0">
          <div class="text-sm font-semibold text-blue-900">All tenants have signed</div>
          <div class="text-xs text-blue-600 mt-0.5">The landlord can now review and sign the lease</div>
        </div>
        <button
          class="btn-primary text-xs flex items-center gap-1.5 flex-shrink-0"
          :disabled="landlordLinkLoading"
          @click="openLandlordSigningLink"
        >
          <Loader2 v-if="landlordLinkLoading" :size="12" class="animate-spin" />
          <PenTool v-else :size="12" />
          Sign as Landlord
        </button>
      </div>

      <!-- Cancel pending submission — only allowed before anyone has signed -->
      <button
        v-if="latestSub && latestSub.status !== 'completed' && latestSub.status !== 'declined' && signedCount === 0"
        class="text-xs text-red-400 hover:text-red-600 flex items-center gap-1 mt-2 transition-colors"
        @click="cancelSubmission"
      >
        <X :size="11" />
        Cancel signing request
      </button>

      <!-- Send again (only if previous is done/declined/expired) -->
      <button
        v-if="canSendAgain"
        class="btn-ghost text-xs flex items-center gap-1.5 w-full justify-center py-2 border-dashed border border-gray-200 rounded-xl mt-2"
        @click="openModal"
      >
        <Send :size="13" />
        Send for signing again
      </button>
    </template>

    <!-- ── Empty state: no submissions yet ── -->
    <div v-else class="text-center py-6">
      <div class="w-12 h-12 rounded-full bg-navy/5 flex items-center justify-center mx-auto mb-3">
        <Send :size="20" class="text-navy" />
      </div>
      <div class="text-sm font-medium text-gray-800">Ready to send for signing</div>
      <p class="text-xs text-gray-400 mt-1 mb-4 max-w-xs mx-auto">
        Send this lease to your tenants to review and sign electronically. They'll get an email with a link.
      </p>
      <button class="btn-primary text-xs flex items-center gap-1.5 mx-auto" @click="openModal">
        <Send :size="13" />
        Send for Signing
      </button>
    </div>

    <!-- Error banner -->
    <div
      v-if="errorMsg"
      class="flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700"
    >
      <AlertCircle :size="14" class="flex-shrink-0" />
      {{ errorMsg }}
    </div>

    <div
      v-if="linkHint"
      class="flex items-center gap-2 px-4 py-3 bg-green-50 border border-green-200 rounded-xl text-sm text-green-800"
    >
      <CheckCircle2 :size="14" class="flex-shrink-0" />
      {{ linkHint }}
    </div>

    <!-- Create submission modal -->
    <BaseModal :open="showModal" size="lg" @close="closeModal">
      <template #header>
        <div class="flex items-center gap-2">
          <Send :size="16" class="text-navy" />
          <span class="font-semibold text-gray-900 text-sm">Send Lease for Signing</span>
        </div>
      </template>

      <div class="space-y-4">
        <p class="text-xs text-gray-500">
          Each signer will receive an email with a link to review and sign the lease document.
        </p>

        <!-- Signer list -->
        <div class="space-y-3">
          <div
            v-for="(signer, idx) in draftSigners"
            :key="idx"
            class="rounded-xl border p-4 space-y-3"
            :class="!signer.email ? 'border-amber-300 bg-amber-50/40' : 'border-gray-200'"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-xs font-semibold text-gray-600">Signer {{ idx + 1 }}</span>
                <span
                  v-if="!signer.email"
                  class="text-micro px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 font-medium"
                >
                  Email required
                </span>
              </div>
              <button
                v-if="draftSigners.length > 1"
                class="text-xs text-red-400 hover:text-red-600 transition-colors"
                @click="removeSigner(idx)"
              >
                Remove
              </button>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div class="col-span-2">
                <label class="label">Full Name</label>
                <input v-model="signer.name" class="input" placeholder="Full legal name" />
              </div>
              <div class="col-span-2">
                <label class="label">Email *</label>
                <input
                  v-model="signer.email"
                  type="email"
                  class="input"
                  :class="!signer.email ? 'border-amber-400 focus:border-amber-500' : ''"
                  placeholder="signer@example.com"
                />
              </div>
              <div>
                <label class="label">Phone</label>
                <input v-model="signer.phone" type="tel" class="input" placeholder="+27 …" />
              </div>
              <div>
                <label class="label">Role</label>
                <input v-model="signer.role" class="input" placeholder="e.g. Tenant" />
              </div>
            </div>

            <!-- Per-signer options -->
            <div class="flex flex-wrap items-center gap-4 pt-1">
              <label class="flex items-center gap-2 text-xs text-gray-600 cursor-pointer select-none">
                <input type="checkbox" v-model="signer.send_email" class="rounded" />
                Send invitation email
              </label>
              <label
                v-if="signer.personId"
                class="flex items-center gap-2 text-xs text-gray-600 cursor-pointer select-none"
              >
                <input type="checkbox" v-model="signer.saveToRecord" class="rounded" />
                Save contact to tenant record
              </label>
            </div>

            <!-- Required documents -->
            <div class="pt-2 border-t border-gray-100">
              <p class="text-micro font-medium text-gray-500 mb-1.5 uppercase tracking-wide">Required Documents</p>
              <div class="flex flex-wrap gap-3">
                <label
                  v-for="doc in SIGNER_DOC_TYPES"
                  :key="doc.key"
                  class="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer select-none"
                >
                  <input
                    type="checkbox"
                    class="rounded"
                    :checked="(signer.required_documents ?? []).includes(doc.key)"
                    @change="toggleSignerDoc(signer, doc.key, ($event.target as HTMLInputElement).checked)"
                  />
                  {{ doc.label }}
                </label>
              </div>
            </div>
          </div>
        </div>

        <button
          class="btn-ghost text-xs flex items-center gap-1.5 w-full justify-center py-2 border-dashed border border-gray-200 rounded-xl"
          @click="addSigner"
        >
          <Plus :size="13" />
          Add Another Signer
        </button>
      </div>

      <template #footer>
        <button class="btn-ghost" @click="closeModal">Cancel</button>
        <button
          class="btn-primary flex items-center gap-2"
          :disabled="submitting || !canSubmit"
          @click="submitSigning"
        >
          <Loader2 v-if="submitting" :size="14" class="animate-spin" />
          <Send v-else :size="14" />
          Send for Signing
        </button>
      </template>
    </BaseModal>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import api from '../../api'
import {
  Send, Mail, CheckCircle2, Clock, XCircle, AlertCircle, Eye,
  Plus, Loader2, Download, Link2, Wifi, WifiOff, PenTool, X,
} from 'lucide-vue-next'
import BaseModal from '../../components/BaseModal.vue'
import { useESigningSocket } from '../../composables/useESigningSocket'

// ── Document type config ─────────────────────────────────────────────── //
const SIGNER_DOC_TYPES = [
  { key: 'bank_statement',   label: 'Bank Statement (3 months)' },
  { key: 'id_copy',          label: 'Copy of ID / Passport' },
  { key: 'proof_of_address', label: 'Proof of Address' },
]

function toggleSignerDoc(signer: DraftSigner, key: string, checked: boolean) {
  const docs = [...(signer.required_documents ?? [])]
  if (checked && !docs.includes(key)) docs.push(key)
  else if (!checked) { const i = docs.indexOf(key); if (i > -1) docs.splice(i, 1) }
  signer.required_documents = docs
}

const props = defineProps<{
  leaseId: number
  leaseTenants?: any[]
  leaseData?: any
  autoOpen?: boolean
}>()

const emit = defineEmits<{ signed: [] }>()

// ── State ────────────────────────────────────────────────────────────── //
const submissions = ref<any[]>([])
const loading     = ref(false)
const errorMsg    = ref('')
const showModal   = ref(false)
const submitting  = ref(false)
const actionLoadingId = ref<number | string | null>(null)
const copyingLinkId = ref<number | string | null>(null)
const linkHint = ref('')

interface DraftSigner {
  name: string
  email: string
  phone: string
  role: string
  send_email: boolean
  personId?: number
  saveToRecord?: boolean
  required_documents?: string[]
}
const draftSigners = ref<DraftSigner[]>([])

// ── Computed ─────────────────────────────────────────────────────────── //
const latestSub = computed(() => submissions.value[0] ?? null)

const totalSigners = computed(() => latestSub.value?.signers?.length ?? 0)

const signedCount = computed(() =>
  (latestSub.value?.signers ?? []).filter((s: any) => isSignerDone(s)).length
)

const canSubmit = computed(() =>
  draftSigners.value.length > 0 &&
  draftSigners.value.every(s => s.name.trim() && s.email.trim())
)

// ── Real-time WebSocket updates ──────────────────────────────────────── //
const { connected: wsConnected } = useESigningSocket(
  () => latestSub.value?.id ?? null,
  (event) => {
    if (!latestSub.value) return
    if (event.signers) {
      latestSub.value.signers = event.signers
    }
    if (event.type === 'submission_completed') {
      latestSub.value.status = 'completed'
      if (event.signed_pdf_url) {
        latestSub.value.signed_pdf_url = event.signed_pdf_url
      }
      loadSubmissions()
      emit('signed')
    } else if (event.type === 'signer_completed') {
      // Reload to get accurate completed_at timestamps
      loadSubmissions()
    } else if (event.type === 'signer_declined') {
      latestSub.value.status = 'declined'
    }
  },
)

const canSendAgain = computed(() => {
  if (!latestSub.value) return false
  return ['declined', 'expired'].includes(latestSub.value.status)
})

// Landlord can sign: all non-landlord signers done, landlord still pending
const landlordSigner = computed(() => {
  if (!latestSub.value?.signers) return null
  return latestSub.value.signers.find((s: any) => {
    const role = (s.role ?? '').toLowerCase()
    return role.includes('landlord') || role.includes('lessor') || role.includes('owner')
  }) ?? null
})

const landlordCanSign = computed(() => {
  if (!latestSub.value || latestSub.value.status === 'completed' || latestSub.value.status === 'declined') return false
  const ls = landlordSigner.value
  if (!ls || isSignerDone(ls)) return false
  // Check all other signers are done
  return latestSub.value.signers
    .filter((s: any) => s !== ls)
    .every((s: any) => isSignerDone(s))
})

const landlordLinkLoading = ref(false)

// ── Lifecycle ────────────────────────────────────────────────────────── //
onMounted(async () => {
  await loadSubmissions()
  if (props.autoOpen && !submissions.value.length) {
    openModal()
  }
})

// Poll for updates when WS is disconnected and submission is active
let pollTimer: ReturnType<typeof setInterval> | null = null
watch(() => latestSub.value?.status, (status) => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (status === 'pending' || status === 'in_progress') {
    pollTimer = setInterval(() => {
      if (!wsConnected.value) loadSubmissions()
    }, 10_000)
  }
}, { immediate: true })
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })

// ── Signer status helpers ───────────────────────────────────────────── //
function isSignerDone(s: any): boolean {
  const st = (s.status ?? '').toLowerCase()
  return st === 'completed' || st === 'signed'
}

function isSignerDeclined(s: any): boolean {
  return (s.status ?? '').toLowerCase() === 'declined'
}

function isSignerViewing(s: any): boolean {
  return (s.status ?? '').toLowerCase() === 'opened'
}

function signerDotClass(s: any): string {
  if (isSignerDone(s)) return 'border-green-500 bg-green-50'
  if (isSignerDeclined(s)) return 'border-red-400 bg-red-50'
  if (isSignerViewing(s)) return 'border-blue-400 bg-blue-50'
  return 'border-gray-300 bg-white'
}

function signerNarrative(s: any): string {
  const name = s.name?.split(' ')[0] || 'Signer'
  const st = (s.status ?? '').toLowerCase()
  if (st === 'completed' || st === 'signed') {
    return s.completed_at
      ? `${name} signed on ${formatDate(s.completed_at)}`
      : `${name} signed`
  }
  if (st === 'declined') return `${name} declined to sign`
  if (st === 'opened') return `${name} viewed the lease — waiting for signature`
  return `Lease sent — waiting for ${name} to open`
}

function signerNarrativeColor(s: any): string {
  const st = (s.status ?? '').toLowerCase()
  if (st === 'completed' || st === 'signed') return 'text-green-600'
  if (st === 'declined') return 'text-red-500'
  if (st === 'opened') return 'text-blue-600'
  return 'text-gray-400'
}

// ── API ──────────────────────────────────────────────────────────────── //
async function loadSubmissions() {
  if (!props.leaseId) return
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await api.get('/esigning/submissions/', {
      params: { lease_id: props.leaseId },
    })
    submissions.value = data.results ?? data
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.error ?? 'Failed to load submissions'
  } finally {
    loading.value = false
  }
}

async function submitSigning() {
  if (!canSubmit.value) return
  submitting.value = true
  errorMsg.value = ''
  try {
    const savePromises = draftSigners.value
      .filter(s => s.personId && s.saveToRecord)
      .map(s => api.patch(`/auth/persons/${s.personId}/`, {
        full_name: s.name,
        email: s.email,
        phone: s.phone,
      }))
    if (savePromises.length) await Promise.allSettled(savePromises)

    const { data } = await api.post('/esigning/submissions/', {
      lease_id: props.leaseId,
      signers: draftSigners.value,
    })
    submissions.value.unshift(data)
    closeModal()
    emit('signed')
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.error ?? 'Failed to create submission'
  } finally {
    submitting.value = false
  }
}

async function sendReminder(submissionId: number, signer: any) {
  actionLoadingId.value = signer.id
  errorMsg.value = ''
  linkHint.value = ''
  try {
    const { data } = await api.post(`/esigning/submissions/${submissionId}/public-link/`, {
      signer_role: signer.role,
      send_email: true,
      public_app_origin: window.location.origin,
    })
    if (data.email_sent) {
      linkHint.value = `Reminder sent to ${signer.name || signer.email}`
      window.setTimeout(() => { linkHint.value = '' }, 5000)
    } else {
      errorMsg.value = (data.email_error as string) || 'Could not send reminder email'
    }
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.error ?? e?.response?.data?.detail ?? 'Could not send reminder'
  } finally {
    actionLoadingId.value = null
  }
}

async function copyPublicLink(submissionId: number, signer: any) {
  copyingLinkId.value = signer.id ?? signer.role
  errorMsg.value = ''
  linkHint.value = ''
  try {
    const { data } = await api.post(`/esigning/submissions/${submissionId}/public-link/`, {
      signer_role: signer.role,
      public_app_origin: window.location.origin,
    })
    const path = (data.sign_path as string) || `/sign/${data.uuid}/`
    const full = (data.signing_url as string) || `${window.location.origin}${path}`
    try {
      await navigator.clipboard.writeText(full)
      linkHint.value = 'Signing link copied to clipboard'
    } catch {
      // Clipboard blocked — show the URL so user can copy manually
      linkHint.value = full
    }
    window.setTimeout(() => { linkHint.value = '' }, 15000)
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.error ?? e?.response?.data?.detail ?? 'Could not create signing link'
  } finally {
    copyingLinkId.value = null
  }
}

async function cancelSubmission() {
  if (!latestSub.value) return
  if (!confirm('Cancel this signing request? All signing links will be invalidated.')) return
  try {
    await api.delete(`/esigning/submissions/${latestSub.value.id}/`)
    submissions.value = submissions.value.filter((s: any) => s.id !== latestSub.value.id)
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail ?? 'Could not cancel submission'
  }
}

async function downloadSignedPdf() {
  if (!latestSub.value) return
  try {
    const { data } = await api.get(`/esigning/submissions/${latestSub.value.id}/download/`)
    if (data.url) {
      window.open(data.url, '_blank')
    }
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail ?? 'Could not fetch signed document'
  }
}

async function openLandlordSigningLink() {
  const ls = landlordSigner.value
  if (!ls?.role || !latestSub.value) return
  landlordLinkLoading.value = true
  errorMsg.value = ''
  // Open the window synchronously while still inside the click gesture so the
  // browser doesn't treat it as a popup and block it. We'll set the URL once
  // the API call resolves.
  const win = window.open('', '_blank')
  try {
    const { data } = await api.post(`/esigning/submissions/${latestSub.value.id}/public-link/`, {
      signer_role: ls.role,
      public_app_origin: window.location.origin,
    })
    const path = (data.sign_path as string) || `/sign/${data.uuid}/`
    const full = (data.signing_url as string) || `${window.location.origin}${path}`
    if (win) {
      win.location.href = full
    } else {
      window.open(full, '_blank')
    }
  } catch (e: any) {
    win?.close()
    errorMsg.value = e?.response?.data?.error ?? e?.response?.data?.detail ?? 'Could not create signing link'
  } finally {
    landlordLinkLoading.value = false
  }
}

// ── Modal helpers ────────────────────────────────────────────────────── //
function buildDefaultSigners(): DraftSigner[] {
  const tenants = props.leaseTenants ?? []
  if (!tenants.length) {
    // Pre-populated test defaults (remove before production)
    return [
      { name: 'Marius du Plessis', email: 'mc@tremly.com', phone: '0821234567', role: 'Tenant', send_email: true },
    ]
  }
  const signers: DraftSigner[] = tenants.map((t, i) => ({
    name:               t.person?.full_name ?? t.full_name ?? '',
    email:              t.person?.email     ?? t.email     ?? '',
    phone:              t.person?.phone     ?? t.phone     ?? '',
    role:               i === 0 ? 'Tenant' : 'Co-Tenant',
    send_email:         true,
    personId:           t.person?.id ?? t.id ?? undefined,
    saveToRecord:       false,
    // Default to all doc types when not set — agent can untick in the modal
    required_documents: t.required_documents?.length ? t.required_documents : SIGNER_DOC_TYPES.map(d => d.key),
  }))

  // Auto-add landlord as last signer
  const ll = props.leaseData?.landlord_info
  if (ll?.email) {
    signers.push({
      name: ll.name ?? '', email: ll.email ?? '', phone: ll.phone ?? '',
      role: 'Landlord', send_email: false,
    })
  }
  return signers
}

function openModal() {
  draftSigners.value = buildDefaultSigners()
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  draftSigners.value = []
  errorMsg.value = ''
  linkHint.value = ''
}

function addSigner() {
  draftSigners.value.push({
    name: '', email: '', phone: '', role: 'Signer', send_email: true,
    required_documents: SIGNER_DOC_TYPES.map(d => d.key),
  })
}

function removeSigner(idx: number) {
  draftSigners.value.splice(idx, 1)
}

// ── Display helpers ──────────────────────────────────────────────────── //
function formatDate(d: string) {
  if (!d) return ''
  const dt = new Date(d)
  const date = dt.toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })
  const time = dt.toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' })
  return `${date} at ${time}`
}

// Expose openModal so parent can trigger it via ref
defineExpose({ openModal })
</script>
