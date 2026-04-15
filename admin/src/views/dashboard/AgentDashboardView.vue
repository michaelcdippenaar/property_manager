<template>
  <div class="space-y-6">

    <!-- ── Quick Actions ── -->
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      <RouterLink
        v-for="(action, idx) in quickActions"
        :key="action.label"
        :to="action.to"
        class="quick-action card group p-4 flex flex-col items-center gap-2.5 text-center hover:shadow-md hover:-translate-y-0.5 transition-all"
        :style="{ animationDelay: `${idx * 60}ms` }"
      >
        <div class="w-10 h-10 rounded-xl flex items-center justify-center transition-transform group-hover:scale-110" :class="action.bg">
          <component :is="action.icon" :size="18" :class="action.iconColor" />
        </div>
        <span class="text-xs font-semibold text-gray-700 leading-tight">{{ action.label }}</span>
      </RouterLink>
    </div>

    <!-- ── Stat cards ── -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <RouterLink
        v-for="stat in stats"
        :key="stat.label"
        :to="stat.href"
        class="card group p-5 block hover:shadow-md hover:-translate-y-0.5 transition-all"
      >
        <div v-if="loading" class="space-y-2 animate-pulse">
          <div class="h-3 bg-gray-100 rounded w-2/3"></div>
          <div class="h-8 bg-gray-100 rounded w-1/2"></div>
        </div>
        <template v-else>
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs font-semibold text-gray-400 uppercase tracking-wider">{{ stat.label }}</span>
            <div class="w-9 h-9 rounded-xl flex items-center justify-center transition-transform group-hover:scale-110" :class="stat.bg">
              <component :is="stat.icon" :size="16" :class="stat.iconColor" />
            </div>
          </div>
          <div class="text-3xl font-bold tracking-tight tabular-nums" :class="stat.value > 0 ? 'text-gray-900' : 'text-gray-300'">{{ stat.value }}</div>
          <div class="text-xs text-gray-400 mt-1.5">{{ stat.sub }}</div>
        </template>
      </RouterLink>
    </div>

    <!-- ── Maintenance + Occupancy ── -->
    <div class="grid grid-cols-1 lg:grid-cols-5 gap-4">

      <!-- Lease timeline -->
      <PropertyTimelineWidget
        :properties="propertiesStore.list"
        :loading="loading || propertiesStore.loading"
      />

      <!-- Occupancy -->
      <div class="card p-5 lg:col-span-2">
        <h2 class="text-sm font-bold text-gray-900 mb-5">Unit occupancy</h2>
        <div v-if="loading" class="flex items-center justify-center py-8 animate-pulse">
          <div class="w-36 h-36 rounded-full bg-gray-100"></div>
        </div>
        <div v-else class="flex items-center gap-6">
          <!-- Donut chart -->
          <div class="relative flex-shrink-0">
            <svg width="140" height="140" viewBox="0 0 140 140" class="transform -rotate-90">
              <circle cx="70" cy="70" r="54" fill="none" stroke="#f1f5f9" stroke-width="14" />
              <circle
                v-for="seg in donutSegments"
                :key="seg.label"
                cx="70" cy="70" r="54"
                fill="none"
                :stroke="seg.color"
                stroke-width="14"
                :stroke-dasharray="`${seg.arc} ${339.29 - seg.arc}`"
                :stroke-dashoffset="`${-seg.offset}`"
                stroke-linecap="round"
                class="transition-all duration-700"
              />
            </svg>
            <div class="absolute inset-0 flex flex-col items-center justify-center">
              <span class="text-2xl font-bold text-gray-900 tabular-nums">{{ statsData.total_units || 0 }}</span>
              <span class="text-xs text-gray-400">units</span>
            </div>
          </div>

          <!-- Legend -->
          <div class="flex-1 space-y-3">
            <div v-for="item in occupancy" :key="item.label" class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <div class="w-2.5 h-2.5 rounded-full" :class="item.barColor"></div>
                <span class="text-sm text-gray-600">{{ item.label }}</span>
              </div>
              <div class="text-right">
                <span class="text-sm font-bold text-gray-900 tabular-nums">{{ item.count }}</span>
                <span class="text-xs text-gray-400 ml-1">{{ item.percent }}%</span>
              </div>
            </div>
          </div>
        </div>

        <RouterLink
          to="/properties"
          class="mt-5 flex items-center gap-1.5 text-xs text-navy hover:underline"
        >
          <Building2 :size="12" /> View all properties →
        </RouterLink>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import { useToast } from '../../composables/useToast'
import { usePropertiesStore } from '../../stores/properties'
import PropertyTimelineWidget from './PropertyTimelineWidget.vue'
import {
  Building2, Users, Wrench, FileText,
  UserCheck, FileSignature, Truck,
} from 'lucide-vue-next'

const toast = useToast()
const propertiesStore = usePropertiesStore()

const loading = ref(true)
const statsData = ref<Record<string, number>>({})

const quickActions = [
  { label: 'Add Property', icon: Building2, to: '/properties', bg: 'bg-navy/10', iconColor: 'text-navy' },
  { label: 'Add Owner', icon: UserCheck, to: '/landlords', bg: 'bg-purple-50', iconColor: 'text-purple-600' },
  { label: 'New Lease', icon: FileText, to: '/leases/build', bg: 'bg-success-50', iconColor: 'text-success-600' },
  { label: 'Templates', icon: FileSignature, to: '/leases/templates', bg: 'bg-info-50', iconColor: 'text-info-600' },
  { label: 'Maintenance', icon: Wrench, to: '/maintenance/issues', bg: 'bg-warning-50', iconColor: 'text-warning-500' },
  { label: 'Suppliers', icon: Truck, to: '/maintenance/suppliers', bg: 'bg-orange-50', iconColor: 'text-orange-500' },
]

async function loadData() {
  loading.value = true
  try {
    const [s] = await Promise.allSettled([
      api.get('/stats/'),
    ])
    propertiesStore.fetchAll()
    if (s.status === 'fulfilled') statsData.value = s.value.data
  } catch {
    toast.error('Failed to load dashboard data')
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

const stats = computed(() => [
  {
    label: 'Properties', value: statsData.value.total_properties ?? 0, sub: 'managed',
    icon: Building2, bg: 'bg-navy/10', iconColor: 'text-navy', href: '/properties',
  },
  {
    label: 'Active tenants', value: statsData.value.active_tenants ?? 0, sub: 'currently leasing',
    icon: Users, bg: 'bg-success-50', iconColor: 'text-success-600', href: '/tenants',
  },
  {
    label: 'Active leases', value: statsData.value.active_leases ?? 0, sub: 'in effect',
    icon: FileText, bg: 'bg-info-50', iconColor: 'text-info-600', href: '/leases',
  },
  {
    label: 'Open requests', value: statsData.value.open_maintenance ?? 0, sub: 'need attention',
    icon: Wrench, bg: 'bg-warning-50', iconColor: 'text-warning-500', href: '/maintenance/issues',
  },
])

// SVG stroke colors — must stay in sync with tailwind tokens (navy, success-500, warning-400)
// referenced by the paired `barColor` class. Hex required because <circle :stroke> cannot
// consume a Tailwind class. Keep in sync with tailwind.config.js if tokens change.
const TOKEN_NAVY = '#2B2D6E'       // navy
const TOKEN_SUCCESS_500 = '#14b8a6' // success-500
const TOKEN_WARNING_400 = '#fbbf24' // warning-400

const occupancy = computed(() => {
  const total = statsData.value.total_units || 1
  const occupied = statsData.value.occupied_units ?? 0
  const available = statsData.value.available_units ?? 0
  const maintenance = Math.max(0, total - occupied - available)
  return [
    { label: 'Occupied',    count: occupied,    percent: Math.round((occupied / total) * 100),    barColor: 'bg-navy',        hex: TOKEN_NAVY },
    { label: 'Available',   count: available,   percent: Math.round((available / total) * 100),   barColor: 'bg-success-500', hex: TOKEN_SUCCESS_500 },
    { label: 'Maintenance', count: maintenance, percent: Math.round((maintenance / total) * 100), barColor: 'bg-warning-400', hex: TOKEN_WARNING_400 },
  ]
})

const donutSegments = computed(() => {
  const circumference = 2 * Math.PI * 54
  const gap = 4
  let offset = 0
  return occupancy.value
    .filter(item => item.percent > 0)
    .map(item => {
      const arc = Math.max(0, (item.percent / 100) * circumference - gap)
      const seg = { label: item.label, color: item.hex, arc, offset }
      offset += (item.percent / 100) * circumference
      return seg
    })
})
</script>

<style scoped>
.quick-action {
  animation: quickFadeUp 0.35s cubic-bezier(0.2, 0, 0, 1) both;
}
@keyframes quickFadeUp {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
</style>
