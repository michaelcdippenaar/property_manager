<!--
  AuditTimeline.vue

  Read-only per-entity audit event timeline.

  Usage:
    <AuditTimeline app-label="leases" model="lease" :pk="lease.id" />
    <AuditTimeline app-label="properties" model="rentalmandate" :pk="mandate.id" />
    <AuditTimeline app-label="payments" model="rentpayment" :pk="payment.id" />

  Fetches from GET /api/v1/audit/timeline/{appLabel}/{model}/{pk}/
  Returns events oldest-first (chronological) for a natural timeline read.
-->
<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import api from '../api'

interface AuditEvent {
  id: number
  actor: number | null
  actor_email: string
  actor_display: string
  action: string
  content_type: number | null
  content_type_label: string | null
  object_id: number | null
  target_repr: string
  before_snapshot: Record<string, unknown> | null
  after_snapshot: Record<string, unknown> | null
  ip_address: string | null
  user_agent: string
  timestamp: string
  prev_hash: string
  self_hash: string
  retention_years: number
}

const props = defineProps<{
  appLabel: string
  model: string
  pk: number
}>()

const events = ref<AuditEvent[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const expanded = ref<Set<number>>(new Set())

async function fetchTimeline() {
  if (!props.pk) return
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get<AuditEvent[]>(
      `/audit/timeline/${props.appLabel}/${props.model}/${props.pk}/`
    )
    events.value = data
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load audit timeline'
  } finally {
    loading.value = false
  }
}

function toggleExpand(id: number) {
  if (expanded.value.has(id)) {
    expanded.value.delete(id)
  } else {
    expanded.value.add(id)
  }
}

function formatTimestamp(ts: string): string {
  const d = new Date(ts)
  return d.toLocaleString('en-ZA', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Map action codes to human-readable labels */
function actionLabel(action: string): string {
  const labels: Record<string, string> = {
    'audit.genesis': 'Chain Genesis',
    'lease.created': 'Lease Created',
    'lease.updated': 'Lease Updated',
    'mandate.created': 'Mandate Created',
    'mandate.updated': 'Mandate Updated',
    'signing.created': 'Signing Session Created',
    'signing.updated': 'Signing Session Updated',
    'payment.created': 'Payment Recorded',
    'payment.updated': 'Payment Updated',
    'user.role_changed': 'User Role Changed',
  }
  return labels[action] ?? action
}

/** Colour tone for the action badge */
function actionTone(action: string): string {
  if (action.endsWith('.created')) return 'text-emerald-700 bg-emerald-50'
  if (action.endsWith('.updated')) return 'text-blue-700 bg-blue-50'
  if (action.includes('role_changed')) return 'text-amber-700 bg-amber-50'
  if (action.includes('genesis')) return 'text-slate-600 bg-slate-100'
  return 'text-slate-700 bg-slate-50'
}

// Computed diff: only show changed fields in snapshots
function changedFields(event: AuditEvent): { field: string; before: unknown; after: unknown }[] {
  if (!event.before_snapshot || !event.after_snapshot) return []
  const before = event.before_snapshot
  const after = event.after_snapshot
  const allKeys = new Set([...Object.keys(before), ...Object.keys(after)])
  const changes: { field: string; before: unknown; after: unknown }[] = []
  for (const key of allKeys) {
    if (JSON.stringify(before[key]) !== JSON.stringify(after[key])) {
      changes.push({ field: key, before: before[key], after: after[key] })
    }
  }
  return changes
}

watch(() => props.pk, fetchTimeline, { immediate: false })
onMounted(fetchTimeline)
</script>

<template>
  <div class="audit-timeline">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-sm font-semibold text-navy-800 uppercase tracking-wide">
        Audit Trail
      </h3>
      <button
        class="text-xs text-slate-500 hover:text-slate-700 underline"
        @click="fetchTimeline"
      >
        Refresh
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center gap-2 py-6 text-slate-400 text-sm">
      <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
      </svg>
      Loading audit events…
    </div>

    <!-- Error -->
    <div v-else-if="error" class="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
      {{ error }}
    </div>

    <!-- Empty -->
    <div v-else-if="events.length === 0" class="py-6 text-center text-slate-400 text-sm">
      No audit events recorded yet.
    </div>

    <!-- Timeline -->
    <ol v-else class="relative border-l border-slate-200 space-y-0">
      <li
        v-for="event in events"
        :key="event.id"
        class="ml-4 pb-6 last:pb-0"
      >
        <!-- Dot -->
        <span
          class="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full border-2 border-white"
          :class="event.action.includes('created') ? 'bg-emerald-500' : event.action.includes('genesis') ? 'bg-slate-400' : 'bg-blue-500'"
        />

        <!-- Event card -->
        <div class="rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden">
          <!-- Top row -->
          <div class="flex items-start justify-between gap-3 px-4 py-3">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span
                  class="inline-flex items-center rounded px-2 py-0.5 text-xs font-medium"
                  :class="actionTone(event.action)"
                >
                  {{ actionLabel(event.action) }}
                </span>
                <span class="text-xs text-slate-400 font-mono">{{ event.action }}</span>
              </div>
              <div class="mt-1 text-sm text-slate-600 truncate">{{ event.target_repr }}</div>
            </div>
            <div class="text-right flex-shrink-0">
              <div class="text-xs text-slate-500">{{ formatTimestamp(event.timestamp) }}</div>
              <div class="text-xs text-slate-400 mt-0.5">by {{ event.actor_display }}</div>
            </div>
          </div>

          <!-- Changed fields (always show if present) -->
          <template v-if="event.before_snapshot && event.after_snapshot">
            <div class="border-t border-slate-100 px-4 py-2">
              <div class="text-xs font-medium text-slate-500 mb-1.5">Changed fields</div>
              <table class="w-full text-xs">
                <thead>
                  <tr class="text-slate-400">
                    <th class="text-left font-medium w-1/3 pr-2 pb-1">Field</th>
                    <th class="text-left font-medium w-1/3 pr-2 pb-1">Before</th>
                    <th class="text-left font-medium w-1/3 pb-1">After</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="change in changedFields(event)"
                    :key="change.field"
                    class="border-t border-slate-50"
                  >
                    <td class="font-mono text-slate-500 pr-2 py-1 truncate max-w-0">{{ change.field }}</td>
                    <td class="text-red-600 pr-2 py-1 truncate max-w-0 font-mono">
                      {{ change.before === null || change.before === undefined ? '—' : String(change.before) }}
                    </td>
                    <td class="text-emerald-700 py-1 truncate max-w-0 font-mono">
                      {{ change.after === null || change.after === undefined ? '—' : String(change.after) }}
                    </td>
                  </tr>
                  <tr v-if="changedFields(event).length === 0">
                    <td colspan="3" class="text-slate-400 italic py-1">No field changes detected</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>

          <!-- Expand/collapse hash detail -->
          <div class="border-t border-slate-100">
            <button
              class="w-full text-left px-4 py-2 text-xs text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors flex items-center justify-between"
              @click="toggleExpand(event.id)"
            >
              <span>Hash details</span>
              <span class="font-mono text-slate-300 truncate max-w-xs ml-2">{{ event.self_hash.slice(0, 12) }}…</span>
              <svg
                class="h-3 w-3 ml-2 transition-transform"
                :class="expanded.has(event.id) ? 'rotate-180' : ''"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.1 1.02l-4.25 4.5a.75.75 0 01-1.1 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd" />
              </svg>
            </button>
            <div v-if="expanded.has(event.id)" class="px-4 pb-3 space-y-1">
              <div class="flex gap-2 text-xs">
                <span class="text-slate-400 w-24 flex-shrink-0">prev_hash</span>
                <span class="font-mono text-slate-500 break-all">{{ event.prev_hash || '(genesis)' }}</span>
              </div>
              <div class="flex gap-2 text-xs">
                <span class="text-slate-400 w-24 flex-shrink-0">self_hash</span>
                <span class="font-mono text-slate-500 break-all">{{ event.self_hash }}</span>
              </div>
              <div v-if="event.ip_address" class="flex gap-2 text-xs">
                <span class="text-slate-400 w-24 flex-shrink-0">IP</span>
                <span class="font-mono text-slate-500">{{ event.ip_address }}</span>
              </div>
            </div>
          </div>
        </div>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.audit-timeline {
  font-family: inherit;
}
</style>
