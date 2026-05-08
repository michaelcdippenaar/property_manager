<template>
  <div class="space-y-5">

    <!-- ── Page header ── -->
    <PageHeader
      title="Dashboard"
      :subtitle="`Portfolio overview${portfolio.length ? ` · ${portfolio.length} ${portfolio.length === 1 ? 'property' : 'properties'}` : ''}`"
    />

    <!-- ── Metrics strip ── -->
    <div class="card flex flex-col sm:flex-row divide-y sm:divide-y-0 sm:divide-x divide-gray-100 overflow-hidden">
      <RouterLink
        v-for="stat in stats"
        :key="stat.label"
        :to="stat.href"
        class="group flex-1 flex items-center gap-3 px-4 py-3 hover:bg-gray-50/70 transition-colors"
      >
        <div v-if="loading" class="flex-1 space-y-1.5 animate-pulse">
          <div class="h-2.5 bg-gray-100 rounded w-16"></div>
          <div class="h-5 bg-gray-100 rounded w-10"></div>
        </div>
        <template v-else>
          <div
            class="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-105"
            :class="stat.bg"
          >
            <component :is="stat.icon" :size="16" :class="stat.iconColor" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-baseline gap-1.5">
              <span
                class="text-xl font-bold tabular-nums leading-none"
                :class="stat.value > 0 ? 'text-gray-900' : 'text-gray-300'"
              >{{ stat.value }}</span>
              <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider truncate">{{ stat.label }}</span>
            </div>
            <div class="text-xs text-gray-400 mt-0.5 truncate">{{ stat.sub }}</div>
            <div
              v-if="stat.meter !== undefined"
              class="mt-1 h-[3px] w-full max-w-[80px] bg-gray-100 rounded-full overflow-hidden"
            >
              <div
                class="h-full rounded-full transition-all duration-500"
                :class="stat.meter >= 90 ? 'bg-success-600' : stat.meter >= 50 ? 'bg-navy' : 'bg-warning-500'"
                :style="{ width: stat.meter + '%' }"
              />
            </div>
          </div>
        </template>
      </RouterLink>
    </div>

    <!-- ── Property Lifecycle ── -->
    <div v-if="portfolio.length || propertiesStore.portfolioLoading" class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="section-header">Property lifecycle</h2>
        <span v-if="portfolio.length" class="text-xs text-gray-400">{{ portfolio.length }} propert{{ portfolio.length === 1 ? 'y' : 'ies' }}</span>
      </div>
      <div v-if="propertiesStore.portfolioLoading && !portfolio.length" class="card p-5 text-sm text-gray-500">Loading lifecycle...</div>
      <div v-else class="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <PropertyLifecycleCard
          v-for="entry in portfolio"
          :key="entry.property_id"
          :entry="entry"
          @prepare-next="openNextLeaseDrawer"
        />
      </div>
    </div>

    <!-- ── Needs Attention ── -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">

      <!-- Pending Signatures -->
      <div class="card p-5">
        <div class="flex items-center justify-between mb-4">
          <h2 class="section-header">Pending signatures</h2>
          <RouterLink v-if="pendingSigning.length" to="/leases/overview" class="text-xs text-navy hover:underline">
            View all →
          </RouterLink>
        </div>
        <div v-if="loading" class="space-y-3 animate-pulse">
          <div v-for="i in 3" :key="i" class="flex items-center gap-3 py-2">
            <div class="w-7 h-7 bg-gray-100 rounded-lg flex-shrink-0"></div>
            <div class="flex-1 space-y-1.5">
              <div class="h-3 bg-gray-100 rounded w-3/4"></div>
              <div class="h-2.5 bg-gray-100 rounded w-1/2"></div>
            </div>
          </div>
        </div>
        <template v-else>
          <div v-if="pendingSigning.length" class="divide-y divide-gray-100">
            <div
              v-for="sub in pendingSigning"
              :key="sub.id"
              class="flex items-center gap-3 py-2.5 first:pt-0 last:pb-0"
            >
              <div class="w-7 h-7 rounded-lg bg-warning-50 flex items-center justify-center flex-shrink-0">
                <PenLine :size="13" class="text-warning-600" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-900 truncate">
                  {{ sub.lease?.unit_label ?? sub.document_title ?? 'Lease document' }}
                </p>
                <p class="text-xs text-gray-400">{{ sub.signers?.length ?? 0 }} signer{{ (sub.signers?.length ?? 0) !== 1 ? 's' : '' }} awaiting</p>
              </div>
              <span class="badge-amber flex-shrink-0">Awaiting sign</span>
            </div>
          </div>
          <div v-else class="flex flex-col items-center justify-center py-6 text-center">
            <div class="w-10 h-10 rounded-xl bg-success-50 flex items-center justify-center mb-2">
              <CheckCircle2 :size="18" class="text-success-600" />
            </div>
            <p class="text-sm font-medium text-gray-700">All clear</p>
            <p class="text-xs text-gray-400 mt-0.5">No pending signatures</p>
          </div>
        </template>
      </div>

      <!-- Maintenance -->
      <MaintenanceWidget :portfolio="portfolio" :loading="loading || propertiesStore.portfolioLoading" />
    </div>

    <!-- ── Bottom: Timeline + Occupancy ── -->
    <div class="grid grid-cols-1 lg:grid-cols-5 gap-4">

      <!-- Lease timeline -->
      <PropertyTimelineWidget
        :properties="propertiesStore.list"
        :loading="loading || propertiesStore.loading"
      />

      <!-- Occupancy donut -->
      <div class="card p-5 lg:col-span-2">
        <h2 class="section-header mb-5">Unit occupancy</h2>
        <div v-if="loading" class="flex items-center justify-center py-8 animate-pulse">
          <div class="w-36 h-36 rounded-full bg-gray-100"></div>
        </div>
        <div v-else-if="(statsData.total_units ?? 0) === 0" class="flex flex-col items-center justify-center py-8 text-center">
          <svg width="120" height="120" viewBox="0 0 140 140">
            <circle cx="70" cy="70" r="54" fill="none" :stroke="TOKEN_TRACK" stroke-width="14" />
          </svg>
          <p class="text-xs text-gray-400 mt-2">No units added yet</p>
          <RouterLink to="/properties" class="mt-2 text-xs text-navy hover:underline">Add a property →</RouterLink>
        </div>
        <div v-else class="flex items-center gap-6">
          <!-- Donut chart -->
          <div class="relative flex-shrink-0">
            <svg width="140" height="140" viewBox="0 0 140 140" class="transform -rotate-90">
              <circle cx="70" cy="70" r="54" fill="none" :stroke="TOKEN_TRACK" stroke-width="14" />
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

    <!-- Next lease drawer -->
    <NextLeaseDrawer
      v-if="nextLeaseSourceId !== null"
      :source-lease-id="nextLeaseSourceId"
      @close="nextLeaseSourceId = null"
      @saved="onRenewalSaved"
    />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'
import { useToast } from '../../composables/useToast'
import { usePropertiesStore } from '../../stores/properties'
import PropertyTimelineWidget from './PropertyTimelineWidget.vue'
import PropertyLifecycleCard from '../../components/PropertyLifecycleCard.vue'
import MaintenanceWidget from '../../components/MaintenanceWidget.vue'
import NextLeaseDrawer from '../../components/NextLeaseDrawer.vue'
import PageHeader from '../../components/PageHeader.vue'
import {
  Building2, Users, Wrench, FileText,
  PenLine, CheckCircle2,
} from 'lucide-vue-next'

const toast = useToast()
const propertiesStore = usePropertiesStore()
const router = useRouter()

const loading = ref(true)
const statsData = ref<Record<string, number>>({})
const pendingSigning = ref<any[]>([])

async function loadData() {
  loading.value = true
  try {
    const [s, signing] = await Promise.allSettled([
      api.get('/stats/'),
      api.get('/esigning/submissions/?status=pending&page_size=3'),
    ])

    propertiesStore.fetchAll()
    propertiesStore.fetchPortfolio({ force: true }).catch(() => { /* non-fatal */ })

    if (s.status === 'fulfilled') statsData.value = s.value.data
    if (signing.status === 'fulfilled') pendingSigning.value = (signing.value.data.results ?? signing.value.data).slice(0, 3)
  } catch {
    toast.error('Failed to load dashboard data')
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

// ── Property lifecycle ──────────────────────────────────────────────────────
const portfolio = computed(() => propertiesStore.portfolio)
const nextLeaseSourceId = ref<number | null>(null)

function openNextLeaseDrawer(leaseId: number) {
  nextLeaseSourceId.value = leaseId
}

async function onRenewalSaved(newLeaseId: number) {
  nextLeaseSourceId.value = null
  toast.success('Next lease drafted as pending.')
  await propertiesStore.fetchPortfolio({ force: true })
  // Land the agent on the new lease's edit drawer so they can immediately
  // capture the new tenant signatories — closing the QA gap where the
  // toast hid the next step ("where do I click on tenant?").
  if (newLeaseId) {
    router.push({ path: '/leases', query: { edit: String(newLeaseId) } })
  }
}

// ── Metrics ─────────────────────────────────────────────────────────────────
const occupancyPct = computed(() => {
  const total = statsData.value.total_units ?? 0
  const occ = statsData.value.occupied_units ?? 0
  return total > 0 ? Math.round((occ / total) * 100) : 0
})

const stats = computed<Array<{
  label: string; value: number; sub: string;
  icon: any; bg: string; iconColor: string; href: string;
  meter?: number;
}>>(() => [
  {
    label: 'Properties',
    value: statsData.value.total_properties ?? 0,
    sub: `${occupancyPct.value}% occupancy · ${statsData.value.occupied_units ?? 0}/${statsData.value.total_units ?? 0} units`,
    meter: occupancyPct.value,
    icon: Building2, bg: 'bg-navy/10', iconColor: 'text-navy', href: '/properties',
  },
  {
    label: 'Active tenants',
    value: statsData.value.active_tenants ?? 0,
    sub: 'currently leasing',
    icon: Users, bg: 'bg-success-50', iconColor: 'text-success-600', href: '/tenants',
  },
  {
    label: 'Active leases',
    value: statsData.value.active_leases ?? 0,
    sub: 'in effect',
    icon: FileText, bg: 'bg-info-50', iconColor: 'text-info-600', href: '/leases',
  },
  {
    label: 'Open requests',
    value: statsData.value.open_maintenance ?? 0,
    sub: 'need attention',
    icon: Wrench, bg: 'bg-warning-50', iconColor: 'text-warning-500', href: '/maintenance/issues',
  },
])

// ── Occupancy ─────────────────────────────────────────────────────────────────
const TOKEN_NAVY = '#2B2D6E'
const TOKEN_SUCCESS_500 = '#14b8a6'
const TOKEN_WARNING_500 = '#f59e0b'
const TOKEN_TRACK = '#f1f5f9'

const occupancy = computed(() => {
  const total = statsData.value.total_units || 1
  const occupied = statsData.value.occupied_units ?? 0
  const available = statsData.value.available_units ?? 0
  const maintenance = Math.max(0, total - occupied - available)
  return [
    { label: 'Occupied',    count: occupied,    percent: Math.round((occupied / total) * 100),    barColor: 'bg-navy',        hex: TOKEN_NAVY },
    { label: 'Available',   count: available,   percent: Math.round((available / total) * 100),   barColor: 'bg-success-500', hex: TOKEN_SUCCESS_500 },
    { label: 'Maintenance', count: maintenance, percent: Math.round((maintenance / total) * 100), barColor: 'bg-warning-500', hex: TOKEN_WARNING_500 },
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
