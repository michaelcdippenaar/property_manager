<template>
  <div class="space-y-6">

    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold text-navy" style="font-family: 'Bricolage Grotesque', 'Inter', sans-serif;">
          Issue Tracker
        </h1>
        <p class="text-sm text-gray-500 mt-0.5">Track failing-test issues across all modules</p>
      </div>
      <!-- New Issue hint -->
      <div class="relative group">
        <button class="btn-ghost gap-2">
          <Plus :size="15" />
          New Issue
        </button>
        <div class="absolute right-0 top-full mt-2 w-72 bg-white border border-gray-200 rounded-xl shadow-lg p-4 hidden group-hover:block z-10 text-left">
          <p class="text-xs font-semibold text-gray-700 mb-2">Bug workflow</p>
          <ol class="text-xs text-gray-500 space-y-1.5 list-decimal list-inside">
            <li>Write a failing test that reproduces the issue</li>
            <li>Create <code class="bg-gray-100 px-1 rounded">backend/tests/issues/&lt;module&gt;/BUG-xxx.md</code></li>
            <li>Include: title, steps, expected, actual, test file path</li>
            <li>The portal picks it up on next poll</li>
          </ol>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap gap-3 items-center">
      <div class="flex gap-2">
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
      <div class="ml-auto flex gap-2">
        <button
          v-for="s in ['all', 'RED', 'FIXED']"
          :key="s"
          class="pill"
          :class="filterStatus === s ? 'pill-active' : ''"
          @click="filterStatus = s"
        >
          {{ s === 'all' ? 'All Status' : s }}
        </button>
      </div>
    </div>

    <!-- Stats row -->
    <div class="grid grid-cols-3 gap-4">
      <div class="card p-4 text-center">
        <div class="text-2xl font-bold text-danger-600">{{ openCount }}</div>
        <div class="text-xs text-gray-500 mt-0.5">Open (RED)</div>
      </div>
      <div class="card p-4 text-center">
        <div class="text-2xl font-bold text-success-600">{{ fixedCount }}</div>
        <div class="text-xs text-gray-500 mt-0.5">Fixed</div>
      </div>
      <div class="card p-4 text-center">
        <div class="text-2xl font-bold text-gray-800">{{ avgDaysOpen }}</div>
        <div class="text-xs text-gray-500 mt-0.5">Avg days open</div>
      </div>
    </div>

    <!-- Issues table -->
    <div class="card">
      <div v-if="loading" class="p-6 animate-pulse space-y-3">
        <div v-for="i in 5" :key="i" class="h-4 bg-gray-100 rounded"></div>
      </div>
      <div v-else-if="!filteredIssues.length" class="p-12 text-center">
        <CheckCircle :size="40" class="mx-auto text-success-400 mb-3" />
        <p class="text-gray-500 text-sm">No issues match the current filters</p>
      </div>
      <table v-else class="table-wrap">
        <thead>
          <tr>
            <th>Title</th>
            <th>Module</th>
            <th>Status</th>
            <th>Discovered</th>
            <th>Days open</th>
            <th>Test file</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="issue in filteredIssues" :key="issue.id" class="cursor-default">
            <td class="font-medium text-gray-800 max-w-xs">
              <span :title="issue.title">{{ issue.title }}</span>
            </td>
            <td>
              <span class="capitalize text-xs font-medium text-navy bg-navy/10 px-2 py-0.5 rounded-full">
                {{ issue.module }}
              </span>
            </td>
            <td>
              <span :class="issue.status === 'RED' ? 'badge-red' : 'badge-green'">{{ issue.status }}</span>
            </td>
            <td class="text-gray-500 text-xs">{{ formatDate(issue.discovered_at) }}</td>
            <td>
              <span
                class="font-medium text-xs"
                :class="daysOpen(issue.discovered_at) > 7 ? 'text-danger-600' : 'text-gray-700'"
              >
                {{ daysOpen(issue.discovered_at) }}d
              </span>
            </td>
            <td class="text-gray-400 text-xs font-mono truncate max-w-[180px]" :title="issue.test_file">
              {{ issue.test_file || '—' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { testingApi } from '../../api/testing'
import { Plus, CheckCircle } from 'lucide-vue-next'

const loading = ref(true)
const filterModule = ref('all')
const filterStatus = ref('all')

const MODULE_NAMES = ['accounts', 'properties', 'leases', 'maintenance', 'esigning', 'ai', 'tenant_portal', 'notifications']

const issues = ref([
  {
    id: 1,
    title: 'Email gateway timeout under high load',
    module: 'notifications',
    status: 'RED',
    discovered_at: '2026-03-28T10:00:00Z',
    test_file: 'backend/tests/notifications/test_email.py',
  },
  {
    id: 2,
    title: 'SMS fallback not triggered on 5xx gateway response',
    module: 'notifications',
    status: 'RED',
    discovered_at: '2026-03-30T14:00:00Z',
    test_file: 'backend/tests/notifications/test_sms.py',
  },
  {
    id: 3,
    title: 'Lease template clone loses merge fields',
    module: 'leases',
    status: 'RED',
    discovered_at: '2026-04-01T09:00:00Z',
    test_file: 'backend/tests/leases/test_template.py',
  },
  {
    id: 4,
    title: 'Public sign link expires prematurely',
    module: 'esigning',
    status: 'RED',
    discovered_at: '2026-04-02T11:00:00Z',
    test_file: 'backend/tests/esigning/test_public_sign.py',
  },
  {
    id: 5,
    title: 'Property unit count mismatch after soft delete',
    module: 'properties',
    status: 'FIXED',
    discovered_at: '2026-03-15T08:00:00Z',
    test_file: 'backend/tests/properties/test_unit_count.py',
  },
  {
    id: 6,
    title: 'JWT refresh token not rotated on use',
    module: 'accounts',
    status: 'FIXED',
    discovered_at: '2026-03-10T08:00:00Z',
    test_file: 'backend/tests/accounts/test_auth.py',
  },
])

const filteredIssues = computed(() => {
  return issues.value.filter(i => {
    const modMatch = filterModule.value === 'all' || i.module === filterModule.value
    const statusMatch = filterStatus.value === 'all' || i.status === filterStatus.value
    return modMatch && statusMatch
  })
})

const openCount = computed(() => issues.value.filter(i => i.status === 'RED').length)
const fixedCount = computed(() => issues.value.filter(i => i.status === 'FIXED').length)
const avgDaysOpen = computed(() => {
  const open = issues.value.filter(i => i.status === 'RED')
  if (!open.length) return 0
  const total = open.reduce((sum, i) => sum + daysOpen(i.discovered_at), 0)
  return Math.round(total / open.length)
})

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' })
}

function daysOpen(iso: string) {
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)
}

onMounted(async () => {
  try {
    const { data } = await testingApi.getIssues()
    if (Array.isArray(data) && data.length) issues.value = data
    else if (data.results?.length) issues.value = data.results
  } catch { /* use mock */ } finally {
    loading.value = false
  }
})
</script>
