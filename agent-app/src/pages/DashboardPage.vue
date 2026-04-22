<template>
  <q-page class="dashboard-page">

    <q-pull-to-refresh @refresh="loadData">

      <!-- ── Greeting ── -->
      <div class="greeting-section">
        <div class="greeting-name">Good {{ timeOfDay }}, {{ auth.user?.first_name || 'Agent' }}</div>
        <div class="greeting-date">{{ todayStr }}</div>
      </div>

      <!-- ── Stats card ── -->
      <div class="stats-card">
        <div class="stat-item">
          <div class="stat-value">{{ stats.propertyCount }}</div>
          <div class="stat-label">Properties</div>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <div class="stat-value">{{ stats.viewingCount }}</div>
          <div class="stat-label">Viewings</div>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <div class="stat-value stat-available">{{ availableCount }}</div>
          <div class="stat-label">Available</div>
        </div>
      </div>

      <!-- ── Upcoming viewings ── -->
      <div class="klikk-section-header q-mb-sm">Upcoming Viewings</div>

      <div v-if="loading" class="row justify-center q-py-xl">
        <q-spinner-dots color="primary" :size="SPINNER_SIZE_PAGE" />
      </div>

      <template v-else-if="upcomingViewings.length === 0">
        <div class="empty-state">
          <q-icon name="event_available" size="40px" color="grey-4" />
          <div class="empty-state-title">No upcoming viewings</div>
          <div class="empty-state-sub">Book your first viewing to get started</div>
        </div>
      </template>

      <template v-else>
        <q-card flat class="section-card q-mb-md">
          <q-list separator>
            <q-item
              v-for="viewing in upcomingViewings.slice(0, 5)"
              :key="viewing.id"
              clickable
              v-ripple
              @click="$router.push(`/viewings/${viewing.id}`)"
            >
              <q-item-section avatar>
                <q-avatar :color="statusColor(viewing.status)" text-color="white" :size="AVATAR_LIST">
                  <q-icon name="person" />
                </q-avatar>
              </q-item-section>

              <q-item-section>
                <q-item-label class="text-weight-medium">{{ viewing.prospect_name }}</q-item-label>
                <q-item-label caption>{{ viewing.property_name }}</q-item-label>
                <q-item-label caption class="text-grey-5">
                  <q-icon name="schedule" size="12px" />
                  {{ formatDateTimeShort(viewing.scheduled_at) }}
                </q-item-label>
              </q-item-section>

              <q-item-section side>
                <q-badge :color="statusColor(viewing.status)" :label="fmtLabel(viewing.status)" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>

        <div v-if="upcomingViewings.length > 5" class="text-center q-mb-md">
          <q-btn flat color="primary" label="See all viewings" @click="$router.push('/calendar')" />
        </div>
      </template>

      <!-- ── Active repairs ── -->
      <div class="repairs-section">
        <div class="row items-center justify-between q-mb-sm">
          <div class="klikk-section-header">Active Repairs</div>
          <q-btn flat dense no-caps color="primary" label="View all" size="sm" @click="$router.push('/maintenance')" />
        </div>

        <div v-if="repairsLoading" class="row justify-center q-py-lg">
          <q-spinner-dots color="primary" size="28px" />
        </div>

        <div v-else-if="activeRepairs.length === 0" class="repairs-empty">
          <q-icon name="check_circle" size="26px" color="positive" />
          <div class="repairs-empty-text">
            <span class="repairs-empty-title">No open repairs</span>
            <span class="repairs-empty-sub">All maintenance requests resolved</span>
          </div>
        </div>

        <div v-else class="column q-gutter-sm">
          <q-card
            v-for="repair in activeRepairs"
            :key="repair.id"
            flat
            clickable
            class="repair-card"
            @click="$router.push('/maintenance')"
          >
            <q-card-section class="q-pa-md">
              <div class="row items-start justify-between q-mb-xs">
                <div class="col">
                  <div class="text-subtitle2 text-weight-bold text-primary ellipsis">{{ repair.title }}</div>
                  <div v-if="repair.tenant_name" class="text-caption text-grey-6 q-mt-xs">{{ repair.tenant_name }}</div>
                </div>
                <q-badge :color="repairStatusColor(repair.status)" :label="fmtLabel(repair.status)" class="q-ml-sm" />
              </div>
              <q-separator class="q-my-sm" />
              <div class="row items-center q-gutter-sm text-caption text-grey-7">
                <div class="row items-center q-gutter-xs">
                  <q-icon name="flag" size="13px" :color="priorityColor(repair.priority)" />
                  <span class="text-weight-medium" :class="`text-${priorityColor(repair.priority)}`">
                    {{ capitalize(repair.priority) }}
                  </span>
                </div>
                <div v-if="repair.category" class="row items-center q-gutter-xs">
                  <q-icon name="category" size="13px" color="grey-5" />
                  <span>{{ capitalize(repair.category) }}</span>
                </div>
                <div class="row items-center q-gutter-xs q-ml-auto">
                  <q-icon name="schedule" size="13px" color="grey-5" />
                  <span>{{ relativeTime(repair.updated_at) }}</span>
                </div>
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- ── Primary CTA ── -->
      <div class="cta-section">
        <q-btn
          color="primary"
          label="Book a Viewing"
          icon="add"
          class="full-width cta-btn"
          :rounded="isIos"
          unelevated
          @click="$router.push('/viewings/new')"
        />
      </div>

    </q-pull-to-refresh>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useAuthStore } from '../stores/auth'
import { usePlatform } from '../composables/usePlatform'
import { getDashboardSummary, listMaintenanceRequests, type PropertyViewing, type Property, type MaintenanceRequest } from '../services/api'
import { statusColor, formatDateTimeShort, fmtLabel } from '../utils/formatters'
import { SPINNER_SIZE_PAGE, AVATAR_LIST } from '../utils/designTokens'

const auth   = useAuthStore()
const $q     = useQuasar()
const { isIos } = usePlatform()

const loading          = ref(true)
const repairsLoading   = ref(true)
const upcomingViewings = ref<PropertyViewing[]>([])
const properties       = ref<Property[]>([])
const stats            = ref({ propertyCount: 0, viewingCount: 0 })
const activeRepairs    = ref<MaintenanceRequest[]>([])

function repairStatusColor(s: string) {
  return { open: 'negative', in_progress: 'warning', resolved: 'positive', closed: 'grey-5' }[s] ?? 'grey-5'
}

function priorityColor(p: string) {
  return { urgent: 'negative', high: 'warning', medium: 'info', low: 'grey-5' }[p] ?? 'grey-5'
}

function capitalize(s: string) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ') : ''
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1)  return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24)  return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 7)  return `${days}d ago`
  return new Date(iso).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })
}

const availableCount = computed(() =>
  properties.value.reduce((n, p) => n + p.units.filter((u) => u.status === 'available').length, 0),
)

const timeOfDay = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'morning'
  if (h < 17) return 'afternoon'
  return 'evening'
})

const todayStr = computed(() =>
  new Date().toLocaleDateString('en-ZA', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }),
)

async function loadData(done?: () => void) {
  try {
    const [summaryRes, repairsRes] = await Promise.allSettled([
      getDashboardSummary(),
      listMaintenanceRequests({ status: 'open,in_progress', page_size: 3 }),
    ])

    if (summaryRes.status === 'fulfilled') {
      const summary = summaryRes.value
      upcomingViewings.value = summary.upcomingViewings
      properties.value       = summary.properties
      stats.value = { propertyCount: summary.propertyCount, viewingCount: summary.viewingCount }
    } else {
      $q.notify({ type: 'negative', message: 'Failed to load dashboard. Pull down to retry.', icon: 'error' })
    }

    if (repairsRes.status === 'fulfilled') {
      activeRepairs.value = repairsRes.value.results ?? []
    }
  } finally {
    loading.value = false
    repairsLoading.value = false
    done?.()
  }
}

onMounted(() => void loadData())
</script>

<style scoped lang="scss">
$navy: $primary;

.dashboard-page {
  background: $surface;
  padding: 20px 16px 16px;
}

/* ── Greeting ── */
.greeting-section {
  margin-bottom: 20px;
}

.greeting-name {
  font-size: 22px;
  font-weight: 700;
  color: var(--klikk-text-primary);
  letter-spacing: -0.01em;
  line-height: 1.2;
}

.greeting-date {
  font-size: 13px;
  color: var(--klikk-text-secondary);
  margin-top: 2px;
}

/* ── Stats card ── */
.stats-card {
  display: flex;
  align-items: center;
  background: white;
  border-radius: var(--klikk-radius-card);
  border: 1px solid var(--klikk-card-border);
  box-shadow: var(--klikk-shadow-soft);
  padding: 20px 0;
  margin-bottom: 24px;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-value {
  font-size: 28px;
  font-weight: 800;
  color: $navy;
  line-height: 1;
  letter-spacing: -0.02em;
}

.stat-available {
  color: $positive;
}

.stat-label {
  font-size: 11px;
  color: var(--klikk-text-secondary);
  font-weight: 500;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.stat-divider {
  width: 1px;
  height: 36px;
  background: var(--klikk-border);
}

/* ── Empty state ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 24px;
  background: white;
  border-radius: var(--klikk-radius-card);
  border: 1px solid var(--klikk-card-border);
  box-shadow: var(--klikk-shadow-soft);
  margin-bottom: 16px;
  text-align: center;
  gap: 6px;
}

.empty-state-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--klikk-text-primary);
  margin-top: 4px;
}

.empty-state-sub {
  font-size: 13px;
  color: var(--klikk-text-secondary);
}

/* ── Repairs widget ── */
.repairs-section {
  margin-bottom: 20px;
}

.repair-card {
  border-radius: var(--klikk-radius-card);
  border: 1px solid var(--klikk-border);
  overflow: hidden;
  cursor: pointer;
}

.repairs-empty {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: white;
  border-radius: var(--klikk-radius-card);
  border: 1px solid var(--klikk-border);
}

.repairs-empty-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.repairs-empty-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--klikk-text-primary);
}

.repairs-empty-sub {
  font-size: 12px;
  color: var(--klikk-text-secondary);
}

/* ── CTA button ── */
.cta-section {
  margin-top: 8px;
}

.cta-btn {
  font-size: 15px;
  font-weight: 600;
  padding: 14px 0;
  letter-spacing: 0.01em;
}
</style>
