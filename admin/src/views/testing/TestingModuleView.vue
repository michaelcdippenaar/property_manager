<template>
  <div class="space-y-6">

    <!-- Back + Header -->
    <div>
      <RouterLink to="/testing" class="text-xs text-gray-400 hover:text-navy flex items-center gap-1 mb-3">
        <ChevronLeft :size="14" /> Back to Dashboard
      </RouterLink>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-navy/10 flex items-center justify-center">
            <component :is="moduleIcon" :size="20" class="text-navy" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-navy capitalize" style="font-family: 'Bricolage Grotesque', 'Inter', sans-serif;">
              {{ moduleName }}
            </h1>
            <p class="text-xs text-gray-500">{{ moduleDescription }}</p>
            <p v-if="lastRun" class="text-xs text-gray-400 mt-0.5">
              Last run: {{ formatDate(lastRun.run_at) }} —
              <span :class="lastRun.tests_failed > 0 ? 'text-red-500' : 'text-green-500'">
                {{ lastRun.tests_passed }}/{{ lastRun.tests_run }} passed
              </span>
            </p>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <!-- Loading indicator while collecting test stats -->
          <div v-if="loading" class="flex items-center gap-2 text-xs text-gray-400">
            <svg class="animate-spin h-4 w-4 text-navy/60" viewBox="0 0 24 24" fill="none">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            <span>Collecting tests…</span>
          </div>
          <button class="btn-primary" @click="runModule" :disabled="running || loading">
            <Play :size="15" />
            {{ running ? 'Running…' : 'Run Tests' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Stats row -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div class="card p-4" v-for="s in moduleStats" :key="s.label">
        <div v-if="loading" class="animate-pulse space-y-2">
          <div class="h-3 bg-gray-100 rounded w-2/3"></div>
          <div class="h-7 bg-gray-100 rounded w-1/2"></div>
        </div>
        <template v-else>
          <div class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">{{ s.label }}</div>
          <div class="text-2xl font-bold" :class="s.color">{{ s.value }}</div>
        </template>
      </div>
    </div>

    <!-- Unit Tests — sectioned by file -->
    <div class="card">
      <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <h2 class="text-sm font-semibold text-gray-800">Unit Tests</h2>
        <span class="badge-gray text-xs">{{ stats.unit }}</span>
      </div>
      <div v-if="loading" class="p-4 animate-pulse space-y-3">
        <div v-for="i in 5" :key="i" class="h-4 bg-gray-100 rounded"></div>
      </div>
      <div v-else-if="!stats.unit" class="p-8 text-center text-gray-400 text-sm">
        No unit tests found
      </div>
      <template v-else>
        <div v-for="(tests, section) in unitSections" :key="section"
             class="border-b border-gray-50 last:border-0">
          <div class="px-5 py-2 bg-gray-50/60 flex items-center justify-between">
            <span class="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              {{ formatSection(section) }}
            </span>
            <span class="text-xs text-gray-400">{{ tests.length }}</span>
          </div>
          <ul class="divide-y divide-gray-50 max-h-64 overflow-y-auto">
            <li v-for="name in tests" :key="name"
                class="px-5 py-2 flex items-center gap-3 hover:bg-gray-50/60 transition-colors">
              <span class="w-1.5 h-1.5 rounded-full flex-shrink-0"
                    :class="runProgress.failedNames.includes(name) ? 'bg-red-500' : 'bg-green-500'"></span>
              <span class="flex-1 text-xs font-mono"
                    :class="runProgress.failedNames.includes(name) ? 'text-red-700 font-semibold' : 'text-gray-700'">{{ name }}</span>
            </li>
          </ul>
        </div>
        <!-- Fallback flat list if no sections parsed -->
        <ul v-if="!Object.keys(unitSections).length" class="divide-y divide-gray-100 max-h-96 overflow-y-auto">
          <li v-for="name in unitTests" :key="name"
              class="px-5 py-2.5 flex items-center gap-3 hover:bg-gray-50/60 transition-colors">
            <span class="w-2 h-2 rounded-full flex-shrink-0"
                  :class="runProgress.failedNames.includes(name) ? 'bg-red-500' : 'bg-green-500'"></span>
            <span class="flex-1 text-xs font-mono"
                  :class="runProgress.failedNames.includes(name) ? 'text-red-700 font-semibold' : 'text-gray-700'">{{ name }}</span>
          </li>
        </ul>
      </template>
    </div>

    <!-- Integration Tests — sectioned by file -->
    <div class="card">
      <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <h2 class="text-sm font-semibold text-gray-800">Integration Tests</h2>
        <span class="badge-gray text-xs">{{ stats.integration }}</span>
      </div>
      <div v-if="loading" class="p-4 animate-pulse space-y-3">
        <div v-for="i in 3" :key="i" class="h-4 bg-gray-100 rounded"></div>
      </div>
      <div v-else-if="!stats.integration" class="p-8 text-center text-gray-400 text-sm">
        No integration tests found
      </div>
      <template v-else>
        <div v-for="(tests, section) in integrationSections" :key="section"
             class="border-b border-gray-50 last:border-0">
          <div class="px-5 py-2 bg-gray-50/60 flex items-center justify-between">
            <span class="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              {{ formatSection(section) }}
            </span>
            <span class="text-xs text-gray-400">{{ tests.length }}</span>
          </div>
          <ul class="divide-y divide-gray-50 max-h-64 overflow-y-auto">
            <li v-for="name in tests" :key="name"
                class="px-5 py-2 flex items-center gap-3 hover:bg-gray-50/60 transition-colors">
              <span class="w-1.5 h-1.5 rounded-full flex-shrink-0"
                    :class="runProgress.failedNames.includes(name) ? 'bg-red-500' : 'bg-blue-500'"></span>
              <span class="flex-1 text-xs font-mono"
                    :class="runProgress.failedNames.includes(name) ? 'text-red-700 font-semibold' : 'text-gray-700'">{{ name }}</span>
            </li>
          </ul>
        </div>
        <ul v-if="!Object.keys(integrationSections).length" class="divide-y divide-gray-100 max-h-96 overflow-y-auto">
          <li v-for="name in integrationTests" :key="name"
              class="px-5 py-2.5 flex items-center gap-3 hover:bg-gray-50/60 transition-colors">
            <span class="w-2 h-2 rounded-full flex-shrink-0"
                  :class="runProgress.failedNames.includes(name) ? 'bg-red-500' : 'bg-blue-500'"></span>
            <span class="flex-1 text-xs font-mono"
                  :class="runProgress.failedNames.includes(name) ? 'text-red-700 font-semibold' : 'text-gray-700'">{{ name }}</span>
          </li>
        </ul>
      </template>
    </div>

    <!-- E-Signing Tests (shown under Leases since esigning is part of the lease flow) -->
    <template v-if="moduleName === 'leases' && relatedEsigning">
      <div class="card border-l-4 border-l-indigo-300">
        <div class="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
          <FileSignature :size="16" class="text-indigo-500" />
          <h2 class="text-sm font-semibold text-gray-800">E-Signing Tests</h2>
          <span class="text-xs text-gray-400 ml-1">(part of lease flow)</span>
          <span class="badge-gray text-xs ml-auto">
            {{ (relatedEsigning.unit?.count ?? 0) + (relatedEsigning.integration?.count ?? 0) }}
          </span>
        </div>

        <!-- Esigning Unit subsections -->
        <div v-if="relatedEsigning.unit?.count">
          <div class="px-5 py-2 bg-indigo-50/40 flex items-center justify-between">
            <span class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Unit Tests</span>
            <span class="text-xs text-gray-400">{{ relatedEsigning.unit.count }}</span>
          </div>
          <div v-for="(tests, section) in relatedEsigning.unit.sections" :key="section"
               class="border-b border-gray-50 last:border-0">
            <div class="px-5 py-2 bg-gray-50/40 flex items-center justify-between pl-8">
              <span class="text-xs font-medium text-gray-500">{{ formatSection(section) }}</span>
              <span class="text-xs text-gray-400">{{ tests.length }}</span>
            </div>
            <ul class="divide-y divide-gray-50 max-h-48 overflow-y-auto">
              <li v-for="name in tests" :key="name"
                  class="px-5 py-2 pl-10 flex items-center gap-3 hover:bg-gray-50/60 transition-colors">
                <span class="w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0"></span>
                <span class="flex-1 text-xs text-gray-700 font-mono">{{ name }}</span>
              </li>
            </ul>
          </div>
        </div>

        <!-- Esigning Integration subsections -->
        <div v-if="relatedEsigning.integration?.count">
          <div class="px-5 py-2 bg-indigo-50/40 flex items-center justify-between">
            <span class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Integration Tests</span>
            <span class="text-xs text-gray-400">{{ relatedEsigning.integration.count }}</span>
          </div>
          <div v-for="(tests, section) in relatedEsigning.integration.sections" :key="section"
               class="border-b border-gray-50 last:border-0">
            <div class="px-5 py-2 bg-gray-50/40 flex items-center justify-between pl-8">
              <span class="text-xs font-medium text-gray-500">{{ formatSection(section) }}</span>
              <span class="text-xs text-gray-400">{{ tests.length }}</span>
            </div>
            <ul class="divide-y divide-gray-50 max-h-48 overflow-y-auto">
              <li v-for="name in tests" :key="name"
                  class="px-5 py-2 pl-10 flex items-center gap-3 hover:bg-gray-50/60 transition-colors">
                <span class="w-1.5 h-1.5 rounded-full bg-indigo-500 flex-shrink-0"></span>
                <span class="flex-1 text-xs text-gray-700 font-mono">{{ name }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </template>

    <!-- Red tests pending -->
    <div v-if="redTests.length" class="card">
      <div class="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
        <span class="w-2.5 h-2.5 rounded-full bg-red-500"></span>
        <h2 class="text-sm font-semibold text-gray-800">Red Tests — Pending Implementation</h2>
        <span class="badge-red text-xs ml-auto">{{ stats.red }}</span>
      </div>
      <ul class="divide-y divide-gray-100">
        <li v-for="name in redTests" :key="name"
            class="px-5 py-2.5 flex items-center gap-3">
          <span class="w-2 h-2 rounded-full bg-red-400 flex-shrink-0"></span>
          <span class="flex-1 text-xs text-gray-700 font-mono">{{ name }}</span>
          <span class="text-xs text-red-500 font-medium">xfail</span>
        </li>
      </ul>
    </div>

    <!-- Open Issues -->
    <div class="card">
      <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <h2 class="text-sm font-semibold text-gray-800">Open Issues</h2>
        <RouterLink to="/testing/issues" class="text-xs text-navy hover:underline">View all</RouterLink>
      </div>
      <div v-if="loading" class="p-4 animate-pulse space-y-3">
        <div v-for="i in 2" :key="i" class="h-4 bg-gray-100 rounded"></div>
      </div>
      <div v-else-if="!moduleIssues.length" class="p-8 text-center text-gray-400 text-sm">
        No open issues for this module
      </div>
      <div v-else class="table-scroll">
        <table class="table-wrap">
          <thead><tr><th>Title</th><th>Status</th><th>Discovered</th><th>Days open</th></tr></thead>
          <tbody>
            <tr v-for="issue in moduleIssues" :key="issue.id">
              <td class="font-medium text-gray-800">{{ issue.title }}</td>
              <td><span :class="issue.status === 'red' ? 'badge-red' : 'badge-green'" class="uppercase">{{ issue.status }}</span></td>
              <td class="text-gray-500 text-xs">{{ formatDate(issue.discovered_at) }}</td>
              <td class="text-gray-500">{{ daysOpen(issue.discovered_at) }}d</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>

  <!-- Live Run Progress Dialog -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="showRunDialog"
           class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50"
           @click.self="showRunDialog = false">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">

          <!-- Header -->
          <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-navy/10 flex items-center justify-center">
                <component :is="moduleIcon" :size="16" class="text-navy" />
              </div>
              <div>
                <h3 class="text-sm font-semibold text-gray-900 capitalize">Running {{ moduleName }}</h3>
                <p class="text-xs text-gray-400">{{ runProgress.done ? 'Complete' : 'Tests in progress…' }}</p>
              </div>
            </div>
            <button v-if="runProgress.done" @click="closeRunDialog"
                    class="text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
          </div>

          <!-- Progress bar -->
          <div class="px-6 pt-5">
            <div class="flex items-center justify-between text-xs text-gray-500 mb-1.5">
              <span>{{ runProgress.passed + runProgress.failed + runProgress.xfailed }} / {{ runProgress.total || '?' }}</span>
              <span>{{ runProgress.pct ?? 0 }}%</span>
            </div>
            <div class="h-2.5 bg-gray-100 rounded-full overflow-hidden">
              <div class="h-full rounded-full transition-all duration-300"
                   :class="runProgress.failed > 0 ? 'bg-red-400' : 'bg-navy'"
                   :style="{ width: (runProgress.pct ?? 0) + '%' }"></div>
            </div>
          </div>

          <!-- Current test -->
          <div class="px-6 py-3">
            <p class="text-xs font-mono text-gray-400 truncate min-h-[1.2rem]">
              {{ runProgress.current || (runProgress.done ? '' : 'Collecting tests…') }}
            </p>
          </div>

          <!-- Stats -->
          <div class="px-6 pb-5 flex gap-6">
            <div class="flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-green-500"></span>
              <span class="text-sm font-semibold text-green-700">{{ runProgress.passed }}</span>
              <span class="text-xs text-gray-400">passed</span>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-red-500"></span>
              <span class="text-sm font-semibold" :class="runProgress.failed > 0 ? 'text-red-600' : 'text-gray-300'">{{ runProgress.failed }}</span>
              <span class="text-xs text-gray-400">failed</span>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-amber-400"></span>
              <span class="text-sm font-semibold text-amber-600">{{ runProgress.xfailed }}</span>
              <span class="text-xs text-gray-400">xfail</span>
            </div>
          </div>

          <!-- Failure details -->
          <div v-if="runProgress.done && runProgress.failures.length > 0"
               class="px-6 pb-4 max-h-60 overflow-y-auto">
            <div class="text-xs font-semibold text-red-600 uppercase tracking-wide mb-2">Failures</div>
            <div v-for="(f, i) in runProgress.failures" :key="i"
                 class="mb-3 last:mb-0 rounded-lg border border-red-200 bg-red-50/50 overflow-hidden">
              <div class="px-3 py-1.5 bg-red-100/60 text-xs font-mono font-semibold text-red-800 truncate">
                {{ f.test }}
              </div>
              <pre class="px-3 py-2 text-[10px] leading-relaxed text-red-700 font-mono whitespace-pre-wrap break-words overflow-x-auto">{{ f.error }}</pre>
            </div>
          </div>
          <!-- Fallback: show failed names if no traceback captured -->
          <div v-else-if="runProgress.done && runProgress.failedNames.length > 0 && runProgress.failures.length === 0"
               class="px-6 pb-4">
            <div class="text-xs font-semibold text-red-600 uppercase tracking-wide mb-2">Failed Tests</div>
            <ul class="space-y-1">
              <li v-for="name in runProgress.failedNames" :key="name"
                  class="flex items-center gap-2 text-xs font-mono text-red-700">
                <span class="w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0"></span>
                {{ name }}
              </li>
            </ul>
          </div>

          <!-- Done footer -->
          <div v-if="runProgress.done"
               class="px-6 py-3 border-t border-gray-100 flex items-center justify-between"
               :class="runProgress.failed > 0 ? 'bg-red-50' : 'bg-green-50'">
            <span class="text-sm font-medium" :class="runProgress.failed > 0 ? 'text-red-700' : 'text-green-700'">
              {{ runProgress.failed > 0 ? `${runProgress.failed} test(s) failed` : 'All tests passed' }}
            </span>
            <button class="btn-primary text-xs py-1.5 px-4" @click="closeRunDialog">Done</button>
          </div>

          <!-- Spinner while running -->
          <div v-else class="px-6 py-3 border-t border-gray-100 flex items-center gap-2">
            <svg class="animate-spin h-3.5 w-3.5 text-navy" viewBox="0 0 24 24" fill="none">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            <span class="text-xs text-gray-400">Running pytest…</span>
          </div>

        </div>
      </div>
    </Transition>
  </Teleport>

</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { testingApi } from '../../api/testing'
import {
  ChevronLeft, Play, FileSignature,
  Users, Building2, FileText, Wrench, Sparkles, Smartphone, Bell,
} from 'lucide-vue-next'

const route = useRoute()
const loading = ref(true)
const running = ref(false)
const showRunDialog = ref(false)
const runProgress = ref({
  total: 0, passed: 0, failed: 0, xfailed: 0,
  pct: 0, current: '', done: false,
  failures: [] as { test: string; error: string }[],
  failedNames: [] as string[],
})

const moduleName = computed(() => (route.params.module as string) || 'unknown')

const MODULE_META: Record<string, { desc: string; icon: any }> = {
  accounts:      { desc: 'User accounts, auth, profiles, roles and permissions', icon: Users },
  properties:    { desc: 'Properties, units, landlords and ownership', icon: Building2 },
  leases:        { desc: 'Lease lifecycle, templates, builder and calendar', icon: FileText },
  maintenance:   { desc: 'Maintenance requests, suppliers and dispatch', icon: Wrench },
  esigning:      { desc: 'Native e-signing, PDF generation and Gotenberg signing flows', icon: FileSignature },
  ai:            { desc: 'AI agent, maintenance chat, MCP tools and RAG', icon: Sparkles },
  tenant_portal: { desc: 'Tenant web and mobile portal features', icon: Smartphone },
  notifications: { desc: 'Email, SMS and push notification delivery', icon: Bell },
}

const moduleIcon = computed(() => MODULE_META[moduleName.value]?.icon ?? FileText)
const moduleDescription = computed(() => MODULE_META[moduleName.value]?.desc ?? '')

// ── Data ────────────────────────────────────────────────────────────
const unitTests = ref<string[]>([])
const unitSections = ref<Record<string, string[]>>({})
const integrationTests = ref<string[]>([])
const integrationSections = ref<Record<string, string[]>>({})
const redTests = ref<string[]>([])
const moduleIssues = ref<any[]>([])
const lastRun = ref<any>(null)
const relatedEsigning = ref<any>(null)
const stats = ref({ unit: 0, integration: 0, red: 0, green: 0, total: 0 })

const moduleStats = computed(() => [
  { label: 'Total',       value: stats.value.total,       color: 'text-navy' },
  { label: 'Unit',        value: stats.value.unit,        color: 'text-blue-600' },
  { label: 'Integration', value: stats.value.integration, color: 'text-indigo-600' },
  { label: 'Red (xfail)', value: stats.value.red,         color: stats.value.red > 0 ? 'text-red-500' : 'text-gray-400' },
])

// ── Helpers ────────────────────────────────────────────────────────
function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' })
}
function daysOpen(iso: string) {
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)
}

/** "test_merge_fields" → "Merge Fields" */
function formatSection(key: string) {
  return key
    .replace(/^test_/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

let _eventSource: EventSource | null = null

function runModule() {
  if (running.value) return
  running.value = true
  showRunDialog.value = true
  runProgress.value = { total: 0, passed: 0, failed: 0, xfailed: 0, pct: 0, current: '', done: false, failures: [], failedNames: [] }

  _eventSource?.close()
  _eventSource = new EventSource(testingApi.streamRunUrl(moduleName.value))

  _eventSource.onmessage = (e) => {
    const msg = JSON.parse(e.data)
    if (msg.type === 'start') {
      runProgress.value.total = msg.total
    } else if (msg.type === 'progress') {
      runProgress.value.passed = msg.passed
      runProgress.value.failed = msg.failed
      runProgress.value.xfailed = msg.xfailed ?? 0
      runProgress.value.pct = msg.pct ?? runProgress.value.pct
      runProgress.value.current = msg.current ?? ''
      // Collect failed test names in real-time
      if (msg.status === 'failed' && msg.current) {
        runProgress.value.failedNames.push(msg.current)
      }
    } else if (msg.type === 'done') {
      runProgress.value.passed = msg.passed
      runProgress.value.failed = msg.failed
      runProgress.value.xfailed = msg.xfailed ?? 0
      runProgress.value.pct = 100
      runProgress.value.done = true
      runProgress.value.failures = msg.failures ?? []
      running.value = false
      if (msg.record) lastRun.value = msg.record
      _eventSource?.close()
    } else if (msg.type === 'error') {
      runProgress.value.current = msg.message
      runProgress.value.done = true
      running.value = false
      _eventSource?.close()
    }
  }

  _eventSource.onerror = () => {
    runProgress.value.done = true
    running.value = false
    _eventSource?.close()
  }
}

function closeRunDialog() {
  showRunDialog.value = false
  // Reload module data to reflect latest run
  loadData(moduleName.value)
}

async function loadData(mod: string) {
  loading.value = true
  runProgress.value = { total: 0, passed: 0, failed: 0, xfailed: 0, pct: 0, current: '', done: false, failures: [], failedNames: [] }
  try {
    const [moduleRes, issuesRes] = await Promise.allSettled([
      testingApi.getModuleStats(mod),
      testingApi.getIssues({ module: mod, status: 'red' }),
    ])

    if (moduleRes.status === 'fulfilled') {
      const d = moduleRes.value.data
      unitTests.value = d.unit?.tests ?? []
      unitSections.value = d.unit?.sections ?? {}
      integrationTests.value = d.integration?.tests ?? []
      integrationSections.value = d.integration?.sections ?? {}
      redTests.value = d.red?.tests ?? []
      lastRun.value = d.last_run ?? null
      relatedEsigning.value = d.related_esigning ?? null
      stats.value = {
        unit: d.unit?.count ?? 0,
        integration: d.integration?.count ?? 0,
        red: d.red?.count ?? 0,
        green: d.green?.count ?? 0,
        total: d.total ?? 0,
      }
    }

    if (issuesRes.status === 'fulfilled') {
      const data = issuesRes.value.data
      moduleIssues.value = data.results ?? data
    }
  } catch (err) {
    console.error('Module stats load failed:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => loadData(moduleName.value))
watch(() => route.params.module, (newMod) => {
  if (newMod) loadData(newMod as string)
})
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
