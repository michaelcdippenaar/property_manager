<template>
  <div class="space-y-6 max-w-[1400px] mx-auto">

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

      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 relative">
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
    <div class="grid grid-cols-2 gap-4">
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
import { usePropertiesStore } from '../../stores/properties'
import PropertyTimelineWidget from './PropertyTimelineWidget.vue'
import {
  Building2, Users, Wrench, FileText,
  UserCheck, FileSignature, CheckCircle2, PenLine,
} from 'lucide-vue-next'

const router = useRouter()
const toast = useToast()
const propertiesStore = usePropertiesStore()

const loading = ref(true)
const animReady = ref(false)
const statsData = ref<Record<string, number>>({})
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
    const [s, signing, landlords, templates, signingAll] = await Promise.allSettled([
      api.get('/stats/'),
      api.get('/esigning/submissions/?status=pending&page_size=3'),
      api.get('/landlords/?page_size=1'),
      api.get('/leases/templates/?page_size=1'),
      api.get('/esigning/submissions/?page_size=1'),
    ])

    // Properties store fetch runs in parallel (has its own loading state)
    propertiesStore.fetchAll()

    if (s.status === 'fulfilled') statsData.value = s.value.data
    if (signing.status === 'fulfilled') pendingSigning.value = (signing.value.data.results ?? signing.value.data).slice(0, 3)

    // Pipeline counts
    if (landlords.status === 'fulfilled') landlordCount.value = landlords.value.data.count ?? (landlords.value.data.results ?? landlords.value.data).length ?? 0
    if (templates.status === 'fulfilled') templateCount.value = templates.value.data.count ?? (templates.value.data.results ?? templates.value.data).length ?? 0
    if (signingAll.status === 'fulfilled') {
      signingTotal.value = signingAll.value.data.count ?? 0
      const pendingCount = pendingSigning.value.length
      signingCompleted.value = Math.max(0, signingTotal.value - pendingCount)
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
      to: '/leases',
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
    label: 'Active tenants', value: statsData.value.active_tenants ?? 0, sub: 'currently leasing',
    icon: Users, bg: 'bg-success-50', iconColor: 'text-success-600', href: '/tenants',
  },
  {
    label: 'Open requests', value: statsData.value.open_maintenance ?? 0, sub: 'need attention',
    icon: Wrench, bg: 'bg-warning-50', iconColor: 'text-warning-500', href: '/maintenance/issues',
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
