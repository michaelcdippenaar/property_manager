<template>
  <div v-if="show" class="card p-5 border-red-100 bg-red-50/30">
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-2">
        <div class="w-7 h-7 rounded-lg bg-red-100 flex items-center justify-center flex-shrink-0">
          <AlertTriangle :size="14" class="text-red-600" />
        </div>
        <h2 class="text-sm font-bold text-gray-900">Overdue maintenance</h2>
        <span v-if="count > 0" class="inline-flex items-center rounded-full bg-red-500 text-white text-micro font-bold px-1.5 py-0.5 min-w-[1.25rem] justify-center">
          {{ count }}
        </span>
      </div>
      <RouterLink to="/maintenance/issues" class="text-xs text-navy hover:underline">
        View all →
      </RouterLink>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-2 animate-pulse">
      <div v-for="i in 2" :key="i" class="h-10 bg-red-100/60 rounded" />
    </div>

    <template v-else-if="tickets.length > 0">
      <div class="divide-y divide-red-100">
        <RouterLink
          v-for="ticket in tickets"
          :key="ticket.id"
          :to="`/maintenance/issues/${ticket.id}`"
          class="flex items-center gap-3 py-2.5 first:pt-0 last:pb-0 group no-underline"
        >
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-gray-900 truncate group-hover:text-navy transition-colors">
              {{ ticket.title }}
            </p>
            <p class="text-xs text-gray-400 truncate">
              {{ ticket.unit_label ?? `Unit #${ticket.unit}` }}
              <span v-if="ticket.tenant_name"> · {{ ticket.tenant_name }}</span>
            </p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <span class="text-micro font-semibold text-red-600 tabular-nums">
              {{ overdueLabel(ticket.sla_resolve_deadline) }}
            </span>
            <span :class="priorityBadge(ticket.priority)" class="text-micro">{{ ticket.priority }}</span>
          </div>
        </RouterLink>
      </div>

      <RouterLink
        v-if="count > tickets.length"
        to="/maintenance/issues?overdue=1"
        class="mt-3 flex items-center gap-1.5 text-xs text-red-600 hover:underline font-semibold"
      >
        <AlertTriangle :size="12" /> {{ count - tickets.length }} more overdue ticket{{ count - tickets.length !== 1 ? 's' : '' }} →
      </RouterLink>
    </template>

    <div v-else class="flex flex-col items-center justify-center py-4 text-center">
      <CheckCircle2 :size="20" class="text-success-500 mb-1" />
      <p class="text-sm text-gray-500">No overdue tickets</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { AlertTriangle, CheckCircle2 } from 'lucide-vue-next'
import api from '../api'

interface Props {
  /** Maximum number of tickets to preview (default 3) */
  maxPreview?: number
}

const props = withDefaults(defineProps<Props>(), {
  maxPreview: 3,
})

const loading = ref(true)
const tickets = ref<any[]>([])
const count = ref(0)

// Only show widget if there is at least one overdue ticket (after first load)
const show = computed(() => loading.value || count.value > 0)

onMounted(loadOverdue)

async function loadOverdue() {
  loading.value = true
  try {
    const { data } = await api.get('/maintenance/overdue/', { params: { page_size: props.maxPreview } })
    const results = data.results ?? data
    tickets.value = results.slice(0, props.maxPreview)
    count.value = data.count ?? results.length
  } catch {
    // Silently hide — don't block the dashboard on a widget error
    count.value = 0
    tickets.value = []
  } finally {
    loading.value = false
  }
}

function overdueLabel(deadline: string | null): string {
  if (!deadline) return ''
  const diffMs = Date.now() - new Date(deadline).getTime()
  if (diffMs < 0) return ''
  const hrs = diffMs / 3600000
  if (hrs < 48) return `${Math.round(hrs)}h overdue`
  return `${Math.round(hrs / 24)}d overdue`
}

function priorityBadge(p: string) {
  return { urgent: 'badge-red', high: 'badge-amber', medium: 'badge-blue', low: 'badge-green' }[p] ?? 'badge-gray'
}
</script>
