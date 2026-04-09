<template>
  <div class="flex flex-col h-full overflow-hidden bg-surface" name="LeaseView">
    <AppHeader title="My Lease" subtitle="Your rental agreement" />

    <div class="scroll-page page-with-tab-bar px-4 pt-4 pb-6 space-y-5">

      <!-- Loading skeleton -->
      <div v-if="loading" class="space-y-3">
        <div v-for="i in 5" :key="i" class="h-14 bg-white rounded-2xl animate-pulse" />
      </div>

      <!-- No lease state -->
      <div v-else-if="!lease" class="flex flex-col items-center justify-center pt-24 text-center">
        <div class="w-16 h-16 bg-navy/5 rounded-2xl flex items-center justify-center mb-4">
          <FileText :size="28" class="text-navy/30" />
        </div>
        <p class="font-semibold text-gray-700">No active lease</p>
        <p class="text-sm text-gray-400 mt-1">Contact your agent to get started</p>
      </div>

      <template v-else>

        <!-- ── Signing CTA ──────────────────────────────────────────── -->
        <div v-if="needsSigning" class="list-section touchable" @click="router.push({ name: 'signing' })">
          <div class="list-row gap-4">
            <div class="list-row-icon bg-accent/10">
              <FileSignature :size="20" class="text-accent" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-semibold text-gray-900">Lease ready to sign</p>
              <p class="text-xs text-gray-500 mt-0.5">Tap to review and sign your agreement</p>
            </div>
            <ChevronRight :size="18" class="text-gray-300 flex-shrink-0" />
          </div>
        </div>

        <!-- ── Lease details ────────────────────────────────────────── -->
        <div>
          <p class="list-section-header px-1">Lease Details</p>
          <div class="list-section">
            <!-- Status pill -->
            <div class="list-row">
              <div class="list-row-icon" :class="statusIconBg">
                <CircleDot :size="18" :class="statusIconColor" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs text-gray-500">Status</p>
                <p class="text-sm font-semibold capitalize" :class="statusIconColor">{{ lease.status }}</p>
              </div>
              <span v-if="daysRemaining !== null" class="text-xs text-gray-400">{{ daysRemaining }}d left</span>
            </div>

            <!-- Property -->
            <div class="list-row">
              <div class="list-row-icon bg-navy/8">
                <Home :size="18" class="text-navy" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs text-gray-500">Property</p>
                <p class="text-sm font-medium text-gray-900 truncate">{{ lease.unit_label }}</p>
              </div>
            </div>

            <!-- Rent -->
            <div class="list-row">
              <div class="list-row-icon bg-green-50">
                <Banknote :size="18" class="text-green-600" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs text-gray-500">Monthly Rent</p>
                <p class="text-sm font-semibold text-gray-900">{{ formatCurrency(lease.monthly_rent) }}</p>
              </div>
              <span class="text-xs text-gray-400">due {{ ordinal(lease.rent_due_day) }}</span>
            </div>

            <!-- Deposit -->
            <div class="list-row">
              <div class="list-row-icon bg-blue-50">
                <Wallet :size="18" class="text-blue-500" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs text-gray-500">Deposit Held</p>
                <p class="text-sm font-medium text-gray-900">{{ formatCurrency(lease.deposit) }}</p>
              </div>
            </div>

            <!-- Period -->
            <div class="list-row">
              <div class="list-row-icon bg-purple-50">
                <CalendarDays :size="18" class="text-purple-500" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs text-gray-500">Lease Period</p>
                <p class="text-sm font-medium text-gray-900">{{ formatDate(lease.start_date) }} – {{ formatDate(lease.end_date) }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- ── Calendar ────────────────────────────────────────────── -->
        <div>
          <p class="list-section-header px-1">Upcoming Dates</p>
          <div class="bg-white rounded-2xl overflow-hidden border border-black/[0.06]">
            <!-- Month nav -->
            <div class="flex items-center justify-between px-4 pt-4 pb-2">
              <button class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors" @click="prevMonth">
                <ChevronLeft :size="17" class="text-navy" />
              </button>
              <p class="text-sm font-semibold text-navy cursor-pointer select-none" @click="goToday">{{ monthLabel }}</p>
              <button class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors" @click="nextMonth">
                <ChevronRight :size="17" class="text-navy" />
              </button>
            </div>

            <!-- Day-of-week headers -->
            <div class="grid grid-cols-7 px-3 mb-1">
              <div v-for="d in dayHeaders" :key="d" class="text-center text-[10px] text-gray-400 font-medium pb-1">{{ d }}</div>
            </div>

            <!-- Calendar grid -->
            <div class="grid grid-cols-7 px-3 pb-4 gap-y-1">
              <div
                v-for="(day, i) in calendarDays"
                :key="i"
                class="flex flex-col items-center justify-start pt-1 rounded-lg aspect-square"
                :class="dayCellClass(day)"
              >
                <span class="text-[11px] leading-5 font-medium" :class="dayNumberClass(day)">{{ day.day }}</span>
                <div v-if="day.dots.length" class="flex gap-0.5 mt-0.5">
                  <span
                    v-for="(dot, di) in day.dots"
                    :key="di"
                    class="w-[5px] h-[5px] rounded-full flex-shrink-0"
                    :style="{ background: dot }"
                  />
                </div>
              </div>
            </div>

            <!-- Legend -->
            <div class="flex gap-5 px-4 pb-4 text-[10px] text-gray-500">
              <div class="flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-accent flex-shrink-0" />
                Rent due
              </div>
              <div class="flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-navy flex-shrink-0" />
                Lease start / end
              </div>
            </div>
          </div>
        </div>

        <!-- ── Utilities ───────────────────────────────────────────── -->
        <div>
          <p class="list-section-header px-1">Utilities</p>
          <div class="list-section">
            <div class="list-row">
              <div class="list-row-icon bg-blue-50">
                <Droplets :size="18" class="text-blue-500" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs text-gray-500">Water</p>
                <p class="text-sm font-medium text-gray-900">{{ lease.water_included ? 'Included' : 'Separate meter' }}</p>
              </div>
              <span v-if="lease.water_included && lease.water_limit_litres" class="text-xs text-gray-400">
                {{ Number(lease.water_limit_litres).toLocaleString('en-ZA') }}L / mo
              </span>
            </div>
            <div class="list-row">
              <div class="list-row-icon bg-yellow-50">
                <Zap :size="18" class="text-yellow-500" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs text-gray-500">Electricity</p>
                <p class="text-sm font-medium text-gray-900">{{ lease.electricity_prepaid ? 'Prepaid meter' : 'Municipality account' }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- ── Unit info ───────────────────────────────────────────── -->
        <div v-if="infoItems.length > 0">
          <p class="list-section-header px-1">Unit Info</p>
          <div class="list-section">
            <div
              v-for="item in infoItems"
              :key="item.id"
              class="list-row"
              :class="isSensitive(item) ? 'touchable' : ''"
              @click="isSensitive(item) ? toggleReveal(item.id) : undefined"
            >
              <div class="list-row-icon" :class="iconBg(item.icon_type)">
                <component :is="iconFor(item.icon_type)" :size="18" :class="iconColor(item.icon_type)" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs text-gray-500">{{ item.label }}</p>
                <p class="text-sm font-medium text-gray-900 font-mono">
                  {{ revealed.has(item.id) ? item.value : maskedValue(item) }}
                </p>
              </div>
              <Eye v-if="isSensitive(item) && !revealed.has(item.id)" :size="16" class="text-gray-300 flex-shrink-0" />
              <EyeOff v-else-if="isSensitive(item) && revealed.has(item.id)" :size="16" class="text-gray-300 flex-shrink-0" />
            </div>
          </div>
        </div>

      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Home, Banknote, Wallet, CalendarDays, CircleDot,
  FileText, FileSignature, ChevronRight, ChevronLeft,
  Droplets, Zap, Wifi, Lock, Shield, Flame, Building2,
  Eye, EyeOff,
} from 'lucide-vue-next'
import AppHeader from '../../components/AppHeader.vue'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth   = useAuthStore()

// ── State ──────────────────────────────────────────────────────────────
const loading    = ref(true)
const lease      = ref<any | null>(null)
const needsSigning = ref(false)
const infoItems  = ref<any[]>([])
const revealed   = ref(new Set<number>())

// ── Lease helpers ──────────────────────────────────────────────────────
function formatCurrency(val: string | number) {
  return `R ${Number(val).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}`
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' })
}

function ordinal(n: number) {
  const s = ['th', 'st', 'nd', 'rd']
  const v = n % 100
  return n + (s[(v - 20) % 10] || s[v] || s[0])
}

const daysRemaining = computed(() => {
  if (!lease.value?.end_date) return null
  const diff = Math.ceil((new Date(lease.value.end_date).getTime() - Date.now()) / 86400000)
  return diff > 0 ? diff : null
})

const statusIconBg = computed(() => ({
  active:     'bg-green-50',
  pending:    'bg-yellow-50',
  expired:    'bg-gray-100',
  terminated: 'bg-red-50',
}[lease.value?.status] ?? 'bg-gray-100'))

const statusIconColor = computed(() => ({
  active:     'text-green-600',
  pending:    'text-yellow-600',
  expired:    'text-gray-400',
  terminated: 'text-red-500',
}[lease.value?.status] ?? 'text-gray-400'))

// ── Calendar ───────────────────────────────────────────────────────────
const today     = new Date()
const viewYear  = ref(today.getFullYear())
const viewMonth = ref(today.getMonth())

const dayHeaders = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

const monthLabel = computed(() =>
  new Date(viewYear.value, viewMonth.value).toLocaleDateString('en-ZA', { month: 'long', year: 'numeric' }),
)

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
}

interface CalDay { day: number; dateStr: string; isToday: boolean; isOutside: boolean; dots: string[] }

const calendarDays = computed<CalDay[]>(() => {
  const days: CalDay[] = []
  const firstDow   = new Date(viewYear.value, viewMonth.value, 1).getDay()
  const daysInMonth = new Date(viewYear.value, viewMonth.value + 1, 0).getDate()
  const prevDays   = new Date(viewYear.value, viewMonth.value, 0).getDate()
  const todayStr   = today.toISOString().slice(0, 10)

  const makeDay = (y: number, m: number, d: number, outside: boolean): CalDay => {
    const dateStr = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    return { day: d, dateStr, isToday: dateStr === todayStr, isOutside: outside, dots: dotsForDate(dateStr) }
  }

  // Prev-month padding
  for (let i = firstDow - 1; i >= 0; i--)
    days.push(makeDay(viewYear.value, viewMonth.value - 1, prevDays - i, true))

  // Current month
  for (let d = 1; d <= daysInMonth; d++)
    days.push(makeDay(viewYear.value, viewMonth.value, d, false))

  // Next-month padding
  const remaining = 42 - days.length
  for (let d = 1; d <= remaining; d++)
    days.push(makeDay(viewYear.value, viewMonth.value + 1, d, true))

  return days
})

function dotsForDate(dateStr: string): string[] {
  if (!lease.value) return []
  const dots: string[] = []
  const [, m, d] = dateStr.split('-').map(Number)

  // Rent due: accent pink dot on rent_due_day of every month
  if (d === (lease.value.rent_due_day ?? 1)) {
    dots.push('#FF3D7F')
  }

  // Lease start / end: navy dot
  if (dateStr === lease.value.start_date || dateStr === lease.value.end_date) {
    dots.push('#2B2D6E')
  }

  return dots
}

function dayCellClass(day: CalDay) {
  return [
    day.isOutside ? 'opacity-25' : '',
    day.isToday   ? 'ring-1 ring-navy/30 bg-navy/5' : '',
  ]
}

function dayNumberClass(day: CalDay) {
  return day.isToday ? 'text-navy font-bold' : 'text-gray-700'
}

// ── Unit info helpers (from InfoView) ─────────────────────────────────
const SENSITIVE = new Set(['wifi', 'alarm', 'gate', 'key', 'code', 'password'])
function isSensitive(item: any) { return SENSITIVE.has(item.icon_type?.toLowerCase()) || item.is_sensitive }
function maskedValue(item: any) { return isSensitive(item) ? '••••••••' : item.value }
function toggleReveal(id: number) {
  if (revealed.value.has(id)) revealed.value.delete(id)
  else revealed.value.add(id)
  revealed.value = new Set(revealed.value)
}

const ICON_MAP: Record<string, any> = { wifi: Wifi, electricity: Zap, water: Droplets, alarm: Shield, gate: Lock, key: Lock, gas: Flame }
function iconFor(t: string) { return ICON_MAP[t] ?? Building2 }
function iconBg(t: string) {
  return { wifi: 'bg-blue-50', electricity: 'bg-yellow-50', water: 'bg-cyan-50', alarm: 'bg-red-50', gate: 'bg-navy/8', gas: 'bg-orange-50' }[t] ?? 'bg-gray-100'
}
function iconColor(t: string) {
  return { wifi: 'text-blue-500', electricity: 'text-yellow-500', water: 'text-cyan-500', alarm: 'text-red-500', gate: 'text-navy', gas: 'text-orange-500' }[t] ?? 'text-gray-400'
}

// ── Data loading ───────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const [leasesRes, infoRes] = await Promise.allSettled([
      api.get('/leases/'),
      api.get('/properties/unit-info/'),
    ])

    if (leasesRes.status === 'fulfilled') {
      const leases = leasesRes.value.data.results ?? leasesRes.value.data
      // Prefer active lease, fall back to most recent
      lease.value = leases.find((l: any) => l.status === 'active')
        ?? leases.find((l: any) => l.status === 'pending')
        ?? leases[0]
        ?? null

      // Check if this lease needs signing
      if (lease.value) {
        try {
          const subsRes = await api.get('/esigning/submissions/', { params: { lease: lease.value.id } })
          const subs = subsRes.data.results ?? subsRes.data
          needsSigning.value = subs.some((s: any) =>
            s.signers?.some((sg: any) => sg.email === auth.user?.email && sg.status === 'pending'),
          )
        } catch { /* signing check is optional */ }
      }
    }

    if (infoRes.status === 'fulfilled') {
      infoItems.value = infoRes.value.data.results ?? infoRes.value.data
    }
  } finally {
    loading.value = false
  }
})
</script>
