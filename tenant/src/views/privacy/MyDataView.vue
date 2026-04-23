<template>
  <div class="flex flex-col h-full overflow-hidden bg-surface" name="MyDataView">
    <AppHeader title="My Data" :show-back="true" @back="router.back()" />

    <div class="scroll-page page-with-tab-bar px-4 pt-4 pb-8 space-y-5">

      <!-- POPIA info card -->
      <div class="list-section p-4 space-y-2">
        <div class="flex items-start gap-3">
          <div class="w-10 h-10 rounded-full bg-navy/10 flex items-center justify-center flex-shrink-0 mt-0.5">
            <ShieldCheck :size="20" class="text-navy" />
          </div>
          <div>
            <p class="text-sm font-semibold text-gray-900">Your data rights</p>
            <p class="text-xs text-gray-500 mt-1 leading-relaxed">
              Under the Protection of Personal Information Act (POPIA), you have the right
              to access a copy of all personal information we hold about you, and to request
              that we delete your account. Some records may be retained for legal compliance.
            </p>
          </div>
        </div>
      </div>

      <!-- Download my data -->
      <div>
        <p class="list-section-header px-1 pt-0 pb-1">Section 23 — Access</p>
        <div class="list-section">
          <div class="p-4 space-y-3">
            <div>
              <p class="text-sm font-semibold text-gray-900">Download my data</p>
              <p class="text-xs text-gray-500 mt-0.5 leading-relaxed">
                Request a copy of all personal information held about you — profile,
                leases, payments, maintenance history, and account activity.
                You will receive an email with a secure download link within a few minutes.
              </p>
            </div>

            <!-- Existing SAR request status -->
            <div
              v-if="pendingSAR"
              class="bg-blue-50 rounded-xl p-3 text-sm text-blue-700 flex items-center gap-2"
            >
              <Loader2 v-if="pendingSAR.status === 'in_review'" :size="16" class="animate-spin flex-shrink-0" />
              <CheckCircle v-else :size="16" class="flex-shrink-0 text-success-600" />
              <span>
                <span v-if="pendingSAR.status === 'in_review'">Your export is being compiled…</span>
                <span v-else-if="pendingSAR.status === 'completed'">Your export was sent to {{ pendingSAR.requester_email }}</span>
                <span v-else>Export request submitted — check your email shortly.</span>
              </span>
            </div>

            <button
              class="btn-primary w-full"
              :disabled="!!pendingSAR || exportLoading"
              @click="requestExport"
            >
              <Download :size="16" />
              <span v-if="exportLoading">Requesting…</span>
              <span v-else-if="pendingSAR">Export in progress</span>
              <span v-else>Download my data</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Delete my account -->
      <div>
        <p class="list-section-header px-1 pt-0 pb-1">Section 24 — Erasure</p>
        <div class="list-section">
          <div class="p-4 space-y-3">
            <div>
              <p class="text-sm font-semibold text-gray-900">Delete my account</p>
              <p class="text-xs text-gray-500 mt-0.5 leading-relaxed">
                Request that your personal information be removed from Klikk.
                An operator will review your request within 30 days. Some records
                (lease agreements, payments) are retained as required by law.
              </p>
            </div>

            <!-- Existing RTBF request status -->
            <div
              v-if="pendingRTBF"
              class="bg-amber-50 rounded-xl p-3 text-sm text-amber-700 flex items-center gap-2"
            >
              <Clock :size="16" class="flex-shrink-0" />
              <span>
                Erasure request pending review — due by
                {{ formatDate(pendingRTBF.sla_deadline) }}.
                We will notify you by email.
              </span>
            </div>

            <button
              v-if="!pendingRTBF"
              class="btn-danger w-full"
              :disabled="erasureLoading"
              @click="confirmErasure = true"
            >
              <Trash2 :size="16" />
              Delete my account
            </button>
          </div>
        </div>
      </div>

      <!-- Past requests -->
      <div v-if="pastRequests.length">
        <p class="list-section-header px-1 pt-0 pb-1">Request history</p>
        <div class="list-section divide-y divide-gray-100">
          <div
            v-for="r in pastRequests"
            :key="r.id"
            class="flex items-center gap-3 px-4 py-3"
          >
            <div
              :class="r.request_type === 'rtbf' ? 'bg-accent/10' : 'bg-navy/10'"
              class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
            >
              <Trash2 v-if="r.request_type === 'rtbf'" :size="14" class="text-accent" />
              <Download v-else :size="14" class="text-navy" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900">
                {{ r.request_type === 'rtbf' ? 'Erasure request' : 'Data export' }}
              </p>
              <p class="text-xs text-gray-500">{{ formatDate(r.created_at) }}</p>
            </div>
            <span
              :class="statusChipClass(r.status)"
              class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize"
            >
              {{ r.status.replace('_', ' ') }}
            </span>
          </div>
        </div>
      </div>

      <!-- Contact -->
      <div class="list-section p-4 text-center space-y-1">
        <p class="text-xs text-gray-500">Information Officer:</p>
        <a href="mailto:privacy@klikk.co.za" class="text-xs text-navy font-medium">
          privacy@klikk.co.za
        </a>
        <p class="text-xs text-gray-400">
          You may also lodge a complaint with the Information Regulator at
          complaints.IR@justice.gov.za
        </p>
      </div>
    </div>

    <!-- Erasure confirmation bottom sheet -->
    <div
      v-if="confirmErasure"
      class="fixed inset-0 z-50 flex items-end justify-center bg-black/40"
      @click.self="confirmErasure = false"
    >
      <div class="bg-white rounded-t-3xl w-full max-w-lg p-6 space-y-4 pb-safe">
        <div class="w-10 h-1 bg-gray-200 rounded-full mx-auto mb-2" />

        <div class="flex items-center gap-3">
          <div class="w-12 h-12 rounded-2xl bg-danger-100 flex items-center justify-center">
            <Trash2 :size="22" class="text-danger-600" />
          </div>
          <div>
            <p class="font-semibold text-gray-900">Delete your account?</p>
            <p class="text-sm text-gray-500">This will be reviewed within 30 days.</p>
          </div>
        </div>

        <p class="text-sm text-gray-600 leading-relaxed">
          Your name, email, phone, and ID number will be removed. Lease and payment records
          are kept for up to 7 years as required by law.
        </p>

        <label class="block text-sm text-gray-700">
          Reason (optional)
        </label>
        <textarea
          v-model="erasureReason"
          class="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm resize-none"
          rows="2"
          placeholder="Why are you requesting deletion?"
        />

        <button
          class="btn-danger w-full"
          :disabled="erasureLoading"
          @click="submitErasure"
        >
          <span v-if="erasureLoading">Submitting…</span>
          <span v-else>Confirm — delete my account</span>
        </button>

        <button class="w-full text-center text-sm text-gray-500 py-1" @click="confirmErasure = false">
          Cancel
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { CheckCircle, Clock, Download, Loader2, ShieldCheck, Trash2 } from 'lucide-vue-next'
import AppHeader from '../../components/AppHeader.vue'
import api from '../../api'
import { useToast } from '../../composables/useToast'

const router = useRouter()
const toast = useToast()

interface DSARRequest {
  id: number
  request_type: 'sar' | 'rtbf'
  status: string
  requester_email: string
  sla_deadline: string
  created_at: string
  days_remaining: number
  is_overdue: boolean
}

const allRequests = ref<DSARRequest[]>([])
const exportLoading = ref(false)
const erasureLoading = ref(false)
const confirmErasure = ref(false)
const erasureReason = ref('')

const pendingSAR = computed(() =>
  allRequests.value.find(
    r => r.request_type === 'sar' && ['pending', 'in_review'].includes(r.status)
  ) ?? null
)

const pendingRTBF = computed(() =>
  allRequests.value.find(
    r => r.request_type === 'rtbf' && ['pending', 'in_review', 'approved'].includes(r.status)
  ) ?? null
)

const pastRequests = computed(() =>
  allRequests.value.filter(r =>
    ['completed', 'denied'].includes(r.status)
  ).slice(0, 5)
)

async function loadRequests() {
  try {
    const { data } = await api.get('/popia/my-requests/')
    allRequests.value = data
  } catch {
    // silently fail — non-critical
  }
}

async function requestExport() {
  exportLoading.value = true
  try {
    await api.post('/popia/data-export/', {})
    toast.success('Export requested — check your email shortly')
    await loadRequests()
  } catch (err: any) {
    const msg = err?.response?.data?.detail || 'Failed to request export'
    toast.error(msg)
  } finally {
    exportLoading.value = false
  }
}

async function submitErasure() {
  erasureLoading.value = true
  try {
    await api.post('/popia/erasure-request/', { reason: erasureReason.value })
    toast.success('Deletion request submitted — we will review it within 30 days')
    confirmErasure.value = false
    erasureReason.value = ''
    await loadRequests()
  } catch (err: any) {
    const msg = err?.response?.data?.detail || 'Failed to submit request'
    toast.error(msg)
  } finally {
    erasureLoading.value = false
  }
}

function statusChipClass(s: string): string {
  switch (s) {
    case 'pending': return 'bg-amber-100 text-amber-700'
    case 'in_review': return 'bg-blue-100 text-blue-700'
    case 'approved': return 'bg-green-100 text-green-700'
    case 'denied': return 'bg-red-100 text-red-700'
    case 'completed': return 'bg-gray-100 text-gray-600'
    default: return 'bg-gray-100 text-gray-400'
  }
}

function formatDate(iso: string): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-ZA', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

onMounted(loadRequests)
</script>
