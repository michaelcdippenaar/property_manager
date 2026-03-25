<template>
  <div class="space-y-5">
    <!-- Filter pills -->
    <div class="flex gap-2 flex-wrap">
      <button
        v-for="f in filters"
        :key="f.value"
        @click="activeFilter = f.value; loadRequests()"
        class="px-3 py-1.5 rounded-full text-sm font-medium transition-colors"
        :class="activeFilter === f.value
          ? 'bg-navy text-white'
          : 'bg-white border border-gray-200 text-gray-600 hover:border-gray-300'"
      >
        {{ f.label }}
      </button>
    </div>

    <!-- Loading skeletons -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="i in 6" :key="i" class="card p-5 space-y-3 animate-pulse">
        <div class="h-3 bg-gray-100 rounded w-1/3"></div>
        <div class="h-4 bg-gray-100 rounded w-2/3"></div>
        <div class="h-3 bg-gray-100 rounded w-full"></div>
      </div>
    </div>

    <!-- Request cards -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="req in requests" :key="req.id" class="card p-5 space-y-3">
        <div class="flex items-start justify-between gap-2">
          <span :class="priorityBadge(req.priority)">{{ req.priority }}</span>
          <select
            :value="req.status"
            @change="updateStatus(req, ($event.target as HTMLSelectElement).value)"
            class="text-xs border border-gray-200 rounded-lg px-2 py-1 text-gray-600 bg-white outline-none focus:ring-1 focus:ring-navy/30 cursor-pointer"
          >
            <option v-for="s in statusOptions" :key="s" :value="s">{{ s.replace('_', ' ') }}</option>
          </select>
        </div>
        <div class="font-medium text-gray-900 text-sm">{{ req.title }}</div>
        <p class="text-xs text-gray-500 leading-relaxed line-clamp-2">{{ req.description }}</p>
        <div class="flex items-center gap-1.5 text-xs text-gray-400 pt-1 border-t border-gray-100">
          <Clock :size="11" />
          {{ formatDate(req.created_at) }}
        </div>
      </div>

      <div v-if="!requests.length" class="col-span-full text-center text-gray-400 py-16">
        No maintenance requests for this filter
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'
import { Clock } from 'lucide-vue-next'

const loading = ref(true)
const activeFilter = ref('all')
const requests = ref<any[]>([])
const statusOptions = ['open', 'in_progress', 'resolved', 'closed']

const filters = [
  { label: 'All', value: 'all' },
  { label: 'Open', value: 'open' },
  { label: 'In Progress', value: 'in_progress' },
  { label: 'Resolved', value: 'resolved' },
]

onMounted(() => loadRequests())

async function loadRequests() {
  loading.value = true
  try {
    const params = activeFilter.value !== 'all' ? { status: activeFilter.value } : {}
    const { data } = await api.get('/maintenance/', { params })
    requests.value = data.results ?? data
  } finally {
    loading.value = false
  }
}

async function updateStatus(req: any, newStatus: string) {
  await api.patch(`/maintenance/${req.id}/`, { status: newStatus })
  req.status = newStatus
}

function priorityBadge(p: string) {
  return { urgent: 'badge-red', high: 'badge-amber', medium: 'badge-blue', low: 'badge-green' }[p] ?? 'badge-gray'
}

function formatDate(iso: string) {
  return iso ? new Date(iso).toLocaleDateString('en-ZA') : '—'
}
</script>
