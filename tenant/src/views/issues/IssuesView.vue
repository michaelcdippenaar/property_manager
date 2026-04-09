<template>
  <div class="flex flex-col h-full overflow-hidden bg-surface" name="IssuesView">
    <AppHeader title="Repairs" />

    <!-- Filter pills -->
    <div class="bg-navy px-4 pb-3 flex gap-2 overflow-x-auto" style="scrollbar-width: none">
      <button
        v-for="f in filters"
        :key="f.value"
        class="pill flex-shrink-0 text-xs py-1 px-3"
        :class="activeFilter === f.value ? 'pill-active' : ''"
        @click="setFilter(f.value)"
      >{{ f.label }}</button>
    </div>

    <div ref="scrollEl" class="scroll-page page-with-tab-bar px-4 pt-4 pb-4" @scroll="onScroll">
      <!-- Loading -->
      <div v-if="loading" class="space-y-2">
        <div v-for="i in 4" :key="i" class="h-20 bg-white rounded-2xl animate-pulse" />
      </div>

      <!-- Empty -->
      <div v-else-if="issues.length === 0" class="flex flex-col items-center justify-center pt-20 text-center">
        <div class="w-16 h-16 bg-navy/5 rounded-2xl flex items-center justify-center mb-4">
          <Wrench :size="28" class="text-navy/30" />
        </div>
        <p class="font-semibold text-gray-700">No repairs found</p>
        <p class="text-sm text-gray-400 mt-1">{{ activeFilter === 'all' ? 'Log a new repair request below' : 'Try a different filter' }}</p>
      </div>

      <!-- Issue list -->
      <div v-else class="list-section">
        <div
          v-for="issue in issues"
          :key="issue.id"
          class="list-row touchable"
          @click="router.push({ name: 'issue-detail', params: { id: issue.id } })"
        >
          <!-- Priority left accent -->
          <div class="w-1 h-10 rounded-full flex-shrink-0" :class="priorityAccent(issue.priority)" />
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold text-gray-900 truncate">{{ issue.title }}</p>
            <p class="text-xs text-gray-500 mt-0.5 truncate">{{ issue.category }} · {{ formatDate(issue.created_at) }}</p>
          </div>
          <StatusBadge :value="issue.status" />
          <ChevronRight :size="16" class="text-gray-300 ml-1 flex-shrink-0" />
        </div>
      </div>
    </div>

    <!-- FAB -->
    <button class="fab" @click="router.push({ name: 'report-issue' })">
      <Plus :size="26" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Wrench, ChevronRight, Plus } from 'lucide-vue-next'
import AppHeader from '../../components/AppHeader.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import api from '../../api'

const router = useRouter()
const scrollEl = ref<HTMLElement | null>(null)
const issues = ref<any[]>([])
const loading = ref(true)
const activeFilter = ref('all')

const filters = [
  { value: 'all',         label: 'All' },
  { value: 'open',        label: 'Open' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'resolved',    label: 'Resolved' },
  { value: 'closed',      label: 'Closed' },
]

function onScroll() {}

function priorityAccent(p: string) {
  return { urgent: 'bg-danger-500', high: 'bg-warning-500', medium: 'bg-info-500', low: 'bg-gray-300' }[p] ?? 'bg-gray-300'
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })
}

async function loadIssues() {
  loading.value = true
  try {
    const params: any = { page_size: 50 }
    if (activeFilter.value !== 'all') params.status = activeFilter.value
    const res = await api.get('/maintenance/', { params })
    issues.value = res.data.results ?? res.data
  } finally {
    loading.value = false
  }
}

function setFilter(v: string) {
  activeFilter.value = v
}

watch(activeFilter, loadIssues)
onMounted(loadIssues)
</script>
