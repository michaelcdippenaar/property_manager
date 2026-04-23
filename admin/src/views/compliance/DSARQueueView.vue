<template>
  <div class="space-y-6">
    <PageHeader
      title="DSAR Queue"
      subtitle="Data Subject Access &amp; Erasure Requests — POPIA s23 / s24"
      :crumbs="[{ label: 'Dashboard', to: '/' }, { label: 'Compliance' }, { label: 'DSAR Queue' }]"
    />

    <!-- Filters -->
    <div class="card p-4 flex flex-wrap items-center gap-3">
      <select v-model="statusFilter" class="input w-44" @change="load">
        <option value="">All statuses</option>
        <option value="pending">Pending</option>
        <option value="in_review">In Review</option>
        <option value="approved">Approved</option>
        <option value="denied">Denied</option>
        <option value="completed">Completed</option>
      </select>

      <select v-model="typeFilter" class="input w-44" @change="load">
        <option value="">All types</option>
        <option value="sar">SAR (Access)</option>
        <option value="rtbf">RTBF (Erasure)</option>
      </select>

      <div class="ml-auto flex items-center gap-2 text-sm text-gray-500">
        <AlertTriangle v-if="overdueCount > 0" :size="16" class="text-danger-600" />
        <span v-if="overdueCount > 0" class="text-danger-600 font-medium">
          {{ overdueCount }} overdue
        </span>
        <span>{{ requests.length }} total</span>
      </div>
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-gray-400">
        <Loader2 :size="20" class="animate-spin mx-auto" />
      </div>

      <table v-else class="table-wrap">
        <thead>
          <tr>
            <th>#</th>
            <th>Requester</th>
            <th>Type</th>
            <th>Status</th>
            <th>SLA Deadline</th>
            <th>Days Left</th>
            <th>Submitted</th>
            <th class="!text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="r in requests"
            :key="r.id"
            :class="{ 'bg-danger-50': r.is_overdue }"
          >
            <td class="text-gray-400 text-xs">{{ r.id }}</td>
            <td class="font-medium text-gray-900">{{ r.requester_email }}</td>
            <td>
              <span
                :class="r.request_type === 'rtbf'
                  ? 'bg-accent/10 text-accent'
                  : 'bg-navy/10 text-navy'"
                class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
              >
                {{ r.request_type === 'rtbf' ? 'Erasure (s24)' : 'Access (s23)' }}
              </span>
            </td>
            <td>
              <span :class="statusClass(r.status)" class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize">
                {{ r.status.replace('_', ' ') }}
              </span>
            </td>
            <td class="text-gray-600 text-sm">{{ formatDate(r.sla_deadline) }}</td>
            <td>
              <span
                :class="r.is_overdue
                  ? 'text-danger-600 font-bold'
                  : r.days_remaining <= 5
                  ? 'text-amber-600 font-semibold'
                  : 'text-gray-600'"
                class="text-sm"
              >
                <span v-if="r.is_overdue">OVERDUE</span>
                <span v-else>{{ r.days_remaining }}d</span>
              </span>
            </td>
            <td class="text-gray-500 text-sm">{{ formatDate(r.created_at) }}</td>
            <td class="text-right">
              <button
                v-if="canReview(r)"
                class="btn-sm btn-primary mr-1"
                @click="openReview(r)"
              >
                Review
              </button>
              <button
                class="btn-sm btn-ghost"
                @click="openDetail(r)"
              >
                View
              </button>
            </td>
          </tr>
          <tr v-if="!requests.length">
            <td colspan="8" class="px-4 py-8 text-center text-gray-400">
              No DSAR requests
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Review modal -->
    <div
      v-if="reviewTarget"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      @click.self="reviewTarget = null"
    >
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 space-y-4">
        <h2 class="text-lg font-semibold text-gray-900">
          Review DSAR #{{ reviewTarget.id }}
        </h2>
        <p class="text-sm text-gray-600">
          <span class="font-medium">{{ reviewTarget.requester_email }}</span>
          &mdash;
          {{ reviewTarget.request_type === 'rtbf' ? 'Erasure (s24)' : 'Access (s23)' }}
        </p>

        <div v-if="reviewTarget.reason" class="bg-gray-50 rounded-lg p-3 text-sm text-gray-700">
          <p class="font-medium text-gray-500 text-xs mb-1">Reason from data subject</p>
          {{ reviewTarget.reason }}
        </div>

        <div class="space-y-3">
          <label class="block text-sm font-medium text-gray-700">
            Operator notes (internal, not shared with data subject)
          </label>
          <textarea
            v-model="reviewForm.operator_notes"
            class="input w-full min-h-[80px] resize-y"
            placeholder="Internal notes..."
          />

          <div v-if="reviewForm.action === 'deny'" class="space-y-2">
            <label class="block text-sm font-medium text-gray-700">
              Denial reason <span class="text-danger-600">*</span>
              <span class="text-gray-400 font-normal">(shared with data subject)</span>
            </label>
            <textarea
              v-model="reviewForm.denial_reason"
              class="input w-full min-h-[80px] resize-y"
              placeholder="Explain why the request is denied (e.g. retention obligations under FICA)..."
            />
          </div>
        </div>

        <!-- Retention flags — shown as soon as modal opens for RTBF -->
        <div
          v-if="reviewTarget.request_type === 'rtbf' && loadingFlags"
          class="flex items-center gap-2 text-sm text-gray-400"
        >
          <Loader2 :size="14" class="animate-spin" />
          Checking retention flags...
        </div>

        <div
          v-if="reviewTarget.request_type === 'rtbf' && retentionFlags && (retentionFlags.has_active_lease || retentionFlags.has_outstanding_payments)"
          class="bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-1"
        >
          <p class="text-sm font-semibold text-amber-800 flex items-center gap-1.5">
            <AlertTriangle :size="15" />
            Retention flags — review before approving
          </p>
          <ul class="text-sm text-amber-700 list-disc list-inside space-y-0.5">
            <li v-if="retentionFlags.has_active_lease">
              This user has an <strong>active lease</strong> — erasure may affect ongoing tenancy obligations.
            </li>
            <li v-if="retentionFlags.has_outstanding_payments">
              This user has <strong>outstanding payments</strong> — unpaid invoices exist on their lease(s).
            </li>
          </ul>
          <p class="text-xs text-amber-600 mt-1">
            You can still approve — this is a guardrail, not a block. Consider denying with a retention reason instead.
          </p>
        </div>

        <!-- Erasure confirmation warning (shown after first Approve click) -->
        <div
          v-if="reviewTarget.request_type === 'rtbf' && reviewForm.action === 'approve'"
          class="bg-danger-50 border border-danger-200 rounded-lg p-3 text-sm text-danger-700"
        >
          <strong>Confirm erasure:</strong> Approving will immediately anonymise the user's account
          (name, email, phone, ID number). Lease and payment records are preserved per
          FICA/RHA/SARS retention rules. This action cannot be undone.
          Click <strong>Approve</strong> again to confirm.
        </div>

        <div class="flex gap-2 pt-2">
          <button
            class="btn-primary flex-1"
            :class="{ 'opacity-50 cursor-not-allowed': saving }"
            :disabled="saving"
            @click="submitReview('approve')"
          >
            <CheckCircle :size="16" />
            Approve
          </button>
          <button
            class="btn-danger flex-1"
            :class="{ 'opacity-50 cursor-not-allowed': saving }"
            :disabled="saving"
            @click="submitReview('deny')"
          >
            <XCircle :size="16" />
            Deny
          </button>
          <button class="btn-ghost" @click="reviewTarget = null">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Detail modal -->
    <div
      v-if="detailTarget"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      @click.self="detailTarget = null"
    >
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold text-gray-900">DSAR #{{ detailTarget.id }}</h2>
          <button @click="detailTarget = null" class="text-gray-400 hover:text-gray-600">
            <X :size="20" />
          </button>
        </div>

        <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt class="text-gray-500">Requester</dt>
          <dd class="font-medium text-gray-900">{{ detailTarget.requester_email }}</dd>

          <dt class="text-gray-500">Type</dt>
          <dd>{{ detailTarget.request_type === 'rtbf' ? 'Erasure (s24)' : 'Access (s23)' }}</dd>

          <dt class="text-gray-500">Status</dt>
          <dd class="capitalize">{{ detailTarget.status.replace('_', ' ') }}</dd>

          <dt class="text-gray-500">SLA deadline</dt>
          <dd :class="detailTarget.is_overdue ? 'text-danger-600 font-bold' : ''">
            {{ formatDate(detailTarget.sla_deadline) }}
          </dd>

          <dt class="text-gray-500">Days remaining</dt>
          <dd :class="detailTarget.is_overdue ? 'text-danger-600 font-bold' : ''">
            {{ detailTarget.is_overdue ? 'OVERDUE' : detailTarget.days_remaining + ' days' }}
          </dd>

          <dt v-if="detailTarget.reviewed_by" class="text-gray-500">Reviewed by</dt>
          <dd v-if="detailTarget.reviewed_by">{{ detailTarget.reviewed_by }}</dd>

          <dt v-if="detailTarget.denial_reason" class="text-gray-500">Denial reason</dt>
          <dd v-if="detailTarget.denial_reason" class="col-span-2 bg-gray-50 p-2 rounded text-gray-700">
            {{ detailTarget.denial_reason }}
          </dd>

          <dt v-if="detailTarget.reason" class="text-gray-500">Data subject reason</dt>
          <dd v-if="detailTarget.reason" class="col-span-2 bg-gray-50 p-2 rounded text-gray-700">
            {{ detailTarget.reason }}
          </dd>
        </dl>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { AlertTriangle, CheckCircle, Loader2, X, XCircle } from 'lucide-vue-next'
import PageHeader from '../../components/PageHeader.vue'
import api from '../../api'
import { useToast } from '../../composables/useToast'

const toast = useToast()

interface DSARRequest {
  id: number
  requester_email: string
  request_type: 'sar' | 'rtbf'
  reason: string
  status: string
  operator_notes: string
  denial_reason: string
  reviewed_by: number | null
  reviewed_at: string | null
  sla_deadline: string
  days_remaining: number
  is_overdue: boolean
  created_at: string
  updated_at: string
  completed_at: string | null
}

interface RetentionFlags {
  has_active_lease: boolean
  has_outstanding_payments: boolean
}

const requests = ref<DSARRequest[]>([])
const loading = ref(false)
const statusFilter = ref('')
const typeFilter = ref('')

const reviewTarget = ref<DSARRequest | null>(null)
const detailTarget = ref<DSARRequest | null>(null)
const saving = ref(false)
const retentionFlags = ref<RetentionFlags | null>(null)
const loadingFlags = ref(false)

const reviewForm = ref({
  action: '' as 'approve' | 'deny' | '',
  operator_notes: '',
  denial_reason: '',
})

const overdueCount = computed(() => requests.value.filter(r => r.is_overdue).length)

async function load() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (statusFilter.value) params.status = statusFilter.value
    if (typeFilter.value) params.request_type = typeFilter.value
    const { data } = await api.get('/popia/dsar-queue/', { params })
    requests.value = data
  } catch (err) {
    toast.error('Failed to load DSAR queue')
  } finally {
    loading.value = false
  }
}

function canReview(r: DSARRequest): boolean {
  return r.status === 'pending' || r.status === 'in_review'
}

async function openReview(r: DSARRequest) {
  reviewTarget.value = r
  reviewForm.value = { action: '', operator_notes: '', denial_reason: '' }
  retentionFlags.value = null

  if (r.request_type === 'rtbf') {
    loadingFlags.value = true
    try {
      const { data } = await api.get(`/popia/dsar-queue/${r.id}/review/`)
      retentionFlags.value = data.retention_flags ?? null
    } catch {
      // Non-fatal: proceed without flags
    } finally {
      loadingFlags.value = false
    }
  }
}

function openDetail(r: DSARRequest) {
  detailTarget.value = r
}

async function submitReview(action: 'approve' | 'deny') {
  if (!reviewTarget.value) return

  if (action === 'deny' && !reviewForm.value.denial_reason.trim()) {
    toast.error('A denial reason is required')
    reviewForm.value.action = 'deny'
    return
  }

  // Show warning for RTBF approval
  if (
    action === 'approve' &&
    reviewTarget.value.request_type === 'rtbf' &&
    reviewForm.value.action !== 'approve'
  ) {
    reviewForm.value.action = 'approve'
    return // Show the warning, user must click again
  }

  saving.value = true
  try {
    await api.post(`/popia/dsar-queue/${reviewTarget.value.id}/review/`, {
      action,
      operator_notes: reviewForm.value.operator_notes,
      ...(action === 'deny' ? { denial_reason: reviewForm.value.denial_reason } : {}),
    })
    toast.success(action === 'approve' ? 'Request approved' : 'Request denied')
    reviewTarget.value = null
    await load()
  } catch (err: any) {
    const msg = err?.response?.data?.detail || 'Review failed'
    toast.error(msg)
  } finally {
    saving.value = false
  }
}

function statusClass(s: string): string {
  switch (s) {
    case 'pending': return 'bg-amber-100 text-amber-700'
    case 'in_review': return 'bg-blue-100 text-blue-700'
    case 'approved': return 'bg-success-100 text-success-700'
    case 'denied': return 'bg-danger-100 text-danger-700'
    case 'completed': return 'bg-gray-100 text-gray-600'
    default: return 'bg-gray-100 text-gray-500'
  }
}

function formatDate(iso: string): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-ZA', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

onMounted(load)
</script>
