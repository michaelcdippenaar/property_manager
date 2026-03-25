<template>
  <div class="space-y-5">
    <!-- Stats row -->
    <div v-if="stats" class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="card p-4">
        <div class="text-xs text-gray-400 uppercase tracking-wide">New Requests</div>
        <div class="text-2xl font-bold text-navy mt-1">{{ stats.new_requests }}</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-gray-400 uppercase tracking-wide">Quoted</div>
        <div class="text-2xl font-bold text-amber-600 mt-1">{{ stats.pending_quotes }}</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-gray-400 uppercase tracking-wide">Awarded</div>
        <div class="text-2xl font-bold text-green-600 mt-1">{{ stats.awarded_jobs }}</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-gray-400 uppercase tracking-wide">Completed</div>
        <div class="text-2xl font-bold text-gray-600 mt-1">{{ stats.completed_jobs }}</div>
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
              <span :class="statusBadge(job.status)" class="text-micro">{{ job.status }}</span>
            </div>
          </div>
          <div class="flex items-center gap-3 mt-2 text-xs text-gray-400">
            <span>{{ formatDate(job.created_at) }}</span>
            <span v-if="job.quote" class="font-medium text-gray-600">R{{ Number(job.quote.amount).toLocaleString() }}</span>
          </div>
        </button>

        <div v-if="!loading && !jobs.length" class="text-center text-gray-400 py-16">
          No jobs for this filter
        </div>
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

            <div v-if="selected.dispatch_notes" class="p-3 bg-blue-50 rounded-lg">
              <div class="text-xs font-medium text-blue-700 mb-1">Agent notes</div>
              <p class="text-sm text-blue-800">{{ selected.dispatch_notes }}</p>
            </div>

            <!-- Status -->
            <div class="flex items-center gap-2">
              <span :class="statusBadge(selected.status)">{{ selected.status }}</span>
              <span v-if="selected.match_score" class="text-xs text-gray-400 font-mono">Score: {{ selected.match_score }}</span>
            </div>

            <!-- Existing quote -->
            <div v-if="selected.quote" class="border-t border-gray-100 pt-4">
              <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Your Quote</h3>
              <div class="p-3 bg-green-50 rounded-lg space-y-1">
                <div class="text-lg font-bold text-green-800">R{{ Number(selected.quote.amount).toLocaleString() }}</div>
                <div v-if="selected.quote.estimated_days" class="text-sm text-green-700">{{ selected.quote.estimated_days }} days</div>
                <div v-if="selected.quote.available_from" class="text-sm text-green-700">Available: {{ selected.quote.available_from }}</div>
                <p v-if="selected.quote.description" class="text-sm text-green-700">{{ selected.quote.description }}</p>
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
                <button @click="declineJob" :disabled="submitting" class="btn-ghost text-red-600">
                  Decline
                </button>
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
import { X, Loader2 } from 'lucide-vue-next'
import FilterPills from '../../components/FilterPills.vue'

const loading = ref(true)
const submitting = ref(false)
const activeFilter = ref('all')
const jobs = ref<any[]>([])
const selected = ref<any | null>(null)
const stats = ref<any | null>(null)

const quoteForm = ref({ amount: null as number | null, estimated_days: null as number | null, available_from: '', description: '' })

const filters = [
  { label: 'All', value: 'all' },
  { label: 'New', value: 'pending' },
  { label: 'Quoted', value: 'quoted' },
  { label: 'Awarded', value: 'awarded' },
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

function priorityBadge(p: string) {
  return { urgent: 'badge-red', high: 'badge-amber', medium: 'badge-blue', low: 'badge-green' }[p] ?? 'badge-gray'
}
function priorityBorderLeft(p: string) {
  return { urgent: 'border-l-red-500', high: 'border-l-amber-400', medium: 'border-l-blue-400', low: 'border-l-green-400' }[p] ?? 'border-l-gray-300'
}
function statusBadge(s: string) {
  return { pending: 'badge-gray', viewed: 'badge-blue', quoted: 'badge-amber', declined: 'badge-red', awarded: 'badge-green', expired: 'badge-gray' }[s] ?? 'badge-gray'
}
function formatDate(iso: string) {
  return iso ? new Date(iso).toLocaleDateString('en-ZA') : '—'
}
</script>
