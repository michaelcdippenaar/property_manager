<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-base font-semibold text-gray-900">PDF Render Queue</h2>
        <p class="text-xs text-gray-500 mt-0.5">
          Documents queued for background generation when Gotenberg was unavailable.
        </p>
      </div>
      <button class="btn-ghost text-xs flex items-center gap-1.5" @click="load">
        <RefreshCw :size="12" :class="loading ? 'animate-spin' : ''" />
        Refresh
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading && !jobs.length" class="flex items-center gap-2 text-sm text-gray-400 py-6">
      <Loader2 :size="14" class="animate-spin" />
      Loading…
    </div>

    <!-- Empty -->
    <div v-else-if="!jobs.length" class="py-10 text-center text-sm text-gray-400">
      No pending render jobs.
    </div>

    <!-- Job table -->
    <div v-else class="overflow-x-auto rounded-xl border border-gray-200">
      <table class="min-w-full text-xs">
        <thead class="bg-gray-50 text-gray-500 uppercase tracking-wide text-micro">
          <tr>
            <th class="px-4 py-2.5 text-left">#</th>
            <th class="px-4 py-2.5 text-left">Template</th>
            <th class="px-4 py-2.5 text-left">Status</th>
            <th class="px-4 py-2.5 text-left">Attempts</th>
            <th class="px-4 py-2.5 text-left">Created</th>
            <th class="px-4 py-2.5 text-left">Error</th>
            <th class="px-4 py-2.5 text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="job in jobs" :key="job.id" class="bg-white hover:bg-gray-50 transition-colors">
            <td class="px-4 py-3 text-gray-400 font-mono">{{ job.id }}</td>
            <td class="px-4 py-3 text-gray-800">{{ job.template_name || '—' }}</td>
            <td class="px-4 py-3">
              <span :class="statusBadge(job.status)" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-micro font-medium">
                <span class="w-1.5 h-1.5 rounded-full" :class="statusDot(job.status)" />
                {{ job.status }}
              </span>
            </td>
            <td class="px-4 py-3 text-gray-600">{{ job.attempts }} / {{ MAX_ATTEMPTS }}</td>
            <td class="px-4 py-3 text-gray-400">{{ fmtDate(job.created_at) }}</td>
            <td class="px-4 py-3 text-danger-600 max-w-xs truncate" :title="job.error || ''">
              {{ job.error || '—' }}
            </td>
            <td class="px-4 py-3 text-right space-x-2">
              <a
                v-if="job.result_pdf_url"
                :href="job.result_pdf_url"
                target="_blank"
                class="btn-ghost text-xs inline-flex items-center gap-1"
              >
                <Download :size="11" /> Download
              </a>
              <button
                v-if="job.status === 'failed' || job.status === 'pending'"
                class="btn-ghost text-xs inline-flex items-center gap-1"
                :disabled="retrying.has(job.id)"
                @click="retry(job.id)"
              >
                <Loader2 v-if="retrying.has(job.id)" :size="11" class="animate-spin" />
                <RotateCcw v-else :size="11" />
                Retry
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Loader2, RefreshCw, Download, RotateCcw } from 'lucide-vue-next'
import api from '../../api'

const MAX_ATTEMPTS = 3

interface RenderJob {
  id: number
  status: string
  attempts: number
  template_id: number | null
  template_name: string | null
  error: string | null
  result_pdf_url: string | null
  created_at: string
  updated_at: string
}

const jobs = ref<RenderJob[]>([])
const loading = ref(false)
const retrying = ref<Set<number>>(new Set())

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/leases/render-jobs/')
    jobs.value = data
  } catch (e) {
    // silently ignore — user will see the empty state
  } finally {
    loading.value = false
  }
}

async function retry(jobId: number) {
  retrying.value = new Set([...retrying.value, jobId])
  try {
    await api.post(`/leases/render-jobs/${jobId}/retry/`)
    await load()
  } finally {
    const next = new Set(retrying.value)
    next.delete(jobId)
    retrying.value = next
  }
}

function statusBadge(s: string) {
  switch (s) {
    case 'done':    return 'bg-success-50 text-success-700'
    case 'failed':  return 'bg-danger-50 text-danger-700'
    case 'running': return 'bg-info-50 text-info-700'
    default:        return 'bg-warning-50 text-warning-700'
  }
}

function statusDot(s: string) {
  switch (s) {
    case 'done':    return 'bg-success-400'
    case 'failed':  return 'bg-danger-400'
    case 'running': return 'bg-info-400 animate-pulse'
    default:        return 'bg-warning-400 animate-pulse'
  }
}

function fmtDate(iso: string) {
  try {
    return new Date(iso).toLocaleString('en-ZA', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return iso
  }
}

onMounted(load)
</script>
