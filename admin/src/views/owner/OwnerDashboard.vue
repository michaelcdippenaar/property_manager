<template>
  <div class="space-y-5">
    <!-- Stats widgets -->
    <div v-if="stats" class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="card p-4">
        <div class="text-xs text-gray-400 uppercase tracking-wide">Properties</div>
        <div class="text-2xl font-bold text-navy mt-1">{{ stats.total_properties }}</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-gray-400 uppercase tracking-wide">Units</div>
        <div class="text-2xl font-bold text-gray-700 mt-1">{{ stats.total_units }}</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-gray-400 uppercase tracking-wide">Occupancy</div>
        <div class="text-2xl font-bold text-success-600 mt-1">{{ stats.occupancy_rate }}%</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-gray-400 uppercase tracking-wide">Active Issues</div>
        <div class="text-2xl font-bold text-warning-600 mt-1">{{ stats.active_issues }}</div>
      </div>
    </div>
    <div v-else class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div v-for="i in 4" :key="i" class="card p-4 animate-pulse">
        <div class="h-3 bg-gray-100 rounded w-2/3 mb-3"></div>
        <div class="h-7 bg-gray-100 rounded w-1/2"></div>
      </div>
    </div>

    <!-- Last updated timestamp -->
    <div v-if="stats?.last_updated" class="flex items-center gap-1.5 text-xs text-gray-400">
      <RefreshCw :size="11" />
      <span>Updated {{ formatRelative(stats.last_updated) }}</span>
      <button
        class="ml-1 text-navy/60 hover:text-navy transition-colors"
        :disabled="refreshing"
        @click="refreshAll"
        title="Refresh dashboard"
      >
        <RefreshCw :size="11" :class="refreshing ? 'animate-spin' : ''" />
      </button>
    </div>

    <!-- Payment performance widget (current month) -->
    <div v-if="stats?.payment_performance" class="card p-5">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5">
          <TrendingUp :size="13" /> Rent collection — {{ formatMonth(stats.payment_performance.month) }}
        </h2>
        <span class="text-xs font-semibold"
          :class="stats.payment_performance.collection_rate >= 80 ? 'text-success-600' : 'text-warning-600'">
          {{ stats.payment_performance.collection_rate }}%
        </span>
      </div>
      <div class="h-2 bg-gray-100 rounded-full overflow-hidden mb-3">
        <div
          class="h-full rounded-full transition-all duration-700"
          :class="stats.payment_performance.collection_rate >= 80 ? 'bg-success-500' : 'bg-warning-500'"
          :style="{ width: `${stats.payment_performance.collection_rate}%` }"
        />
      </div>
      <div class="flex justify-between text-xs text-gray-500">
        <span>{{ stats.payment_performance.invoices_paid }} / {{ stats.payment_performance.invoices_due }} invoices paid</span>
        <span>R{{ formatAmount(stats.payment_performance.total_collected_zar) }} / R{{ formatAmount(stats.payment_performance.total_due_zar) }}</span>
      </div>
    </div>

    <!-- Onboarding in progress -->
    <div v-if="pendingOnboardings.length > 0" class="card p-5">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5">
          <ClipboardList :size="13" /> Tenant onboarding in progress
        </h2>
      </div>
      <div class="space-y-3">
        <div v-for="ob in pendingOnboardings" :key="ob.id" class="flex items-center gap-3">
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
        </div>
      </div>
    </div>

    <!-- Overdue maintenance widget -->
    <OverdueMaintenanceWidget :max-preview="3" />

    <!-- Recent activity feed -->
    <div class="card p-5">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5">
          <Activity :size="13" /> Recent activity
        </h2>
        <span v-if="feedLoading" class="text-xs text-gray-400">Loading…</span>
      </div>
      <div v-if="!feedLoading && activityFeed.length === 0" class="text-xs text-gray-400 py-2">
        No recent activity across your portfolio.
      </div>
      <div v-else class="divide-y divide-gray-50">
        <div
          v-for="(event, idx) in activityFeed"
          :key="idx"
          class="flex items-start gap-3 py-2.5 first:pt-0 last:pb-0"
        >
          <div class="mt-0.5 flex-shrink-0">
            <component :is="eventIcon(event.event_type)" :size="14" :class="eventIconClass(event.event_type)" />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs text-gray-700 leading-snug">{{ event.label }}</p>
            <p class="text-xs text-gray-400 mt-0.5">{{ formatRelative(event.occurred_at) }}</p>
          </div>
          <span class="flex-shrink-0 text-xs font-medium px-2 py-0.5 rounded-full"
            :class="eventBadgeClass(event.event_type)">
            {{ eventBadgeLabel(event.event_type) }}
          </span>
        </div>
      </div>
    </div>

    <!-- AI Lease Builder CTA -->
    <RouterLink to="/owner/leases"
      class="card p-5 flex items-center gap-4 hover:shadow-md transition-shadow cursor-pointer group no-underline block"
    >
      <div class="w-12 h-12 rounded-xl bg-navy/8 flex items-center justify-center flex-shrink-0 group-hover:bg-navy/12 transition-colors">
        <Sparkles :size="22" class="text-navy" />
      </div>
      <div class="flex-1 min-w-0">
        <div class="text-sm font-semibold text-gray-900">Draft a Lease with AI</div>
        <div class="text-xs text-gray-500 mt-0.5">Generate an RHA-compliant lease agreement in minutes — just answer a few questions.</div>
      </div>
      <ChevronRight :size="18" class="text-gray-400 flex-shrink-0 group-hover:text-navy transition-colors" />
    </RouterLink>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import {
  Sparkles, ChevronRight, ClipboardList, RefreshCw, TrendingUp,
  Activity, Wrench, CheckCircle2, FileText, FileSignature, DollarSign,
} from 'lucide-vue-next'
import api from '../../api'
import OverdueMaintenanceWidget from '../../components/OverdueMaintenanceWidget.vue'

interface PaymentPerformance {
  month: string
  invoices_due: number
  invoices_paid: number
  total_due_zar: string
  total_collected_zar: string
  collection_rate: number
}

interface DashboardStats {
  total_properties: number
  total_units: number
  occupied_units: number
  occupancy_rate: number
  active_issues: number
  payment_performance: PaymentPerformance | null
  last_updated: string | null
}

interface ActivityEvent {
  event_type: string
  label: string
  occurred_at: string
  meta: Record<string, unknown>
}

const stats = ref<DashboardStats | null>(null)
const pendingOnboardings = ref<any[]>([])
const activityFeed = ref<ActivityEvent[]>([])
const feedLoading = ref(true)
const refreshing = ref(false)

async function loadDashboard() {
  try {
    const [dashRes, onboardingRes] = await Promise.allSettled([
      api.get('/properties/owner/dashboard/'),
      api.get('/tenant/onboarding/?page_size=10'),
    ])
    if (dashRes.status === 'fulfilled') stats.value = dashRes.value.data
    if (onboardingRes.status === 'fulfilled') {
      const all = onboardingRes.value.data.results ?? onboardingRes.value.data
      pendingOnboardings.value = all.filter((ob: any) => !ob.is_complete).slice(0, 5)
    }
  } catch { /* ignore */ }
}

async function loadActivityFeed() {
  feedLoading.value = true
  try {
    const resp = await api.get('/properties/owner/activity/?limit=20')
    activityFeed.value = resp.data
  } catch {
    activityFeed.value = []
  } finally {
    feedLoading.value = false
  }
}

async function refreshAll() {
  refreshing.value = true
  await Promise.allSettled([loadDashboard(), loadActivityFeed()])
  refreshing.value = false
}

onMounted(() => {
  loadDashboard()
  loadActivityFeed()
})

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatRelative(isoStr: string | null): string {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    if (isNaN(d.getTime())) return isoStr
    const diffMs = Date.now() - d.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    if (diffDays < 30) return `${diffDays}d ago`
    return d.toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' })
  } catch {
    return isoStr
  }
}

function formatMonth(monthStr: string): string {
  try {
    const d = new Date(`${monthStr}-01`)
    if (isNaN(d.getTime())) return monthStr
    return d.toLocaleDateString('en-ZA', { month: 'long', year: 'numeric' })
  } catch {
    return monthStr
  }
}

function formatAmount(val: string | number): string {
  const n = parseFloat(String(val))
  if (isNaN(n)) return '0'
  return n.toLocaleString('en-ZA', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

type EventIconComponent = typeof DollarSign

function eventIcon(type: string): EventIconComponent {
  const map: Record<string, EventIconComponent> = {
    rent_received: DollarSign,
    maintenance_opened: Wrench,
    maintenance_closed: CheckCircle2,
    lease_signed: FileText,
    mandate_signed: FileSignature,
  }
  return map[type] ?? Activity
}

function eventIconClass(type: string): string {
  const map: Record<string, string> = {
    rent_received: 'text-success-600',
    maintenance_opened: 'text-warning-600',
    maintenance_closed: 'text-success-500',
    lease_signed: 'text-navy',
    mandate_signed: 'text-navy',
  }
  return map[type] ?? 'text-gray-400'
}

function eventBadgeClass(type: string): string {
  const map: Record<string, string> = {
    rent_received: 'bg-success-50 text-success-700',
    maintenance_opened: 'bg-warning-50 text-warning-700',
    maintenance_closed: 'bg-success-50 text-success-700',
    lease_signed: 'bg-navy/8 text-navy',
    mandate_signed: 'bg-navy/8 text-navy',
  }
  return map[type] ?? 'bg-gray-50 text-gray-500'
}

function eventBadgeLabel(type: string): string {
  const map: Record<string, string> = {
    rent_received: 'Rent',
    maintenance_opened: 'Maintenance',
    maintenance_closed: 'Resolved',
    lease_signed: 'Lease',
    mandate_signed: 'Mandate',
  }
  return map[type] ?? type
}
</script>
