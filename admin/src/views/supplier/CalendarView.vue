<template>
  <div class="space-y-5">
    <div class="flex items-center justify-end gap-2">
      <button @click="prevMonth" class="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100"><ChevronLeft :size="18" /></button>
      <span class="text-sm font-medium text-gray-800 min-w-[120px] text-center">{{ monthLabel }}</span>
      <button @click="nextMonth" class="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100"><ChevronRight :size="18" /></button>
    </div>

    <!-- Calendar grid -->
    <div class="card overflow-hidden">
      <!-- Day headers -->
      <div class="grid grid-cols-7 border-b border-gray-200">
        <div v-for="d in dayNames" :key="d" class="px-2 py-2 text-center text-xs font-medium text-gray-500">
          {{ d }}
        </div>
      </div>
      <!-- Weeks -->
      <div v-for="(week, wi) in weeks" :key="wi" class="grid grid-cols-7 border-b border-gray-100 last:border-0">
        <div v-for="(day, di) in week" :key="di"
          class="min-h-[80px] p-1.5 border-r border-gray-100 last:border-0"
          :class="day.isCurrentMonth ? 'bg-white' : 'bg-gray-50'">
          <div class="text-xs text-right" :class="day.isToday ? 'text-white bg-navy rounded-full w-5 h-5 flex items-center justify-center ml-auto' : day.isCurrentMonth ? 'text-gray-700' : 'text-gray-300'">
            {{ day.date }}
          </div>
          <div v-for="job in day.jobs" :key="job.id"
            class="mt-0.5 px-1.5 py-0.5 rounded text-micro font-medium truncate cursor-pointer"
            :class="job.status === 'resolved' || job.status === 'closed' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'"
            :title="`${job.title} — ${job.property_name} — R${job.amount}`">
            {{ job.title }}
          </div>
        </div>
      </div>
    </div>

    <!-- Legend -->
    <div class="flex items-center gap-4 text-xs text-gray-500">
      <span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-blue-100"></span> In progress</span>
      <span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-green-100"></span> Completed</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'

const currentYear = ref(new Date().getFullYear())
const currentMonth = ref(new Date().getMonth()) // 0-indexed
const calendarItems = ref<any[]>([])
const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const monthLabel = computed(() => {
  return new Date(currentYear.value, currentMonth.value).toLocaleDateString('en-ZA', { month: 'long', year: 'numeric' })
})

onMounted(() => loadCalendar())

async function loadCalendar() {
  try {
    const { data } = await api.get('/maintenance/supplier/calendar/')
    calendarItems.value = data
  } catch { /* ignore */ }
}

function prevMonth() {
  if (currentMonth.value === 0) { currentMonth.value = 11; currentYear.value-- }
  else currentMonth.value--
}

function nextMonth() {
  if (currentMonth.value === 11) { currentMonth.value = 0; currentYear.value++ }
  else currentMonth.value++
}

const weeks = computed(() => {
  const year = currentYear.value
  const month = currentMonth.value
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const today = new Date()

  // Start from Monday before the first day
  let start = new Date(firstDay)
  const dayOfWeek = start.getDay() || 7 // Monday=1, Sunday=7
  start.setDate(start.getDate() - (dayOfWeek - 1))

  const result: any[][] = []
  let current = new Date(start)

  for (let w = 0; w < 6; w++) {
    const week: any[] = []
    for (let d = 0; d < 7; d++) {
      const dateStr = current.toISOString().split('T')[0]
      const isCurrentMonth = current.getMonth() === month
      const isToday = current.toDateString() === today.toDateString()

      // Find jobs that overlap with this day
      const dayJobs = calendarItems.value.filter(item => {
        return dateStr >= item.start_date && dateStr <= item.end_date
      })

      week.push({
        date: current.getDate(),
        isCurrentMonth,
        isToday,
        jobs: dayJobs.slice(0, 2), // max 2 per cell
      })
      current.setDate(current.getDate() + 1)
    }
    result.push(week)
    if (current.getMonth() !== month && current.getDate() > 7) break
  }

  return result
})
</script>
