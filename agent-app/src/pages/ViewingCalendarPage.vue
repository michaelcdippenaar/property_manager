<template>
  <q-page class="q-pa-md">

    <!-- Month navigation -->
    <div class="row items-center justify-between q-mb-md">
      <q-btn flat round icon="chevron_left" color="primary" @click="prevMonth" />
      <div class="text-subtitle1 text-weight-bold text-primary cursor-pointer" @click="goToday">
        {{ monthLabel }}
      </div>
      <q-btn flat round icon="chevron_right" color="primary" @click="nextMonth" />
    </div>

    <!-- Day-of-week headers -->
    <div class="row calendar-header q-mb-xs">
      <div
        v-for="d in dayHeaders"
        :key="d"
        class="col calendar-day-label text-center text-caption text-grey-6"
      >
        {{ d }}
      </div>
    </div>

    <!-- Calendar grid -->
    <div class="calendar-grid q-mb-md">
      <div
        v-for="(day, idx) in calendarDays"
        :key="idx"
        class="calendar-cell"
        :class="{
          'calendar-cell--today': day.isToday,
          'calendar-cell--outside': day.isOutside,
          'calendar-cell--selected': selectedDate === day.dateStr,
        }"
        @click="selectDay(day)"
      >
        <div class="calendar-date" :class="{ 'calendar-date--today': day.isToday }">
          {{ day.day }}
        </div>
        <!-- Viewing dots -->
        <div class="calendar-dots">
          <span
            v-for="(v, i) in day.viewings.slice(0, 3)"
            :key="i"
            class="calendar-dot"
            :style="{ background: statusDotColor(v.status) }"
          />
        </div>
      </div>
    </div>

    <!-- Selected day viewings -->
    <template v-if="selectedDate">
      <div class="text-subtitle2 text-weight-semibold text-grey-8 q-mb-sm">
        {{ selectedDateLabel }}
      </div>

      <div v-if="selectedDayViewings.length === 0" class="text-center q-py-md">
        <div class="text-caption text-grey-5">No viewings this day</div>
        <q-btn
          flat
          color="secondary"
          label="Book a viewing"
          size="sm"
          class="q-mt-xs"
          @click="bookViewingForDate"
        />
      </div>

      <q-card v-else flat class="section-card">
        <q-list separator>
          <q-item
            v-for="v in selectedDayViewings"
            :key="v.id"
            clickable
            v-ripple
            @click="$router.push(`/viewings/${v.id}`)"
          >
            <q-item-section avatar>
              <q-avatar :color="statusColor(v.status)" text-color="white" size="40px">
                <q-icon name="person" />
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-weight-medium">{{ v.prospect_name }}</q-item-label>
              <q-item-label caption>{{ v.property_name }}{{ v.unit_number ? ` · Unit ${v.unit_number}` : '' }}</q-item-label>
              <q-item-label caption class="text-grey-5">
                <q-icon name="schedule" size="12px" />
                {{ formatTime(v.scheduled_at) }} · {{ v.duration_minutes }}min
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-badge :color="statusColor(v.status)" :label="v.status" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>
    </template>

    <!-- Loading -->
    <div v-if="loading" class="row justify-center q-py-md">
      <q-spinner-dots color="primary" size="28px" />
    </div>

    <!-- iOS FAB -->
    <div class="q-mt-lg" v-if="isIos">
      <q-btn
        unelevated rounded color="secondary"
        label="Book a Viewing" icon="add"
        class="full-width"
        @click="$router.push('/viewings/new')"
      />
    </div>

  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getViewingsCalendar, type PropertyViewing } from '../services/api'
import { usePlatform } from '../composables/usePlatform'

const router = useRouter()
const { isIos } = usePlatform()

interface CalendarDay {
  day: number
  dateStr: string
  isToday: boolean
  isOutside: boolean
  viewings: PropertyViewing[]
}

const today      = new Date()
const viewYear   = ref(today.getFullYear())
const viewMonth  = ref(today.getMonth())       // 0-indexed
const viewings   = ref<PropertyViewing[]>([])
const loading    = ref(false)
const selectedDate = ref<string | null>(null)

const dayHeaders = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

const monthLabel = computed(() => {
  return new Date(viewYear.value, viewMonth.value).toLocaleDateString('en-ZA', {
    month: 'long', year: 'numeric',
  })
})

const selectedDateLabel = computed(() => {
  if (!selectedDate.value) return ''
  return new Date(selectedDate.value).toLocaleDateString('en-ZA', {
    weekday: 'long', day: 'numeric', month: 'long',
  })
})

const calendarDays = computed<CalendarDay[]>(() => {
  const days: CalendarDay[] = []
  const firstDay = new Date(viewYear.value, viewMonth.value, 1).getDay()
  const daysInMonth = new Date(viewYear.value, viewMonth.value + 1, 0).getDate()
  const prevDays = new Date(viewYear.value, viewMonth.value, 0).getDate()
  const todayStr = toDateStr(today)

  // Padding days from prev month
  for (let i = firstDay - 1; i >= 0; i--) {
    const d = prevDays - i
    const dateStr = toDateStr(new Date(viewYear.value, viewMonth.value - 1, d))
    days.push({ day: d, dateStr, isToday: false, isOutside: true, viewings: viewingsForDate(dateStr) })
  }

  // Days in current month
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = toDateStr(new Date(viewYear.value, viewMonth.value, d))
    days.push({ day: d, dateStr, isToday: dateStr === todayStr, isOutside: false, viewings: viewingsForDate(dateStr) })
  }

  // Padding days from next month
  const remaining = 42 - days.length
  for (let d = 1; d <= remaining; d++) {
    const dateStr = toDateStr(new Date(viewYear.value, viewMonth.value + 1, d))
    days.push({ day: d, dateStr, isToday: false, isOutside: true, viewings: viewingsForDate(dateStr) })
  }

  return days
})

const selectedDayViewings = computed(() => {
  if (!selectedDate.value) return []
  return viewings.value.filter((v) => v.scheduled_at.startsWith(selectedDate.value!))
})

function toDateStr(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function viewingsForDate(dateStr: string): PropertyViewing[] {
  return viewings.value.filter((v) => v.scheduled_at.startsWith(dateStr))
}

function selectDay(day: CalendarDay) {
  selectedDate.value = day.dateStr
  if (day.isOutside) {
    // Jump to that month
    const d = new Date(day.dateStr)
    viewYear.value  = d.getFullYear()
    viewMonth.value = d.getMonth()
  }
}

function prevMonth() {
  if (viewMonth.value === 0) { viewYear.value--; viewMonth.value = 11 }
  else viewMonth.value--
}

function nextMonth() {
  if (viewMonth.value === 11) { viewYear.value++; viewMonth.value = 0 }
  else viewMonth.value++
}

function goToday() {
  viewYear.value  = today.getFullYear()
  viewMonth.value = today.getMonth()
  selectedDate.value = toDateStr(today)
}

function statusColor(status: string) {
  const m: Record<string, string> = { scheduled: 'info', confirmed: 'primary', completed: 'positive', cancelled: 'negative', converted: 'secondary' }
  return m[status] || 'grey'
}

function statusDotColor(status: string) {
  const m: Record<string, string> = { scheduled: '#31CCEC', confirmed: '#2B2D6E', completed: '#21BA45', cancelled: '#DB2828', converted: '#FF3D7F' }
  return m[status] || '#9e9e9e'
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' })
}

function bookViewingForDate() {
  void router.push('/viewings/new')
}

async function loadViewings() {
  loading.value = true
  const from = toDateStr(new Date(viewYear.value, viewMonth.value - 1, 1))
  const to   = toDateStr(new Date(viewYear.value, viewMonth.value + 2, 0))
  try {
    viewings.value = await getViewingsCalendar(from, to)
  } finally {
    loading.value = false
  }
}

// Reload when month changes
watch([viewYear, viewMonth], () => void loadViewings())

onMounted(() => {
  selectedDate.value = toDateStr(today)
  void loadViewings()
})
</script>

<style scoped lang="scss">
.calendar-header {
  gap: 0;
}

.calendar-day-label {
  flex: 1;
  padding: 4px 0;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}

.calendar-cell {
  aspect-ratio: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  padding: 4px 2px 2px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;

  &:active { background: rgba(43,45,110,0.08); }

  &--outside { opacity: 0.3; }

  &--selected {
    background: rgba(43,45,110,0.1);
  }

  &--today .calendar-date--today {
    background: #2B2D6E;
    color: white;
    border-radius: 50%;
    width: 26px;
    height: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
  }
}

.calendar-date {
  font-size: 13px;
  line-height: 26px;
  min-width: 26px;
  text-align: center;
}

.calendar-dots {
  display: flex;
  gap: 2px;
  margin-top: 2px;
}

.calendar-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
}

.section-card {
  border-radius: 12px;
  border: 1px solid rgba(0,0,0,0.08);
  overflow: hidden;
}
</style>
