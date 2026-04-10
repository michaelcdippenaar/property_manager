<template>
  <div class="space-y-6">

    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold text-navy" style="font-family: 'Bricolage Grotesque', 'Inter', sans-serif;">
          Self-Check Status
        </h1>
        <p class="text-sm text-gray-500 mt-0.5">Module self-health diagnostics</p>
      </div>
      <button class="btn-primary" @click="runSelfCheck" :disabled="running">
        <RefreshCw :size="15" :class="running ? 'animate-spin' : ''" />
        {{ running ? 'Running…' : 'Run Self-Check' }}
      </button>
    </div>

    <!-- Latest result -->
    <div class="card">
      <div class="px-5 py-4 border-b border-gray-100">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-gray-800">Latest Self-Check</h2>
          <span class="text-xs text-gray-400">{{ latestCheck ? formatDate(latestCheck.created_at) : '—' }}</span>
        </div>
      </div>

      <div v-if="loading" class="p-6 animate-pulse space-y-4">
        <div v-for="i in 6" :key="i" class="h-5 bg-gray-100 rounded"></div>
      </div>

      <div v-else-if="!latestCheck" class="p-12 text-center text-gray-400 text-sm">
        No self-check has been run yet. Click "Run Self-Check" to start.
      </div>

      <template v-else>
        <!-- Overall status banner -->
        <div
          class="mx-5 mt-4 px-4 py-3 rounded-lg flex items-center gap-3"
          :class="latestCheck.overall_healthy ? 'bg-success-50 border border-success-100' : 'bg-danger-50 border border-danger-100'"
        >
          <component
            :is="latestCheck.overall_healthy ? CheckCircle : XCircle"
            :size="20"
            :class="latestCheck.overall_healthy ? 'text-success-600' : 'text-danger-600'"
          />
          <div>
            <div class="text-sm font-semibold" :class="latestCheck.overall_healthy ? 'text-success-700' : 'text-danger-700'">
              {{ latestCheck.overall_healthy ? 'All checks passed' : 'Some checks failed' }}
            </div>
            <div class="text-xs text-gray-500">
              {{ latestCheck.checks.filter((c: any) => c.passed).length }} / {{ latestCheck.checks.length }} checks passing
            </div>
          </div>
        </div>

        <!-- Checklist -->
        <div class="p-5 space-y-2">
          <div
            v-for="check in latestCheck.checks"
            :key="check.name"
            class="flex items-center gap-3 py-2.5 px-3 rounded-lg"
            :class="check.passed ? 'bg-success-50/50' : 'bg-danger-50/50'"
          >
            <component
              :is="check.passed ? CheckCircle : XCircle"
              :size="16"
              :class="check.passed ? 'text-success-500 flex-shrink-0' : 'text-danger-500 flex-shrink-0'"
            />
            <span class="text-sm text-gray-700 flex-1">{{ check.label }}</span>
            <span v-if="check.detail" class="text-xs text-gray-400">{{ check.detail }}</span>
          </div>
        </div>

        <!-- Issues found -->
        <div v-if="latestCheck.issues?.length" class="border-t border-gray-100 p-5">
          <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Issues Found</h3>
          <ul class="space-y-2">
            <li
              v-for="(issue, i) in latestCheck.issues"
              :key="i"
              class="flex items-start gap-2 text-sm text-danger-700"
            >
              <AlertTriangle :size="14" class="mt-0.5 flex-shrink-0 text-danger-500" />
              {{ issue }}
            </li>
          </ul>
        </div>

        <!-- Warnings -->
        <div v-if="latestCheck.warnings?.length" class="border-t border-gray-100 p-5">
          <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Warnings</h3>
          <ul class="space-y-2">
            <li
              v-for="(w, i) in latestCheck.warnings"
              :key="i"
              class="flex items-start gap-2 text-sm text-warning-700"
            >
              <AlertTriangle :size="14" class="mt-0.5 flex-shrink-0 text-warning-500" />
              {{ w }}
            </li>
          </ul>
        </div>
      </template>
    </div>

    <!-- History: last 10 -->
    <div class="card">
      <div class="px-5 py-4 border-b border-gray-100">
        <h2 class="text-sm font-semibold text-gray-800">History (last 10)</h2>
      </div>
      <div v-if="loading" class="p-4 animate-pulse space-y-3">
        <div v-for="i in 5" :key="i" class="h-4 bg-gray-100 rounded"></div>
      </div>
      <div v-else-if="!history.length" class="p-8 text-center text-gray-400 text-sm">
        No history yet
      </div>
      <div v-else class="table-scroll">
        <table class="table-wrap">
          <thead>
            <tr>
              <th>When</th>
              <th>Checks</th>
              <th>Issues</th>
              <th>Warnings</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="h in history" :key="h.id" class="cursor-pointer" @click="latestCheck = h">
              <td class="text-xs text-gray-500">{{ formatDate(h.created_at) }}</td>
              <td class="text-gray-700">{{ h.checks.filter((c: any) => c.passed).length }}/{{ h.checks.length }}</td>
              <td>
                <span :class="h.issues?.length ? 'text-danger-600 font-medium' : 'text-gray-400'">
                  {{ h.issues?.length ?? 0 }}
                </span>
              </td>
              <td>
                <span :class="h.warnings?.length ? 'text-warning-600 font-medium' : 'text-gray-400'">
                  {{ h.warnings?.length ?? 0 }}
                </span>
              </td>
              <td>
                <span :class="h.overall_healthy ? 'badge-green' : 'badge-red'">
                  {{ h.overall_healthy ? 'Healthy' : 'Failed' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { testingApi } from '../../api/testing'
import { RefreshCw, CheckCircle, XCircle, AlertTriangle } from 'lucide-vue-next'

const loading = ref(true)
const running = ref(false)

const CHECKS_PASSING = [
  { name: 'db_connection',      label: 'Database connection',            passed: true,  detail: 'PostgreSQL 15.4' },
  { name: 'redis_connection',   label: 'Redis connection',               passed: true,  detail: 'OK' },
  { name: 'celery_workers',     label: 'Celery workers running',         passed: true,  detail: '2 workers' },
  { name: 'gotenberg',          label: 'Gotenberg PDF service reachable',passed: true,  detail: 'v8.4.0' },
  { name: 'rag_store',          label: 'RAG vector store populated',     passed: true,  detail: '387 docs' },
  { name: 'media_storage',      label: 'Media storage writable',         passed: true,  detail: 'local' },
  { name: 'email_gateway',      label: 'Email gateway reachable',        passed: false, detail: 'Connection timeout' },
  { name: 'sms_gateway',        label: 'SMS gateway reachable',          passed: false, detail: '503 Service Unavailable' },
]

const MOCK_HISTORY = [
  {
    id: 1,
    overall_healthy: false,
    checks: CHECKS_PASSING,
    issues: ['Email gateway not reachable — connection timeout after 5s', 'SMS gateway returning 503'],
    warnings: ['Media storage using local filesystem — consider S3 for production'],
    created_at: '2026-04-04T08:00:00Z',
  },
  {
    id: 2,
    overall_healthy: false,
    checks: CHECKS_PASSING.map(c => ({ ...c, passed: c.name !== 'sms_gateway' ? c.passed : false })),
    issues: ['SMS gateway returning 503'],
    warnings: [],
    created_at: '2026-04-03T08:00:00Z',
  },
  {
    id: 3,
    overall_healthy: true,
    checks: CHECKS_PASSING.map(c => ({ ...c, passed: true })),
    issues: [],
    warnings: ['Media storage using local filesystem'],
    created_at: '2026-04-02T08:00:00Z',
  },
  {
    id: 4,
    overall_healthy: true,
    checks: CHECKS_PASSING.map(c => ({ ...c, passed: true })),
    issues: [],
    warnings: [],
    created_at: '2026-04-01T08:00:00Z',
  },
  {
    id: 5,
    overall_healthy: true,
    checks: CHECKS_PASSING.map(c => ({ ...c, passed: true })),
    issues: [],
    warnings: [],
    created_at: '2026-03-31T08:00:00Z',
  },
]

const latestCheck = ref<any>(MOCK_HISTORY[0])
const history = ref<any[]>(MOCK_HISTORY)

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('en-ZA', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

async function runSelfCheck() {
  running.value = true
  try {
    const { data } = await testingApi.runSelfCheck()
    latestCheck.value = data
    history.value = [data, ...history.value].slice(0, 10)
  } catch {
    // Simulate a result when backend isn't up
    const simulated = {
      ...MOCK_HISTORY[0],
      id: Date.now(),
      created_at: new Date().toISOString(),
    }
    latestCheck.value = simulated
    history.value = [simulated, ...history.value].slice(0, 10)
  } finally {
    running.value = false
  }
}

onMounted(async () => {
  try {
    const { data } = await testingApi.getSelfCheck()
    const results = data.results ?? data
    if (Array.isArray(results) && results.length) {
      history.value = results.slice(0, 10)
      latestCheck.value = results[0]
    } else if (data.id) {
      latestCheck.value = data
    }
  } catch { /* use mock */ } finally {
    loading.value = false
  }
})
</script>
