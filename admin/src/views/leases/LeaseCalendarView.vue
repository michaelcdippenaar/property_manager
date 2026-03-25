<template>
  <div class="space-y-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <button @click="prevMonth" class="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-500">
          <ChevronLeft :size="18" />
        </button>
        <h2 class="text-lg font-semibold text-gray-900 w-44 text-center">{{ monthLabel }}</h2>
        <button @click="nextMonth" class="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-500">
          <ChevronRight :size="18" />
        </button>
        <button @click="goToday" class="btn-ghost text-xs px-2.5 py-1">Today</button>
      </div>

      <!-- Filters -->
      <div class="flex items-center gap-2">
        <select v-model="filterType" class="input text-xs py-1.5 px-3 w-44">
          <option value="">All event types</option>
          <option value="contract_start">Contract Start</option>
          <option value="contract_end">Contract End</option>
          <option value="deposit_due">Deposit Due</option>
          <option value="rent_due">Rent Due</option>
          <option value="first_rent">First Rent Due</option>
          <option value="inspection_in">Move-in Inspection</option>
          <option value="inspection_out">Move-out Inspection</option>
          <option value="inspection_routine">Routine Inspection</option>
          <option value="notice_deadline">Notice Deadline</option>
          <option value="renewal_review">Renewal Review</option>
        </select>
      </div>
    </div>

    <!-- Legend -->
    <div class="flex flex-wrap items-center gap-3 text-xs text-gray-600">
      <div v-for="leg in legend" :key="leg.label" class="flex items-center gap-1.5">
        <div class="w-2.5 h-2.5 rounded-full" :style="{ background: leg.color }"></div>
        {{ leg.label }}
      </div>
    </div>

    <!-- Calendar grid -->
    <div class="card overflow-hidden">
      <!-- Day headers -->
      <div class="grid grid-cols-7 border-b border-gray-200">
        <div
          v-for="day in dayNames"
          :key="day"
          class="py-2.5 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide"
        >
          {{ day }}
        </div>
      </div>

      <!-- Weeks -->
      <div v-if="loading" class="p-10 text-center text-gray-400 text-sm animate-pulse">Loading events…</div>

      <div v-else class="grid grid-cols-7">
        <div
          v-for="(cell, idx) in calendarCells"
          :key="idx"
          class="min-h-[100px] border-b border-r border-gray-100 p-1.5 last:border-r-0"
          :class="[
            !cell.inMonth ? 'bg-gray-50/60' : 'bg-white',
            cell.isToday ? 'bg-blue-50/40' : '',
          ]"
        >
          <!-- Date number -->
          <div
            class="text-xs font-medium mb-1 w-6 h-6 flex items-center justify-center rounded-full"
            :class="cell.isToday
              ? 'bg-navy text-white'
              : cell.inMonth ? 'text-gray-700' : 'text-gray-300'"
          >
            {{ cell.day }}
          </div>

          <!-- Events -->
          <div class="space-y-0.5">
            <button
              v-for="ev in filteredCellEvents(cell)"
              :key="ev.id"
              @click="selectedEvent = ev"
              class="w-full text-left text-[10px] font-medium px-1.5 py-0.5 rounded truncate leading-4"
              :style="{ background: eventColor(ev.event_type) + '22', color: eventColor(ev.event_type) }"
              :title="ev.title + (ev.tenant_name ? ` — ${ev.tenant_name}` : '')"
            >
              {{ ev.title }}
            </button>
            <div v-if="hiddenCount(cell) > 0" class="text-[10px] text-gray-400 px-1">
              +{{ hiddenCount(cell) }} more
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Event detail panel -->
    <Teleport to="body">
      <div v-if="selectedEvent" class="fixed inset-0 z-50 flex items-center justify-center p-4" @click.self="selectedEvent = null">
        <div class="absolute inset-0 bg-black/30 backdrop-blur-sm" @click="selectedEvent = null" />
        <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
          <div class="flex items-start justify-between">
            <div>
              <div
                class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold mb-2"
                :style="{ background: eventColor(selectedEvent.event_type) + '22', color: eventColor(selectedEvent.event_type) }"
              >
                {{ eventTypeLabel(selectedEvent.event_type) }}
              </div>
              <h3 class="font-semibold text-gray-900 text-base">{{ selectedEvent.title }}</h3>
              <div class="text-sm text-gray-500 mt-0.5">{{ formatDate(selectedEvent.date) }}</div>
            </div>
            <button @click="selectedEvent = null" class="text-gray-400 hover:text-gray-600 mt-1">
              <X :size="18" />
            </button>
          </div>

          <div v-if="selectedEvent.description" class="text-sm text-gray-600 bg-gray-50 rounded-xl px-4 py-3">
            {{ selectedEvent.description }}
          </div>

          <div class="grid grid-cols-2 gap-3 text-sm">
            <div v-if="selectedEvent.tenant_name">
              <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-0.5">Tenant</div>
              <div class="font-medium text-gray-800">{{ selectedEvent.tenant_name }}</div>
            </div>
            <div v-if="selectedEvent.property_name">
              <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-0.5">Property</div>
              <div class="font-medium text-gray-800">{{ selectedEvent.property_name }}</div>
            </div>
            <div>
              <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-0.5">Status</div>
              <span :class="statusBadge(selectedEvent.status)">{{ selectedEvent.status }}</span>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import api from '../../api'
import { ChevronLeft, ChevronRight, X } from 'lucide-vue-next'

const today = new Date()
const currentYear = ref(today.getFullYear())
const currentMonth = ref(today.getMonth()) // 0-indexed
const loading = ref(false)
const events = ref<any[]>([])
const selectedEvent = ref<any>(null)
const filterType = ref('')

const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

const monthLabel = computed(() => {
  return new Date(currentYear.value, currentMonth.value, 1).toLocaleString('default', {
    month: 'long', year: 'numeric',
  })
})

function prevMonth() {
  if (currentMonth.value === 0) { currentMonth.value = 11; currentYear.value-- }
  else currentMonth.value--
}

function nextMonth() {
  if (currentMonth.value === 11) { currentMonth.value = 0; currentYear.value++ }
  else currentMonth.value++
}

function goToday() {
  currentYear.value = today.getFullYear()
  currentMonth.value = today.getMonth()
}

const calendarCells = computed(() => {
  const year = currentYear.value
  const month = currentMonth.value
  const first = new Date(year, month, 1)
  const last = new Date(year, month + 1, 0)
  const cells: { date: Date; day: number; inMonth: boolean; isToday: boolean }[] = []

  // Fill leading days from prev month
  for (let i = 0; i < first.getDay(); i++) {
    const d = new Date(year, month, -first.getDay() + i + 1)
    cells.push({ date: d, day: d.getDate(), inMonth: false, isToday: false })
  }

  // Current month days
  for (let d = 1; d <= last.getDate(); d++) {
    const date = new Date(year, month, d)
    const isToday = date.toDateString() === today.toDateString()
    cells.push({ date, day: d, inMonth: true, isToday })
  }

  // Fill trailing days
  const remaining = 42 - cells.length
  for (let i = 1; i <= remaining; i++) {
    const d = new Date(year, month + 1, i)
    cells.push({ date: d, day: d.getDate(), inMonth: false, isToday: false })
  }

  return cells
})

function dateKey(d: Date) {
  return d.toISOString().slice(0, 10)
}

const eventsByDate = computed(() => {
  const map = new Map<string, any[]>()
  for (const ev of events.value) {
    const k = ev.date
    if (!map.has(k)) map.set(k, [])
    map.get(k)!.push(ev)
  }
  return map
})

function filteredCellEvents(cell: { date: Date }) {
  const all = eventsByDate.value.get(dateKey(cell.date)) ?? []
  const filtered = filterType.value ? all.filter(e => e.event_type === filterType.value) : all
  return filtered.slice(0, 3)
}

function hiddenCount(cell: { date: Date }) {
  const all = eventsByDate.value.get(dateKey(cell.date)) ?? []
  const filtered = filterType.value ? all.filter(e => e.event_type === filterType.value) : all
  return Math.max(0, filtered.length - 3)
}

// Color map by event type
const COLOR_MAP: Record<string, string> = {
  contract_start: '#1e3a5f',
  contract_end: '#1e3a5f',
  deposit_due: '#7c3aed',
  first_rent: '#2563eb',
  rent_due: '#2563eb',
  inspection_in: '#d97706',
  inspection_out: '#d97706',
  inspection_routine: '#d97706',
  notice_deadline: '#dc2626',
  renewal_review: '#059669',
  onboarding: '#16a34a',
  custom: '#6b7280',
}

function eventColor(type: string) {
  return COLOR_MAP[type] ?? '#6b7280'
}

const legend = [
  { label: 'Contract', color: '#1e3a5f' },
  { label: 'Rent', color: '#2563eb' },
  { label: 'Deposit', color: '#7c3aed' },
  { label: 'Inspection', color: '#d97706' },
  { label: 'Notice', color: '#dc2626' },
  { label: 'Renewal', color: '#059669' },
]

const TYPE_LABELS: Record<string, string> = {
  contract_start: 'Contract Start', contract_end: 'Contract End',
  deposit_due: 'Deposit Due', first_rent: 'First Rent Due', rent_due: 'Rent Due',
  inspection_in: 'Move-in Inspection', inspection_out: 'Move-out Inspection',
  inspection_routine: 'Routine Inspection', notice_deadline: 'Notice Deadline',
  renewal_review: 'Renewal Review', onboarding: 'Onboarding', custom: 'Custom',
}

function eventTypeLabel(type: string) {
  return TYPE_LABELS[type] ?? type
}

function statusBadge(s: string) {
  return { upcoming: 'badge-gray', due: 'badge-amber', completed: 'badge-green', overdue: 'badge-red', cancelled: 'badge-gray' }[s] ?? 'badge-gray'
}

function formatDate(d: string) {
  return new Date(d + 'T00:00:00').toLocaleDateString('en-ZA', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

async function loadEvents() {
  loading.value = true
  try {
    const year = currentYear.value
    const month = currentMonth.value
    const from = new Date(year, month, 1).toISOString().slice(0, 10)
    const to = new Date(year, month + 1, 0).toISOString().slice(0, 10)
    const { data } = await api.get(`/leases/calendar/?from=${from}&to=${to}`)
    events.value = data
  } finally {
    loading.value = false
  }
}

watch([currentYear, currentMonth], loadEvents)
onMounted(loadEvents)
</script>
