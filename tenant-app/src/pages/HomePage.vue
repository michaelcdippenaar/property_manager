<template>
  <q-page class="page-container">
    <q-pull-to-refresh @refresh="onRefresh">

      <!-- Greeting -->
      <div class="q-mb-md">
        <div class="text-h6 text-weight-bold text-primary">{{ greeting }}</div>
        <div class="text-caption text-grey-6">Here's your overview</div>
      </div>

      <!-- Signing CTA -->
      <q-card v-if="signingCta" flat class="q-mb-md" @click="$router.push('/lease')">
        <q-item clickable v-ripple>
          <q-item-section avatar>
            <q-avatar color="secondary" text-color="white" size="40px">
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
      <div class="q-mb-md">
        <div class="row items-center justify-between q-mb-xs q-px-xs">
          <!-- Admin-aligned section header (navy, uppercase, tracking-wide) -->
          <div class="klikk-section-header">Active Repairs</div>
          <q-btn flat dense no-caps color="primary" label="View all" size="sm" @click="$router.push('/repairs')" />
        </div>

        <!-- Loading -->
        <div v-if="issuesLoading" class="column q-gutter-sm">
          <q-skeleton v-for="i in 2" :key="i" type="QItem" height="60px" class="rounded-borders" />
        </div>

        <!-- Empty -->
        <q-card v-else-if="activeIssues.length === 0" flat>
          <div class="empty-state">
            <q-icon name="check_circle" size="32px" color="positive" class="empty-state-icon" />
            <div class="empty-state-title">No active repairs</div>
            <div class="empty-state-sub">Everything looks good!</div>
          </div>
        </q-card>

        <!-- Issue list — uses admin-aligned .section-card (white, border, soft shadow) -->
        <q-card v-else flat class="section-card">
          <q-list separator>
            <q-item
              v-for="issue in activeIssues"
              :key="issue.id"
              clickable
              v-ripple
              @click="$router.push(`/repairs/ticket/${issue.id}`)"
            >
              <q-item-section avatar>
                <q-avatar :color="priorityAvatarColor(issue.priority)" size="36px">
                  <q-icon name="build" :color="priorityIconColor(issue.priority)" size="18px" />
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-semibold ellipsis">{{ issue.title }}</q-item-label>
                <q-item-label caption class="ellipsis">{{ issue.category }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <StatusBadge :value="issue.status" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </div>

      <!-- Unit info preview -->
      <div v-if="infoItems.length > 0" class="q-mb-md">
        <div class="row items-center justify-between q-mb-xs q-px-xs">
          <div class="section-header">Your Unit</div>
          <q-btn flat dense no-caps color="primary" label="More info" size="sm" @click="$router.push('/lease')" />
        </div>
        <q-card flat>
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
import type { MaintenanceIssue, UnitInfoItem } from '../services/api'

const auth = useAuthStore()
const $q = useQuasar()

const activeIssues  = ref<MaintenanceIssue[]>([])
const issuesLoading = ref(true)
const infoItems     = ref<UnitInfoItem[]>([])
const signingCta    = ref(false)

// ── Computed (in component per user requirement) ──────────────────────────────
const greeting = computed(() => {
  const hour = new Date().getHours()
  const name = auth.user?.full_name?.split(' ')[0] || 'there'
  if (hour < 12) return `Good morning, ${name}`
  if (hour < 17) return `Good afternoon, ${name}`
  return `Good evening, ${name}`
})

// ── Helpers ──────────────────────────────────────────────────────────────────
function priorityAvatarColor(p: string) {
  return { urgent: 'red-1', high: 'orange-1', medium: 'light-blue-1', low: 'grey-2' }[p] ?? 'grey-2'
}

function priorityIconColor(p: string) {
  return { urgent: 'negative', high: 'warning', medium: 'info', low: 'grey-5' }[p] ?? 'grey-5'
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
    const [issuesRes, infoRes] = await Promise.allSettled([
      tenantApi.listIssues({ status: 'open,in_progress', page_size: 3 }),
      tenantApi.listUnitInfo(),
    ])
    if (issuesRes.status === 'fulfilled') activeIssues.value = issuesRes.value.data.results ?? issuesRes.value.data as MaintenanceIssue[]
    else $q.notify({ type: 'negative', message: 'Failed to load repairs.', icon: 'error' })
    if (infoRes.status === 'fulfilled') infoItems.value = infoRes.value.data.results ?? infoRes.value.data as UnitInfoItem[]

    // Check for pending signing
    try {
      const leasesRes = await tenantApi.listLeases()
      const leases = leasesRes.data.results ?? leasesRes.data
      if ((leases as unknown[]).length > 0) {
        const firstLease = (leases as { id: number }[])[0]
        const subsRes = await tenantApi.listSubmissions({ lease: firstLease.id })
        const subs = subsRes.data.results ?? subsRes.data
        signingCta.value = (subs as { signers?: { email: string; status: string }[] }[]).some((s) =>
          s.signers?.some((sg) => sg.email === auth.user?.email && sg.status === 'pending'),
        )
      }
    } catch { /* signing CTA is optional — not critical data */ }
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
</style>
