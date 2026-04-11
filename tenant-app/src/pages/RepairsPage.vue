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
      <q-skeleton v-for="i in 4" :key="i" type="QItem" height="64px" class="rounded-borders" />
    </div>

    <!-- Empty -->
    <div v-else-if="issues.length === 0" class="text-center q-pt-xl">
      <q-icon name="build" :size="EMPTY_ICON_SIZE" color="grey-3" class="q-mb-md" />
      <div class="text-weight-semibold text-grey-8">No repairs found</div>
      <div class="text-caption text-grey-5 q-mt-xs">
        {{ activeFilter === 'all' ? 'Log a new repair request below' : 'Try a different filter' }}
      </div>
    </div>

    <!-- Issue list -->
    <q-card v-else flat>
      <q-list separator>
        <q-item
          v-for="issue in issues"
          :key="issue.id"
          clickable
          v-ripple
          @click="$router.push(`/repairs/${issue.id}`)"
        >
          <!-- Priority accent bar -->
          <q-item-section avatar>
            <div
              class="rounded-borders"
              :style="{ width: '4px', height: '40px', background: priorityAccentHex(issue.priority) }"
            />
          </q-item-section>
          <q-item-section>
            <q-item-label class="text-weight-semibold ellipsis">{{ issue.title }}</q-item-label>
            <q-item-label caption class="ellipsis">
              {{ issue.category }} · {{ formatDateShort(issue.created_at) }}
            </q-item-label>
          </q-item-section>
          <q-item-section side>
            <StatusBadge :value="issue.status" />
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <!-- Report FAB -->
    <q-page-sticky position="bottom-right" :offset="[18, 18]">
      <q-btn fab icon="add" color="secondary" @click="$router.push('/repairs/report')" aria-label="Report repair" />
    </q-page-sticky>

  </q-page>
</template>

<script setup lang="ts">
defineOptions({ name: 'RepairsPage' })

import { ref, watch, onMounted } from 'vue'
import StatusBadge from '../components/StatusBadge.vue'
import * as tenantApi from '../services/api'
import type { MaintenanceIssue } from '../services/api'
import { EMPTY_ICON_SIZE } from '../utils/designTokens'

const issues       = ref<MaintenanceIssue[]>([])
const loading      = ref(true)
const activeFilter = ref('all')

const filters = [
  { value: 'all',         label: 'All' },
  { value: 'open',        label: 'Open' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'resolved',    label: 'Resolved' },
  { value: 'closed',      label: 'Closed' },
]

function priorityAccentHex(p: string) {
  return { urgent: '#DB2828', high: '#F2C037', medium: '#31CCEC', low: '#9e9e9e' }[p] ?? '#9e9e9e'
}

function formatDateShort(d: string) {
  return new Date(d).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })
}

async function loadIssues() {
  loading.value = true
  try {
    const params: { status?: string; page_size: number } = { page_size: 50 }
    if (activeFilter.value !== 'all') params.status = activeFilter.value
    const res = await tenantApi.listIssues(params)
    issues.value = res.data.results ?? res.data as MaintenanceIssue[]
  } finally {
    loading.value = false
  }
}

// Watcher in component per user requirement
watch(activeFilter, loadIssues)
onMounted(loadIssues)
</script>
