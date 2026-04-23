<template>
  <div class="space-y-5">
    <!-- Stats row -->
    <div v-if="stats" class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="card p-4">
        <div class="text-xs text-gray-400 uppercase tracking-wide">New Requests</div>
        <div class="text-2xl font-bold text-navy mt-1">{{ stats.new_requests }}</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-gray-400 uppercase tracking-wide">In Progress</div>
        <div class="text-2xl font-bold text-blue-600 mt-1">{{ stats.awarded_jobs }}</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-gray-400 uppercase tracking-wide">Awaiting Payment</div>
        <div class="text-2xl font-bold text-amber-600 mt-1">{{ stats.awaiting_payment }}</div>
        <div v-if="Number(stats.outstanding_amount) > 0" class="text-xs text-amber-600 mt-0.5 font-medium">
          R{{ Number(stats.outstanding_amount).toLocaleString('en-ZA') }}
        </div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-gray-400 uppercase tracking-wide">Paid</div>
        <div class="text-2xl font-bold text-success-600 mt-1">{{ stats.paid_jobs }}</div>
        <div v-if="Number(stats.paid_amount) > 0" class="text-xs text-success-600 mt-0.5 font-medium">
          R{{ Number(stats.paid_amount).toLocaleString('en-ZA') }}
        </div>
      </div>
    </div>

    <!-- Filter tabs -->
    <FilterPills v-model="activeFilter" :options="filters" @update:model-value="loadJobs()" />

    <!-- Two column layout -->
    <div class="grid gap-5" :class="selected ? 'xl:grid-cols-[minmax(0,1.15fr)_minmax(420px,0.85fr)]' : ''">

      <!-- Job list -->
      <div class="space-y-3 min-w-0">
        <div v-if="loading" class="space-y-3">
          <div v-for="i in 4" :key="i" class="card p-4 animate-pulse space-y-2">
            <div class="h-4 bg-gray-100 rounded w-2/3"></div>
            <div class="h-3 bg-gray-100 rounded w-1/3"></div>
          </div>
        </div>

        <button v-else v-for="job in jobs" :key="job.id" type="button"
          class="w-full text-left rounded-xl border px-4 py-3 transition-all border-l-4"
          :class="[
            priorityBorderLeft(job.job_priority),
            selected?.id === job.id ? 'bg-slate-50 shadow-sm border-gray-300' : 'bg-white hover:bg-gray-50 border-gray-200',
          ]"
          @click="selectJob(job)">
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0 flex-1">
              <div class="font-medium text-gray-900 text-sm">{{ job.job_title }}</div>
              <div class="text-xs text-gray-500 mt-0.5">{{ job.property_name }} — {{ job.property_city }}</div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <span :class="priorityBadge(job.job_priority)" class="text-micro">{{ job.job_priority }}</span>
              <span :class="jobStatusBadge(job)" class="text-micro">{{ jobStatusLabel(job) }}</span>
            </div>
          </div>
          <div class="flex items-center gap-3 mt-2 text-xs text-gray-400">
            <span>{{ formatDate(job.created_at) }}</span>
            <span v-if="job.quote" class="font-medium text-gray-600">R{{ Number(job.quote.amount).toLocaleString('en-ZA') }}</span>
          </div>
        </button>

        <EmptyState
          v-if="!loading && !jobs.length"
          title="No jobs"
          description="No jobs for this filter."
          :icon="Briefcase"
        />
      </div>

      <!-- Detail panel -->
      <div v-if="selected" class="min-w-0">
        <div class="card sticky top-5 min-h-[70vh] max-h-[calc(100vh-7rem)] overflow-hidden flex flex-col">
          <div class="px-5 py-4 border-b border-gray-100">
            <div class="flex items-start justify-between gap-3">
              <div>
                <h2 class="text-base font-semibold text-gray-900">{{ selected.job_title }}</h2>
                <div class="text-xs text-gray-500 mt-1">{{ selected.property_name }} — {{ selected.property_city }}</div>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <span :class="priorityBadge(selected.job_priority)">{{ selected.job_priority }}</span>
                <button @click="selected = null" class="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
                  <X :size="16" />
                </button>
              </div>
            </div>
          </div>

          <div class="flex-1 min-h-0 overflow-y-auto px-5 py-4 space-y-5">
            <p class="text-sm text-gray-600 whitespace-pre-wrap">{{ selected.job_description }}</p>

            <div v-if="selected.dispatch_notes" class="p-3 bg-info-50 rounded-lg">
              <div class="text-xs font-medium text-info-700 mb-1">Agent notes</div>
              <p class="text-sm text-info-700">{{ selected.dispatch_notes }}</p>
            </div>

            <!-- Status -->
            <div class="flex items-center gap-2">
              <span :class="jobStatusBadge(selected)">{{ jobStatusLabel(selected) }}</span>
              <span v-if="selected.match_score" class="text-xs text-gray-400 font-mono">Score: {{ selected.match_score }}</span>
            </div>

            <!-- Existing quote -->
            <div v-if="selected.quote" class="border-t border-gray-100 pt-4">
              <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Your Quote</h3>
              <div class="p-3 bg-success-50 rounded-lg space-y-1">
                <div class="text-lg font-bold text-success-700">R{{ Number(selected.quote.amount).toLocaleString('en-ZA') }}</div>
                <div v-if="selected.quote.estimated_days" class="text-sm text-success-700">{{ selected.quote.estimated_days }} days</div>
                <div v-if="selected.quote.available_from" class="text-sm text-success-700">Available: {{ selected.quote.available_from }}</div>
                <p v-if="selected.quote.description" class="text-sm text-success-700">{{ selected.quote.description }}</p>
              </div>
            </div>

            <!-- Quote form (if not yet quoted) -->
            <div v-if="!selected.quote && !['awarded', 'expired', 'declined'].includes(selected.status)"
              class="border-t border-gray-100 pt-4 space-y-3">
              <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wide">Submit Quote</h3>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="label text-xs">Amount (R)</label>
                  <input v-model.number="quoteForm.amount" type="number" class="input" placeholder="5000" />
                </div>
                <div>
                  <label class="label text-xs">Estimated days</label>
                  <input v-model.number="quoteForm.estimated_days" type="number" class="input" placeholder="3" />
                </div>
              </div>
              <div>
                <label class="label text-xs">Available from</label>
                <input v-model="quoteForm.available_from" type="date" class="input" />
              </div>
              <div>
                <label class="label text-xs">Scope / Notes</label>
                <textarea v-model="quoteForm.description" class="input" rows="3" placeholder="Describe the work you'll do…"></textarea>
              </div>
              <div class="flex gap-2">
                <button @click="submitQuote" :disabled="!quoteForm.amount || submitting"
                  class="btn-primary flex-1">
                  <Loader2 v-if="submitting" :size="14" class="animate-spin" />
                  Submit Quote
                </button>
                <button @click="declineJob" :disabled="submitting" class="btn-ghost text-danger-600">
                  Decline
                </button>
              </div>
            </div>

            <!-- Accept awarded job -->
            <div v-if="selected.status === 'awarded' && selected.mr_status === 'open'"
              class="border-t border-gray-100 pt-4">
              <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wide mb-3">Ready to start?</h3>
              <button @click="acceptJob" :disabled="submitting" class="btn-primary w-full">
                <Loader2 v-if="submitting" :size="14" class="animate-spin" />
                Accept Job &amp; Start Work
              </button>
            </div>

            <!-- Status update (in-progress jobs) -->
            <div v-if="selected.status === 'awarded' && ['in_progress', 'open'].includes(selected.mr_status ?? '')"
              class="border-t border-gray-100 pt-4 space-y-3">
              <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wide">Update Progress</h3>
              <div>
                <label class="label text-xs">Status</label>
                <select v-model="statusForm.status" class="input">
                  <option value="in_progress">In Progress</option>
                  <option value="resolved">Mark Complete</option>
                </select>
              </div>
              <div>
                <label class="label text-xs">Note (optional)</label>
                <textarea v-model="statusForm.note" class="input" rows="2" placeholder="Any update for the agent or tenant…"></textarea>
              </div>
              <div>
                <label class="label text-xs">Progress Photo (optional)</label>
                <input type="file" accept="image/*" class="input text-sm" @change="onPhotoSelected" />
              </div>
              <button @click="updateStatus" :disabled="submitting" class="btn-primary w-full">
                <Loader2 v-if="submitting" :size="14" class="animate-spin" />
                Send Update
              </button>
            </div>

            <!-- Invoice submission -->
            <div v-if="selected.status === 'awarded' && !selected.invoice_status"
              class="border-t border-gray-100 pt-4 space-y-3">
              <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wide">Submit Invoice</h3>
              <!-- Line items -->
              <div class="space-y-2">
                <div v-for="(item, idx) in invoiceForm.line_items" :key="idx" class="flex gap-2 items-start">
                  <input v-model="item.description" class="input flex-1 text-sm" placeholder="Description" />
                  <input v-model.number="item.amount" type="number" class="input w-28 text-sm" placeholder="Amount" @input="recalcTotal" />
                  <button @click="removeLineItem(idx)" class="p-2 text-gray-400 hover:text-danger-600 mt-1">
                    <Trash2 :size="14" />
                  </button>
                </div>
                <button @click="addLineItem" class="text-xs text-navy hover:underline flex items-center gap-1">
                  <Plus :size="12" /> Add line item
                </button>
              </div>
              <div class="flex items-center gap-3">
                <div class="flex-1">
                  <label class="label text-xs">Total (R)</label>
                  <input v-model.number="invoiceForm.total_amount" type="number" class="input font-semibold" />
                </div>
              </div>
              <div>
                <label class="label text-xs">Notes / Reference</label>
                <input v-model="invoiceForm.notes" class="input text-sm" placeholder="Invoice number, payment terms…" />
              </div>
              <div>
                <label class="label text-xs">Invoice PDF / Image (optional)</label>
                <input type="file" accept=".pdf,image/*" class="input text-sm" @change="onInvoiceFileSelected" />
              </div>
              <button @click="submitInvoice" :disabled="!invoiceForm.total_amount || submitting" class="btn-primary w-full">
                <Loader2 v-if="submitting" :size="14" class="animate-spin" />
                Submit Invoice for Approval
              </button>
            </div>

            <!-- Existing invoice status -->
            <div v-if="selected.invoice_status" class="border-t border-gray-100 pt-4">
              <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Invoice</h3>
              <div class="p-3 rounded-lg" :class="invoiceStatusClass(selected.invoice_status)">
                <div class="flex items-center gap-2">
                  <component :is="invoiceStatusIcon(selected.invoice_status)" :size="15" />
                  <span class="text-sm font-medium">{{ invoiceStatusText(selected.invoice_status) }}</span>
                </div>
              </div>
            </div>

            <div v-if="selected.status === 'declined'" class="text-center text-gray-400 py-4">
              You declined this job
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'
import { X, Loader2, Briefcase, Plus, Trash2, Clock, CheckCircle, XCircle, FileText } from 'lucide-vue-next'
import EmptyState from '../../components/EmptyState.vue'
import FilterPills from '../../components/FilterPills.vue'

const loading = ref(true)
const submitting = ref(false)
const activeFilter = ref('all')
const jobs = ref<any[]>([])
const selected = ref<any | null>(null)
const stats = ref<any | null>(null)

const quoteForm = ref({ amount: null as number | null, estimated_days: null as number | null, available_from: '', description: '' })

const statusForm = ref({ status: 'in_progress', note: '', photo: null as File | null })

const invoiceForm = ref({
  line_items: [{ description: '', amount: null as number | null }] as { description: string; amount: number | null }[],
  total_amount: null as number | null,
  notes: '',
  file: null as File | null,
})

const filters = [
  { label: 'All', value: 'all' },
  { label: 'New', value: 'pending' },
  { label: 'Quoted', value: 'quoted' },
  { label: 'Awarded', value: 'awarded' },
  { label: 'In Progress', value: 'in_progress' },
  { label: 'Awaiting Payment', value: 'awaiting_payment' },
  { label: 'Paid', value: 'paid' },
  { label: 'Declined', value: 'declined' },
]

onMounted(async () => {
  await Promise.all([loadJobs(), loadStats()])
})

async function loadStats() {
  try {
    const { data } = await api.get('/maintenance/supplier/dashboard/')
    stats.value = data
  } catch { /* ignore */ }
}

async function loadJobs() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (activeFilter.value !== 'all') params.status = activeFilter.value
    const { data } = await api.get('/maintenance/supplier/jobs/', { params })
    jobs.value = data
  } finally {
    loading.value = false
  }
}

async function selectJob(job: any) {
  try {
    const { data } = await api.get(`/maintenance/supplier/jobs/${job.id}/`)
    selected.value = data
    quoteForm.value = { amount: null, estimated_days: null, available_from: '', description: '' }
    statusForm.value = { status: 'in_progress', note: '', photo: null }
    invoiceForm.value = {
      line_items: [{ description: '', amount: null }],
      total_amount: null,
      notes: '',
      file: null,
    }
  } catch {
    selected.value = job
  }
}

async function submitQuote() {
  if (!selected.value || !quoteForm.value.amount) return
  submitting.value = true
  try {
    await api.post(`/maintenance/supplier/jobs/${selected.value.id}/quote/`, quoteForm.value)
    await selectJob(selected.value)
    await Promise.all([loadJobs(), loadStats()])
  } finally {
    submitting.value = false
  }
}

async function declineJob() {
  if (!selected.value) return
  if (!confirm('Decline this job? You won\'t be able to quote on it later.')) return
  submitting.value = true
  try {
    await api.post(`/maintenance/supplier/jobs/${selected.value.id}/decline/`)
    await selectJob(selected.value)
    await Promise.all([loadJobs(), loadStats()])
  } finally {
    submitting.value = false
  }
}

async function acceptJob() {
  if (!selected.value) return
  submitting.value = true
  try {
    await api.post(`/maintenance/supplier/jobs/${selected.value.id}/accept/`)
    await selectJob(selected.value)
    await Promise.all([loadJobs(), loadStats()])
  } finally {
    submitting.value = false
  }
}

function onPhotoSelected(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0] ?? null
  statusForm.value.photo = file
}

async function updateStatus() {
  if (!selected.value) return
  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('status', statusForm.value.status)
    if (statusForm.value.note) fd.append('note', statusForm.value.note)
    if (statusForm.value.photo) fd.append('photo', statusForm.value.photo)
    await api.post(`/maintenance/supplier/jobs/${selected.value.id}/status/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    await selectJob(selected.value)
    await Promise.all([loadJobs(), loadStats()])
  } finally {
    submitting.value = false
  }
}

function addLineItem() {
  invoiceForm.value.line_items.push({ description: '', amount: null })
}

function removeLineItem(idx: number) {
  invoiceForm.value.line_items.splice(idx, 1)
  recalcTotal()
}

function recalcTotal() {
  const sum = invoiceForm.value.line_items.reduce((acc, item) => acc + (Number(item.amount) || 0), 0)
  if (sum > 0) invoiceForm.value.total_amount = sum
}

function onInvoiceFileSelected(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0] ?? null
  invoiceForm.value.file = file
}

async function submitInvoice() {
  if (!selected.value || !invoiceForm.value.total_amount) return
  submitting.value = true
  try {
    const fd = new FormData()
    // Filter out empty line items before submitting
    const cleanItems = invoiceForm.value.line_items.filter(i => i.description || i.amount)
    fd.append('line_items', JSON.stringify(cleanItems))
    fd.append('total_amount', String(invoiceForm.value.total_amount))
    if (invoiceForm.value.notes) fd.append('notes', invoiceForm.value.notes)
    if (invoiceForm.value.file) fd.append('invoice_file', invoiceForm.value.file)
    await api.post(`/maintenance/supplier/jobs/${selected.value.id}/invoice/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    await selectJob(selected.value)
    await Promise.all([loadJobs(), loadStats()])
  } finally {
    submitting.value = false
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────

function priorityBadge(p: string) {
  return { urgent: 'badge-red', high: 'badge-amber', medium: 'badge-blue', low: 'badge-green' }[p] ?? 'badge-gray'
}
function priorityBorderLeft(p: string) {
  return { urgent: 'border-l-red-500', high: 'border-l-amber-400', medium: 'border-l-blue-400', low: 'border-l-green-400' }[p] ?? 'border-l-gray-300'
}

function jobStatusLabel(job: any): string {
  if (job.status === 'awarded') {
    if (job.invoice_status === 'paid') return 'Paid'
    if (job.invoice_status === 'approved') return 'Awaiting Payment'
    if (job.invoice_status === 'pending') return 'Invoice Review'
    if (job.mr_status === 'resolved') return 'Complete'
    if (job.mr_status === 'in_progress') return 'In Progress'
    return 'Awarded'
  }
  const labels: Record<string, string> = {
    pending: 'New', viewed: 'Viewed', quoted: 'Quoted', declined: 'Declined', expired: 'Expired',
  }
  return labels[job.status] ?? job.status
}

function jobStatusBadge(job: any): string {
  if (job.status === 'awarded') {
    if (job.invoice_status === 'paid') return 'badge-green'
    if (job.invoice_status === 'approved') return 'badge-amber'
    if (job.invoice_status === 'pending') return 'badge-blue'
    if (job.mr_status === 'resolved') return 'badge-green'
    if (job.mr_status === 'in_progress') return 'badge-blue'
    return 'badge-green'
  }
  return { pending: 'badge-gray', viewed: 'badge-blue', quoted: 'badge-amber', declined: 'badge-red', expired: 'badge-gray' }[job.status] ?? 'badge-gray'
}

function invoiceStatusClass(s: string) {
  return {
    pending: 'bg-blue-50 text-blue-700',
    approved: 'bg-amber-50 text-amber-700',
    rejected: 'bg-red-50 text-red-700',
    paid: 'bg-success-50 text-success-700',
  }[s] ?? 'bg-gray-50 text-gray-600'
}

function invoiceStatusIcon(s: string) {
  return { pending: Clock, approved: FileText, rejected: XCircle, paid: CheckCircle }[s] ?? FileText
}

function invoiceStatusText(s: string) {
  return {
    pending: 'Invoice submitted — awaiting agent review',
    approved: 'Invoice approved — payment on the way',
    rejected: 'Invoice rejected — contact your agent',
    paid: 'Paid',
  }[s] ?? s
}

function formatDate(iso: string) {
  return iso ? new Date(iso).toLocaleDateString('en-ZA') : '—'
}
</script>
