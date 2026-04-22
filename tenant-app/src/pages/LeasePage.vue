<template>
  <q-layout view="hHh lpR fFf">
    <q-header :elevated="!isIos" :class="headerClass">
      <q-toolbar>
        <q-btn flat round :icon="backIcon" :color="isIos ? 'primary' : 'white'" aria-label="Go back" @click="$router.back()" />
        <q-toolbar-title :class="isIos ? 'text-primary text-weight-semibold' : 'text-white text-weight-medium'">
          My Lease
        </q-toolbar-title>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <q-page class="page-container">

        <!-- Loading -->
        <div v-if="loading" class="column q-gutter-sm">
          <q-skeleton v-for="i in 5" :key="i" type="QItem" height="56px" class="rounded-borders" />
        </div>

        <!-- No lease -->
        <div v-else-if="!lease" class="empty-state">
          <q-icon name="description" :size="EMPTY_ICON_SIZE" class="empty-state-icon" />
          <div class="empty-state-title">No active lease</div>
          <div class="empty-state-sub">Contact your agent to get started</div>
        </div>

        <template v-else>

          <!-- Signing CTA -->
          <q-card v-if="needsSigning" flat class="q-mb-md" @click="$router.push('/signing')">
            <q-item clickable v-ripple>
              <q-item-section avatar>
                <q-avatar color="primary" text-color="white" size="40px">
                  <q-icon name="draw" />
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-semibold">Lease ready to sign</q-item-label>
                <q-item-label caption>Tap to review and sign your agreement</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-icon name="chevron_right" color="grey-4" />
              </q-item-section>
            </q-item>
          </q-card>

          <!-- Lease details -->
          <div class="section-header">Lease Details</div>
          <q-card flat class="q-mb-md">
            <q-list separator>
              <!-- Status -->
              <q-item>
                <q-item-section avatar>
                  <q-avatar :color="leaseStatusBg" size="36px">
                    <q-icon name="circle" :color="leaseStatusIconColor" size="18px" />
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label caption>Status</q-item-label>
                  <q-item-label class="text-weight-semibold text-capitalize" :class="`text-${leaseStatusIconColor}`">{{ lease.status }}</q-item-label>
                </q-item-section>
                <q-item-section v-if="leaseDaysRemaining !== null" side>
                  <q-item-label caption>{{ leaseDaysRemaining }}d left</q-item-label>
                </q-item-section>
              </q-item>

              <!-- Property -->
              <q-item>
                <q-item-section avatar>
                  <q-avatar color="grey-2" size="36px">
                    <q-icon name="home" color="primary" size="18px" />
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label caption>Property</q-item-label>
                  <q-item-label class="text-weight-medium ellipsis">{{ lease.unit_label }}</q-item-label>
                </q-item-section>
              </q-item>

              <!-- Rent -->
              <q-item>
                <q-item-section avatar>
                  <q-avatar color="green-1" size="36px">
                    <q-icon name="payments" color="positive" size="18px" />
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label caption>Monthly Rent</q-item-label>
                  <q-item-label class="text-weight-semibold">{{ formatCurrency(lease.monthly_rent) }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-item-label caption>due {{ ordinal(lease.rent_due_day) }}</q-item-label>
                </q-item-section>
              </q-item>

              <!-- Deposit -->
              <q-item>
                <q-item-section avatar>
                  <q-avatar color="blue-1" size="36px">
                    <q-icon name="account_balance_wallet" color="info" size="18px" />
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label caption>Deposit Held</q-item-label>
                  <q-item-label class="text-weight-medium">{{ formatCurrency(lease.deposit) }}</q-item-label>
                </q-item-section>
              </q-item>

              <!-- Period -->
              <q-item>
                <q-item-section avatar>
                  <q-avatar color="purple-1" size="36px">
                    <q-icon name="date_range" color="purple-5" size="18px" />
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label caption>Lease Period</q-item-label>
                  <q-item-label class="text-weight-medium">{{ formatDate(lease.start_date) }} – {{ formatDate(lease.end_date) }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Utilities -->
          <div class="section-header">Utilities</div>
          <q-card flat class="q-mb-md">
            <q-list separator>
              <q-item>
                <q-item-section avatar>
                  <q-avatar color="blue-1" size="36px">
                    <q-icon name="water_drop" color="blue-5" size="18px" />
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label caption>Water</q-item-label>
                  <q-item-label class="text-weight-medium">{{ lease.water_included ? 'Included' : 'Separate meter' }}</q-item-label>
                </q-item-section>
                <q-item-section v-if="lease.water_included && lease.water_limit_litres" side>
                  <q-item-label caption>{{ formatZAR(lease.water_limit_litres) }}L / mo</q-item-label>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section avatar>
                  <q-avatar color="amber-1" size="36px">
                    <q-icon name="bolt" color="amber-8" size="18px" />
                  </q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label caption>Electricity</q-item-label>
                  <q-item-label class="text-weight-medium">{{ lease.electricity_prepaid ? 'Prepaid meter' : 'Municipality account' }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Unit info -->
          <template v-if="infoItems.length > 0">
            <div class="section-header">Unit Info</div>
            <q-card flat class="q-mb-md">
              <q-list separator>
                <q-item
                  v-for="item in infoItems"
                  :key="item.id"
                  :clickable="isSensitive(item)"
                  @click="isSensitive(item) ? toggleReveal(item.id) : undefined"
                >
                  <q-item-section avatar>
                    <q-avatar :color="unitInfoIconBg(item.icon_type)" size="36px">
                      <q-icon :name="unitInfoIcon(item.icon_type)" color="primary" size="18px" />
                    </q-avatar>
                  </q-item-section>
                  <q-item-section>
                    <q-item-label caption>{{ item.label }}</q-item-label>
                    <q-item-label class="text-weight-medium" style="font-family: monospace">
                      {{ revealed.has(item.id) ? item.value : maskedValue(item) }}
                    </q-item-label>
                  </q-item-section>
                  <q-item-section v-if="isSensitive(item)" side>
                    <q-icon :name="revealed.has(item.id) ? 'visibility_off' : 'visibility'" color="grey-4" size="18px" />
                  </q-item-section>
                </q-item>
              </q-list>
            </q-card>
          </template>

        </template>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { usePlatform } from '../composables/usePlatform'
import { useAuthStore } from '../stores/auth'
import * as tenantApi from '../services/api'
import type { TenantLease, UnitInfoItem } from '../services/api'
import { formatDate, formatCurrency, ordinal, daysRemaining } from '../utils/formatters'
import { EMPTY_ICON_SIZE, formatZAR } from '../utils/designTokens'

const auth = useAuthStore()
const $q = useQuasar()
const { isIos, backIcon, headerClass } = usePlatform()

const loading      = ref(true)
const lease        = ref<TenantLease | null>(null)
const needsSigning = ref(false)
const infoItems    = ref<UnitInfoItem[]>([])
const revealed     = ref(new Set<number>())

// ── Computed in component ─────────────────────────────────────────────────────
const leaseDaysRemaining = computed(() => {
  if (!lease.value?.end_date) return null
  return daysRemaining(lease.value.end_date)
})

const leaseStatusBg = computed(() => ({
  active: 'green-1', pending: 'amber-1', expired: 'grey-2', terminated: 'red-1',
}[lease.value?.status ?? ''] ?? 'grey-2'))

const leaseStatusIconColor = computed(() => ({
  active: 'positive', pending: 'warning', expired: 'grey-5', terminated: 'negative',
}[lease.value?.status ?? ''] ?? 'grey-5'))

// ── Unit info helpers ─────────────────────────────────────────────────────────
const SENSITIVE = new Set(['wifi', 'alarm', 'gate', 'key', 'code', 'password'])

function isSensitive(item: UnitInfoItem) {
  return SENSITIVE.has(item.icon_type?.toLowerCase()) || item.is_sensitive
}

function maskedValue(item: UnitInfoItem) {
  return isSensitive(item) ? '••••••••' : item.value
}

function toggleReveal(id: number) {
  const next = new Set(revealed.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  revealed.value = next
}

function unitInfoIcon(type: string) {
  return { wifi: 'wifi', electricity: 'bolt', water: 'water_drop', alarm: 'shield', gate: 'lock', gas: 'local_fire_department' }[type] ?? 'apartment'
}

function unitInfoIconBg(type: string) {
  return { wifi: 'blue-1', electricity: 'amber-1', water: 'cyan-1', alarm: 'red-1', gate: 'grey-2', gas: 'orange-1' }[type] ?? 'grey-2'
}

// ── Data loading ─────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const [leasesRes, infoRes] = await Promise.allSettled([
      tenantApi.listLeases(),
      tenantApi.listUnitInfo(),
    ])

    if (leasesRes.status === 'rejected') {
      $q.notify({ type: 'negative', message: 'Failed to load lease details.', icon: 'error' })
    }
    if (leasesRes.status === 'fulfilled') {
      const leases = leasesRes.value.data.results ?? leasesRes.value.data as TenantLease[]
      lease.value = (leases as TenantLease[]).find(l => l.status === 'active')
        ?? (leases as TenantLease[]).find(l => l.status === 'pending')
        ?? (leases as TenantLease[])[0]
        ?? null

      if (lease.value) {
        try {
          const subsRes = await tenantApi.listSubmissions({ lease: lease.value.id })
          const subs = subsRes.data.results ?? subsRes.data
          needsSigning.value = (subs as { signers?: { email: string; status: string }[] }[]).some(s =>
            s.signers?.some(sg => sg.email === auth.user?.email && sg.status === 'pending'),
          )
        } catch { /* signing check is optional */ }
      }
    }

    if (infoRes.status === 'fulfilled') {
      infoItems.value = infoRes.value.data.results ?? infoRes.value.data as UnitInfoItem[]
    }
  } finally {
    loading.value = false
  }
})
</script>

<style scoped lang="scss">
</style>
