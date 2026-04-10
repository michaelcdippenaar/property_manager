<template>
  <div class="space-y-6">

    <!-- Page header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-navy" style="font-family: 'Bricolage Grotesque', 'Inter', sans-serif;">
          Developer Testing Portal
        </h1>
        <p class="text-sm text-gray-500 mt-0.5">Test suite health, run history and RAG store status</p>
      </div>
      <button class="btn-primary" @click="triggerFullRun" :disabled="triggering">
        <Play :size="15" />
        {{ triggering ? 'Running…' : 'Run All Tests' }}
      </button>
    </div>

    <!-- Top row: Health Score + Suite Summary -->
    <div class="grid grid-cols-1 lg:grid-cols-5 gap-4">

      <!-- Health Score -->
      <div class="card p-6 lg:col-span-1 flex flex-col items-center justify-center text-center">
        <div v-if="loading" class="animate-pulse space-y-3 w-full">
          <div class="h-20 bg-gray-100 rounded-full w-20 mx-auto"></div>
          <div class="h-4 bg-gray-100 rounded w-1/2 mx-auto"></div>
        </div>
        <template v-else>
          <!-- Score ring -->
          <div class="relative w-24 h-24 mb-3">
            <svg class="w-full h-full -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="40" fill="none" stroke="#e5e7eb" stroke-width="10" />
              <circle
                cx="50" cy="50" r="40" fill="none"
                :stroke="scoreColor"
                stroke-width="10"
                stroke-linecap="round"
                :stroke-dasharray="`${(health.score / 100) * 251.2} 251.2`"
                class="transition-all duration-700"
              />
            </svg>
            <div class="absolute inset-0 flex items-center justify-center">
              <span class="text-2xl font-bold" :style="{ color: scoreColor }">{{ health.score }}</span>
            </div>
          </div>
          <div class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Health Score</div>
          <div class="mt-1 text-xs px-2 py-0.5 rounded-full font-medium" :class="scoreBadgeClass">
            {{ scoreTier }}
          </div>
        </template>
      </div>

      <!-- Suite Summary -->
      <div class="lg:col-span-4 grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div v-for="s in suiteSummary" :key="s.label" class="card p-5">
          <div v-if="loading" class="animate-pulse space-y-2">
            <div class="h-3 bg-gray-100 rounded w-2/3"></div>
            <div class="h-8 bg-gray-100 rounded w-1/2"></div>
          </div>
          <template v-else>
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-medium text-gray-500 uppercase tracking-wide">{{ s.label }}</span>
              <div class="w-6 h-6 rounded-md flex items-center justify-center" :class="s.bg">
                <component :is="s.icon" :size="12" :class="s.iconColor" />
              </div>
            </div>
            <div class="text-3xl font-bold tracking-tight" :class="s.valueColor">{{ s.value }}</div>
          </template>
        </div>
      </div>
    </div>

    <!-- Module Status Grid -->
    <div>
      <h2 class="text-sm font-semibold text-gray-700 mb-3 uppercase tracking-wider">Module Status</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          v-for="mod in modules"
          :key="mod.name"
          class="card p-4 card-interactive cursor-pointer"
          @click="goToModule(mod.name)"
        >
          <div v-if="loading" class="animate-pulse space-y-2">
            <div class="h-3 bg-gray-100 rounded w-1/2"></div>
            <div class="h-5 bg-gray-100 rounded w-full"></div>
            <div class="h-3 bg-gray-100 rounded w-2/3"></div>
          </div>
          <template v-else>
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-semibold text-gray-800 capitalize">{{ mod.label }}</span>
              <!-- Health dot -->
              <span
                class="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
                :style="{ backgroundColor: moduleHealthColor(mod) }"
              ></span>
            </div>
            <div class="flex gap-3 text-xs mb-2">
              <span class="flex items-center gap-1 text-success-600 font-medium">
                <span class="w-2 h-2 rounded-full bg-success-500 inline-block"></span>
                {{ mod.passing }}
              </span>
              <span class="flex items-center gap-1 text-danger-600 font-medium">
                <span class="w-2 h-2 rounded-full bg-danger-500 inline-block"></span>
                {{ mod.failing }}
              </span>
            </div>
            <div class="text-xs text-gray-400">{{ formatTime(mod.last_run) }}</div>
          </template>
        </div>
      </div>
    </div>

    <!-- Frontend Tests (Vitest) -->
    <div class="card">
      <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="w-7 h-7 rounded-lg bg-yellow-50 flex items-center justify-center">
            <Zap :size="14" class="text-yellow-500" />
          </div>
          <h2 class="text-sm font-semibold text-gray-800">Frontend Tests <span class="text-gray-400 font-normal">(Vitest Browser)</span></h2>
        </div>
        <div class="flex items-center gap-3">
          <span v-if="frontendStats.last_run" class="text-xs text-gray-400">
            Last: <span :class="(frontendStats.last_run.tests_failed ?? 0) > 0 ? 'text-red-500' : 'text-green-500'">
              {{ frontendStats.last_run.tests_passed }}/{{ frontendStats.last_run.tests_run }} passed
            </span>
            · {{ formatTime(frontendStats.last_run.run_at) }}
          </span>
          <button class="btn-primary text-xs py-1.5 px-3" @click="runFrontendTests" :disabled="frontendRunning">
            <Play :size="13" />
            {{ frontendRunning ? 'Running…' : 'Run' }}
          </button>
        </div>
      </div>

      <!-- Stats row -->
      <div class="px-5 py-3 flex items-center gap-6 border-b border-gray-50">
        <div class="flex items-center gap-1.5 text-sm">
          <span class="w-2 h-2 rounded-full bg-gray-300"></span>
          <span class="font-semibold text-gray-700">{{ frontendStats.total }}</span>
          <span class="text-gray-400 text-xs">tests</span>
        </div>
        <div v-if="frontendStats.last_run" class="flex items-center gap-4 text-sm">
          <div class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-green-500"></span>
            <span class="font-semibold text-green-700">{{ frontendStats.last_run.tests_passed }}</span>
            <span class="text-gray-400 text-xs">passed</span>
          </div>
          <div class="flex items-center gap-1.5" v-if="(frontendStats.last_run.tests_failed ?? 0) > 0">
            <span class="w-2 h-2 rounded-full bg-red-500"></span>
            <span class="font-semibold text-red-600">{{ frontendStats.last_run.tests_failed }}</span>
            <span class="text-gray-400 text-xs">failed</span>
          </div>
        </div>
      </div>

      <!-- Test list by file section -->
      <div v-if="Object.keys(frontendStats.sections).length">
        <div v-for="(tests, file) in frontendStats.sections" :key="file"
             class="border-b border-gray-50 last:border-0">
          <div class="px-5 py-2 bg-gray-50/60 flex items-center justify-between">
            <span class="text-xs font-semibold text-gray-500 font-mono">{{ file }}</span>
            <span class="text-xs text-gray-400">{{ tests.length }}</span>
          </div>
          <ul class="divide-y divide-gray-50">
            <li v-for="name in tests" :key="name"
                class="px-5 py-1.5 flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full flex-shrink-0"
                    :class="frontendFailedNames.includes(name) ? 'bg-red-500' : 'bg-yellow-400'"></span>
              <span class="text-xs font-mono"
                    :class="frontendFailedNames.includes(name) ? 'text-red-700 font-semibold' : 'text-gray-700'">{{ name }}</span>
            </li>
          </ul>
        </div>
      </div>
      <div v-else class="px-5 py-6 text-center text-sm text-gray-400">
        No tests collected yet — click Run to collect
      </div>

      <!-- Live run progress (inline, not dialog) -->
      <div v-if="frontendRunning || frontendRunDone" class="px-5 py-4 border-t border-gray-100 bg-gray-50/50">
        <div class="flex items-center justify-between text-xs text-gray-500 mb-1.5">
          <span>{{ frontendProgress.passed + frontendProgress.failed }} / {{ frontendProgress.total || '?' }}</span>
          <span>{{ frontendProgress.pct ?? 0 }}%</span>
        </div>
        <div class="h-2 bg-gray-200 rounded-full overflow-hidden mb-2">
          <div class="h-full rounded-full transition-all duration-300"
               :class="frontendProgress.failed > 0 ? 'bg-red-400' : 'bg-yellow-400'"
               :style="{ width: (frontendProgress.pct ?? 0) + '%' }"></div>
        </div>
        <p class="text-xs font-mono text-gray-400 truncate">{{ frontendProgress.current }}</p>
        <!-- Failure details -->
        <div v-if="frontendRunDone && frontendProgress.failures.length > 0" class="mt-3 space-y-2">
          <div class="text-xs font-semibold text-red-600 uppercase tracking-wide">Failures</div>
          <div v-for="(f, i) in frontendProgress.failures" :key="i"
               class="rounded-lg border border-red-200 bg-red-50/50 overflow-hidden">
            <div class="px-3 py-1.5 bg-red-100/60 text-xs font-mono font-semibold text-red-800 truncate">{{ f.test }}</div>
            <pre class="px-3 py-2 text-[10px] leading-relaxed text-red-700 font-mono whitespace-pre-wrap break-words">{{ f.error }}</pre>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom row: Recent Runs + Open Issues + RAG Status -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">

      <!-- Recent Runs -->
      <div class="card lg:col-span-2">
        <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-gray-800">Recent Runs</h2>
          <RouterLink to="/testing/runs" class="text-xs text-navy hover:underline">View all</RouterLink>
        </div>
        <div v-if="loading" class="p-4 space-y-3 animate-pulse">
          <div v-for="i in 5" :key="i" class="h-4 bg-gray-100 rounded"></div>
        </div>
        <div v-else class="table-scroll">
          <table class="table-wrap">
            <thead>
              <tr>
                <th>Module</th>
                <th>Tier</th>
                <th>Pass rate</th>
                <th>Triggered by</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="run in recentRuns" :key="run.id">
                <td class="capitalize font-medium text-gray-800">{{ run.module }}</td>
                <td><span class="badge-blue">{{ run.tier }}</span></td>
                <td>
                  <span class="font-medium" :class="run.pass_rate >= 80 ? 'text-success-600' : run.pass_rate >= 50 ? 'text-warning-600' : 'text-danger-600'">
                    {{ run.pass_rate }}%
                  </span>
                </td>
                <td class="text-gray-500">{{ run.triggered_by }}</td>
                <td class="text-gray-400 text-xs">{{ formatTime(run.created_at) }}</td>
              </tr>
              <tr v-if="!recentRuns.length">
                <td colspan="5" class="text-center text-gray-400 py-8">No runs yet</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Right column: Issues + RAG -->
      <div class="space-y-4">

        <!-- Open Issues -->
        <div class="card p-5">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-sm font-semibold text-gray-800">Open Issues</h2>
            <RouterLink to="/testing/issues" class="text-xs text-navy hover:underline">View all</RouterLink>
          </div>
          <div v-if="loading" class="animate-pulse space-y-2">
            <div class="h-8 bg-gray-100 rounded w-1/2 mx-auto"></div>
          </div>
          <template v-else>
            <div class="flex items-center gap-3">
              <span class="text-4xl font-bold" :class="health.open_issues > 0 ? 'text-danger-600' : 'text-success-600'">
                {{ health.open_issues }}
              </span>
              <div>
                <div class="text-sm text-gray-600">{{ health.open_issues === 1 ? 'issue' : 'issues' }} open</div>
                <RouterLink to="/testing/issues" class="text-xs text-navy hover:underline mt-0.5 block">
                  Go to tracker →
                </RouterLink>
              </div>
            </div>
          </template>
        </div>

        <!-- RAG Store Status -->
        <div class="card p-5">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-sm font-semibold text-gray-800">RAG Store</h2>
            <button
              class="btn-ghost btn-xs"
              @click="reindex"
              :disabled="reindexing"
            >
              <RefreshCw :size="12" :class="reindexing ? 'animate-spin' : ''" />
              {{ reindexing ? 'Indexing…' : 'Re-index' }}
            </button>
          </div>
          <div v-if="loading" class="animate-pulse space-y-2">
            <div class="h-3 bg-gray-100 rounded w-2/3"></div>
            <div class="h-3 bg-gray-100 rounded w-1/2"></div>
          </div>
          <template v-else>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-gray-500">Documents</span>
                <span class="font-medium text-gray-800">{{ ragStatus.doc_count }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-500">Last indexed</span>
                <span class="font-medium text-gray-800 text-xs">{{ formatTime(ragStatus.last_indexed) }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-500">Status</span>
                <span :class="ragStatus.healthy ? 'badge-green' : 'badge-red'">
                  {{ ragStatus.healthy ? 'Healthy' : 'Stale' }}
                </span>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { testingApi } from '../../api/testing'
import { Play, RefreshCw, CheckCircle, XCircle, TestTube2, BarChart2, Zap } from 'lucide-vue-next'

const router = useRouter()
const loading = ref(true)
const triggering = ref(false)
const reindexing = ref(false)

// ── Frontend (Vitest) state ─────────────────────────────────────────
const frontendStats = ref<{
  total: number
  tests: string[]
  sections: Record<string, string[]>
  last_run: any | null
}>({ total: 0, tests: [], sections: {}, last_run: null })

const frontendRunning = ref(false)
const frontendRunDone = ref(false)
const frontendProgress = ref({
  total: 0, passed: 0, failed: 0, pct: 0, current: '',
  failures: [] as { test: string; error: string }[],
})
const frontendFailedNames = ref<string[]>([])
let _frontendEventSource: EventSource | null = null

function runFrontendTests() {
  if (frontendRunning.value) return
  frontendRunning.value = true
  frontendRunDone.value = false
  frontendProgress.value = { total: 0, passed: 0, failed: 0, pct: 0, current: '', failures: [] }
  frontendFailedNames.value = []

  _frontendEventSource?.close()
  _frontendEventSource = new EventSource(testingApi.streamFrontendRunUrl())

  _frontendEventSource.onmessage = (e) => {
    const msg = JSON.parse(e.data)
    if (msg.type === 'progress') {
      frontendProgress.value.passed = msg.passed ?? frontendProgress.value.passed
      frontendProgress.value.failed = msg.failed ?? frontendProgress.value.failed
      frontendProgress.value.current = msg.current ?? ''
      const total = frontendProgress.value.passed + frontendProgress.value.failed
      frontendProgress.value.pct = frontendStats.value.total > 0
        ? Math.round((total / frontendStats.value.total) * 100)
        : 0
      if (msg.status === 'failed' && msg.current) {
        frontendFailedNames.value.push(msg.current)
      }
    } else if (msg.type === 'done') {
      frontendProgress.value.passed = msg.passed
      frontendProgress.value.failed = msg.failed
      frontendProgress.value.total = msg.total
      frontendProgress.value.pct = 100
      frontendProgress.value.failures = msg.failures ?? []
      frontendRunning.value = false
      frontendRunDone.value = true
      if (msg.record) frontendStats.value.last_run = msg.record
      _frontendEventSource?.close()
    } else if (msg.type === 'error') {
      frontendProgress.value.current = msg.message
      frontendRunning.value = false
      frontendRunDone.value = true
      _frontendEventSource?.close()
    }
  }

  _frontendEventSource.onerror = () => {
    frontendRunning.value = false
    frontendRunDone.value = true
    _frontendEventSource?.close()
  }
}

// ── Mock / live data ────────────────────────────────────────────────
const health = ref({
  score: 84,
  open_issues: 3,
})

const snapshot = ref({
  total: 142,
  passing: 119,
  failing: 23,
  coverage: 71,
})

const modules = ref([
  { name: 'accounts',      label: 'Accounts',      passing: 18, failing: 0, last_run: '2026-04-04T08:12:00Z' },
  { name: 'properties',   label: 'Properties',    passing: 22, failing: 1, last_run: '2026-04-04T08:12:30Z' },
  { name: 'leases',       label: 'Leases',        passing: 15, failing: 4, last_run: '2026-04-04T08:13:00Z' },
  { name: 'maintenance',  label: 'Maintenance',   passing: 20, failing: 2, last_run: '2026-04-04T08:13:30Z' },
  { name: 'esigning',     label: 'E-Signing',     passing: 14, failing: 3, last_run: '2026-04-04T08:14:00Z' },
  { name: 'ai',           label: 'AI',            passing: 11, failing: 0, last_run: '2026-04-04T08:14:30Z' },
  { name: 'tenant_portal',label: 'Tenant Portal', passing: 10, failing: 1, last_run: '2026-04-04T08:15:00Z' },
  { name: 'notifications',label: 'Notifications', passing: 9,  failing: 12, last_run: '2026-04-04T08:15:30Z' },
])

const recentRuns = ref([
  { id: 1, module: 'all',          tier: 'unit',        pass_rate: 84, triggered_by: 'agent',  created_at: '2026-04-04T08:15:00Z' },
  { id: 2, module: 'leases',       tier: 'integration', pass_rate: 73, triggered_by: 'manual', created_at: '2026-04-03T17:22:00Z' },
  { id: 3, module: 'esigning',     tier: 'unit',        pass_rate: 82, triggered_by: 'agent',  created_at: '2026-04-03T14:10:00Z' },
  { id: 4, module: 'notifications',tier: 'unit',        pass_rate: 43, triggered_by: 'agent',  created_at: '2026-04-03T09:45:00Z' },
  { id: 5, module: 'all',          tier: 'unit',        pass_rate: 80, triggered_by: 'agent',  created_at: '2026-04-02T08:00:00Z' },
])

const ragStatus = ref({
  doc_count: 387,
  last_indexed: '2026-04-04T06:00:00Z',
  healthy: true,
})

// ── Computed ────────────────────────────────────────────────────────
const scoreColor = computed(() => {
  if (health.value.score > 80) return '#22c55e'
  if (health.value.score >= 50) return '#f59e0b'
  return '#ef4444'
})

const scoreTier = computed(() => {
  if (health.value.score > 80) return 'Healthy'
  if (health.value.score >= 50) return 'Degraded'
  return 'Critical'
})

const scoreBadgeClass = computed(() => {
  if (health.value.score > 80) return 'bg-success-50 text-success-700'
  if (health.value.score >= 50) return 'bg-warning-50 text-warning-700'
  return 'bg-danger-50 text-danger-700'
})

const suiteSummary = computed(() => [
  {
    label: 'Total Tests',
    value: snapshot.value.total,
    icon: TestTube2,
    bg: 'bg-navy/10',
    iconColor: 'text-navy',
    valueColor: 'text-navy',
  },
  {
    label: 'Passing',
    value: snapshot.value.passing,
    icon: CheckCircle,
    bg: 'bg-success-50',
    iconColor: 'text-success-600',
    valueColor: 'text-success-600',
  },
  {
    label: 'Failing',
    value: snapshot.value.failing,
    icon: XCircle,
    bg: 'bg-danger-50',
    iconColor: 'text-danger-600',
    valueColor: snapshot.value.failing > 0 ? 'text-danger-600' : 'text-gray-900',
  },
  {
    label: 'Coverage',
    value: `${snapshot.value.coverage}%`,
    icon: BarChart2,
    bg: 'bg-info-50',
    iconColor: 'text-info-600',
    valueColor: 'text-gray-900',
  },
])

// ── Helpers ────────────────────────────────────────────────────────
function moduleHealthColor(mod: { passing: number; failing: number }) {
  const total = mod.passing + mod.failing
  if (total === 0) return '#9ca3af'
  const rate = mod.passing / total
  if (rate > 0.8) return '#22c55e'
  if (rate >= 0.5) return '#f59e0b'
  return '#ef4444'
}

function formatTime(iso: string) {
  if (!iso) return '—'
  const d = new Date(iso)
  const now = Date.now()
  const diff = now - d.getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return d.toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })
}

function goToModule(name: string) {
  router.push(`/testing/module/${name}`)
}

// ── Actions ────────────────────────────────────────────────────────
async function triggerFullRun() {
  triggering.value = true
  try {
    await testingApi.triggerRun()
  } catch {
    // backend not yet live — silent
  } finally {
    triggering.value = false
  }
}

async function reindex() {
  reindexing.value = true
  try {
    await testingApi.reindexRAG()
    ragStatus.value.last_indexed = new Date().toISOString()
  } catch {
    // silent
  } finally {
    reindexing.value = false
  }
}

// ── Lifecycle ────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const [h, snap, runs, rag, fe] = await Promise.allSettled([
      testingApi.getHealth(),
      testingApi.getSnapshot(),
      testingApi.getRuns(),
      testingApi.getRAGStatus(),
      testingApi.getFrontendStats(),
    ])
    if (h.status === 'fulfilled') health.value = h.value.data
    if (snap.status === 'fulfilled') {
      const d = snap.value.data
      snapshot.value = d.summary ?? snapshot.value
      modules.value = d.modules ?? modules.value
    }
    if (runs.status === 'fulfilled') recentRuns.value = (runs.value.data.results ?? runs.value.data).slice(0, 5)
    if (rag.status === 'fulfilled') ragStatus.value = rag.value.data
    if (fe.status === 'fulfilled') frontendStats.value = fe.value.data
  } finally {
    loading.value = false
  }
})
</script>
