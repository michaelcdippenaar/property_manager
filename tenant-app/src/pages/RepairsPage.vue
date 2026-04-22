<template>
  <q-page class="q-pa-md">
    <q-pull-to-refresh @refresh="loadIssues">

      <!-- Loading -->
      <div v-if="loading" class="row justify-center q-py-xl">
        <q-spinner-dots color="primary" size="32px" />
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

        <!-- Empty state -->
        <div v-if="issues.length === 0" class="empty-state">
          <q-icon name="build" size="40px" class="empty-state-icon" />
          <div class="empty-state-title">No repairs found</div>
          <div class="empty-state-sub">
            {{ activeFilter === 'all' ? 'Tap + to report a new issue' : 'Try a different filter' }}
          </div>
        </div>

        <!-- Repair cards -->
        <div v-else class="column q-gutter-sm">
          <q-card
            v-for="issue in issues"
            :key="issue.id"
            flat
            clickable
            class="repair-card"
            @click="$router.push(`/repairs/ticket/${issue.id}`)"
          >
            <q-card-section class="q-pa-md">

              <!-- Header row: title + status -->
              <div class="row items-start justify-between q-mb-xs">
                <div class="col">
                  <div class="text-subtitle2 text-weight-bold text-primary ellipsis">
                    {{ issue.title }}
                  </div>
                  <div class="text-caption text-grey-6 q-mt-xs ellipsis">
                    {{ issue.description || issue.category || '—' }}
                  </div>
                </div>
                <StatusBadge :value="issue.status" class="q-ml-sm" />
              </div>

              <q-separator class="q-my-sm" />

              <!-- Details row: priority + category + time -->
              <div class="row items-center q-gutter-sm text-caption text-grey-7">
                <div class="row items-center q-gutter-xs">
                  <q-icon
                    name="flag"
                    size="14px"
                    :color="priorityIconColor(issue.priority)"
                  />
                  <span
                    class="text-weight-medium"
                    :class="`text-${priorityIconColor(issue.priority)}`"
                  >
                    {{ capitalize(issue.priority) }}
                  </span>
                </div>
                <div v-if="issue.category" class="row items-center q-gutter-xs">
                  <q-icon name="category" size="14px" color="grey-5" />
                  <span>{{ issue.category }}</span>
                </div>
                <div class="row items-center q-gutter-xs q-ml-auto">
                  <q-icon name="schedule" size="14px" color="grey-5" />
                  <span>{{ relativeTime(issue.updated_at) }}</span>
                </div>
              </div>

            </q-card-section>
          </q-card>
        </div>

      </template>
    </q-pull-to-refresh>

    <!-- New ticket FAB -->
    <q-page-sticky position="bottom-right" :offset="[18, 18]">
      <q-btn
        fab
        icon="add"
        color="primary"
        aria-label="New repair"
        :loading="creating"
        @click="createTicket"
      />
    </q-page-sticky>

  </q-page>
</template>

<script setup lang="ts">
defineOptions({ name: 'RepairsPage' })

import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import StatusBadge from '../components/StatusBadge.vue'
import * as tenantApi from '../services/api'
import type { MaintenanceIssue } from '../services/api'
import { useMaintenanceListSocket } from '../composables/useMaintenanceListSocket'

const router = useRouter()
const $q     = useQuasar()

const issues       = ref<MaintenanceIssue[]>([])
const loading      = ref(true)
const creating     = ref(false)
const activeFilter = ref('all')

const filters = [
  { value: 'all',         label: 'All' },
  { value: 'open',        label: 'Open' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'resolved',    label: 'Resolved' },
  { value: 'closed',      label: 'Closed' },
]

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

async function loadIssues(done?: () => void) {
  loading.value = true
  try {
    const params: { status?: string; page_size: number } = { page_size: 50 }
    if (activeFilter.value !== 'all') params.status = activeFilter.value
    const res = await tenantApi.listIssues(params)
    issues.value = res.data.results ?? res.data as MaintenanceIssue[]
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to load repairs.', icon: 'error' })
  } finally {
    loading.value = false
    done?.()
  }
}

async function createTicket() {
  if (creating.value) return
  creating.value = true
  try {
    const res = await tenantApi.createConversation({ title: 'New repair request' })
    await router.push(`/repairs/chat/${res.data.id}`)
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to start chat. Please try again.', icon: 'error' })
  } finally {
    creating.value = false
  }
}

watch(activeFilter, loadIssues)
onMounted(loadIssues)
useMaintenanceListSocket(loadIssues)
</script>

<style scoped lang="scss">
.repair-card {
  border-radius: var(--klikk-radius-card);
  border: 1px solid var(--klikk-border);
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow 0.15s;

  &:active {
    box-shadow: var(--klikk-shadow-soft);
  }
}
</style>
