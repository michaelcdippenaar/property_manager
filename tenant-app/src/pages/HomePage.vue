<template>
  <q-page class="page-container">
    <q-pull-to-refresh @refresh="onRefresh">

      <!-- Greeting -->
      <div class="greeting-block q-mb-lg">
        <div class="greeting-name">{{ greeting }}</div>
        <div class="greeting-date">{{ todayLabel }}</div>
      </div>

      <!-- Stats card -->
      <q-card v-if="lease" flat class="stats-card q-mb-lg">
        <div class="stats-grid">
          <div class="stat-cell">
            <div class="stat-value">{{ lease.status === 'active' ? 'Active' : (lease.status ?? '—') }}</div>
            <div class="stat-label">LEASE STATUS</div>
          </div>
          <div class="stat-divider" />
          <div class="stat-cell">
            <div class="stat-value">{{ rentDueLabel }}</div>
            <div class="stat-label">RENT DUE</div>
          </div>
          <div class="stat-divider" />
          <div class="stat-cell">
            <div class="stat-value">{{ activeIssues.length }}</div>
            <div class="stat-label">OPEN REPAIRS</div>
          </div>
        </div>
      </q-card>

      <!-- Signing CTA -->
      <q-card v-if="signingCta" flat class="cta-card q-mb-lg" @click="$router.push('/lease')">
        <q-item clickable v-ripple>
          <q-item-section avatar>
            <q-avatar color="primary" text-color="white" size="40px">
              <q-icon name="draw" />
            </q-avatar>
          </q-item-section>
          <q-item-section>
            <q-item-label class="text-weight-semibold">Lease ready to sign</q-item-label>
            <q-item-label caption>Tap to view and sign your agreement</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-icon name="chevron_right" color="grey-4" />
          </q-item-section>
        </q-item>
      </q-card>

      <!-- Active repairs -->
      <div class="q-mb-lg">
        <div class="row items-center justify-between q-mb-sm q-px-xs">
          <div class="klikk-section-header">Active Repairs</div>
          <q-btn flat dense no-caps color="primary" label="View all" size="sm" @click="$router.push('/repairs')" />
        </div>

        <!-- Loading -->
        <div v-if="issuesLoading" class="row justify-center q-py-lg">
          <q-spinner-dots color="primary" size="28px" />
        </div>

        <!-- Empty -->
        <div v-else-if="activeIssues.length === 0" class="repairs-empty">
          <q-icon name="check_circle" size="28px" color="positive" />
          <div class="repairs-empty-text">
            <span class="repairs-empty-title">All clear</span>
            <span class="repairs-empty-sub">No active repairs — everything looks good</span>
          </div>
          <q-btn
            flat
            dense
            no-caps
            color="primary"
            icon="add"
            label="Report"
            size="sm"
            @click="$router.push('/repairs')"
          />
        </div>

        <!-- Issue cards -->
        <div v-else class="column q-gutter-sm">
          <q-card
            v-for="issue in activeIssues"
            :key="issue.id"
            flat
            clickable
            class="repair-card"
            @click="$router.push(`/repairs/ticket/${issue.id}`)"
          >
            <q-card-section class="q-pa-md">
              <!-- Header row -->
              <div class="row items-start justify-between q-mb-xs">
                <div class="col">
                  <div class="text-subtitle2 text-weight-bold text-primary ellipsis">
                    {{ issue.title }}
                  </div>
                  <div v-if="issue.category" class="text-caption text-grey-6 q-mt-xs">
                    {{ issue.category }}
                  </div>
                </div>
                <StatusBadge :value="issue.status" class="q-ml-sm" />
              </div>

              <q-separator class="q-my-sm" />

              <!-- Details row -->
              <div class="row items-center q-gutter-sm text-caption text-grey-7">
                <div class="row items-center q-gutter-xs">
                  <q-icon name="flag" size="13px" :color="priorityIconColor(issue.priority)" />
                  <span :class="`text-${priorityIconColor(issue.priority)}`" class="text-weight-medium">
                    {{ capitalize(issue.priority) }}
                  </span>
                </div>
                <div class="row items-center q-gutter-xs q-ml-auto">
                  <q-icon name="schedule" size="13px" color="grey-5" />
                  <span>{{ relativeTime(issue.updated_at) }}</span>
                </div>
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Unit info preview -->
      <div v-if="infoItems.length > 0" class="q-mb-lg">
        <div class="row items-center justify-between q-mb-sm q-px-xs">
          <div class="klikk-section-header">Your Unit</div>
          <q-btn flat dense no-caps color="primary" label="More info" size="sm" @click="$router.push('/lease')" />
        </div>
        <q-card flat class="section-card">
          <q-list separator>
            <q-item v-for="item in infoItems.slice(0, 3)" :key="item.id">
              <q-item-section avatar>
                <q-avatar :color="infoIconBg(item.icon_type)" size="36px">
                  <q-icon :name="infoIcon(item.icon_type)" color="primary" size="18px" />
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label caption>{{ item.label }}</q-item-label>
                <q-item-label class="text-weight-medium">{{ maskValue(item) }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </div>

    </q-pull-to-refresh>
  </q-page>
</template>

<script setup lang="ts">
defineOptions({ name: 'HomePage' })

import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useAuthStore } from '../stores/auth'
import StatusBadge from '../components/StatusBadge.vue'
import * as tenantApi from '../services/api'
import type { MaintenanceIssue, UnitInfoItem, TenantLease } from '../services/api'

const auth = useAuthStore()
const $q = useQuasar()

const activeIssues  = ref<MaintenanceIssue[]>([])
const issuesLoading = ref(true)
const infoItems     = ref<UnitInfoItem[]>([])
const signingCta    = ref(false)
const lease         = ref<TenantLease | null>(null)

// ── Computed ──────────────────────────────────────────────────────────────────
const greeting = computed(() => {
  const hour = new Date().getHours()
  const name = auth.user?.full_name?.split(' ')[0] || 'there'
  if (hour < 12) return `Good morning, ${name}`
  if (hour < 17) return `Good afternoon, ${name}`
  return `Good evening, ${name}`
})

const todayLabel = computed(() => {
  return new Date().toLocaleDateString('en-ZA', {
    weekday: 'long', day: 'numeric', month: 'long',
  })
})

const rentDueLabel = computed(() => {
  if (!lease.value?.rent_due_day) return '—'
  return `${ordinal(lease.value.rent_due_day)}`
})

function ordinal(n: number) {
  const s = ['th', 'st', 'nd', 'rd']
  const v = n % 100
  return n + (s[(v - 20) % 10] || s[v] || s[0])
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function priorityIconColor(p: string) {
  return { urgent: 'negative', high: 'warning', medium: 'info', low: 'grey-5' }[p] ?? 'grey-5'
}

function capitalize(s: string) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''
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

function infoIcon(type: string) {
  return { wifi: 'wifi', electricity: 'bolt', water: 'water_drop', alarm: 'shield', gate: 'lock' }[type] ?? 'apartment'
}

function infoIconBg(type: string) {
  return { wifi: 'blue-1', electricity: 'amber-1', water: 'cyan-1', alarm: 'red-1', gate: 'grey-2' }[type] ?? 'grey-2'
}

const SENSITIVE = new Set(['wifi', 'alarm', 'gate', 'key', 'code', 'password'])

function maskValue(item: UnitInfoItem) {
  return SENSITIVE.has(item.icon_type?.toLowerCase()) || item.is_sensitive
    ? '••••••••'
    : item.value
}

// ── Data loading ─────────────────────────────────────────────────────────────
async function loadData() {
  issuesLoading.value = true
  try {
    const [issuesRes, infoRes, leasesRes] = await Promise.allSettled([
      tenantApi.listIssues({ status: 'open,in_progress', page_size: 3 }),
      tenantApi.listUnitInfo(),
      tenantApi.listLeases(),
    ])
    if (issuesRes.status === 'fulfilled') activeIssues.value = issuesRes.value.data.results ?? issuesRes.value.data as MaintenanceIssue[]
    else $q.notify({ type: 'negative', message: 'Failed to load repairs.', icon: 'error' })
    if (infoRes.status === 'fulfilled') infoItems.value = infoRes.value.data.results ?? infoRes.value.data as UnitInfoItem[]

    // Active lease for stats card
    if (leasesRes.status === 'fulfilled') {
      const leases = leasesRes.value.data.results ?? leasesRes.value.data as TenantLease[]
      const list = leases as TenantLease[]
      lease.value = list.find(l => l.status === 'active') ?? list[0] ?? null

      // Check for pending signing
      if (lease.value) {
        try {
          const subsRes = await tenantApi.listSubmissions({ lease: lease.value.id })
          const subs = subsRes.data.results ?? subsRes.data
          signingCta.value = (subs as { signers?: { email: string; status: string }[] }[]).some((s) =>
            s.signers?.some((sg) => sg.email === auth.user?.email && sg.status === 'pending'),
          )
        } catch { /* signing CTA is optional — not critical data */ }
      }
    }
  } finally {
    issuesLoading.value = false
  }
}

async function onRefresh(done: () => void) {
  await loadData()
  done()
}

onMounted(loadData)
</script>

<style scoped lang="scss">
.greeting-block {
  padding: 4px 4px 0;
}

.greeting-name {
  font-size: 22px;
  font-weight: 700;
  color: $primary;
  line-height: 1.2;
  letter-spacing: -0.01em;
}

.greeting-date {
  font-size: 13px;
  color: var(--klikk-text-secondary);
  margin-top: 2px;
}

.stats-card {
  border: 1px solid var(--klikk-border);
  border-radius: var(--klikk-radius-card);
  overflow: hidden;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.06);
}

.stats-grid {
  display: flex;
  align-items: stretch;
}

.stat-cell {
  flex: 1;
  padding: 18px 12px;
  text-align: center;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: $primary;
  line-height: 1;
  margin-bottom: 6px;
}

.stat-label {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--klikk-text-secondary);
  text-transform: uppercase;
}

.stat-divider {
  width: 0.5px;
  background: var(--klikk-border);
  align-self: stretch;
  margin: 14px 0;
}

.cta-card {
  border: 1px solid rgba(43, 45, 110, 0.15);
  border-radius: var(--klikk-radius-card);
  overflow: hidden;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.06);
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
</style>
