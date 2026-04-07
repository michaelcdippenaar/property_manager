<template>
  <div class="space-y-6 max-w-[1400px] mx-auto">

    <!-- ── Zone A: Action Required ── -->
    <div class="card overflow-hidden">
      <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <h2 class="text-sm font-bold text-gray-900">Needs attention</h2>
          <span
            v-if="!loading && actionItems.length"
            class="min-w-[20px] h-5 px-1.5 rounded-full bg-danger-500 text-white text-xs font-bold flex items-center justify-center leading-none"
          >{{ actionItems.length }}</span>
        </div>
        <button
          aria-label="Refresh action items"
          class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          @click="loadData"
        >
          <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" />
        </button>
      </div>

      <!-- Skeleton -->
      <div v-if="loading" class="divide-y divide-gray-50">
        <div v-for="i in 3" :key="i" class="flex items-center gap-3 px-5 py-3.5 animate-pulse">
          <div class="w-9 h-9 bg-gray-100 rounded-lg flex-shrink-0"></div>
          <div class="flex-1 space-y-1.5">
            <div class="h-3.5 bg-gray-100 rounded w-2/5"></div>
            <div class="h-3 bg-gray-100 rounded w-1/4"></div>
          </div>
          <div class="w-20 h-7 bg-gray-100 rounded-lg flex-shrink-0"></div>
        </div>
      </div>

      <!-- All clear -->
      <div v-else-if="!actionItems.length" class="flex items-center gap-3 px-5 py-5">
        <div class="w-9 h-9 rounded-lg bg-success-50 flex items-center justify-center flex-shrink-0">
          <CheckCircle2 :size="16" class="text-success-600" />
        </div>
        <div>
          <div class="text-sm font-semibold text-gray-800">All clear</div>
          <div class="text-xs text-gray-400 mt-0.5">No urgent items need your attention right now</div>
        </div>
      </div>

      <!-- Action items -->
      <div v-else class="divide-y divide-gray-50">
        <RouterLink
          v-for="item in actionItems"
          :key="item.id"
          :to="item.to"
          class="flex items-center gap-3 px-5 py-3.5 hover:bg-gray-50/60 transition-colors group"
        >
          <div class="w-1 h-9 rounded-full flex-shrink-0" :class="item.accentBar"></div>
          <div class="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center" :class="item.iconBg">
            <component :is="item.icon" :size="15" :class="item.iconColor" />
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-sm font-medium text-gray-800 truncate">{{ item.title }}</div>
            <div class="text-xs text-gray-400 truncate mt-0.5">{{ item.subtitle }}</div>
          </div>
          <span class="btn btn-ghost btn-xs flex-shrink-0 group-hover:border-navy group-hover:text-navy">{{ item.cta }}</span>
        </RouterLink>
      </div>
    </div>

    <!-- ── Zone B: Workflow Pipeline ── -->
    <div class="card p-5 overflow-hidden">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-navy/10 flex items-center justify-center">
            <FileSignature :size="15" class="text-navy" />
          </div>
          <div>
            <h2 class="text-sm font-bold text-gray-900">Rental workflow</h2>
            <p class="text-xs text-gray-400 mt-0.5">{{ completedSteps }} of 5 steps complete</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-24 h-2 rounded-full bg-gray-100 overflow-hidden">
            <div class="h-full rounded-full bg-navy transition-all duration-700" :style="`width: ${overallProgress}%`" />
          </div>
          <span class="text-xs font-semibold tabular-nums" :class="overallProgress >= 100 ? 'text-success-600' : 'text-navy'">{{ overallProgress }}%</span>
        </div>
      </div>

      <div class="grid grid-cols-5 gap-3 relative">
        <!-- Connector line behind cards -->
        <div class="absolute top-1/2 left-0 right-0 -translate-y-1/2 h-px bg-gray-200 z-0 hidden sm:block" aria-hidden="true"></div>

        <RouterLink
          v-for="(step, idx) in pipelineSteps"
          :key="step.label"
          :to="step.to"
          class="pipeline-card relative z-10 p-4 flex flex-col items-center gap-2.5 text-center rounded-xl transition-all hover:-translate-y-0.5"
          :class="step.percent >= 100
            ? 'bg-success-50/60 ring-1 ring-success-200 hover:ring-success-300'
            : step.percent > 0
              ? 'bg-navy/[0.03] ring-1 ring-navy/10 hover:ring-navy/25'
              : 'bg-gray-50 ring-1 ring-gray-200 hover:ring-gray-300'"
          :style="{ animationDelay: `${idx * 80}ms` }"
        >
          <!-- Step number -->
          <div
            class="absolute -top-2.5 -left-1.5 w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center leading-none shadow-sm"
            :class="step.percent >= 100
              ? 'bg-success-500 text-white'
              : step.percent > 0
                ? 'bg-navy text-white'
                : 'bg-white border border-gray-200 text-gray-400'"
          >
            <CheckCircle2 v-if="step.percent >= 100" :size="12" />
            <span v-else>{{ idx + 1 }}</span>
          </div>

          <!-- Icon -->
          <div
            class="w-11 h-11 rounded-xl flex items-center justify-center transition-colors"
            :class="step.percent >= 100 ? 'bg-success-100' : step.percent > 0 ? 'bg-navy/10' : 'bg-gray-100'"
          >
            <component
              :is="step.icon"
              :size="20"
              :class="step.percent >= 100 ? 'text-success-600' : step.percent > 0 ? 'text-navy' : 'text-gray-400'"
            />
          </div>

          <!-- Label + percent -->
          <div>
            <span class="text-sm font-semibold text-gray-900 leading-tight block">{{ step.label }}</span>
            <span class="text-sm tabular-nums mt-1 block font-bold" :class="step.percent >= 100 ? 'text-success-600' : step.percent > 0 ? 'text-navy' : 'text-gray-300'">
              {{ step.percent >= 100 ? 'Done' : `${step.percent}%` }}
            </span>
          </div>

          <!-- Progress bar -->
          <div class="w-full h-1.5 rounded-full bg-gray-100 overflow-hidden" role="progressbar" :aria-valuenow="step.percent" aria-valuemin="0" aria-valuemax="100">
            <div
              class="h-full rounded-full transition-all duration-1000 ease-out"
              :class="[
                step.percent >= 100 ? 'bg-success-500' : step.percent > 0 ? 'bg-navy' : 'bg-gray-200',
                step.percent > 0 && step.percent < 100 ? 'pipeline-shimmer' : ''
              ]"
              :style="{ width: `${animReady ? step.percent : 0}%` }"
            />
          </div>
        </RouterLink>
      </div>
    </div>

    <!-- ── Zone C: Portfolio Pulse ── -->

    <!-- Stat cards -->
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

    <!-- Maintenance + Occupancy -->
    <div class="grid grid-cols-1 lg:grid-cols-5 gap-4">

      <!-- Recent maintenance -->
      <div class="card lg:col-span-3 overflow-hidden">
        <div class="px-5 py-3.5 border-b border-gray-100 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-gray-800">Recent maintenance</h2>
          <RouterLink to="/maintenance/issues" class="text-xs text-navy hover:underline">View all →</RouterLink>
        </div>
        <div v-if="loading" class="p-5 space-y-3 animate-pulse">
          <div v-for="i in 4" :key="i" class="flex gap-3">
            <div class="h-4 bg-gray-100 rounded flex-1"></div>
            <div class="h-4 bg-gray-100 rounded w-16"></div>
            <div class="h-4 bg-gray-100 rounded w-14"></div>
          </div>
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
              class="cursor-pointer"
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
              <!-- Background ring -->
              <circle cx="70" cy="70" r="54" fill="none" stroke="#f1f5f9" stroke-width="14" />
              <!-- Segments -->
              <circle
                v-for="(seg, i) in donutSegments"
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
            <!-- Center label -->
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
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'
import { useToast } from '../../composables/useToast'
import EmptyState from '../../components/EmptyState.vue'
import {
  Building2, Users, Wrench, FileText, UserCheck,
  FileSignature, CheckCircle2, RefreshCw, AlertTriangle,
  Clock, PenLine,
} from 'lucide-vue-next'

const router = useRouter()
const toast = useToast()

const loading = ref(true)
const animReady = ref(false)
const statsData = ref<Record<string, number>>({})
const recentMaintenance = ref<any[]>([])
const urgentMaintenance = ref<any[]>([])
const expiringLeases = ref<any[]>([])
const pendingSigning = ref<any[]>([])

// Pipeline counts
const landlordCount = ref(0)
const templateCount = ref(0)
const signingCompleted = ref(0)
const signingTotal = ref(0)

async function loadData() {
  loading.value = true
  animReady.value = false
  try {
    const [s, m, urgent, l, signing, landlords, templates, signingAll] = await Promise.allSettled([
      api.get('/stats/'),
      api.get('/maintenance/?status=open&page_size=5'),
      api.get('/maintenance/?status=open&priority=urgent&page_size=3'),
      api.get('/leases/?status=active&page_size=10&ordering=end_date'),
      api.get('/esigning/submissions/?status=pending&page_size=3'),
      api.get('/landlords/?page_size=1'),
      api.get('/leases/templates/?page_size=1'),
      api.get('/esigning/submissions/?page_size=1'),
    ])

    if (s.status === 'fulfilled') statsData.value = s.value.data
    if (m.status === 'fulfilled') recentMaintenance.value = (m.value.data.results ?? m.value.data).slice(0, 5)
    if (urgent.status === 'fulfilled') urgentMaintenance.value = (urgent.value.data.results ?? urgent.value.data).slice(0, 3)
    if (signing.status === 'fulfilled') pendingSigning.value = (signing.value.data.results ?? signing.value.data).slice(0, 3)

    // Pipeline counts
    if (landlords.status === 'fulfilled') landlordCount.value = landlords.value.data.count ?? (landlords.value.data.results ?? landlords.value.data).length ?? 0
    if (templates.status === 'fulfilled') templateCount.value = templates.value.data.count ?? (templates.value.data.results ?? templates.value.data).length ?? 0
    if (signingAll.status === 'fulfilled') {
      signingTotal.value = signingAll.value.data.count ?? 0
      const pendingCount = pendingSigning.value.length
      signingCompleted.value = Math.max(0, signingTotal.value - pendingCount)
    }

    if (l.status === 'fulfilled') {
      const today = new Date()
      const rawLeases = l.value.data.results ?? l.value.data
      expiringLeases.value = rawLeases
        .map((lease: any) => {
          const end = new Date(lease.end_date)
          const days = Math.ceil((end.getTime() - today.getTime()) / 86400000)
          return {
            ...lease,
            days_remaining: days,
            tenant_name: lease.tenant_name ?? lease.tenant ?? '—',
            unit_label: lease.unit_label ?? lease.unit ?? '',
          }
        })
        .filter((l: any) => l.days_remaining >= 0 && l.days_remaining <= 30)
        .sort((a: any, b: any) => a.days_remaining - b.days_remaining)
    }
  } catch {
    toast.error('Failed to load dashboard data')
  } finally {
    loading.value = false
    // Trigger progress bar animation after render
    nextTick(() => { requestAnimationFrame(() => { animReady.value = true }) })
  }
}

onMounted(loadData)

// ── Zone A: Action items ──────────────────────────────────────────────────────
const actionItems = computed(() => {
  const items: any[] = []

  urgentMaintenance.value.forEach((req, i) => {
    items.push({
      id: `urg-${req.id ?? i}`,
      icon: AlertTriangle, iconBg: 'bg-danger-50', iconColor: 'text-danger-600', accentBar: 'bg-danger-400',
      title: req.title,
      subtitle: `Urgent · ${req.unit || 'Unknown unit'}`,
      to: '/maintenance/issues', cta: 'View issue', sort: 0,
    })
  })

  expiringLeases.value.filter((l: any) => l.days_remaining <= 7).forEach((lease, i) => {
    items.push({
      id: `exp7-${lease.id ?? i}`,
      icon: Clock, iconBg: 'bg-danger-50', iconColor: 'text-danger-600', accentBar: 'bg-danger-300',
      title: `Lease expiring in ${lease.days_remaining} day${lease.days_remaining === 1 ? '' : 's'}`,
      subtitle: `${lease.tenant_name} · ${lease.unit_label}`,
      to: '/leases', cta: 'View lease', sort: 1,
    })
  })

  expiringLeases.value.filter((l: any) => l.days_remaining > 7).forEach((lease, i) => {
    items.push({
      id: `exp30-${lease.id ?? i}`,
      icon: Clock, iconBg: 'bg-warning-50', iconColor: 'text-warning-600', accentBar: 'bg-warning-300',
      title: `Lease expiring in ${lease.days_remaining} days`,
      subtitle: `${lease.tenant_name} · ${lease.unit_label}`,
      to: '/leases', cta: 'View lease', sort: 2,
    })
  })

  pendingSigning.value.forEach((doc, i) => {
    items.push({
      id: `sign-${doc.id ?? i}`,
      icon: PenLine, iconBg: 'bg-info-50', iconColor: 'text-info-600', accentBar: 'bg-info-300',
      title: 'Document awaiting signature',
      subtitle: doc.tenant_name ?? doc.lease_reference ?? 'Lease agreement',
      to: '/leases/overview', cta: 'Review', sort: 3,
    })
  })

  return items.sort((a, b) => a.sort - b.sort).slice(0, 6)
})

// ── Zone B: Pipeline steps ────────────────────────────────────────────────────
const pipelineSteps = computed(() => {
  const totalUnits = statsData.value.total_units || 0
  const activeLeases = statsData.value.active_leases ?? 0

  // Landlord: partial credit if properties exist (implies owner context), full if landlord entities created
  const hasProperties = (statsData.value.total_properties ?? 0) > 0
  let landlordPct = 0
  if (landlordCount.value > 0) landlordPct = 100
  else if (hasProperties) landlordPct = 30  // properties exist but no formal landlord entity yet

  return [
    {
      label: 'Owner',
      icon: UserCheck,
      to: '/landlords',
      percent: landlordPct,
    },
    {
      label: 'Property',
      icon: Building2,
      to: '/properties',
      percent: hasProperties
        ? (totalUnits > 0 ? 100 : 50)
        : 0,
    },
    {
      label: 'Template',
      icon: FileSignature,
      to: '/leases/templates',
      percent: templateCount.value > 0 ? 100 : 0,
    },
    {
      label: 'Lease',
      icon: FileText,
      to: '/leases/build',
      percent: totalUnits > 0
        ? Math.min(100, Math.round((activeLeases / totalUnits) * 100))
        : 0,
    },
    {
      label: 'Sign',
      icon: PenLine,
      to: '/leases/overview',
      percent: signingTotal.value > 0
        ? Math.min(100, Math.round((signingCompleted.value / signingTotal.value) * 100))
        : (activeLeases > 0 ? 0 : 0),
    },
  ]
})

// Pipeline summary
const completedSteps = computed(() => pipelineSteps.value.filter(s => s.percent >= 100).length)
const overallProgress = computed(() => Math.round(pipelineSteps.value.reduce((sum, s) => sum + Math.min(100, s.percent), 0) / 5))

// ── Zone C: Stats ─────────────────────────────────────────────────────────────
const stats = computed(() => [
  {
    label: 'Properties', value: statsData.value.total_properties ?? 0, sub: 'in portfolio',
    icon: Building2, bg: 'bg-info-50', iconColor: 'text-info-600', href: '/properties',
  },
  {
    label: 'Active tenants', value: statsData.value.active_tenants ?? 0, sub: 'currently leasing',
    icon: Users, bg: 'bg-success-50', iconColor: 'text-success-600', href: '/tenants',
  },
  {
    label: 'Open requests', value: statsData.value.open_maintenance ?? 0, sub: 'need attention',
    icon: Wrench, bg: 'bg-warning-50', iconColor: 'text-warning-500', href: '/maintenance/issues',
  },
  {
    label: 'Active leases', value: statsData.value.active_leases ?? 0, sub: 'signed agreements',
    icon: FileText, bg: 'bg-navy/10', iconColor: 'text-navy', href: '/leases',
  },
])

const occupancy = computed(() => {
  const total = statsData.value.total_units || 1
  const occupied = statsData.value.occupied_units ?? 0
  const available = statsData.value.available_units ?? 0
  const maintenance = Math.max(0, total - occupied - available)
  return [
    { label: 'Occupied',    count: occupied,    percent: Math.round((occupied / total) * 100),    barColor: 'bg-navy',        hex: '#2B2D6E' },
    { label: 'Available',   count: available,   percent: Math.round((available / total) * 100),   barColor: 'bg-success-500', hex: '#14b8a6' },
    { label: 'Maintenance', count: maintenance, percent: Math.round((maintenance / total) * 100), barColor: 'bg-warning-400', hex: '#fbbf24' },
  ]
})

// Donut chart segments
const donutSegments = computed(() => {
  const circumference = 2 * Math.PI * 54 // ~339.29
  const gap = 4 // gap between segments in px
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

function priorityBadge(p: string) {
  return { urgent: 'badge badge-red', high: 'badge badge-amber', medium: 'badge badge-blue', low: 'badge badge-green' }[p] ?? 'badge badge-gray'
}
function statusBadge(s: string) {
  return { open: 'badge badge-red', in_progress: 'badge badge-amber', resolved: 'badge badge-green', closed: 'badge badge-gray' }[s] ?? 'badge badge-gray'
}
</script>

<style scoped>
/* Staggered card entrance */
.pipeline-card {
  animation: pipelineFadeUp 0.4s cubic-bezier(0.2, 0, 0, 1) both;
}
@keyframes pipelineFadeUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Shimmer on in-progress bars */
.pipeline-shimmer {
  position: relative;
  overflow: hidden;
}
.pipeline-shimmer::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.35) 50%,
    transparent 100%
  );
  animation: shimmer 2s ease-in-out infinite;
}
@keyframes shimmer {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
</style>
