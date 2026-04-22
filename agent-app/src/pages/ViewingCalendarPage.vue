<template>
  <q-page class="q-pa-md">

    <!-- Month navigation -->
    <div class="row items-center justify-between q-mb-md">
      <q-btn flat round icon="chevron_left" color="primary" aria-label="Previous month" @click="prevMonth" />
      <div class="text-subtitle1 text-weight-bold text-primary cursor-pointer" @click="goToday">
        {{ monthLabel }}
      </div>
      <q-btn flat round icon="chevron_right" color="primary" aria-label="Next month" @click="nextMonth" />
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

    <!-- Calendar grid (with inline loading overlay) -->
    <div class="calendar-grid-wrap q-mb-md">
      <transition name="fade">
        <div v-if="loading" class="calendar-loading-overlay">
          <q-spinner-dots color="primary" :size="SPINNER_SIZE_INLINE" />
        </div>
      </transition>
    <div class="calendar-grid" :class="{ 'calendar-grid--loading': loading }">
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
            v-for="(v, i) in day.viewings.slice(0, 2)"
            :key="`v${i}`"
            class="calendar-dot"
            :style="{ background: statusDotColor(v.status) }"
          />
          <!-- Lease event dots: green = start, orange = end -->
          <span
            v-for="(e, i) in day.leaseEvents.slice(0, 2)"
            :key="`l${i}`"
            class="calendar-dot"
            :style="{ background: e.type === 'start' ? 'var(--q-positive)' : 'var(--q-warning)' }"
          />
        </div>
      </div>
    </div>
    </div>

    <!-- Selected day viewings -->
    <template v-if="selectedDate">
      <div class="text-subtitle2 text-weight-semibold text-grey-8 q-mb-sm">
        {{ selectedDateLabel }}
      </div>

      <div v-if="selectedDayViewings.length === 0 && selectedDayLeaseEvents.length === 0" class="text-center q-py-md">
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

      <template v-else>
        <!-- Lease events for selected day -->
        <q-card v-if="selectedDayLeaseEvents.length > 0" flat class="section-card q-mb-sm">
          <q-list separator>
            <q-item v-for="(e, i) in selectedDayLeaseEvents" :key="i">
              <q-item-section avatar>
                <q-avatar :color="e.type === 'start' ? 'positive' : 'warning'" text-color="white" :size="AVATAR_LIST">
                  <q-icon :name="e.type === 'start' ? 'login' : 'logout'" />
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-medium">{{ e.label }}</q-item-label>
                <q-item-label caption>Lease {{ e.type === 'start' ? 'commences' : 'expires' }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge :color="e.type === 'start' ? 'positive' : 'warning'" :label="e.type === 'start' ? 'Start' : 'End'" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>

        <!-- Viewings for selected day -->
        <q-card v-if="selectedDayViewings.length > 0" flat class="section-card">
          <q-list separator>
            <q-item
              v-for="v in selectedDayViewings"
              :key="v.id"
              clickable
              v-ripple
              @click="$router.push(`/viewings/${v.id}`)"
            >
              <q-item-section avatar>
                <q-avatar :color="statusColor(v.status)" text-color="white" :size="AVATAR_LIST">
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
                <q-badge :color="statusColor(v.status)" :label="fmtLabel(v.status)" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </template>
    </template>

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
import { useQuasar } from 'quasar'
import { getViewingsCalendar, listLeases, type PropertyViewing, type AgentLease } from '../services/api'
import { usePlatform } from '../composables/usePlatform'
import { statusColor, statusDotColor, formatTime, fmtLabel } from '../utils/formatters'
import { SPINNER_SIZE_INLINE, AVATAR_LIST } from '../utils/designTokens'

const router = useRouter()
const $q     = useQuasar()
const { isIos } = usePlatform()

interface CalendarDay {
  day: number
  dateStr: string
  isToday: boolean
  isOutside: boolean
  viewings: PropertyViewing[]
  leaseEvents: { label: string; type: 'start' | 'end' }[]
}

const today      = new Date()
const viewYear   = ref(today.getFullYear())
const viewMonth  = ref(today.getMonth())       // 0-indexed
const viewings   = ref<PropertyViewing[]>([])
const leases     = ref<AgentLease[]>([])
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
    days.push({ day: d, dateStr, isToday: false, isOutside: true, viewings: viewingsForDate(dateStr), leaseEvents: leaseEventsForDate(dateStr) })
  }

  // Days in current month
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = toDateStr(new Date(viewYear.value, viewMonth.value, d))
    days.push({ day: d, dateStr, isToday: dateStr === todayStr, isOutside: false, viewings: viewingsForDate(dateStr), leaseEvents: leaseEventsForDate(dateStr) })
  }

  // Padding days from next month
  const remaining = 42 - days.length
  for (let d = 1; d <= remaining; d++) {
    const dateStr = toDateStr(new Date(viewYear.value, viewMonth.value + 1, d))
    days.push({ day: d, dateStr, isToday: false, isOutside: true, viewings: viewingsForDate(dateStr), leaseEvents: leaseEventsForDate(dateStr) })
  }

  return days
})

const selectedDayViewings = computed(() => {
  if (!selectedDate.value) return []
  return viewings.value.filter((v) => v.scheduled_at.startsWith(selectedDate.value!))
})

const selectedDayLeaseEvents = computed(() => {
  if (!selectedDate.value) return []
  return leaseEventsForDate(selectedDate.value)
})

function toDateStr(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function viewingsForDate(dateStr: string): PropertyViewing[] {
  return viewings.value.filter((v) => v.scheduled_at.startsWith(dateStr))
}

function leaseEventsForDate(dateStr: string) {
  const events: { label: string; type: 'start' | 'end' }[] = []
  for (const l of leases.value) {
    if (l.start_date === dateStr) events.push({ label: `${l.unit_label} starts`, type: 'start' })
    if (l.end_date   === dateStr) events.push({ label: `${l.unit_label} ends`,   type: 'end'   })
  }
  return events
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

function bookViewingForDate() {
  void router.push('/viewings/new')
}

async function loadViewings() {
  loading.value = true
  const from = toDateStr(new Date(viewYear.value, viewMonth.value - 1, 1))
  const to   = toDateStr(new Date(viewYear.value, viewMonth.value + 2, 0))
  try {
    const [calendarViewings, leasesResp] = await Promise.all([
      getViewingsCalendar(from, to),
      listLeases({ status: 'active,pending' }).catch(() => ({ results: [] })),
    ])
    viewings.value = calendarViewings
    leases.value   = leasesResp.results
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to load calendar data. Pull down to retry.', icon: 'error' })
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
.calendar-grid-wrap {
  position: relative;
}

.calendar-loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.7);
  z-index: 1;
  border-radius: 8px;
}

.fade-enter-active,
.fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from,
.fade-leave-to     { opacity: 0; }

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

  &:active { background: rgba($primary, 0.08); }

  &--outside { opacity: 0.3; }

  &--selected {
    background: rgba($primary, 0.1);
  }

  &--today .calendar-date--today {
    background: $primary;
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

</style>
