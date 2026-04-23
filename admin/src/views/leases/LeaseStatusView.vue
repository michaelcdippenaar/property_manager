<template>
  <div class="space-y-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <p class="text-sm text-gray-500">Track e-signing status for your leases.</p>
    </div>

    <!-- Filter pills -->
    <FilterPills v-model="activeFilter" :options="filterOptions" @update:modelValue="applyFilter" />

    <!-- Loading skeletons -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 5" :key="i" class="card p-4 space-y-2 animate-pulse">
        <div class="h-3 bg-gray-100 rounded w-1/3"></div>
        <div class="h-4 bg-gray-100 rounded w-2/3"></div>
        <div class="h-3 bg-gray-100 rounded w-full"></div>
      </div>
    </div>

    <!-- Two-column layout: list + detail panel -->
    <div v-else class="grid gap-5" :class="selected ? 'xl:grid-cols-[minmax(0,0.75fr)_minmax(420px,1.25fr)]' : ''">

      <!-- Left: lease cards -->
      <div class="space-y-3 min-w-0">
        <button
          v-for="lease in filteredLeases"
          :key="lease.id"
          type="button"
          class="w-full text-left rounded-xl border px-4 py-3 transition-all border-l-4"
          :class="[
            signingBorderLeft(signingStatuses.get(lease.id)),
            selected?.id === lease.id ? 'bg-slate-50 shadow-sm border-gray-300' : 'bg-white hover:bg-gray-50 hover:border-gray-300 border-gray-200',
          ]"
          @click="selectLease(lease)"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-medium text-gray-900 text-sm truncate">
                  {{ lease.all_tenant_names?.[0] || lease.tenant_name || '—' }}
                </span>
                <span
                  v-if="(lease.all_tenant_names?.length ?? 0) > 1"
                  class="inline-flex items-center px-1.5 py-0.5 rounded text-micro font-medium bg-gray-100 text-gray-500"
                >
                  +{{ lease.all_tenant_names.length - 1 }} more
                </span>
              </div>
              <div class="text-xs text-gray-400 mt-0.5 truncate">
                {{ lease.unit_label }}
                <span v-if="lease.lease_number" class="mx-1 text-gray-300">&middot;</span>
                <span v-if="lease.lease_number" class="font-mono">{{ lease.lease_number }}</span>
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <span :class="leaseStatusBadge(lease.status)" class="text-micro">{{ lease.status }}</span>
              <span :class="signingBadge(signingStatuses.get(lease.id))" class="text-micro">
                {{ signingLabel(signingStatuses.get(lease.id)) }}
              </span>
            </div>
          </div>
          <div class="flex items-center gap-3 mt-2 text-xs text-gray-400">
            <span class="flex items-center gap-1">
              <Calendar :size="10" />
              {{ formatDate(lease.start_date) }} &rarr; {{ formatDate(lease.end_date) }}
            </span>
            <span class="font-semibold text-gray-600 tabular-nums">R{{ Number(lease.monthly_rent).toLocaleString() }}</span>
          </div>
        </button>

        <EmptyState
          v-if="!filteredLeases.length"
          title="No leases"
          description="No leases for this filter."
          :icon="FileText"
        />
      </div>

      <!-- Right: detail panel -->
      <div v-if="selected" class="min-w-0">
        <div class="card sticky top-5 min-h-[70vh] max-h-[calc(100vh-7rem)] overflow-hidden flex flex-col">

          <!-- Header -->
          <div class="px-5 py-4 border-b border-gray-100 space-y-1">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div v-if="selected.lease_number" class="text-xs font-mono text-gray-500">{{ selected.lease_number }}</div>
                <h2 class="text-base font-semibold text-gray-900 mt-0.5">
                  {{ selected.all_tenant_names?.join(', ') || selected.tenant_name || '—' }}
                </h2>
                <div class="text-xs text-gray-400 mt-0.5">{{ selected.unit_label }}</div>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <span :class="leaseStatusBadge(selected.status)">{{ selected.status }}</span>
                <button @click="selected = null" class="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
                  <X :size="16" />
                </button>
              </div>
            </div>
          </div>

          <!-- Scrollable detail content -->
          <div class="flex-1 min-h-0 overflow-y-auto px-5 py-4 space-y-5">

            <!-- Lease terms summary -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <div class="text-xs text-gray-400">Monthly rent</div>
                <div class="text-sm font-semibold text-gray-900">R{{ Number(selected.monthly_rent).toLocaleString() }}</div>
              </div>
              <div>
                <div class="text-xs text-gray-400">Deposit</div>
                <div class="text-sm font-semibold text-gray-900">R{{ Number(selected.deposit).toLocaleString() }}</div>
              </div>
              <div>
                <div class="text-xs text-gray-400">Period</div>
                <div class="text-sm font-semibold text-gray-900">{{ leasePeriodMonths(selected.start_date, selected.end_date) }}</div>
                <div class="text-micro text-gray-400">{{ formatDate(selected.start_date) }} &rarr; {{ formatDate(selected.end_date) }}</div>
              </div>
              <div>
                <div class="text-xs text-gray-400">Payment ref</div>
                <div class="text-sm font-semibold text-gray-900 font-mono">{{ selected.payment_reference || '—' }}</div>
              </div>
            </div>

            <!-- E-Signing section -->
            <div class="border-t border-gray-100 pt-4">
              <ESigningPanel
                :key="selected.id"
                :lease-id="selected.id"
                :lease-tenants="selectedTenants"
              />
            </div>

            <!-- Move-in prep checklist (active leases only) -->
            <div v-if="selected.status === 'active'" class="border-t border-gray-100 pt-4">
              <MoveInChecklist :key="`mic-${selected.id}`" :lease-id="selected.id" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../api'
import { Calendar, X, FileText } from 'lucide-vue-next'
import EmptyState from '../../components/EmptyState.vue'
import FilterPills from '../../components/FilterPills.vue'
import ESigningPanel from './ESigningPanel.vue'
import MoveInChecklist from '../../components/leases/MoveInChecklist.vue'
import { useLeasesStore } from '../../stores/leases'

const leasesStore = useLeasesStore()

const route = useRoute()
const loading = ref(true)
const activeFilter = ref('all')
const leases = ref<any[]>([])
const selected = ref<any | null>(null)
const signingStatuses = reactive(new Map<number, string>())

const filterOptions = [
  { label: 'All', value: 'all' },
  { label: 'Pending', value: 'pending' },
  { label: 'Active', value: 'active' },
]

const filteredLeases = computed(() => {
  if (activeFilter.value === 'all') return leases.value
  return leases.value.filter(l => l.status === activeFilter.value)
})

const selectedTenants = computed(() => {
  if (!selected.value) return []
  const co = (selected.value.co_tenants ?? []).map((ct: any) => ct.person ?? ct)
  const primary = selected.value.primary_tenant_detail
  return primary ? [primary, ...co] : co
})

onMounted(async () => {
  await loadLeases()
  // Auto-select lease from query param (e.g. from builder success screen)
  const leaseParam = route.query.lease
  if (leaseParam) {
    const leaseId = Number(leaseParam)
    const match = leases.value.find((l: any) => l.id === leaseId)
    if (match) selectLease(match)
  }
})

async function loadLeases() {
  loading.value = true
  try {
    await leasesStore.fetchAll()
    leases.value = leasesStore.list
  } finally {
    loading.value = false
  }
  await loadSigningStatuses()
}

async function loadSigningStatuses() {
  const ids = leases.value.map(l => l.id)
  const results = await Promise.allSettled(
    ids.map(id =>
      api.get('/esigning/submissions/', { params: { lease_id: id } })
        .then(({ data }) => ({ id, submissions: data.results ?? data }))
    )
  )
  for (const r of results) {
    if (r.status !== 'fulfilled') continue
    const { id, submissions } = r.value
    if (!submissions.length) {
      signingStatuses.set(id, 'not_sent')
    } else {
      const latest = submissions[0]
      signingStatuses.set(id, latest.status ?? 'not_sent')
    }
  }
}

function selectLease(lease: any) {
  selected.value = { ...lease }
}

function applyFilter() {
  selected.value = null
}

function signingBorderLeft(status: string | undefined) {
  const map: Record<string, string> = {
    not_sent: 'border-l-amber-400',
    pending: 'border-l-amber-400',
    in_progress: 'border-l-blue-400',
    completed: 'border-l-green-400',
    declined: 'border-l-red-500',
    expired: 'border-l-gray-300',
  }
  return map[status ?? 'not_sent'] ?? 'border-l-gray-300'
}

function signingBadge(status: string | undefined) {
  const map: Record<string, string> = {
    not_sent: 'badge-gray',
    pending: 'badge-amber',
    in_progress: 'badge-blue',
    completed: 'badge-green',
    declined: 'badge-red',
    expired: 'badge-gray',
  }
  return map[status ?? 'not_sent'] ?? 'badge-gray'
}

function signingLabel(status: string | undefined) {
  const map: Record<string, string> = {
    not_sent: 'Not sent',
    pending: 'Signing pending',
    in_progress: 'Signing',
    completed: 'Signed',
    declined: 'Declined',
    expired: 'Expired',
  }
  return map[status ?? 'not_sent'] ?? 'Not sent'
}

function leaseStatusBadge(s: string) {
  return { active: 'badge-green', pending: 'badge-amber', expired: 'badge-red', terminated: 'badge-gray' }[s] ?? 'badge-gray'
}

function formatDate(d: string) {
  return d ? new Date(d).toLocaleDateString('en-ZA') : '—'
}

function leasePeriodMonths(start: string, end: string): string {
  if (!start || !end) return '—'
  const s = new Date(start)
  const e = new Date(end)
  const months = (e.getFullYear() - s.getFullYear()) * 12 + (e.getMonth() - s.getMonth())
  return months > 0 ? `${months} month${months !== 1 ? 's' : ''}` : '—'
}
</script>
