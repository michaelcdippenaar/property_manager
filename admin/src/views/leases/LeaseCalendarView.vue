<template>
  <div class="space-y-5">
    <PageHeader
      title="Lease Calendar"
      subtitle="Track rent due dates, lease start/end, inspections, and key deadlines across all properties."
      :crumbs="[{ label: 'Dashboard', to: '/' }, { label: 'Leases', to: '/leases' }, { label: 'Calendar' }]"
    >
      <template #actions>
        <div class="flex items-center gap-1 flex-shrink-0">
          <button @click="prevMonth" class="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100">
            <ChevronLeft :size="18" />
          </button>
          <span class="text-sm font-semibold text-gray-800 min-w-[140px] text-center">{{ monthLabel }}</span>
          <button @click="nextMonth" class="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100">
            <ChevronRight :size="18" />
          </button>
        </div>
      </template>
    </PageHeader>

    <!-- Legend + Filters (combined) -->
    <div class="flex items-center gap-2 flex-wrap">
      <button
        v-for="f in typeFilters"
        :key="f.value"
        @click="toggleFilter(f.value)"
        class="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-xs font-medium transition-colors border"
        :class="activeFilters.has(f.value)
          ? `${f.activeClass} border-transparent`
          : 'bg-white text-gray-400 border-gray-200 hover:border-gray-300 line-through'"
      >
        <span class="w-2 h-2 rounded-full flex-shrink-0" :class="f.dotClass"></span>
        {{ f.label }}
      </button>
    </div>

    <!-- Calendar grid -->
    <div class="card overflow-hidden">
      <div class="grid grid-cols-7 border-b border-gray-200 bg-gray-50">
        <div v-for="d in dayNames" :key="d" class="px-2 py-2.5 text-center text-xs font-medium text-gray-500">
          {{ d }}
        </div>
      </div>
      <div v-for="(week, wi) in weeks" :key="wi" class="grid grid-cols-7 border-b border-gray-100 last:border-0">
        <div
          v-for="(day, di) in week"
          :key="di"
          class="min-h-[100px] p-1.5 border-r border-gray-100 last:border-0 cursor-pointer hover:bg-gray-50/50 transition-colors"
          :class="day.isCurrentMonth ? 'bg-white' : 'bg-gray-50/60'"
          @click="selectDay(day)"
        >
          <div
            class="text-xs text-right mb-1"
            :class="day.isToday
              ? 'text-white bg-navy rounded-full w-6 h-6 flex items-center justify-center ml-auto text-micro font-bold'
              : day.isCurrentMonth ? 'text-gray-700' : 'text-gray-300'"
          >
            {{ day.date }}
          </div>
          <div v-for="evt in day.events.slice(0, 3)" :key="evt.id"
            class="mb-0.5 px-1.5 py-0.5 rounded text-micro font-medium truncate"
            :class="eventColor(evt.event_type)"
            :title="evt.title"
          >
            {{ evt.title }}
          </div>
          <div v-if="day.events.length > 3" class="text-micro text-gray-400 px-1">
            +{{ day.events.length - 3 }} more
          </div>
        </div>
      </div>
    </div>

    <!-- Day detail panel -->
    <BaseDrawer
      :open="!!(selectedDay && selectedDay.events.length)"
      :title="selectedDay ? new Date(currentYear, currentMonth, selectedDay.date).toLocaleDateString('en-ZA', { weekday: 'long', day: 'numeric', month: 'long' }) : ''"
      @close="selectedDay = null"
    >
      <div v-if="selectedDay" class="p-6 space-y-4">
        <div v-for="evt in selectedDay.events" :key="evt.id"
          class="p-3 rounded-lg border border-gray-200 space-y-2">
          <div class="flex items-start justify-between gap-2">
            <div>
              <span :class="eventColor(evt.event_type)" class="text-xs px-1.5 py-0.5 rounded">
                {{ evt.type_label }}
              </span>
              <div class="font-medium text-gray-900 text-sm mt-1">{{ evt.title }}</div>
            </div>
            <span :class="statusBadge(evt.status)" class="text-micro shrink-0">{{ evt.status }}</span>
          </div>
          <p v-if="evt.description" class="text-xs text-gray-500">{{ evt.description }}</p>
          <div class="text-xs text-gray-400">
            {{ evt.property_name }} — {{ evt.lease_label }}
          </div>
          <button
            v-if="evt.status !== 'completed' && evt.status !== 'cancelled'"
            @click="markComplete(evt)"
            class="text-xs text-navy hover:underline"
          >
            Mark complete
          </button>
        </div>
      </div>
    </BaseDrawer>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import api from '../../api'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import BaseDrawer from '../../components/BaseDrawer.vue'
import PageHeader from '../../components/PageHeader.vue'

const currentYear = ref(new Date().getFullYear())
const currentMonth = ref(new Date().getMonth())
const events = ref<any[]>([])
const selectedDay = ref<any | null>(null)
const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const activeFilters = ref(new Set<string>([
  'contract_start', 'contract_end', 'deposit_due', 'first_rent', 'rent_due',
  'inspection_in', 'inspection_out', 'inspection_routine',
  'notice_deadline', 'renewal_review', 'custom',
]))

const typeFilters = [
  { value: 'rent_due', label: 'Rent', activeClass: 'bg-info-100 text-info-700', dotClass: 'bg-info-500' },
  { value: 'inspection_routine', label: 'Inspections', activeClass: 'bg-warning-100 text-warning-700', dotClass: 'bg-warning-500' },
  { value: 'contract_start', label: 'Start', activeClass: 'bg-navy/80 text-white', dotClass: 'bg-navy' },
  { value: 'contract_end', label: 'End', activeClass: 'bg-navy/80 text-white', dotClass: 'bg-navy' },
  { value: 'deposit_due', label: 'Deposit', activeClass: 'bg-success-100 text-success-700', dotClass: 'bg-success-400' },
  { value: 'notice_deadline', label: 'Notice', activeClass: 'bg-danger-100 text-danger-700', dotClass: 'bg-danger-400' },
  { value: 'renewal_review', label: 'Renewal', activeClass: 'bg-purple-100 text-purple-800', dotClass: 'bg-purple-400' },
]

const monthLabel = computed(() =>
  new Date(currentYear.value, currentMonth.value).toLocaleDateString('en-ZA', { month: 'long', year: 'numeric' })
)

onMounted(() => loadEvents())
watch([currentYear, currentMonth], () => loadEvents())

async function loadEvents() {
  const from = new Date(currentYear.value, currentMonth.value - 1, 1).toISOString().split('T')[0]
  const to = new Date(currentYear.value, currentMonth.value + 2, 0).toISOString().split('T')[0]
  try {
    const { data } = await api.get('/leases/calendar/', { params: { from, to } })
    events.value = data
  } catch { events.value = [] }
}

function prevMonth() {
  if (currentMonth.value === 0) { currentMonth.value = 11; currentYear.value-- }
  else currentMonth.value--
}

function nextMonth() {
  if (currentMonth.value === 11) { currentMonth.value = 0; currentYear.value++ }
  else currentMonth.value++
}

function toggleFilter(type: string) {
  if (activeFilters.value.has(type)) activeFilters.value.delete(type)
  else activeFilters.value.add(type)
}

function selectDay(day: any) {
  if (day.events.length) selectedDay.value = day
}

async function markComplete(evt: any) {
  try {
    await api.patch(`/leases/${evt.lease}/events/${evt.id}/`, { status: 'completed' })
    evt.status = 'completed'
  } catch { /* ignore */ }
}

const filteredEvents = computed(() =>
  events.value.filter(e => activeFilters.value.has(e.event_type))
)

const weeks = computed(() => {
  const year = currentYear.value
  const month = currentMonth.value
  const today = new Date()

  let start = new Date(year, month, 1)
  const dayOfWeek = start.getDay() || 7
  start.setDate(start.getDate() - (dayOfWeek - 1))

  const result: any[][] = []
  let current = new Date(start)

  for (let w = 0; w < 6; w++) {
    const week: any[] = []
    for (let d = 0; d < 7; d++) {
      const dateStr = current.toISOString().split('T')[0]
      const isCurrentMonth = current.getMonth() === month
      const isToday = current.toDateString() === today.toDateString()

      const dayEvents = filteredEvents.value.filter((e: any) => e.date === dateStr)

      week.push({
        date: current.getDate(),
        dateStr,
        isCurrentMonth,
        isToday,
        events: dayEvents,
      })
      current.setDate(current.getDate() + 1)
    }
    result.push(week)
    if (current.getMonth() !== month && current.getDate() > 7) break
  }

  return result
})

function eventColor(type: string) {
  return {
    contract_start: 'bg-navy/80 text-white',
    contract_end: 'bg-navy/80 text-white',
    deposit_due: 'bg-success-100 text-success-700',
    first_rent: 'bg-info-100 text-info-700',
    rent_due: 'bg-info-100 text-info-700',
    inspection_in: 'bg-warning-100 text-warning-700',
    inspection_out: 'bg-warning-100 text-warning-700',
    inspection_routine: 'bg-warning-100 text-warning-700',
    notice_deadline: 'bg-danger-100 text-danger-700',
    renewal_review: 'bg-purple-100 text-purple-800',
    custom: 'bg-gray-100 text-gray-700',
  }[type] ?? 'bg-gray-100 text-gray-700'
}

function statusBadge(s: string) {
  return {
    upcoming: 'badge-gray', due: 'badge-blue',
    completed: 'badge-green', overdue: 'badge-red', cancelled: 'badge-gray',
  }[s] ?? 'badge-gray'
}
</script>
