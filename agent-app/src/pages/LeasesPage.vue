<template>
  <q-page class="q-pa-md">
    <q-pull-to-refresh @refresh="loadLeases">

      <!-- Loading -->
      <div v-if="loading" class="row justify-center q-py-xl">
        <q-spinner-dots color="primary" :size="SPINNER_SIZE_PAGE" />
      </div>

      <template v-else>

        <!-- Search -->
        <q-input
          v-model="search"
          placeholder="Search tenant or property…"
          outlined
          :rounded="isIos"
          dense
          clearable
          class="q-mb-md"
        >
          <template #prepend>
            <q-icon name="search" color="grey-6" />
          </template>
        </q-input>

        <!-- Status filter chips -->
        <div class="row q-gutter-xs q-mb-md">
          <q-chip
            v-for="s in statusFilters"
            :key="s.value"
            :selected="activeFilter === s.value"
            :color="activeFilter === s.value ? 'primary' : 'grey-2'"
            :text-color="activeFilter === s.value ? 'white' : 'grey-7'"
            clickable
            dense
            @click="activeFilter = s.value"
          >
            {{ s.label }}
          </q-chip>
        </div>

        <!-- Empty state -->
        <div v-if="filteredLeases.length === 0" class="empty-state">
          <q-icon name="description" :size="EMPTY_ICON_SIZE" class="empty-state-icon" />
          <div class="empty-state-title">No leases found</div>
          <div v-if="activeFilter !== 'all'" class="empty-state-sub">
            Try changing the filter or search term
          </div>
        </div>

        <!-- Lease list -->
        <div v-else class="column q-gutter-sm">
          <q-card
            v-for="lease in filteredLeases"
            :key="lease.id"
            flat
            class="lease-card"
          >
            <q-card-section class="q-pa-md">
              <!-- Header row -->
              <div class="row items-start justify-between q-mb-xs">
                <div class="col">
                  <div class="text-subtitle2 text-weight-bold text-primary ellipsis">
                    {{ lease.unit_label }}
                  </div>
                  <div class="text-caption text-grey-6">
                    {{ lease.tenant_name || lease.all_tenant_names?.[0] || '—' }}
                  </div>
                </div>
                <q-badge
                  :color="leaseStatusColor(lease.status)"
                  :label="fmtLabel(lease.status)"
                  class="q-ml-sm"
                />
              </div>

              <q-separator class="q-my-sm" />

              <!-- Details row -->
              <div class="row q-gutter-sm text-caption text-grey-7">
                <div class="row items-center q-gutter-xs">
                  <q-icon name="payments" size="14px" color="positive" />
                  <span class="text-weight-medium text-grey-9">
                    R{{ formatZAR(lease.monthly_rent) }}/mo
                  </span>
                </div>
                <div class="row items-center q-gutter-xs">
                  <q-icon name="calendar_today" size="14px" color="grey-5" />
                  <span>{{ formatDate(lease.start_date) }}</span>
                </div>
                <div class="row items-center q-gutter-xs">
                  <q-icon name="event_busy" size="14px" color="grey-5" />
                  <span>{{ formatDate(lease.end_date) }}</span>
                </div>
              </div>

              <!-- Days remaining pill -->
              <div v-if="lease.status === 'active' && daysRemaining(lease.end_date) !== null" class="q-mt-sm">
                <q-badge
                  outline
                  :color="daysRemaining(lease.end_date)! < 60 ? 'warning' : 'grey-5'"
                  :label="`${daysRemaining(lease.end_date)} days remaining`"
                />
              </div>
            </q-card-section>
          </q-card>
        </div>

      </template>
    </q-pull-to-refresh>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { listLeases, type AgentLease } from '../services/api'
import { usePlatform } from '../composables/usePlatform'
import { leaseStatusColor, formatDate, daysRemaining, fmtLabel } from '../utils/formatters'
import { SPINNER_SIZE_PAGE, EMPTY_ICON_SIZE, formatZAR } from '../utils/designTokens'

const $q = useQuasar()
const { isIos } = usePlatform()

const loading     = ref(true)
const leases      = ref<AgentLease[]>([])
const search      = ref('')
const activeFilter = ref<string>('all')

const statusFilters = [
  { label: 'All',        value: 'all'        },
  { label: 'Active',     value: 'active'     },
  { label: 'Pending',    value: 'pending'    },
  { label: 'Expired',    value: 'expired'    },
  { label: 'Terminated', value: 'terminated' },
]

const filteredLeases = computed(() => {
  let result = leases.value

  if (activeFilter.value !== 'all') {
    result = result.filter((l) => l.status === activeFilter.value)
  }

  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    result = result.filter(
      (l) =>
        l.unit_label.toLowerCase().includes(q) ||
        l.tenant_name?.toLowerCase().includes(q),
    )
  }

  return result
})

async function loadLeases(done?: () => void) {
  try {
    const resp = await listLeases()
    leases.value = resp.results
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to load leases. Pull down to retry.', icon: 'error' })
  } finally {
    loading.value = false
    done?.()
  }
}

onMounted(() => void loadLeases())
</script>

<style scoped lang="scss">
.lease-card {
  border-radius: var(--klikk-radius-card);
  border: 1px solid var(--klikk-border);
  overflow: hidden;
}
</style>
