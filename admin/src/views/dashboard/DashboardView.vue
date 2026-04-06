<template>
  <div class="space-y-6">
    <!-- Stat cards -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <RouterLink
        v-for="stat in stats"
        :key="stat.label"
        :to="stat.href"
        class="card p-5 block hover:shadow-md transition-shadow"
      >
        <div v-if="loading" class="space-y-2 animate-pulse">
          <div class="h-3 bg-gray-100 rounded w-2/3"></div>
          <div class="h-7 bg-gray-100 rounded w-1/2"></div>
        </div>
        <template v-else>
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ stat.label }}</span>
            <div class="w-8 h-8 rounded-lg flex items-center justify-center" :class="stat.bg">
              <component :is="stat.icon" :size="15" :class="stat.iconColor" />
            </div>
          </div>
          <div class="text-3xl font-bold tracking-tight text-gray-900">{{ stat.value }}</div>
          <div class="text-xs text-gray-400 mt-1">{{ stat.sub }}</div>
        </template>
      </RouterLink>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-5 gap-4">
      <!-- Recent maintenance -->
      <div class="card lg:col-span-3">
        <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-gray-800">Recent Maintenance</h2>
          <RouterLink to="/maintenance/issues" class="text-xs text-navy hover:underline">View all →</RouterLink>
        </div>
        <div v-if="loading" class="p-5 space-y-3 animate-pulse">
          <div v-for="i in 4" :key="i" class="h-4 bg-gray-100 rounded"></div>
        </div>
        <table v-else-if="recentMaintenance.length" class="table-wrap">
          <thead>
            <tr>
              <th scope="col">Title</th>
              <th scope="col">Unit</th>
              <th scope="col">Priority</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="req in recentMaintenance"
              :key="req.id"
              class="cursor-pointer hover:bg-gray-50"
              @click="router.push('/maintenance/issues')"
            >
              <td class="font-medium text-gray-800">{{ req.title }}</td>
              <td class="text-gray-500">{{ req.unit }}</td>
              <td><span :class="priorityBadge(req.priority)">{{ req.priority }}</span></td>
              <td><span :class="statusBadge(req.status)">{{ req.status.replace('_', ' ') }}</span></td>
            </tr>
          </tbody>
        </table>
        <EmptyState
          v-else
          title="No open requests"
          description="All maintenance requests are resolved."
          :icon="Wrench"
        />
      </div>

      <!-- Right column -->
      <div class="lg:col-span-2 space-y-4">
        <!-- Occupancy -->
        <div class="card p-5">
          <h2 class="text-sm font-semibold text-gray-800 mb-4">Unit Occupancy</h2>
          <div v-if="loading" class="space-y-4 animate-pulse">
            <div v-for="i in 3" :key="i" class="space-y-1.5">
              <div class="h-3 bg-gray-100 rounded w-1/2"></div>
              <div class="h-3 bg-gray-100 rounded"></div>
            </div>
          </div>
          <div v-else class="space-y-4">
            <div v-for="item in occupancy" :key="item.label">
              <div class="flex justify-between text-sm mb-2">
                <span class="text-gray-600">{{ item.label }}</span>
                <span class="font-semibold text-gray-900">{{ item.count }} <span class="text-gray-400 font-normal text-xs">({{ item.percent }}%)</span></span>
              </div>
              <div
                class="h-3 rounded-full bg-gray-100 overflow-hidden"
                role="progressbar"
                :aria-valuenow="item.percent"
                aria-valuemin="0"
                aria-valuemax="100"
                :aria-label="`${item.label}: ${item.percent}%`"
              >
                <div
                  class="h-full rounded-full transition-all duration-500"
                  :class="item.barColor"
                  :style="`width: ${item.percent}%`"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Expiring leases -->
        <div class="card p-5">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-sm font-semibold text-gray-800">Expiring Soon</h2>
            <RouterLink to="/leases" class="text-xs text-navy hover:underline">All leases →</RouterLink>
          </div>
          <div v-if="loading" class="space-y-3 animate-pulse">
            <div v-for="i in 2" :key="i" class="h-10 bg-gray-100 rounded"></div>
          </div>
          <div v-else-if="expiringLeases.length" class="space-y-2">
            <div
              v-for="lease in expiringLeases"
              :key="lease.id"
              class="flex items-center justify-between p-2.5 rounded-lg bg-gray-50 hover:bg-surface-secondary cursor-pointer transition-colors"
              @click="router.push('/leases')"
            >
              <div>
                <div class="text-sm font-medium text-gray-800">{{ lease.tenant_name }}</div>
                <div class="text-xs text-gray-400">{{ lease.unit_label }}</div>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <span :class="leaseUrgencyBadge(lease.days_remaining)">{{ lease.days_remaining }}d</span>
                <span class="text-xs text-gray-500">{{ lease.payment_reference || 'Ad Lease' }}</span>
                <span class="text-xs font-medium text-gray-700">{{ fmtDate(lease.end_date) }}</span>
              </div>
            </div>
          </div>
          <p v-else class="text-sm text-gray-400">No leases expiring in the next 60 days.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'
import { useToast } from '../../composables/useToast'
import EmptyState from '../../components/EmptyState.vue'
import { Building2, Users, Wrench, FileText } from 'lucide-vue-next'

const router = useRouter()
const toast = useToast()

const loading = ref(true)
const statsData = ref<Record<string, number>>({})
const recentMaintenance = ref<any[]>([])
const expiringLeases = ref<any[]>([])

onMounted(async () => {
  try {
    const [s, m, l] = await Promise.all([
      api.get('/stats/'),
      api.get('/maintenance/?status=open&page_size=5'),
      api.get('/leases/?status=active&page_size=5&ordering=end_date'),
    ])
    statsData.value = s.data
    recentMaintenance.value = (m.data.results ?? m.data).slice(0, 5)

    // Filter leases expiring in next 60 days
    const today = new Date()
    const in60 = new Date(today.getTime() + 60 * 86400000)
    const rawLeases = (l.data.results ?? l.data)
    expiringLeases.value = rawLeases
      .map((lease: any) => {
        const end = new Date(lease.end_date)
        const days = Math.ceil((end.getTime() - today.getTime()) / 86400000)
        return { ...lease, days_remaining: days, tenant_name: lease.tenant_name ?? lease.tenant ?? '—', unit_label: lease.unit_label ?? lease.unit ?? '' }
      })
      .filter((l: any) => l.days_remaining >= 0 && l.days_remaining <= 60)
      .sort((a: any, b: any) => a.days_remaining - b.days_remaining)
      .slice(0, 4)
  } catch {
    toast.error('Failed to load dashboard data')
  } finally {
    loading.value = false
  }
})

const stats = computed(() => [
  {
    label: 'Properties',
    value: statsData.value.total_properties ?? 0,
    sub: 'in portfolio',
    icon: Building2,
    bg: 'bg-info-50',
    iconColor: 'text-info-600',
    href: '/properties',
  },
  {
    label: 'Active Tenants',
    value: statsData.value.active_tenants ?? 0,
    sub: 'currently leasing',
    icon: Users,
    bg: 'bg-success-50',
    iconColor: 'text-success-600',
    href: '/tenants',
  },
  {
    label: 'Open Requests',
    value: statsData.value.open_maintenance ?? 0,
    sub: 'need attention',
    icon: Wrench,
    bg: 'bg-warning-50',
    iconColor: 'text-warning-500',
    href: '/maintenance/issues',
  },
  {
    label: 'Active Leases',
    value: statsData.value.active_leases ?? 0,
    sub: 'signed agreements',
    icon: FileText,
    bg: 'bg-navy/10',
    iconColor: 'text-navy',
    href: '/leases',
  },
])

const occupancy = computed(() => {
  const total = statsData.value.total_units || 1
  const occupied = statsData.value.occupied_units ?? 0
  const available = statsData.value.available_units ?? 0
  const maintenance = Math.max(0, total - occupied - available)
  return [
    { label: 'Occupied', count: occupied, percent: Math.round((occupied / total) * 100), barColor: 'bg-navy' },
    { label: 'Available', count: available, percent: Math.round((available / total) * 100), barColor: 'bg-success-500' },
    { label: 'Maintenance', count: maintenance, percent: Math.round((maintenance / total) * 100), barColor: 'bg-warning-400' },
  ]
})

function priorityBadge(p: string) {
  return { urgent: 'badge-red', high: 'badge-amber', medium: 'badge-blue', low: 'badge-green' }[p] ?? 'badge-gray'
}
function statusBadge(s: string) {
  return { open: 'badge-red', in_progress: 'badge-amber', resolved: 'badge-green', closed: 'badge-gray' }[s] ?? 'badge-gray'
}
function fmtDate(iso: string) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' })
}

function leaseUrgencyBadge(days: number) {
  if (days <= 14) return 'badge-red'
  if (days <= 30) return 'badge-amber'
  return 'badge-blue'
}
</script>
