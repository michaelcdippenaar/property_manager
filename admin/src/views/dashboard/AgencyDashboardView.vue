<template>
  <div class="space-y-5">

    <!-- ── Page header ── -->
    <PageHeader
      v-if="!showWelcome"
      title="Agency Dashboard"
      subtitle="Agency overview and setup pipeline"
    />

    <!-- ── Welcome banner (new agency, 0 properties) ── -->
    <div
      v-if="showWelcome"
      class="card p-6 bg-gradient-to-br from-navy/[0.04] to-transparent border-navy/10"
    >
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-lg font-bold text-gray-900">Welcome to Klikk, {{ agencyName }}</h2>
          <p class="text-sm text-gray-500 mt-1">Let's get your agency set up. Complete these steps to unlock the full dashboard.</p>
          <div class="flex flex-wrap gap-2.5 mt-4">
            <RouterLink to="/admin/agency" class="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold bg-navy text-white rounded-lg hover:bg-navy/90 transition-colors">
              <Settings :size="14" /> Complete agency profile
            </RouterLink>
            <RouterLink to="/admin/users" class="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-navy bg-navy/5 rounded-lg hover:bg-navy/10 transition-colors">
              <UserPlus :size="14" /> Invite your team
            </RouterLink>
            <RouterLink to="/properties" class="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-navy bg-navy/5 rounded-lg hover:bg-navy/10 transition-colors">
              <Building2 :size="14" /> Add first property
            </RouterLink>
          </div>
        </div>
        <button @click="dismissWelcome" class="text-gray-300 hover:text-gray-500 transition-colors flex-shrink-0 mt-1">
          <X :size="16" />
        </button>
      </div>
    </div>

    <!-- ── Quick Actions (setup steps) ── -->
    <div class="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-5 gap-3">
      <RouterLink
        v-for="(step, idx) in pipelineSteps"
        :key="step.label"
        :to="step.to"
        class="quick-action card group p-4 flex flex-col items-center gap-2.5 text-center hover:shadow-md hover:-translate-y-0.5 transition-all relative"
        :style="{ animationDelay: `${idx * 60}ms` }"
      >
        <!-- Completion badge -->
        <div
          v-if="step.percent >= 100"
          class="absolute top-2 right-2 w-4 h-4 rounded-full bg-success-500 flex items-center justify-center"
        >
          <CheckCircle2 :size="10" class="text-white" />
        </div>
        <div
          class="w-10 h-10 rounded-xl flex items-center justify-center transition-transform group-hover:scale-110"
          :class="step.percent >= 100 ? 'bg-success-50' : step.percent > 0 ? 'bg-navy/10' : 'bg-gray-100'"
        >
          <component
            :is="step.icon"
            :size="18"
            :class="step.percent >= 100 ? 'text-success-600' : step.percent > 0 ? 'text-navy' : 'text-gray-400'"
          />
        </div>
        <span class="text-xs font-semibold leading-tight" :class="step.percent >= 100 ? 'text-success-700' : 'text-gray-700'">{{ step.label }}</span>
      </RouterLink>
    </div>

    <!-- ── Hero Metrics Bar ── -->
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
          <div class="h-3 bg-gray-100 rounded w-1/2"></div>
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

    <!-- ── Setup Progress ── -->
    <div v-if="overallProgress < 100 && !loading" class="card px-5 py-3">
      <div class="flex items-center gap-3">
        <span class="label-upper shrink-0">Agency setup</span>
        <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
          <div
            class="h-full bg-navy rounded-full transition-all duration-700"
            :style="{ width: animReady ? overallProgress + '%' : '0%' }"
          />
        </div>
        <span class="text-micro text-gray-400 shrink-0">{{ completedSteps }}/5 steps · {{ overallProgress }}%</span>
      </div>
    </div>

    <!-- ── Needs Attention ── -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">

      <!-- Pending Signatures -->
      <div class="card p-5">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-sm font-bold text-gray-900">Pending signatures</h2>
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
              <span class="badge badge-amber flex-shrink-0">Awaiting sign</span>
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

      <!-- Open Maintenance -->
      <div class="card p-5">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-sm font-bold text-gray-900">Open maintenance</h2>
          <RouterLink to="/maintenance/issues" class="text-xs text-navy hover:underline">
            View all →
          </RouterLink>
        </div>
        <div v-if="loading" class="space-y-2 animate-pulse">
          <div class="h-12 bg-gray-100 rounded w-1/3"></div>
          <div class="h-3 bg-gray-100 rounded w-1/2"></div>
        </div>
        <template v-else>
          <div v-if="(statsData.open_maintenance ?? 0) > 0">
            <div class="text-5xl font-bold tracking-tight tabular-nums text-gray-900 mb-1">
              {{ statsData.open_maintenance }}
            </div>
            <p class="text-sm text-gray-500">request{{ statsData.open_maintenance !== 1 ? 's' : '' }} need attention</p>
            <RouterLink
              to="/maintenance/issues"
              class="mt-4 inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold bg-warning-50 text-warning-700 rounded-lg hover:bg-warning-100 transition-colors"
            >
              <Wrench :size="13" /> Review requests
            </RouterLink>
          </div>
          <div v-else class="flex flex-col items-center justify-center py-6 text-center">
            <div class="w-10 h-10 rounded-xl bg-success-50 flex items-center justify-center mb-2">
              <CheckCircle2 :size="18" class="text-success-600" />
            </div>
            <p class="text-sm font-medium text-gray-700">All clear</p>
            <p class="text-xs text-gray-400 mt-0.5">No open maintenance requests</p>
          </div>
        </template>
      </div>
    </div>

    <!-- ── Overdue Maintenance Widget ── -->
    <OverdueMaintenanceWidget />

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
        <h2 class="text-sm font-bold text-gray-900 mb-5">Unit occupancy</h2>
        <div v-if="loading" class="flex items-center justify-center py-8 animate-pulse">
          <div class="w-36 h-36 rounded-full bg-gray-100"></div>
        </div>
        <div v-else-if="(statsData.total_units ?? 0) === 0" class="flex flex-col items-center justify-center py-8 text-center">
          <svg width="120" height="120" viewBox="0 0 140 140">
            <circle cx="70" cy="70" r="54" fill="none" stroke="#f1f5f9" stroke-width="14" />
          </svg>
          <p class="text-xs text-gray-400 mt-2">No units added yet</p>
          <RouterLink to="/properties" class="mt-2 text-xs text-navy hover:underline">Add a property →</RouterLink>
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
import { ref, computed, onMounted, nextTick } from 'vue'
import api from '../../api'
import { useToast } from '../../composables/useToast'
import { useAuthStore } from '../../stores/auth'
import { usePropertiesStore } from '../../stores/properties'
import PropertyTimelineWidget from './PropertyTimelineWidget.vue'
import OverdueMaintenanceWidget from '../../components/OverdueMaintenanceWidget.vue'
import PageHeader from '../../components/PageHeader.vue'
import {
  Building2, Users, Wrench, FileText, Home,
  UserCheck, FileSignature, PenLine, CheckCircle2,
  Settings, UserPlus, X, ShieldAlert,
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
      api.get('/properties/landlords/?page_size=1'),
      api.get('/leases/templates/?page_size=1'),
      api.get('/esigning/submissions/?page_size=1'),
    ])

    propertiesStore.fetchAll()

    if (s.status === 'fulfilled') statsData.value = s.value.data
    if (signing.status === 'fulfilled') pendingSigning.value = (signing.value.data.results ?? signing.value.data).slice(0, 3)

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

// ── Hero Metrics ─────────────────────────────────────────────────────────────
const stats = computed(() => [
  {
    label: 'Properties',
    value: statsData.value.total_properties ?? 0,
    sub: `${statsData.value.total_units ?? 0} unit${(statsData.value.total_units ?? 0) !== 1 ? 's' : ''} total`,
    icon: Building2, bg: 'bg-navy/10', iconColor: 'text-navy', href: '/properties',
  },
  {
    label: 'Total units',
    value: statsData.value.total_units ?? 0,
    sub: `${statsData.value.occupied_units ?? 0} occupied`,
    icon: Home, bg: 'bg-info-50', iconColor: 'text-info-600', href: '/properties',
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

// ── Pipeline steps ────────────────────────────────────────────────────────────
const pipelineSteps = computed(() => {
  const totalUnits = statsData.value.total_units || 0
  const activeLeases = statsData.value.active_leases ?? 0
  const hasProperties = (statsData.value.total_properties ?? 0) > 0
  let landlordPct = 0
  if (landlordCount.value > 0) landlordPct = 100
  else if (hasProperties) landlordPct = 30

  return [
    { label: 'Owner',    icon: UserCheck,     to: '/landlords',        percent: landlordPct, hint: 'Add an owner' },
    { label: 'Property', icon: Building2,     to: '/properties',       percent: hasProperties ? (totalUnits > 0 ? 100 : 50) : 0, hint: 'Add a property' },
    { label: 'Template', icon: FileSignature, to: '/leases/templates', percent: templateCount.value > 0 ? 100 : 0, hint: 'Create template' },
    { label: 'Lease',    icon: FileText,      to: '/leases',           percent: totalUnits > 0 ? Math.min(100, Math.round((activeLeases / totalUnits) * 100)) : 0, hint: 'Draft a lease' },
    { label: 'Sign',     icon: PenLine,       to: '/leases/overview',  percent: signingTotal.value > 0 ? Math.min(100, Math.round((signingCompleted.value / signingTotal.value) * 100)) : 0, hint: 'Send for signing' },
  ]
})

const completedSteps = computed(() => pipelineSteps.value.filter(s => s.percent >= 100).length)
const overallProgress = computed(() => Math.round(pipelineSteps.value.reduce((sum, s) => sum + Math.min(100, s.percent), 0) / 5))

// ── Occupancy ─────────────────────────────────────────────────────────────────
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
