<template>
  <div class="space-y-6">
    <!-- Stat cards -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div v-for="stat in stats" :key="stat.label" class="card p-5">
        <div v-if="loading" class="space-y-2 animate-pulse">
          <div class="h-3 bg-gray-100 rounded w-2/3"></div>
          <div class="h-7 bg-gray-100 rounded w-1/2"></div>
        </div>
        <template v-else>
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs font-medium text-gray-500 uppercase tracking-wide">{{ stat.label }}</span>
            <div class="w-7 h-7 rounded-lg flex items-center justify-center" :class="stat.bg">
              <component :is="stat.icon" :size="14" :class="stat.iconColor" />
            </div>
          </div>
          <div class="text-2xl font-bold" :class="stat.valueColor">{{ stat.value }}</div>
        </template>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-5 gap-4">
      <!-- Recent maintenance -->
      <div class="card lg:col-span-3">
        <div class="px-5 py-4 border-b border-gray-100">
          <h2 class="text-sm font-semibold text-gray-800">Recent Maintenance</h2>
        </div>
        <div v-if="loading" class="p-5 space-y-3 animate-pulse">
          <div v-for="i in 4" :key="i" class="h-4 bg-gray-100 rounded"></div>
        </div>
        <table v-else class="table-wrap">
          <thead>
            <tr>
              <th>Title</th>
              <th>Unit</th>
              <th>Priority</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="req in recentMaintenance" :key="req.id">
              <td class="font-medium text-gray-800">{{ req.title }}</td>
              <td class="text-gray-500">{{ req.unit }}</td>
              <td><span :class="priorityBadge(req.priority)">{{ req.priority }}</span></td>
              <td><span :class="statusBadge(req.status)">{{ req.status.replace('_', ' ') }}</span></td>
            </tr>
            <tr v-if="!recentMaintenance.length">
              <td colspan="4" class="text-center text-gray-400 py-8">No open requests</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Occupancy -->
      <div class="card lg:col-span-2 p-5">
        <h2 class="text-sm font-semibold text-gray-800 mb-4">Unit Occupancy</h2>
        <div v-if="loading" class="space-y-4 animate-pulse">
          <div v-for="i in 3" :key="i" class="space-y-1">
            <div class="h-3 bg-gray-100 rounded w-1/2"></div>
            <div class="h-2 bg-gray-100 rounded"></div>
          </div>
        </div>
        <div v-else class="space-y-4">
          <div v-for="item in occupancy" :key="item.label">
            <div class="flex justify-between text-sm mb-1.5">
              <span class="text-gray-600">{{ item.label }}</span>
              <span class="font-medium text-gray-800">{{ item.count }}</span>
            </div>
            <div class="h-2 rounded-full bg-gray-100 overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-500"
                :class="item.barColor"
                :style="`width: ${item.percent}%`"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import { Building2, Users, Wrench, FileText } from 'lucide-vue-next'

const loading = ref(true)
const statsData = ref<Record<string, number>>({})
const recentMaintenance = ref<any[]>([])

onMounted(async () => {
  try {
    const [s, m] = await Promise.all([
      api.get('/stats/'),
      api.get('/maintenance/?status=open&page_size=5'),
    ])
    statsData.value = s.data
    recentMaintenance.value = (m.data.results ?? m.data).slice(0, 5)
  } finally {
    loading.value = false
  }
})

const stats = computed(() => [
  { label: 'Properties', value: statsData.value.total_properties ?? 0, icon: Building2, bg: 'bg-navy/10', iconColor: 'text-navy', valueColor: 'text-navy' },
  { label: 'Active Tenants', value: statsData.value.active_tenants ?? 0, icon: Users, bg: 'bg-pink-brand/10', iconColor: 'text-pink-brand', valueColor: 'text-gray-900' },
  { label: 'Open Requests', value: statsData.value.open_maintenance ?? 0, icon: Wrench, bg: 'bg-amber-50', iconColor: 'text-amber-600', valueColor: 'text-gray-900' },
  { label: 'Active Leases', value: statsData.value.active_leases ?? 0, icon: FileText, bg: 'bg-emerald-50', iconColor: 'text-emerald-600', valueColor: 'text-gray-900' },
])

const occupancy = computed(() => {
  const total = statsData.value.total_units || 1
  const occupied = statsData.value.occupied_units ?? 0
  const available = statsData.value.available_units ?? 0
  const maintenance = total - occupied - available
  return [
    { label: 'Occupied', count: occupied, percent: Math.round((occupied / total) * 100), barColor: 'bg-navy' },
    { label: 'Available', count: available, percent: Math.round((available / total) * 100), barColor: 'bg-emerald-500' },
    { label: 'Maintenance', count: Math.max(0, maintenance), percent: Math.round((Math.max(0, maintenance) / total) * 100), barColor: 'bg-amber-400' },
  ]
})

function priorityBadge(p: string) {
  return { urgent: 'badge-red', high: 'badge-amber', medium: 'badge-blue', low: 'badge-green' }[p] ?? 'badge-gray'
}
function statusBadge(s: string) {
  return { open: 'badge-red', in_progress: 'badge-amber', resolved: 'badge-green', closed: 'badge-gray' }[s] ?? 'badge-gray'
}
</script>
