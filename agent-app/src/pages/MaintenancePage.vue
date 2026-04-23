<template>
  <q-page class="q-pa-md">
    <q-pull-to-refresh @refresh="loadRequests">

      <!-- Loading -->
      <div v-if="loading" class="row justify-center q-py-xl">
        <q-spinner-dots color="primary" :size="SPINNER_SIZE_PAGE" />
      </div>

      <template v-else>

        <!-- Filter chips -->
        <div class="row q-gutter-xs q-mb-md">
          <q-chip
            v-for="f in filters"
            :key="f.value"
            :selected="activeFilter === f.value"
            :color="activeFilter === f.value ? 'primary' : 'grey-2'"
            :text-color="activeFilter === f.value ? 'white' : 'grey-7'"
            clickable
            dense
            @click="activeFilter = f.value"
          >
            {{ f.label }}
          </q-chip>
        </div>

        <!-- Empty -->
        <div v-if="filteredRequests.length === 0" class="empty-state">
          <q-icon name="build" :size="EMPTY_ICON_SIZE" class="empty-state-icon" />
          <div class="empty-state-title">No maintenance requests</div>
          <div class="empty-state-sub">
            {{ activeFilter === 'all' ? 'No requests have been submitted yet' : 'Try a different filter' }}
          </div>
        </div>

        <!-- Cards -->
        <div v-else class="column q-gutter-sm">
          <q-card
            v-for="req in filteredRequests"
            :key="req.id"
            flat
            class="maintenance-card"
          >
            <q-card-section class="q-pa-md">

              <!-- Header row -->
              <div class="row items-start justify-between q-mb-xs">
                <div class="col">
                  <div class="text-subtitle2 text-weight-bold text-primary ellipsis">
                    {{ req.title }}
                  </div>
                  <div v-if="req.tenant_name" class="text-caption text-grey-6 q-mt-xs">
                    {{ req.tenant_name }}
                  </div>
                </div>
                <q-badge
                  :color="statusColor(req.status)"
                  :label="fmtLabel(req.status)"
                  class="q-ml-sm"
                />
              </div>

              <q-separator class="q-my-sm" />

              <!-- Details row -->
              <div class="row items-center q-gutter-sm text-caption text-grey-7">
                <div class="row items-center q-gutter-xs">
                  <q-icon name="flag" size="13px" :color="priorityColor(req.priority)" />
                  <span class="text-weight-medium" :class="`text-${priorityColor(req.priority)}`">
                    {{ capitalize(req.priority) }}
                  </span>
                </div>
                <div v-if="req.category" class="row items-center q-gutter-xs">
                  <q-icon name="category" size="13px" color="grey-5" />
                  <span>{{ capitalize(req.category) }}</span>
                </div>
                <div v-if="req.supplier_name" class="row items-center q-gutter-xs">
                  <q-icon name="handyman" size="13px" color="grey-5" />
                  <span>{{ req.supplier_name }}</span>
                </div>
                <div class="row items-center q-gutter-xs q-ml-auto">
                  <q-icon name="schedule" size="13px" color="grey-5" />
                  <span>{{ relativeTime(req.updated_at) }}</span>
                </div>
              </div>

            </q-card-section>
          </q-card>
        </div>

      </template>
    </q-pull-to-refresh>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { listMaintenanceRequests, type MaintenanceRequest } from '../services/api'
import { fmtLabel } from '../utils/formatters'
import { SPINNER_SIZE_PAGE, EMPTY_ICON_SIZE } from '../utils/designTokens'

const $q = useQuasar()

const requests     = ref<MaintenanceRequest[]>([])
const loading      = ref(true)
const activeFilter = ref('all')

const filters = [
  { value: 'all',         label: 'All' },
  { value: 'open',        label: 'Open' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'resolved',    label: 'Resolved' },
  { value: 'closed',      label: 'Closed' },
]

const filteredRequests = computed(() => {
  if (activeFilter.value === 'all') return requests.value
  return requests.value.filter(r => r.status === activeFilter.value)
})

function statusColor(s: string) {
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

async function loadRequests(done?: () => void) {
  loading.value = true
  try {
    const res = await listMaintenanceRequests({ page_size: 50 })
    requests.value = res.results ?? []
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to load maintenance requests.', icon: 'error' })
  } finally {
    loading.value = false
    done?.()
  }
}

watch(activeFilter, () => void loadRequests())
onMounted(() => void loadRequests())
</script>

<style scoped lang="scss">
.maintenance-card {
  border-radius: var(--klikk-radius-card);
  border: 1px solid var(--klikk-border);
  overflow: hidden;
}
</style>
