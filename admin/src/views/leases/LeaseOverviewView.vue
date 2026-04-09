<template>
  <div class="space-y-6">
    <p class="text-sm text-gray-500">Lease portfolio at a glance.</p>

    <!-- Stat cards -->
    <div v-if="loading" class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div v-for="i in 4" :key="i" class="card p-5 animate-pulse">
        <div class="h-3 bg-gray-100 rounded w-1/2 mb-3"></div>
        <div class="h-7 bg-gray-100 rounded w-1/3"></div>
      </div>
    </div>

    <div v-else class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <RouterLink
        v-for="card in statCards"
        :key="card.label"
        :to="card.to"
        class="card p-5 hover:shadow-sm transition-shadow group"
      >
        <div class="flex items-center gap-2 text-xs text-gray-400 mb-1">
          <component :is="card.icon" :size="14" />
          {{ card.label }}
        </div>
        <div class="text-2xl font-bold text-gray-900">{{ card.value }}</div>
        <div v-if="card.sub" class="text-xs text-gray-400 mt-1">{{ card.sub }}</div>
      </RouterLink>
    </div>

    <!-- Quick actions -->
    <div class="flex items-center gap-3">
      <button class="btn-primary" @click="router.push('/leases/build')">
        <Plus :size="15" /> New Lease
      </button>
      <button class="btn-ghost" @click="router.push('/leases/templates')">
        <FileSignature :size="15" /> Templates
      </button>
      <button class="btn-ghost" @click="router.push('/leases/status')">
        <Activity :size="15" /> Signing Status
      </button>
    </div>

    <!-- Expiring soon -->
    <div v-if="expiringSoon.length" class="card overflow-hidden">
      <div class="px-5 py-3 border-b border-gray-100">
        <h3 class="text-sm font-semibold text-gray-900">Expiring within 60 days</h3>
      </div>
      <div class="divide-y divide-gray-100">
        <div
          v-for="lease in expiringSoon"
          :key="lease.id"
          class="px-5 py-3 flex items-center justify-between"
        >
          <div>
            <div class="text-sm font-medium text-gray-900">
              {{ lease.all_tenant_names?.[0] || lease.tenant_name || '—' }}
            </div>
            <div class="text-xs text-gray-400">{{ lease.unit_label }}</div>
          </div>
          <div class="text-right">
            <div class="text-sm font-semibold text-amber-600">
              {{ daysUntil(lease.end_date) }} days left
            </div>
            <div class="text-xs text-gray-400">Ends {{ formatDate(lease.end_date) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'
import { FileText, FolderOpen, PenTool, Calendar, Plus, FileSignature, Activity } from 'lucide-vue-next'
import { useLeasesStore } from '../../stores/leases'

const router = useRouter()
const leasesStore = useLeasesStore()
const loading = ref(true)
const leases = ref<any[]>([])
const draftCount = ref(0)
const signingCount = ref(0)

onMounted(async () => {
  await Promise.all([loadLeases(), loadDrafts(), loadSigning()])
  loading.value = false
})

async function loadLeases() {
  try {
    await leasesStore.fetchAll()
    leases.value = leasesStore.list
  } catch { /* silent */ }
}

async function loadDrafts() {
  try {
    const { data } = await api.get('/leases/builder/drafts/')
    draftCount.value = Array.isArray(data) ? data.length : 0
  } catch { /* silent */ }
}

async function loadSigning() {
  try {
    const { data } = await api.get('/esigning/submissions/', { params: { status: 'pending' } })
    const items = data.results ?? data
    signingCount.value = Array.isArray(items) ? items.length : 0
  } catch { /* silent */ }
}

const activeCount = computed(() => leases.value.filter(l => l.status === 'active').length)
const expiredCount = computed(() => leases.value.filter(l => l.status === 'expired' || l.status === 'terminated').length)

const expiringSoon = computed(() => {
  const now = new Date()
  const cutoff = new Date(now.getTime() + 60 * 24 * 60 * 60 * 1000)
  return leases.value
    .filter(l => l.status === 'active' && l.end_date)
    .filter(l => {
      const end = new Date(l.end_date)
      return end >= now && end <= cutoff
    })
    .sort((a, b) => new Date(a.end_date).getTime() - new Date(b.end_date).getTime())
})

const statCards = computed(() => [
  { label: 'Active Leases', value: activeCount.value, icon: FileText, to: '/leases?tab=active' },
  { label: 'Drafts', value: draftCount.value, icon: FolderOpen, to: '/leases?tab=draft' },
  { label: 'Awaiting Signing', value: signingCount.value, icon: PenTool, to: '/leases/status' },
  {
    label: 'Expiring Soon',
    value: expiringSoon.value.length,
    icon: Calendar,
    to: '/leases?tab=active',
    sub: expiringSoon.value.length ? 'Within 60 days' : '',
  },
])

function daysUntil(d: string) {
  const now = new Date()
  const end = new Date(d)
  return Math.max(0, Math.ceil((end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)))
}

function formatDate(d: string) {
  return d ? new Date(d).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' }) : '—'
}
</script>
