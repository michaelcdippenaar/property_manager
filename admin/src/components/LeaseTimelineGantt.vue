<template>
  <div class="w-full">
    <div v-if="!visibleLeases.length" class="text-sm text-gray-500 italic py-6 text-center">
      No active or pending leases to display.
    </div>
    <div v-else class="relative">
      <!-- x-axis header -->
      <div class="relative h-5 mb-2 text-xs text-gray-400 border-b border-gray-100">
        <span
          v-for="tick in axisTicks"
          :key="tick.label"
          class="absolute -translate-x-1/2"
          :style="{ left: tick.pct + '%' }"
        >
          {{ tick.label }}
        </span>
      </div>

      <!-- rows -->
      <div class="relative space-y-3">
        <!-- today vertical cursor spans all rows -->
        <div
          v-if="todayPct !== null"
          class="absolute top-0 bottom-0 w-[2px] bg-accent-500 z-10 pointer-events-none"
          :style="{ left: todayPct + '%' }"
          title="Today"
        />
        <div
          v-for="row in visibleLeases"
          :key="row.lease.id"
          class="relative h-8 bg-gray-50 rounded"
        >
          <!-- bar -->
          <div
            class="absolute inset-y-1 rounded flex items-center px-2 text-xs font-medium truncate"
            :class="barClass(row.lease.status)"
            :style="{ left: row.left + '%', width: row.width + '%' }"
            :title="`${row.lease.status.toUpperCase()} · ${fmtDate(row.lease.start_date)} → ${fmtDate(row.lease.end_date)}`"
          >
            {{ barLabel(row.lease) }}
          </div>
          <!-- milestones overlay -->
          <div
            v-for="m in row.milestones"
            :key="m.kind + m.date"
            class="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-2.5 h-2.5 rounded-full border-2 border-white z-20"
            :class="milestoneColor(m.kind)"
            :style="{ left: m.pct + '%' }"
            :title="`${m.label} — ${fmtDate(m.date)}`"
          />
        </div>
      </div>

      <!-- legend -->
      <div class="flex items-center gap-4 mt-4 text-micro text-gray-500">
        <span class="inline-flex items-center gap-1"><span class="w-3 h-3 rounded bg-info-100" />Active lease</span>
        <span class="inline-flex items-center gap-1"><span class="w-3 h-3 rounded bg-warning-100" />Pending lease</span>
        <span class="inline-flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-navy-dark" />Signed</span>
        <span class="inline-flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-warning-500" />Notice opens</span>
        <span class="inline-flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-gray-500" />Lease ends</span>
        <span class="inline-flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-success-600" />Renewal drafted</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface LeaseLike {
  id: number
  status: string
  start_date: string | null
  end_date: string | null
  notice_period_days?: number
  created_at?: string
  signed_at?: string | null
  all_tenant_names?: string[]
  tenant_name?: string
  successor_lease_id?: number | null
  _displayStatus?: string
}

const props = defineProps<{
  leases: LeaseLike[]
}>()

function toDate(s: string | null | undefined): Date | null {
  if (!s) return null
  const d = new Date(s)
  return isNaN(d.getTime()) ? null : d
}

function fmtDate(s: string | null | undefined): string {
  const d = toDate(s)
  if (!d) return '—'
  return d.toLocaleDateString('en-ZA', { day: '2-digit', month: 'short', year: 'numeric' })
}

// Rolling 12-month window starting from the first of the current month.
// Forward-looking only: shows upcoming renewals, notice periods, and the
// active slice of the current lease without historical clutter.
const bounds = computed(() => {
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const min = new Date(today.getFullYear(), today.getMonth(), 1)
  const max = new Date(min); max.setMonth(max.getMonth() + 12)
  const minMs = min.getTime()
  const maxMs = max.getTime()
  return { min: minMs, max: maxMs, span: Math.max(maxMs - minMs, 1) }
})

// Filter: active + pending only, and only leases that overlap the window
// (lease end >= min AND lease start <= max) to avoid tiny edge slivers.
const visibleLeasesRaw = computed<LeaseLike[]>(() => {
  const KEEP = new Set(['active', 'pending'])
  const b = bounds.value
  return (props.leases || []).filter(l => {
    if (!KEEP.has((l._displayStatus ?? l.status) || '')) return false
    const s = toDate(l.start_date)?.getTime()
    const e = toDate(l.end_date)?.getTime()
    if (s === undefined || e === undefined) return false
    return e >= b.min && s <= b.max
  })
})

function pct(ms: number): number {
  const b = bounds.value
  const raw = ((ms - b.min) / b.span) * 100
  return Math.max(0, Math.min(100, raw))
}

const todayPct = computed(() => {
  const t = new Date(); t.setHours(0, 0, 0, 0)
  return pct(t.getTime())
})

const axisTicks = computed(() => {
  const b = bounds.value
  const ticks: { label: string; pct: number }[] = []
  const start = new Date(b.min)
  const end = new Date(b.max)
  // Round to start of month, step every 2 months (~6 ticks over a 12-month window).
  const cursor = new Date(start.getFullYear(), start.getMonth(), 1)
  while (cursor.getTime() <= end.getTime()) {
    ticks.push({
      label: cursor.toLocaleDateString('en-ZA', { month: 'short', year: '2-digit' }),
      pct: pct(cursor.getTime()),
    })
    cursor.setMonth(cursor.getMonth() + 2)
  }
  return ticks
})

function milestonesFor(l: LeaseLike) {
  const out: { kind: string; label: string; date: string | null; pct: number }[] = []
  const push = (kind: string, label: string, dateStr: string | null) => {
    if (!dateStr) return
    const ms = toDate(dateStr)?.getTime()
    if (ms === undefined || ms === null) return
    out.push({ kind, label, date: dateStr, pct: pct(ms) })
  }
  push('lease_signed', 'Signed', l.signed_at ?? l.created_at ?? null)
  if (l.end_date && l.notice_period_days) {
    const end = toDate(l.end_date)!
    const notice = new Date(end); notice.setDate(notice.getDate() - l.notice_period_days)
    push('notice_opens', 'Notice opens', notice.toISOString().slice(0, 10))
  }
  push('lease_ends', 'Ends', l.end_date)
  return out
}

const visibleLeases = computed(() => {
  return visibleLeasesRaw.value
    .map(lease => {
      const s = toDate(lease.start_date)?.getTime()
      const e = toDate(lease.end_date)?.getTime()
      if (!s || !e) return null
      const left = pct(s)
      const right = pct(e)
      return {
        lease,
        left,
        width: Math.max(right - left, 2),
        milestones: milestonesFor(lease),
      }
    })
    .filter((r): r is NonNullable<typeof r> => !!r)
    .sort((a, b) => a.left - b.left)
})

function barClass(status: string): string {
  if (status === 'active') return 'bg-info-100 text-navy'
  if (status === 'pending') return 'bg-warning-100 text-warning-700'
  return 'bg-gray-100 text-gray-700'
}

function barLabel(l: LeaseLike): string {
  const names = l.all_tenant_names?.length ? l.all_tenant_names.join(', ') : (l.tenant_name || 'Unassigned')
  return `${names} · ${fmtDate(l.start_date)} → ${fmtDate(l.end_date)}`
}

function milestoneColor(kind: string): string {
  switch (kind) {
    case 'lease_signed': return 'bg-navy-dark'
    case 'notice_opens': return 'bg-warning-500'
    case 'lease_ends': return 'bg-gray-500'
    case 'renewal_drafted': return 'bg-success-600'
    default: return 'bg-gray-400'
  }
}
</script>
