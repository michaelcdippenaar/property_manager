<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-gray-900">Active Dispatches</h2>
      <button @click="loadDispatches" class="btn-ghost text-sm">
        <RefreshCw :size="14" :class="{ 'animate-spin': loading }" /> Refresh
      </button>
    </div>

    <div v-if="loading" class="space-y-4">
      <div v-for="i in 3" :key="i" class="card p-5 animate-pulse space-y-3">
        <div class="h-4 bg-gray-100 rounded w-1/3"></div>
        <div class="h-3 bg-gray-100 rounded w-2/3"></div>
      </div>
    </div>

    <EmptyState
      v-else-if="!dispatches.length"
      title="No active dispatches"
      description='Use "Get Quotes" on a maintenance request to start.'
      :icon="Truck"
    />

    <!-- Dispatch cards -->
    <div v-else class="space-y-4">
      <div v-for="d in dispatches" :key="d.id" class="card p-5 space-y-4">
        <!-- Header -->
        <div class="flex items-start justify-between">
          <div>
            <div class="font-medium text-gray-900">{{ d.request_title }}</div>
            <div class="flex items-center gap-2 mt-1">
              <span :class="priorityBadge(d.request_priority)">{{ d.request_priority }}</span>
              <span :class="statusBadge(d.status)">{{ d.status }}</span>
              <span v-if="d.dispatched_by_name" class="text-xs text-gray-400">
                by {{ d.dispatched_by_name }}
              </span>
            </div>
          </div>
          <span class="text-xs text-gray-400">{{ formatDate(d.created_at) }}</span>
        </div>

        <!-- Quotes table -->
        <div v-if="d.quote_requests?.length" class="border border-gray-200 rounded-lg overflow-hidden">
          <table class="w-full text-sm">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">Supplier</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">Score</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">Status</th>
                <th class="px-3 py-2 text-right text-xs font-medium text-gray-500">Amount</th>
                <th class="px-3 py-2 text-right text-xs font-medium text-gray-500">Days</th>
                <th class="px-3 py-2 text-right text-xs font-medium text-gray-500">Available</th>
                <th class="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="qr in d.quote_requests" :key="qr.id"
                :class="qr.status === 'awarded' ? 'bg-success-50' : ''">
                <td class="px-3 py-2">
                  <div class="font-medium text-gray-800">{{ qr.supplier_name }}</div>
                  <div class="text-xs text-gray-400">{{ qr.supplier_city }}</div>
                </td>
                <td class="px-3 py-2">
                  <span v-if="qr.match_score" class="text-xs font-mono text-gray-600">
                    {{ qr.match_score }}
                  </span>
                </td>
                <td class="px-3 py-2">
                  <span :class="quoteStatusBadge(qr.status)">{{ qr.status }}</span>
                </td>
                <td class="px-3 py-2 text-right">
                  <span v-if="qr.quote" class="font-medium text-gray-900">
                    R{{ Number(qr.quote.amount).toLocaleString() }}
                  </span>
                  <span v-else class="text-gray-400">—</span>
                </td>
                <td class="px-3 py-2 text-right">
                  <span v-if="qr.quote?.estimated_days" class="text-gray-700">
                    {{ qr.quote.estimated_days }}d
                  </span>
                  <span v-else class="text-gray-400">—</span>
                </td>
                <td class="px-3 py-2 text-right">
                  <span v-if="qr.quote?.available_from" class="text-xs text-gray-600">
                    {{ qr.quote.available_from }}
                  </span>
                  <span v-else class="text-gray-400">—</span>
                </td>
                <td class="px-3 py-2 text-right">
                  <button
                    v-if="qr.quote && qr.status === 'quoted' && d.status !== 'awarded'"
                    @click="awardQuote(d, qr)"
                    class="px-2 py-1 text-xs font-medium text-white bg-success-600 rounded hover:bg-success-700"
                  >
                    Award
                  </button>
                  <span v-if="qr.status === 'awarded'" class="text-xs text-success-700 font-medium">
                    Awarded
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Match reasons detail (expandable) -->
        <div v-if="d.quote_requests?.some((qr: any) => qr.match_reasons)">
          <button @click="toggleReasons(d.id)" class="text-xs text-navy hover:underline">
            {{ expandedReasons.has(d.id) ? 'Hide' : 'Show' }} match breakdown
          </button>
          <div v-if="expandedReasons.has(d.id)" class="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2">
            <div v-for="qr in d.quote_requests.filter((q: any) => q.match_reasons)" :key="qr.id"
              class="p-2 bg-gray-50 rounded text-xs">
              <div class="font-medium text-gray-700 mb-1">{{ qr.supplier_name }} ({{ qr.match_score }})</div>
              <div v-for="(val, key) in qr.match_reasons" :key="key" class="flex justify-between text-gray-500">
                <span class="capitalize">{{ key }}</span>
                <span class="font-mono">{{ val.score }}</span>
              </div>
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
import { RefreshCw, Truck } from 'lucide-vue-next'
import EmptyState from '../../components/EmptyState.vue'

const loading = ref(true)
const dispatches = ref<any[]>([])
const expandedReasons = ref(new Set<number>())

onMounted(() => loadDispatches())

async function loadDispatches() {
  loading.value = true
  try {
    const { data } = await api.get('/maintenance/dispatches/')
    dispatches.value = data
  } finally {
    loading.value = false
  }
}

async function awardQuote(dispatch: any, qr: any) {
  if (!confirm(`Award this job to ${qr.supplier_name} for R${qr.quote.amount}?`)) return
  await api.post(`/maintenance/${dispatch.maintenance_request}/dispatch/award/`, {
    quote_request_id: qr.id,
  })
  await loadDispatches()
}

function toggleReasons(id: number) {
  if (expandedReasons.value.has(id)) expandedReasons.value.delete(id)
  else expandedReasons.value.add(id)
}

function priorityBadge(p: string) {
  return { urgent: 'badge-red', high: 'badge-amber', medium: 'badge-blue', low: 'badge-green' }[p] ?? 'badge-gray'
}

function statusBadge(s: string) {
  return {
    draft: 'badge-gray', sent: 'badge-blue', quoting: 'badge-amber',
    awarded: 'badge-green', cancelled: 'badge-gray',
  }[s] ?? 'badge-gray'
}

function quoteStatusBadge(s: string) {
  return {
    pending: 'badge-gray', viewed: 'badge-blue', quoted: 'badge-amber',
    declined: 'badge-red', awarded: 'badge-green', expired: 'badge-gray',
  }[s] ?? 'badge-gray'
}

function formatDate(iso: string) {
  return iso ? new Date(iso).toLocaleDateString('en-ZA') : '—'
}
</script>
