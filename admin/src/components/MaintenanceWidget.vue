<template>
  <div class="card p-5">
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-2">
        <h2 class="text-sm font-bold text-gray-900">Maintenance</h2>
        <span
          v-if="totalOpen > 0"
          class="text-xs font-bold uppercase tracking-wider px-1.5 py-0.5 rounded"
          :class="totalUrgent > 0 ? 'bg-danger-100 text-danger-700' : 'bg-warning-100 text-warning-700'"
        >
          {{ totalOpen }} open{{ totalUrgent > 0 ? ` · ${totalUrgent} urgent` : '' }}
        </span>
      </div>
      <RouterLink to="/maintenance/issues" class="text-xs font-semibold text-navy hover:underline">
        View all →
      </RouterLink>
    </div>

    <div v-if="loading" class="space-y-2 animate-pulse">
      <div v-for="i in 3" :key="i" class="h-10 bg-gray-100 rounded"></div>
    </div>

    <template v-else>
      <div v-if="topIssues.length" class="divide-y divide-gray-100 border border-gray-100 rounded-lg overflow-hidden">
        <RouterLink
          v-for="item in topIssues"
          :key="item.id"
          :to="`/maintenance/issues/${item.id}`"
          class="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-50 transition-colors"
        >
          <span
            class="text-xs font-bold uppercase px-1.5 py-0.5 rounded flex-shrink-0"
            :class="priorityChipClass(item.priority)"
          >
            {{ item.priority }}
          </span>
          <div class="flex-1 min-w-0">
            <div class="text-sm font-medium text-gray-800 truncate">{{ item.title }}</div>
            <div class="text-micro text-gray-400 truncate">{{ item.property_name }}</div>
          </div>
          <span
            class="text-micro font-medium flex-shrink-0 tabular-nums"
            :class="item.days_open >= 7 ? 'text-danger-500' : item.days_open >= 3 ? 'text-warning-600' : 'text-gray-400'"
          >
            {{ item.days_open }}d open
          </span>
          <span class="text-micro font-medium text-gray-500 flex-shrink-0 capitalize">
            {{ item.status.replace('_', ' ') }}
          </span>
        </RouterLink>
      </div>

      <div v-else class="flex flex-col items-center justify-center py-6 text-center">
        <div class="w-10 h-10 rounded-xl bg-success-50 flex items-center justify-center mb-2">
          <BadgeCheck :size="20" class="text-success-600" />
        </div>
        <p class="text-sm font-medium text-gray-700">All clear</p>
        <p class="text-xs text-gray-400 mt-0.5">No open maintenance requests</p>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { BadgeCheck } from 'lucide-vue-next'
import type { PortfolioEntry } from '../stores/properties'

const props = defineProps<{
  portfolio: PortfolioEntry[]
  loading?: boolean
}>()

type Row = {
  id: number
  title: string
  priority: 'low' | 'medium' | 'high' | 'urgent'
  status: string
  days_open: number
  property_name: string
}

const PRIORITY_RANK: Record<Row['priority'], number> = { urgent: 0, high: 1, medium: 2, low: 3 }

const allIssues = computed<Row[]>(() => {
  const out: Row[] = []
  for (const entry of props.portfolio) {
    for (const m of entry.top_maintenance) {
      out.push({
        id: m.id,
        title: m.title,
        priority: m.priority,
        status: m.status,
        days_open: m.days_open,
        property_name: entry.property_name,
      })
    }
  }
  return out.sort((a, b) => {
    const pa = PRIORITY_RANK[a.priority] ?? 9
    const pb = PRIORITY_RANK[b.priority] ?? 9
    if (pa !== pb) return pa - pb
    return b.days_open - a.days_open
  })
})

const topIssues = computed(() => allIssues.value.slice(0, 5))
const totalOpen = computed(() =>
  props.portfolio.reduce((sum, e) => sum + (e.open_maintenance_count || 0), 0),
)
const totalUrgent = computed(() => allIssues.value.filter(i => i.priority === 'urgent').length)

function priorityChipClass(p: Row['priority']): string {
  switch (p) {
    case 'urgent': return 'bg-danger-100 text-danger-700'
    case 'high': return 'bg-orange-100 text-orange-700'
    case 'medium': return 'bg-warning-100 text-warning-700'
    case 'low': return 'bg-gray-100 text-gray-600'
    default: return 'bg-gray-100 text-gray-600'
  }
}
</script>
