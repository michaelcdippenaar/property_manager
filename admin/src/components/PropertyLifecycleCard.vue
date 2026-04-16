<template>
  <div class="card p-5 space-y-5">
    <!-- Header -->
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0">
        <RouterLink
          :to="`/properties/${entry.property_id}`"
          class="text-base font-semibold text-gray-900 hover:text-navy truncate block"
        >
          {{ entry.property_name }}
        </RouterLink>
        <div class="text-xs text-gray-500 truncate mt-0.5">{{ entry.property_address }}</div>
      </div>
      <span
        class="text-xs font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full flex-shrink-0 border"
        :class="propertyTypeBadgeClass"
      >
        {{ entry.property_type }}
      </span>
    </div>

    <!-- Active lease -->
    <div v-if="lease" class="space-y-3">
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-2 min-w-0">
          <div class="flex items-center gap-1.5">
            <span
              v-for="(name, i) in tenantNames"
              :key="i"
              class="text-sm font-medium text-gray-900 whitespace-nowrap"
              :title="name"
            >{{ shortName(name) }}<span v-if="i < tenantNames.length - 1" class="text-gray-300">,</span></span>
          </div>
          <span class="badge-green flex-shrink-0">Active</span>
        </div>
        <div class="text-right flex-shrink-0">
          <div class="text-xs font-semibold uppercase tracking-wider" :class="noticeBandTextClass">
            {{ noticeLabel }}
          </div>
        </div>
      </div>

      <!-- Timeline bar -->
      <LeaseTimelineBar
        :start-date="lease.start_date"
        :end-date="lease.end_date"
        :notice-period-days="lease.notice_period_days"
        :successor-lease-id="lease.successor_lease_id"
        :milestones="milestones"
      />

    </div>

    <div v-else class="flex-1 flex items-center justify-center px-4 py-6 bg-gray-50 rounded-lg text-center text-sm text-gray-500">
      No active lease for this property.
    </div>

    <!-- Maintenance alert -->
    <RouterLink
      v-if="entry.open_maintenance_count > 0"
      :to="`/maintenance/issues?property=${entry.property_id}`"
      class="flex items-center gap-2.5 px-3 py-2 rounded-lg border transition-colors"
      :class="hasUrgent
        ? 'bg-danger-50 border-danger-100 hover:bg-danger-100/70 text-danger-700'
        : 'bg-warning-50 border-warning-100 hover:bg-warning-100/70 text-warning-700'"
    >
      <AlertTriangle :size="15" class="flex-shrink-0" />
      <span class="text-xs font-semibold flex-1 truncate">
        {{ entry.open_maintenance_count }} open maintenance
        {{ entry.open_maintenance_count === 1 ? 'issue' : 'issues' }}
        <span v-if="urgentCount > 0" class="font-bold">· {{ urgentCount }} urgent</span>
      </span>
      <span class="text-xs font-semibold opacity-90">Review →</span>
    </RouterLink>
    <div v-else class="flex items-center gap-1.5 text-xs text-success-700 py-1">
      <BadgeCheck :size="16" class="text-success-600" />
      <span>All clear — no open jobs</span>
    </div>

    <!-- Unified card action bar -->
    <div class="flex items-center justify-end gap-2 pt-1 border-t border-gray-100 -mx-5 px-5 -mb-1">
      <button
        v-if="lease && !lease.successor_lease_id"
        @click="$emit('prepare-next', lease.id)"
        class="inline-flex items-center gap-1.5 px-3.5 py-2 text-sm font-semibold bg-navy text-white rounded-lg hover:bg-navy/90 transition-colors"
      >
        <FilePlus :size="14" /> Prepare next lease
      </button>
      <RouterLink
        v-else-if="lease && lease.successor_lease_id"
        :to="`/properties/${entry.property_id}?tab=leases&lease=${lease.successor_lease_id}`"
        class="btn-primary btn-sm"
      >
        <Send :size="14" /> Send for Signing
      </RouterLink>
      <RouterLink
        v-else
        :to="`/properties/${entry.property_id}?tab=leases&action=new`"
        class="inline-flex items-center gap-1.5 px-3.5 py-2 text-sm font-semibold bg-navy text-white rounded-lg hover:bg-navy/90 transition-colors"
      >
        <FilePlus :size="14" /> Create lease
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { FilePlus, Send, AlertTriangle, BadgeCheck } from 'lucide-vue-next'
import LeaseTimelineBar, { type TimelineMilestone } from './LeaseTimelineBar.vue'
import type { PortfolioEntry } from '../stores/properties'

const props = defineProps<{ entry: PortfolioEntry }>()
defineEmits<{ (e: 'prepare-next', leaseId: number): void }>()

const lease = computed(() => props.entry.active_lease)

function fmtDate(s: string | null | undefined): string {
  if (!s) return '—'
  const d = new Date(s)
  if (isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('en-ZA', { day: '2-digit', month: 'short', year: 'numeric' })
}

function formatRand(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === '') return '0'
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (isNaN(n)) return '0'
  return n.toLocaleString('en-ZA', { maximumFractionDigits: 0 })
}

function shortName(full: string): string {
  if (!full) return '?'
  const parts = full.trim().split(/\s+/)
  if (parts.length <= 1) return full
  const surname = parts[parts.length - 1]
  const initial = parts[0].charAt(0).toUpperCase()
  return `${initial} ${surname}`
}

const tenantNames = computed(() => {
  const l = lease.value
  if (!l) return []
  if (l.all_tenant_names && l.all_tenant_names.length) return l.all_tenant_names
  return l.tenant_name ? [l.tenant_name] : []
})

const noticeDateIso = computed(() => lease.value?.notice_window_date || null)

const daysToNotice = computed(() => {
  if (!noticeDateIso.value) return null
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const target = new Date(noticeDateIso.value); target.setHours(0, 0, 0, 0)
  return Math.ceil((target.getTime() - today.getTime()) / 86_400_000)
})

const noticeLabel = computed(() => {
  const d = daysToNotice.value
  if (d === null) return 'No end date'
  if (d < 0) return '⚠ Notice overdue'
  if (d === 0) return 'Notice window opens today'
  return `Renewal decision in ${d}d`
})

const noticeBandTextClass = computed(() => {
  const d = daysToNotice.value
  if (d === null) return 'text-gray-400'
  if (d < 0) return 'text-danger-600'
  if (d < 30) return 'text-danger-500'
  if (d < 60) return 'text-warning-600'
  return 'text-gray-500'
})

const propertyTypeBadgeClass = computed(() => {
  const t = (props.entry.property_type || '').toLowerCase()
  if (t.includes('apart') || t === 'flat') return 'bg-navy/10 text-navy border-navy/40'
  if (t.includes('house')) return 'bg-success-50 text-success-700 border-success-100'
  if (t.includes('town')) return 'bg-warning-50 text-warning-700 border-warning-100'
  if (t.includes('studio') || t.includes('garden') || t.includes('cottage')) return 'bg-rose-50 text-rose-800 border-rose-100'
  return 'bg-gray-100 text-gray-600 border-gray-200'
})

const milestones = computed<TimelineMilestone[]>(() => {
  const l = lease.value
  if (!l) return []
  const out: TimelineMilestone[] = []
  if (l.signed_at) out.push({ kind: 'lease_signed', label: 'Signed', date: l.signed_at })
  if (noticeDateIso.value) out.push({ kind: 'notice_opens', label: 'Notice opens', date: noticeDateIso.value })
  if (l.end_date) out.push({ kind: 'lease_ends', label: 'Lease ends', date: l.end_date })
  if (l.successor_lease_id) out.push({ kind: 'renewal_drafted', label: 'Renewal drafted', date: l.end_date })
  return out
})

const urgentCount = computed(() =>
  props.entry.top_maintenance.filter(m => m.priority === 'urgent').length,
)
const hasUrgent = computed(() => urgentCount.value > 0)
</script>
