<template>
  <q-page class="page-container">

    <!-- Filter pills -->
    <div class="row q-gutter-xs q-mb-md">
      <q-btn
        v-for="f in filters"
        :key="f.value"
        :label="f.label"
        :color="activeFilter === f.value ? 'primary' : undefined"
        :outline="activeFilter !== f.value"
        :flat="activeFilter !== f.value"
        size="sm"
        no-caps
        rounded
        dense
        class="q-px-sm"
        @click="activeFilter = f.value"
      />
    </div>

    <!-- Loading -->
    <div v-if="loading" class="column q-gutter-sm">
      <q-skeleton v-for="i in 4" :key="i" type="QItem" height="72px" class="rounded-borders" />
    </div>

    <!-- Empty -->
    <div v-else-if="issues.length === 0" class="empty-state">
      <q-icon name="build" :size="EMPTY_ICON_SIZE" class="empty-state-icon" />
      <div class="empty-state-title">No repairs found</div>
      <div class="empty-state-sub">
        {{ activeFilter === 'all' ? 'Tap + to report a new issue' : 'Try a different filter' }}
      </div>
    </div>

    <!-- Ticket chat preview list -->
    <q-card v-else flat class="ticket-list-card">
      <q-list separator>
        <q-item
          v-for="issue in issues"
          :key="issue.id"
          clickable
          v-ripple
          class="ticket-item"
          @click="$router.push(`/repairs/ticket/${issue.id}`)"
        >
          <q-item-section avatar>
            <q-avatar :color="priorityAvatarColor(issue.priority)" size="40px">
              <q-icon name="build" :color="priorityIconColor(issue.priority)" size="18px" />
            </q-avatar>
          </q-item-section>
          <q-item-section>
            <div class="row items-center no-wrap q-mb-xs">
              <q-item-label class="text-weight-semibold ellipsis col">{{ issue.title }}</q-item-label>
              <span class="text-caption text-grey-5 q-ml-xs" style="white-space: nowrap">{{ relativeTime(issue.updated_at) }}</span>
            </div>
            <q-item-label caption class="ellipsis-2-lines text-grey-6">
              {{ issue.description || issue.category }}
            </q-item-label>
          </q-item-section>
          <q-item-section side top>
            <StatusBadge :value="issue.status" />
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <!-- New ticket FAB -->
    <q-page-sticky position="bottom-right" :offset="[18, 18]">
      <q-btn fab icon="add" color="secondary" aria-label="New repair" @click="createTicket" />
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
import { EMPTY_ICON_SIZE } from '../utils/designTokens'

const router = useRouter()
const $q = useQuasar()

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

function priorityAvatarColor(p: string) {
  return { urgent: 'red-1', high: 'orange-1', medium: 'light-blue-1', low: 'grey-2' }[p] ?? 'grey-2'
}

function priorityIconColor(p: string) {
  return { urgent: 'negative', high: 'warning', medium: 'info', low: 'grey-5' }[p] ?? 'grey-5'
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'now'
  if (mins < 60) return `${mins}m`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days}d`
  return new Date(iso).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })
}

async function loadIssues() {
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
  }
}

async function createTicket() {
  if (creating.value) return
  creating.value = true
  try {
    const res = await tenantApi.createConversation({ title: 'New repair request' })
    const conv = res.data
    await router.push(`/repairs/chat/${conv.id}`)
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to start chat. Please try again.', icon: 'error' })
  } finally {
    creating.value = false
  }
}

// Watcher in component per user requirement
watch(activeFilter, loadIssues)
onMounted(loadIssues)
</script>

<style scoped lang="scss">
.ticket-list-card {
  border-radius: var(--klikk-radius-card);
  border: 1px solid var(--klikk-border);
  overflow: hidden;
}

.ticket-item {
  min-height: 72px;
}

.ellipsis-2-lines {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
