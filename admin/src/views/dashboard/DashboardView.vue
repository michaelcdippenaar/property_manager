<template>
  <div class="space-y-5">

    <!-- ── Page header ── -->
    <PageHeader
      v-if="!showWelcome"
      title="Dashboard"
      :subtitle="`Portfolio overview${portfolio.length ? ` · ${portfolio.length} ${portfolio.length === 1 ? 'property' : 'properties'}` : ''}`"
    />

    <!-- ── Welcome banner (new agency, 0 properties) ── -->
    <div
      v-if="showWelcome"
      class="card p-6 bg-gradient-to-br from-navy/5 to-transparent border-navy/10"
    >
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-lg font-bold text-gray-900">Welcome to Klikk, {{ agencyName }}</h2>
          <p class="text-sm text-gray-500 mt-1">Let's get your agency set up. Complete these steps to unlock the full dashboard.</p>
          <div class="flex flex-wrap gap-2.5 mt-4">
            <!-- Primary + ghost variants migrated from hand-rolled inline utilities to design-system btn classes.
                 Note: the secondary CTAs previously used a tonal navy variant (text-navy bg-navy/5).
                 `.btn-ghost` renders white/gray instead — accepted as the design-system canonical ghost style. -->
            <RouterLink to="/admin/agency" class="btn-primary btn-sm">
              <Settings :size="16" /> Complete agency profile
            </RouterLink>
            <RouterLink to="/admin/users" class="btn-ghost btn-sm">
              <UserPlus :size="16" /> Invite your team
            </RouterLink>
            <RouterLink to="/properties" class="btn-ghost btn-sm">
              <Building2 :size="16" /> Add first property
            </RouterLink>
          </div>
        </div>
        <button @click="dismissWelcome" aria-label="Dismiss welcome banner" class="text-gray-300 hover:text-gray-500 transition-colors flex-shrink-0 mt-1">
          <X :size="16" />
        </button>
      </div>
    </div>

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
      <div v-if="propertiesStore.portfolioLoading && !portfolio.length" class="card p-5 text-sm text-gray-500">Loading lifecycle…</div>
      <div v-else class="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <PropertyLifecycleCard
          v-for="entry in portfolio"
          :key="entry.property_id"
          :entry="entry"
          @prepare-next="openNextLeaseDrawer"
        />
      </div>
    </div>

    <!-- ── Onboarding in progress ── -->
    <div v-if="!loading && pendingOnboardings.length > 0" class="card p-5">
      <div class="flex items-center justify-between mb-4">
        <h2 class="section-header flex items-center gap-1.5">
          <ClipboardList :size="15" class="text-navy" /> Tenant onboarding in progress
        </h2>
        <RouterLink to="/tenants" class="text-xs text-navy hover:underline">View all tenants →</RouterLink>
      </div>
      <div class="space-y-3">
        <div
          v-for="ob in pendingOnboardings"
          :key="ob.id"
          class="flex items-center gap-3"
        >
          <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm font-medium text-gray-800 truncate">{{ ob.tenant_name }}</span>
              <span class="text-xs font-semibold text-gray-600 tabular-nums ml-2">{{ ob.progress }}%</span>
            </div>
            <div class="h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                class="h-full bg-navy rounded-full transition-all duration-500"
                :style="{ width: `${ob.progress}%` }"
              />
            </div>
            <p class="text-xs text-gray-400 mt-0.5 truncate">{{ ob.lease_number }}</p>
          </div>
          <RouterLink
            :to="{ name: 'tenant-detail', params: { id: ob.primary_tenant_id } }"
            class="btn-ghost btn-sm text-xs flex-shrink-0"
          >
            View
          </RouterLink>
        </div>
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

    <!-- Agency profile nudge -->
    <div
      v-if="agencyProfileIncomplete"
      class="card p-4 flex items-center gap-3 bg-warning-50/50 border-warning-200"
    >
      <div class="w-9 h-9 rounded-xl bg-warning-100 flex items-center justify-center flex-shrink-0">
        <ShieldAlert :size="16" class="text-warning-600" />
      </div>
      <div class="flex-1 min-w-0">
        <p class="text-sm font-semibold text-gray-900">Complete your agency profile</p>
        <p class="text-xs text-gray-500 mt-0.5">Add your FFC number, trust account, and contact details for compliant documents.</p>
      </div>
      <RouterLink to="/admin/agency" class="text-xs font-semibold text-warning-700 hover:text-warning-800 whitespace-nowrap">
        Complete profile &rarr;
      </RouterLink>
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
import api from '../../api'
import { useToast } from '../../composables/useToast'
import { useAuthStore } from '../../stores/auth'
import { usePropertiesStore } from '../../stores/properties'
import PropertyTimelineWidget from './PropertyTimelineWidget.vue'
import PropertyLifecycleCard from '../../components/PropertyLifecycleCard.vue'
import MaintenanceWidget from '../../components/MaintenanceWidget.vue'
import NextLeaseDrawer from '../../components/NextLeaseDrawer.vue'
import PageHeader from '../../components/PageHeader.vue'
import {
  Building2, Users, Wrench,
  PenLine, CheckCircle2,
  Settings, UserPlus, X, ShieldAlert, ClipboardList,
} from 'lucide-vue-next'

const toast = useToast()
const auth = useAuthStore()
const propertiesStore = usePropertiesStore()

const loading = ref(true)
const animReady = ref(false)
const welcomeDismissed = ref(sessionStorage.getItem('klikk_welcome_dismissed') === '1')

const agencyName = computed(() => auth.agency?.name || auth.user?.full_name || 'your agency')
const showWelcome = computed(() =>
  !loading.value
  && !welcomeDismissed.value
  && (statsData.value.total_properties ?? 0) === 0
)
function dismissWelcome() {
  welcomeDismissed.value = true
  sessionStorage.setItem('klikk_welcome_dismissed', '1')
}

const agencyProfileIncomplete = computed(() => {
  const a = auth.agency
  if (!a || a.account_type !== 'agency') return false
  return !a.eaab_ffc_number || !a.trust_account_number || !a.contact_number
})

const statsData = ref<Record<string, number>>({})
const pendingSigning = ref<any[]>([])
const pendingOnboardings = ref<any[]>([])
const landlordCount = ref(0)
const templateCount = ref(0)
const signingCompleted = ref(0)
const signingTotal = ref(0)

async function loadData() {
  loading.value = true
  animReady.value = false
  try {
    const [s, signing, landlords, templates, signingAll, onboarding] = await Promise.allSettled([
      api.get('/stats/'),
      api.get('/esigning/submissions/?status=pending&page_size=3'),
      api.get('/properties/landlords/?page_size=1'),
      api.get('/leases/templates/?page_size=1'),
      api.get('/esigning/submissions/?page_size=1'),
      api.get('/tenant/onboarding/?page_size=10'),
    ])

    propertiesStore.fetchAll()
    propertiesStore.fetchPortfolio({ force: true }).catch(() => { /* non-fatal */ })

    if (s.status === 'fulfilled') statsData.value = s.value.data
    if (signing.status === 'fulfilled') pendingSigning.value = (signing.value.data.results ?? signing.value.data).slice(0, 3)
    if (onboarding.status === 'fulfilled') {
      const all = onboarding.value.data.results ?? onboarding.value.data
      pendingOnboardings.value = all.filter((ob: any) => !ob.is_complete).slice(0, 5)
    }

    if (landlords.status === 'fulfilled') landlordCount.value = landlords.value.data.count ?? (landlords.value.data.results ?? landlords.value.data).length ?? 0
    if (templates.status === 'fulfilled') templateCount.value = templates.value.data.count ?? (templates.value.data.results ?? templates.value.data).length ?? 0
    if (signingAll.status === 'fulfilled') {
      signingTotal.value = signingAll.value.data.count ?? 0
      signingCompleted.value = Math.max(0, signingTotal.value - pendingSigning.value.length)
    }
  } catch {
    toast.error('Failed to load dashboard data')
  } finally {
    loading.value = false
    nextTick(() => { requestAnimationFrame(() => { animReady.value = true }) })
  }
}

onMounted(loadData)

// ── Property lifecycle ──────────────────────────────────────────────────────
const portfolio = computed(() => propertiesStore.portfolio)
const nextLeaseSourceId = ref<number | null>(null)

function openNextLeaseDrawer(leaseId: number) {
  nextLeaseSourceId.value = leaseId
}

async function onRenewalSaved(_newLeaseId: number) {
  nextLeaseSourceId.value = null
  toast.success('Next lease drafted as pending.')
  await propertiesStore.fetchPortfolio({ force: true })
}

// ── Hero Metrics ─────────────────────────────────────────────────────────────
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
    label: 'Open requests',
    value: statsData.value.open_maintenance ?? 0,
    sub: 'need attention',
    icon: Wrench, bg: 'bg-warning-50', iconColor: 'text-warning-500', href: '/maintenance/issues',
  },
])

// ── Occupancy ─────────────────────────────────────────────────────────────────
// SVG stroke colors — must stay in sync with tailwind tokens (navy, success-500, warning-500)
// referenced by the paired `barColor` class, plus the unfilled donut track color. Hex required
// because <circle :stroke> cannot consume a Tailwind class. Keep in sync with tailwind.config.js
// if tokens change.
const TOKEN_NAVY = '#2B2D6E'        // navy
const TOKEN_SUCCESS_500 = '#14b8a6' // success-500
const TOKEN_WARNING_500 = '#f59e0b' // warning-500
const TOKEN_TRACK = '#f1f5f9'       // gray-100-ish, donut unfilled track

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
