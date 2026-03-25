<template>
  <div class="space-y-4">

    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2 text-sm text-gray-700">
        <FileSignature :size="16" class="text-navy" />
        <span class="font-medium">Signing Submissions</span>
        <span v-if="submissions.length" class="text-xs text-gray-400">({{ submissions.length }})</span>
      </div>
      <button class="btn-primary text-xs flex items-center gap-1.5" @click="openModal">
        <Send :size="13" />
        Send for Signing
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center gap-2 text-sm text-gray-400 py-4">
      <Loader2 :size="15" class="animate-spin" />
      Loading submissions…
    </div>

    <!-- Submission list -->
    <div v-else-if="submissions.length" class="space-y-3">
      <div
        v-for="sub in submissions"
        :key="sub.id"
        class="rounded-xl border border-gray-200 bg-white overflow-hidden"
      >
        <!-- Submission header -->
        <div class="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-100">
          <div class="flex items-center gap-2">
            <span
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
              :class="statusBadgeClass(sub.status)"
            >
              <component :is="statusIcon(sub.status)" :size="11" />
              {{ statusLabel(sub.status) }}
            </span>
            <span class="text-xs text-gray-400">{{ formatDate(sub.created_at) }}</span>
          </div>
          <a
            v-if="sub.signed_pdf_url"
            :href="sub.signed_pdf_url"
            target="_blank"
            class="text-xs text-navy hover:underline flex items-center gap-1"
          >
            <Download :size="12" />
            Signed PDF
          </a>
        </div>

        <!-- Signer rows -->
        <div class="divide-y divide-gray-100">
          <div
            v-for="signer in sub.signers"
            :key="signer.id"
            class="flex items-center gap-3 px-4 py-2.5"
          >
            <div class="w-6 h-6 rounded-full bg-navy/10 flex items-center justify-center flex-shrink-0">
              <component
                :is="signerStatusIcon(signer.status)"
                :size="12"
                :class="signerStatusColor(signer.status)"
              />
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-gray-800">{{ signer.name || signer.email }}</div>
              <div class="text-xs text-gray-400">{{ signer.email }} · {{ signer.role }}</div>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-xs" :class="signerStatusColor(signer.status)">
                {{ signerStatusLabel(signer.status) }}
              </span>
              <button
                v-if="signer.id && sub.status !== 'completed'"
                class="btn-ghost text-xs py-1 px-2 flex items-center gap-1"
                :disabled="resendingId === signer.id"
                @click="resend(sub.id, signer.id)"
              >
                <Loader2 v-if="resendingId === signer.id" :size="11" class="animate-spin" />
                <RefreshCw v-else :size="11" />
                Resend
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="flex flex-col items-center justify-center py-8 text-center text-gray-400">
      <FileSignature :size="28" class="mb-2 opacity-40" />
      <p class="text-sm">No signing submissions yet</p>
      <p class="text-xs mt-1">Click "Send for Signing" to start the e-signing process</p>
    </div>

    <!-- Error banner -->
    <div
      v-if="errorMsg"
      class="flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700"
    >
      <AlertCircle :size="14" class="flex-shrink-0" />
      {{ errorMsg }}
    </div>

    <!-- Create submission modal -->
    <Teleport to="body">
      <div v-if="showModal" class="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/40">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg flex flex-col max-h-[90vh]">

          <!-- Modal header -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 flex-shrink-0">
            <div class="flex items-center gap-2">
              <Send :size="16" class="text-navy" />
              <span class="font-semibold text-gray-900 text-sm">Send Lease for Signing</span>
            </div>
            <button class="p-1 text-gray-400 hover:text-gray-600 transition-colors" @click="closeModal">
              <X :size="18" />
            </button>
          </div>

          <!-- Modal body -->
          <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
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
                      class="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 font-medium"
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

          <!-- Modal footer -->
          <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 flex-shrink-0">
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
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import {
  Send, Mail, CheckCircle2, Clock, XCircle, AlertCircle,
  Plus, Loader2, FileSignature, RefreshCw, X, Download,
} from 'lucide-vue-next'

const props = defineProps<{
  leaseId: number
  leaseTenants?: any[]
}>()

const emit = defineEmits<{ signed: [] }>()

// ── State ────────────────────────────────────────────────────────────── //
const submissions = ref<any[]>([])
const loading     = ref(false)
const errorMsg    = ref('')
const showModal   = ref(false)
const submitting  = ref(false)
const resendingId = ref<number | string | null>(null)

interface DraftSigner {
  name: string
  email: string
  phone: string
  role: string
  send_email: boolean
  personId?: number        // set when pre-populated from a known tenant
  saveToRecord?: boolean   // if true, PATCH the person record on submit
}
const draftSigners = ref<DraftSigner[]>([])

// ── Computed ─────────────────────────────────────────────────────────── //
const canSubmit = computed(() =>
  draftSigners.value.length > 0 &&
  draftSigners.value.every(s => s.name.trim() && s.email.trim())
)

// ── Lifecycle ────────────────────────────────────────────────────────── //
onMounted(loadSubmissions)

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
    // Save updated contact details back to person records where requested
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

async function resend(submissionId: number, submitterId: number | string) {
  resendingId.value = submitterId
  errorMsg.value = ''
  try {
    await api.post(`/esigning/submissions/${submissionId}/resend/`, {
      submitter_id: submitterId,
    })
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.error ?? 'Failed to resend invitation'
  } finally {
    resendingId.value = null
  }
}

// ── Modal helpers ────────────────────────────────────────────────────── //
function buildDefaultSigners(): DraftSigner[] {
  const tenants = props.leaseTenants ?? []
  if (!tenants.length) {
    return [{ name: '', email: '', phone: '', role: 'Tenant', send_email: true }]
  }
  return tenants.map((t, i) => ({
    name:         t.person?.full_name ?? t.full_name ?? '',
    email:        t.person?.email     ?? t.email     ?? '',
    phone:        t.person?.phone     ?? t.phone     ?? '',
    role:         i === 0 ? 'Tenant' : 'Co-Tenant',
    send_email:   true,
    personId:     t.person?.id ?? t.id ?? undefined,
    saveToRecord: false,
  }))
}

function openModal() {
  draftSigners.value = buildDefaultSigners()
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  draftSigners.value = []
  errorMsg.value = ''
}

function addSigner() {
  draftSigners.value.push({ name: '', email: '', phone: '', role: 'Signer', send_email: true })
}

function removeSigner(idx: number) {
  draftSigners.value.splice(idx, 1)
}

// ── Display helpers ──────────────────────────────────────────────────── //
function statusLabel(s: string) {
  const map: Record<string, string> = {
    pending:     'Pending',
    in_progress: 'In Progress',
    completed:   'Completed',
    declined:    'Declined',
    expired:     'Expired',
  }
  return map[s] ?? s
}

function statusBadgeClass(s: string) {
  const map: Record<string, string> = {
    pending:     'bg-gray-100 text-gray-600',
    in_progress: 'bg-blue-100 text-blue-700',
    completed:   'bg-green-100 text-green-700',
    declined:    'bg-red-100 text-red-700',
    expired:     'bg-amber-100 text-amber-700',
  }
  return map[s] ?? 'bg-gray-100 text-gray-600'
}

function statusIcon(s: string) {
  const map: Record<string, any> = {
    pending:     Clock,
    in_progress: Loader2,
    completed:   CheckCircle2,
    declined:    XCircle,
    expired:     AlertCircle,
  }
  return map[s] ?? Clock
}

function signerStatusIcon(s: string) {
  if (s === 'completed' || s === 'signed') return CheckCircle2
  if (s === 'declined') return XCircle
  return Mail
}

function signerStatusColor(s: string) {
  if (s === 'completed' || s === 'signed') return 'text-green-600'
  if (s === 'declined') return 'text-red-500'
  return 'text-gray-400'
}

function signerStatusLabel(s: string) {
  const map: Record<string, string> = {
    sent:      'Sent',
    opened:    'Opened',
    completed: 'Signed',
    signed:    'Signed',
    declined:  'Declined',
  }
  return map[s] ?? s
}

function formatDate(d: string) {
  return d
    ? new Date(d).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' })
    : '—'
}
</script>
