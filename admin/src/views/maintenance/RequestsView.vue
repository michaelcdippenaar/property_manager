<template>
  <div class="space-y-5">
    <PageHeader
      title="Maintenance issues"
      subtitle="Track, assign, and resolve maintenance requests across all properties."
      :crumbs="[{ label: 'Dashboard', to: '/' }, { label: 'Maintenance' }, { label: 'Issues' }]"
    />

    <!-- Tabs: Active / Archived -->
    <div class="flex items-center gap-0 border-b border-gray-200 -mb-1">
      <button
        class="px-4 py-2 text-sm font-medium transition-colors relative"
        :class="activeTab === 'active' ? 'text-navy' : 'text-gray-400 hover:text-gray-600'"
        @click="switchTab('active')"
      >
        Active
        <span v-if="activeTab === 'active'" class="absolute bottom-0 left-0 right-0 h-0.5 bg-navy rounded-full" />
      </button>
      <button
        class="px-4 py-2 text-sm font-medium transition-colors relative flex items-center gap-1.5"
        :class="activeTab === 'archived' ? 'text-navy' : 'text-gray-400 hover:text-gray-600'"
        @click="switchTab('archived')"
      >
        <Archive :size="13" />
        Archived
        <span v-if="activeTab === 'archived'" class="absolute bottom-0 left-0 right-0 h-0.5 bg-navy rounded-full" />
      </button>
    </div>

    <!-- Filter pills -->
    <FilterPills v-model="activeFilter" :options="filterOptions" @update:modelValue="loadRequests()" />

    <!-- Loading skeletons -->
    <LoadingState v-if="loading" variant="cards" :rows="6" />

    <ErrorState
      v-else-if="loadError"
      :on-retry="loadRequests"
      :offline="isOffline"
    />

    <!-- Request cards -->
    <div v-else class="space-y-3">
      <button
        v-for="req in requests"
        :key="req.id"
        type="button"
        class="w-full text-left rounded-xl border px-4 py-3 transition-all border-l-4 bg-white hover:bg-gray-50 hover:border-gray-300 border-gray-200"
        :class="priorityBorderLeft(req.priority)"
        @click="$router.push({ name: 'maintenance-detail', params: { id: req.id } })"
      >
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="text-xs font-mono text-gray-400">{{ req.ticket_reference || `#${req.id}` }}</span>
              <span class="font-medium text-gray-900 text-sm">{{ req.title }}</span>
            </div>
            <p class="text-xs text-gray-500 mt-1 line-clamp-1">{{ req.description }}</p>
          </div>
          <div class="flex items-center gap-2 shrink-0 flex-wrap justify-end">
            <SLACountdownChip
              :resolve-deadline="req.sla_resolve_deadline"
              :resolve-pct="req.sla_resolve_pct"
              :is-overdue="req.is_sla_overdue"
              :status="req.status"
            />
            <span :class="priorityBadge(req.priority)" class="text-micro">{{ req.priority }}</span>
            <span :class="statusBadge(req.status)" class="text-micro">{{ req.status?.replace('_', ' ') }}</span>
          </div>
        </div>
        <div class="flex items-center gap-3 mt-2 text-xs text-gray-400">
          <span class="flex items-center gap-1"><Clock :size="10" /> {{ formatDateTime(req.created_at) }}</span>
          <span v-if="req.tenant_name" class="flex items-center gap-1"><User :size="10" /> {{ req.tenant_name }}</span>
          <span v-if="req.supplier_name" class="flex items-center gap-1"><Truck :size="10" /> {{ req.supplier_name }}</span>
          <span v-if="req.activity_count" class="flex items-center gap-1"><MessageCircle :size="10" /> {{ req.activity_count }}</span>
        </div>
      </button>

      <EmptyState
        v-if="!requests.length"
        title="No maintenance requests"
        description="No maintenance requests for this filter."
        :icon="Wrench"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '../../api'
import { Clock, Truck, Archive, MessageCircle, User, Wrench } from 'lucide-vue-next'
import EmptyState from '../../components/EmptyState.vue'
import LoadingState from '../../components/states/LoadingState.vue'
import ErrorState from '../../components/states/ErrorState.vue'
import FilterPills from '../../components/FilterPills.vue'
import PageHeader from '../../components/PageHeader.vue'
import SLACountdownChip from '../../components/SLACountdownChip.vue'

const loading = ref(true)
const loadError = ref(false)
const isOffline = ref(false)
const activeFilter = ref('all')
const requests = ref<any[]>([])
const activeTab = ref<'active' | 'archived'>('active')
let listSocket: WebSocket | null = null

const filterOptions = computed(() =>
  activeTab.value === 'archived'
    ? [{ label: 'All Closed', value: 'all' }]
    : [
        { label: 'All', value: 'all' },
        { label: 'Open', value: 'open' },
        { label: 'In Progress', value: 'in_progress' },
        { label: 'Resolved', value: 'resolved' },
      ]
)

function switchTab(tab: 'active' | 'archived') {
  activeTab.value = tab
  activeFilter.value = 'all'
  loadRequests()
}

onMounted(async () => {
  await loadRequests()
  connectListSocket()
})

onUnmounted(() => {
  if (listSocket) {
    listSocket.onclose = null
    listSocket.close()
    listSocket = null
  }
})

function getWsBase() {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL
  const apiUrl = import.meta.env.VITE_API_URL || ''
  if (apiUrl) {
    return apiUrl.replace(/^http/, 'ws').replace(/\/api\/v1\/?$/, '')
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}`
}

function connectListSocket() {
  const host = getWsBase()
  const token = localStorage.getItem('access_token') || ''
  listSocket = new WebSocket(`${host}/ws/maintenance/updates/?token=${token}`)

  listSocket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.event === 'issue_created' || data.event === 'issue_updated') {
      loadRequests()
    }
  }

  listSocket.onerror = () => {
    console.warn('Maintenance list WebSocket failed')
  }

  listSocket.onclose = () => {
    setTimeout(() => {
      if (!listSocket || listSocket.readyState === WebSocket.CLOSED) {
        connectListSocket()
      }
    }, 5000)
  }
}

async function loadRequests() {
  loading.value = true
  loadError.value = false
  isOffline.value = false
  try {
    const params: Record<string, string> = {}
    if (activeTab.value === 'archived') {
      params.status = 'closed'
    } else if (activeFilter.value !== 'all') {
      params.status = activeFilter.value
    } else {
      params.exclude_status = 'closed'
    }
    const { data } = await api.get('/maintenance/', { params })
    requests.value = data.results ?? data
  } catch (err: any) {
    isOffline.value = !navigator.onLine
    loadError.value = true
  } finally {
    loading.value = false
  }
}

function priorityBadge(p: string) {
  return { urgent: 'badge-red', high: 'badge-amber', medium: 'badge-blue', low: 'badge-green' }[p] ?? 'badge-gray'
}

function priorityBorderLeft(p: string) {
  return {
    urgent: 'border-l-red-500',
    high: 'border-l-amber-400',
    medium: 'border-l-blue-400',
    low: 'border-l-green-400',
  }[p] ?? 'border-l-gray-300'
}

function statusBadge(s: string) {
  return { open: 'badge-blue', in_progress: 'badge-amber', resolved: 'badge-green', closed: 'badge-gray' }[s] ?? 'badge-gray'
}

function formatDateTime(iso: string) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('en-ZA') + ' ' + d.toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' })
}
</script>
