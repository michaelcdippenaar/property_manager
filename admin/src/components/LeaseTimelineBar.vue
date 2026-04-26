<template>
  <div class="w-full">
    <div class="relative h-2.5 bg-gray-100 rounded-full overflow-visible">
      <!-- filled portion: start → today -->
      <div
        class="absolute inset-y-0 left-0 bg-navy rounded-full"
        :style="{ width: filledPct + '%' }"
      />
      <!-- notice window marker -->
      <div
        v-if="noticeMarkerPct !== null"
        class="absolute -top-1 -bottom-1 w-0.5"
        :class="noticeMarkerClass"
        :style="{ left: noticeMarkerPct + '%' }"
        :title="`Notice window opens ${fmtDate(noticeDate)}`"
      />
      <!-- today cursor -->
      <div
        v-if="todayCursorPct !== null"
        class="absolute -top-1.5 -bottom-1.5 w-[2px] bg-accent rounded"
        :style="{ left: todayCursorPct + '%' }"
        title="Today"
      />
      <!-- milestone dots -->
      <div
        v-for="m in renderedMilestones"
        :key="m.kind + m.date"
        class="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-2 h-2 rounded-full border border-white"
        :class="milestoneColor(m.kind)"
        :style="{ left: m.pct + '%' }"
        :title="`${m.label} — ${fmtDate(m.date)}`"
      />
    </div>
    <!-- Compact: single line with key numbers -->
    <div v-if="compact" class="flex items-center justify-between mt-1 text-[11px] tabular-nums text-gray-500">
      <span>{{ fmtDate(start) }}</span>
      <span v-if="successorLeaseId" class="text-success-600 font-medium">Renewal drafted</span>
      <span v-else-if="daysElapsed !== null" class="font-medium" :class="daysRemaining < 30 ? 'text-danger-500' : daysRemaining < 60 ? 'text-warning-600' : 'text-gray-500'">
        {{ daysRemaining >= 0 ? `${daysRemaining}d left` : `${Math.abs(daysRemaining)}d overdue` }}
      </span>
      <span>{{ fmtDate(end) }}</span>
    </div>
    <!-- Full: two rows with all details -->
    <template v-else>
      <div class="flex items-center justify-between mt-1 text-micro text-gray-400 tracking-wide">
        <span>{{ fmtDate(start) }}</span>
        <span v-if="successorLeaseId" class="text-success-600 font-medium">Renewal drafted</span>
        <span>{{ fmtDate(end) }}</span>
      </div>
      <div
        v-if="daysElapsed !== null"
        class="flex items-center justify-between mt-0.5 text-micro font-semibold tabular-nums"
      >
        <span class="text-gray-500">Day {{ daysElapsed }} / {{ totalDays }}</span>
        <span v-if="daysToNotice !== null" :class="noticeTextColor">
          {{ daysToNotice > 0
            ? `${daysToNotice}d to notice`
            : daysToNotice === 0
              ? 'Notice opens today'
              : `Notice overdue ${Math.abs(daysToNotice)}d` }}
        </span>
        <span :class="daysRemaining < 30 ? 'text-danger-500' : daysRemaining < 60 ? 'text-warning-600' : 'text-gray-500'">
          {{ daysRemaining >= 0 ? `${daysRemaining}d left` : `${Math.abs(daysRemaining)}d overdue` }}
        </span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface TimelineMilestone {
  kind: 'lease_signed' | 'notice_opens' | 'lease_ends' | 'renewal_drafted'
  label: string
  date: string | null
}

const props = defineProps<{
  startDate: string | null
  endDate: string | null
  noticePeriodDays: number
  milestones?: TimelineMilestone[]
  successorLeaseId?: number | null
  compact?: boolean
}>()

function toDate(s: string | null | undefined): Date | null {
  if (!s) return null
  const d = new Date(s)
  return isNaN(d.getTime()) ? null : d
}

function fmtDate(s: string | Date | null): string {
  const d = typeof s === 'string' ? toDate(s) : s
  if (!d) return '—'
  return d.toLocaleDateString('en-ZA', { day: '2-digit', month: 'short', year: 'numeric' })
}

const start = computed(() => props.startDate)
const end = computed(() => props.endDate)

const startMs = computed(() => toDate(props.startDate)?.getTime() ?? null)
const endMs = computed(() => toDate(props.endDate)?.getTime() ?? null)
const spanMs = computed(() => {
  if (startMs.value === null || endMs.value === null) return null
  return Math.max(endMs.value - startMs.value, 1)
})

const todayMs = computed(() => {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  return d.getTime()
})

function pct(dateMs: number): number {
  if (spanMs.value === null || startMs.value === null) return 0
  const raw = ((dateMs - startMs.value) / spanMs.value) * 100
  return Math.max(0, Math.min(100, raw))
}

const filledPct = computed(() => {
  if (spanMs.value === null) return 0
  return pct(todayMs.value)
})

const todayCursorPct = computed(() => {
  if (startMs.value === null || endMs.value === null) return null
  if (todayMs.value < startMs.value || todayMs.value > endMs.value) return null
  return pct(todayMs.value)
})

const noticeDate = computed(() => {
  if (endMs.value === null) return null
  const d = new Date(endMs.value)
  d.setDate(d.getDate() - (props.noticePeriodDays || 0))
  return d.toISOString().slice(0, 10)
})

const noticeMarkerPct = computed(() => {
  const nd = noticeDate.value
  if (!nd) return null
  const ms = toDate(nd)?.getTime()
  if (ms === undefined || ms === null) return null
  return pct(ms)
})

const noticeMarkerClass = computed(() => {
  if (endMs.value === null || startMs.value === null) return 'bg-warning-500'
  const daysToNotice = Math.ceil(
    ((toDate(noticeDate.value)?.getTime() ?? endMs.value) - todayMs.value) / 86_400_000,
  )
  if (daysToNotice < 0) return 'bg-danger-500'
  if (daysToNotice < 30) return 'bg-danger-400'
  if (daysToNotice < 60) return 'bg-warning-500'
  return 'bg-gray-400'
})

const renderedMilestones = computed(() => {
  const list = (props.milestones || []).filter(m => !!m.date)
  return list.map(m => {
    const ms = toDate(m.date!)?.getTime() ?? null
    return { ...m, pct: ms === null ? 0 : pct(ms) }
  })
})

const totalDays = computed(() => {
  if (spanMs.value === null) return 0
  return Math.max(1, Math.round(spanMs.value / 86_400_000))
})

const daysElapsed = computed(() => {
  if (startMs.value === null || endMs.value === null) return null
  const raw = Math.round((todayMs.value - startMs.value) / 86_400_000)
  return Math.max(0, Math.min(totalDays.value, raw))
})

const daysRemaining = computed(() => {
  if (endMs.value === null) return 0
  return Math.round((endMs.value - todayMs.value) / 86_400_000)
})

const daysToNotice = computed(() => {
  const nd = noticeDate.value
  if (!nd) return null
  const ms = toDate(nd)?.getTime()
  if (ms === undefined || ms === null) return null
  return Math.ceil((ms - todayMs.value) / 86_400_000)
})

const noticeTextColor = computed(() => {
  const d = daysToNotice.value
  if (d === null) return 'text-gray-400'
  if (d < 0) return 'text-danger-600'
  if (d < 30) return 'text-danger-500'
  if (d < 60) return 'text-warning-600'
  return 'text-gray-500'
})

function milestoneColor(kind: TimelineMilestone['kind']): string {
  switch (kind) {
    case 'lease_signed': return 'bg-navy-dark'
    case 'notice_opens': return 'bg-warning-500'
    case 'lease_ends': return 'bg-gray-500'
    case 'renewal_drafted': return 'bg-success-600'
    default: return 'bg-gray-400'
  }
}
</script>
