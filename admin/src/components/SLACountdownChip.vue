<template>
  <span
    v-if="show"
    :title="tooltipText"
    class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-micro font-semibold tabular-nums select-none"
    :class="chipClass"
  >
    <Clock :size="9" />
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Clock } from 'lucide-vue-next'

interface Props {
  /** ISO datetime string for the resolve deadline */
  resolveDeadline?: string | null
  /** Percentage of resolve window remaining (negative = overdue) */
  resolvePct?: number | null
  /** Whether the ticket is already overdue (backend-computed) */
  isOverdue?: boolean
  /** Ticket status — don't show for resolved/closed */
  status?: string
}

const props = withDefaults(defineProps<Props>(), {
  resolveDeadline: null,
  resolvePct: null,
  isOverdue: false,
  status: 'open',
})

// Hide chip for resolved/closed tickets
const show = computed(() => {
  if (!props.resolveDeadline) return false
  return !['resolved', 'closed'].includes(props.status ?? '')
})

// Countdown text
const label = computed(() => {
  if (!props.resolveDeadline) return ''
  const deadline = new Date(props.resolveDeadline)
  const now = new Date()
  const diffMs = deadline.getTime() - now.getTime()
  if (diffMs < 0) {
    const overdueMins = Math.abs(diffMs) / 60000
    if (overdueMins < 60) return `${Math.round(overdueMins)}m overdue`
    const overdueHrs = overdueMins / 60
    if (overdueHrs < 48) return `${Math.round(overdueHrs)}h overdue`
    return `${Math.round(overdueHrs / 24)}d overdue`
  }
  const mins = diffMs / 60000
  if (mins < 60) return `${Math.round(mins)}m left`
  const hrs = mins / 60
  if (hrs < 48) return `${Math.round(hrs)}h left`
  return `${Math.round(hrs / 24)}d left`
})

const tooltipText = computed(() => {
  if (!props.resolveDeadline) return ''
  const d = new Date(props.resolveDeadline)
  const formatted = d.toLocaleDateString('en-ZA') + ' ' + d.toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' })
  return `SLA resolve deadline: ${formatted}`
})

// Color: green >50%, yellow 20–50%, red <20% or overdue
const chipClass = computed(() => {
  const pct = props.resolvePct
  const overdue = props.isOverdue || (pct !== null && pct !== undefined && pct < 0)

  if (overdue) {
    return 'bg-red-50 text-red-700 border border-red-200'
  }
  if (pct === null || pct === undefined) {
    return 'bg-gray-50 text-gray-500 border border-gray-200'
  }
  if (pct > 50) {
    return 'bg-green-50 text-green-700 border border-green-200'
  }
  if (pct >= 20) {
    return 'bg-amber-50 text-amber-700 border border-amber-200'
  }
  return 'bg-red-50 text-red-700 border border-red-200'
})
</script>
