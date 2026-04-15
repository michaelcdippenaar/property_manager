<template>
  <div class="space-y-6">

    <!-- Header -->
    <PageHeader
      title="Test Run History"
      subtitle="Pass rate trends and raw output for every run"
      :crumbs="[{ label: 'Dashboard', to: '/' }, { label: 'Testing', to: '/testing' }, { label: 'Runs' }]"
    >
      <template #actions>
        <button class="btn-primary" @click="triggerRun" :disabled="triggering">
          <Play :size="15" />
          {{ triggering ? 'Running…' : 'Run All' }}
        </button>
      </template>
    </PageHeader>

    <!-- Trend chart: last 14 runs -->
    <div class="card p-5">
      <h2 class="text-sm font-semibold text-gray-800 mb-4">Pass Rate — Last 14 Runs</h2>
      <div v-if="loading" class="h-24 animate-pulse bg-gray-100 rounded-lg"></div>
      <div v-else class="relative h-24 flex items-end gap-1">
        <!-- Horizontal guide lines -->
        <div class="absolute inset-0 flex flex-col justify-between pointer-events-none">
          <div class="border-b border-gray-100 w-full relative">
            <span class="absolute -top-2 -left-1 text-micro text-gray-400">100%</span>
          </div>
          <div class="border-b border-gray-100 w-full relative">
            <span class="absolute -top-2 -left-1 text-micro text-gray-400">80%</span>
          </div>
          <div class="border-b border-dashed border-warning-300 w-full relative">
            <span class="absolute -top-2 -left-1 text-micro text-warning-500">50%</span>
          </div>
          <div class="border-b border-gray-50 w-full relative">
            <span class="absolute -top-2 -left-1 text-micro text-gray-400">0%</span>
          </div>
        </div>
        <!-- Bars -->
        <div
          v-for="(run, i) in trendRuns"
          :key="i"
          class="flex-1 rounded-t transition-all duration-300 cursor-pointer relative group"
          :class="run.pass_rate > 80 ? 'bg-success-500' : run.pass_rate >= 50 ? 'bg-warning-500' : 'bg-danger-500'"
          :style="{
            height: `${run.pass_rate}%`,
            minHeight: '4px',
          }"
          @click="expandRun(run.id)"
        >
          <!-- Tooltip -->
          <div class="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-micro rounded px-1.5 py-0.5 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
            {{ run.pass_rate }}% · {{ run.module }}
          </div>
        </div>
      </div>
      <div class="flex justify-between text-micro text-gray-400 mt-1 px-0.5">
        <span>Oldest</span>
        <span>Latest</span>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap gap-2">
      <button
        v-for="mod in ['all', ...MODULE_NAMES]"
        :key="mod"
        class="pill"
        :class="filterModule === mod ? 'pill-active' : ''"
        @click="filterModule = mod"
      >
        {{ mod === 'all' ? 'All Modules' : mod }}
      </button>
    </div>

    <!-- Runs table -->
    <div class="card">
      <div v-if="loading" class="p-6 animate-pulse space-y-3">
        <div v-for="i in 6" :key="i" class="h-4 bg-gray-100 rounded"></div>
      </div>
      <div v-else-if="!filteredRuns.length" class="p-12 text-center text-gray-400 text-sm">
        No runs found
      </div>
      <template v-else>
        <div class="table-scroll">
          <table class="table-wrap">
            <thead>
              <tr>
                <th></th>
                <th>Date</th>
                <th>Module</th>
                <th>Tier</th>
                <th>Passed</th>
                <th>Failed</th>
                <th>Coverage</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="run in filteredRuns" :key="run.id">
                <tr
                  class="cursor-pointer"
                  :class="expandedRunId === run.id ? 'bg-navy/5' : ''"
                  @click="expandRun(run.id)"
                >
                  <td class="w-8 text-center">
                    <ChevronDown
                      :size="14"
                      class="text-gray-400 transition-transform"
                      :class="expandedRunId === run.id ? 'rotate-180' : ''"
                    />
                  </td>
                  <td class="text-xs text-gray-500">{{ formatDate(run.created_at) }}</td>
                  <td class="capitalize font-medium text-gray-800">{{ run.module }}</td>
                  <td><span class="badge-blue text-xs">{{ run.tier }}</span></td>
                  <td>
                    <span class="font-medium text-success-600">{{ run.passed }}</span>
                    <span class="text-gray-400 text-xs ml-1">({{ run.pass_rate }}%)</span>
                  </td>
                  <td>
                    <span
                      class="font-medium"
                      :class="run.failed > 0 ? 'text-danger-600' : 'text-gray-400'"
                    >{{ run.failed }}</span>
                  </td>
                  <td class="text-gray-700 text-xs">{{ run.coverage ?? '—' }}%</td>
                  <td class="text-gray-400 text-xs">{{ run.duration_s ? `${run.duration_s}s` : '—' }}</td>
                </tr>
                <!-- Expanded raw output -->
                <tr v-if="expandedRunId === run.id">
                  <td colspan="8" class="p-0">
                    <div class="bg-gray-900 text-success-400 text-xs font-mono p-4 leading-relaxed max-h-64 overflow-y-auto">
                      <pre>{{ run.raw_output || 'No output captured.' }}</pre>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { testingApi } from '../../api/testing'
import { Play, ChevronDown } from 'lucide-vue-next'
import PageHeader from '../../components/PageHeader.vue'

const loading = ref(true)
const triggering = ref(false)
const filterModule = ref('all')
const expandedRunId = ref<number | null>(null)

const MODULE_NAMES = ['accounts', 'properties', 'leases', 'maintenance', 'esigning', 'ai', 'tenant_portal', 'notifications']

const runs = ref([
  {
    id: 1, module: 'all',           tier: 'unit',        passed: 119, failed: 23, pass_rate: 84, coverage: 71, duration_s: 42, created_at: '2026-04-04T08:15:00Z',
    raw_output: `Ran 142 tests in 42.3s\n\nOK (skipped=0)\nFAILED tests/notifications/test_email.py::test_email_send\nFAILED tests/notifications/test_sms.py::test_sms_gateway\nFAILED tests/leases/test_template.py::test_template_clone\n...`,
  },
  {
    id: 2, module: 'leases',        tier: 'integration', passed: 11, failed: 4, pass_rate: 73, coverage: 68, duration_s: 18, created_at: '2026-04-03T17:22:00Z',
    raw_output: `Ran 15 tests in 18.1s\n\nFAILED tests/leases/test_integration.py::test_lease_esigning_flow\n...`,
  },
  {
    id: 3, module: 'esigning',      tier: 'unit',        passed: 12, failed: 3, pass_rate: 80, coverage: 74, duration_s: 9, created_at: '2026-04-03T14:10:00Z',
    raw_output: `Ran 15 tests in 9.2s\n\nFAILED tests/esigning/test_public_sign.py::test_public_sign_link\n...`,
  },
  {
    id: 4, module: 'notifications',  tier: 'unit',       passed: 4, failed: 9, pass_rate: 31, coverage: 55, duration_s: 6, created_at: '2026-04-03T09:45:00Z',
    raw_output: `Ran 13 tests in 6.4s\n\nFAILED 9 tests\nEmail and SMS gateways returning 503\n...`,
  },
  {
    id: 5, module: 'all',            tier: 'unit',       passed: 114, failed: 28, pass_rate: 80, coverage: 70, duration_s: 40, created_at: '2026-04-02T08:00:00Z',
    raw_output: `Ran 142 tests in 40.1s\n\nFAILED 28 tests across 4 modules\n...`,
  },
  {
    id: 6, module: 'accounts',       tier: 'unit',       passed: 18, failed: 0, pass_rate: 100, coverage: 88, duration_s: 5, created_at: '2026-04-01T10:00:00Z',
    raw_output: `Ran 18 tests in 5.1s\n\nOK\n`,
  },
  {
    id: 7, module: 'properties',     tier: 'unit',       passed: 21, failed: 1, pass_rate: 95, coverage: 82, duration_s: 7, created_at: '2026-04-01T09:30:00Z',
    raw_output: `Ran 22 tests in 7.3s\n\nFAILED 1 test\n...`,
  },
  {
    id: 8, module: 'all',            tier: 'unit',       passed: 110, failed: 32, pass_rate: 77, coverage: 69, duration_s: 38, created_at: '2026-03-31T08:00:00Z',
    raw_output: `Ran 142 tests in 38.7s\n\nFAILED 32 tests\n...`,
  },
  {
    id: 9, module: 'all',            tier: 'unit',       passed: 100, failed: 42, pass_rate: 70, coverage: 65, duration_s: 37, created_at: '2026-03-30T08:00:00Z',
    raw_output: `Ran 142 tests in 37.2s\n\nFAILED 42 tests\n...`,
  },
  {
    id: 10, module: 'all',           tier: 'unit',       passed: 105, failed: 37, pass_rate: 74, coverage: 67, duration_s: 39, created_at: '2026-03-29T08:00:00Z',
    raw_output: `Ran 142 tests in 39.1s\n`,
  },
  {
    id: 11, module: 'all',           tier: 'unit',       passed: 108, failed: 34, pass_rate: 76, coverage: 68, duration_s: 41, created_at: '2026-03-28T08:00:00Z',
    raw_output: `Ran 142 tests in 41.0s\n`,
  },
  {
    id: 12, module: 'all',           tier: 'unit',       passed: 112, failed: 30, pass_rate: 79, coverage: 70, duration_s: 40, created_at: '2026-03-27T08:00:00Z',
    raw_output: `Ran 142 tests in 40.3s\n`,
  },
  {
    id: 13, module: 'all',           tier: 'unit',       passed: 115, failed: 27, pass_rate: 81, coverage: 70, duration_s: 42, created_at: '2026-03-26T08:00:00Z',
    raw_output: `Ran 142 tests in 42.1s\n`,
  },
  {
    id: 14, module: 'all',           tier: 'unit',       passed: 90, failed: 52, pass_rate: 63, coverage: 62, duration_s: 36, created_at: '2026-03-25T08:00:00Z',
    raw_output: `Ran 142 tests in 36.9s\n`,
  },
])

// Trend: last 14 "all" runs sorted ascending
const trendRuns = computed(() => {
  return [...runs.value]
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    .slice(-14)
})

const filteredRuns = computed(() => {
  if (filterModule.value === 'all') return runs.value
  return runs.value.filter(r => r.module === filterModule.value)
})

function expandRun(id: number) {
  expandedRunId.value = expandedRunId.value === id ? null : id
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('en-ZA', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

async function triggerRun() {
  triggering.value = true
  try { await testingApi.triggerRun() } catch { /* silent */ } finally { triggering.value = false }
}

onMounted(async () => {
  try {
    const { data } = await testingApi.getRuns()
    const results = data.results ?? data
    if (Array.isArray(results) && results.length) runs.value = results
  } catch { /* use mock */ } finally {
    loading.value = false
  }
})
</script>
