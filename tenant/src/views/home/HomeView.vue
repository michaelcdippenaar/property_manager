<template>
  <div class="flex flex-col h-full overflow-hidden bg-surface" name="HomeView">
    <AppHeader :title="greeting" subtitle="Here's your overview" />

    <div ref="scrollEl" class="scroll-page page-with-tab-bar px-4 pt-4 pb-4 space-y-5" @scroll="onScroll">

      <!-- Signing CTA (if unsigned submission exists) -->
      <div v-if="signingCta" class="list-section touchable" @click="router.push({ name: 'lease' })">
        <div class="list-row gap-4">
          <div class="list-row-icon bg-accent/10">
            <FileSignature :size="20" class="text-accent" />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold text-gray-900">Lease ready to sign</p>
            <p class="text-xs text-gray-500 mt-0.5">Tap to view and sign your agreement</p>
          </div>
          <ChevronRight :size="18" class="text-gray-300 flex-shrink-0" />
        </div>
      </div>

      <!-- Active repairs -->
      <div>
        <div class="flex items-center justify-between mb-2 px-1">
          <p class="label-upper">Active Repairs</p>
          <button class="text-xs text-navy font-medium touchable" @click="router.push({ name: 'issues' })">View all</button>
        </div>
        <div v-if="issuesLoading" class="space-y-2">
          <div v-for="i in 2" :key="i" class="h-16 bg-white rounded-2xl animate-pulse" />
        </div>
        <div v-else-if="activeIssues.length === 0" class="list-section">
          <div class="px-5 py-6 text-center">
            <CheckCircle :size="32" class="text-success-500 mx-auto mb-2" />
            <p class="text-sm font-medium text-gray-700">No active repairs</p>
            <p class="text-xs text-gray-400 mt-1">Everything looks good!</p>
          </div>
        </div>
        <div v-else class="list-section">
          <div
            v-for="issue in activeIssues"
            :key="issue.id"
            class="list-row touchable"
            @click="router.push({ name: 'issue-detail', params: { id: issue.id } })"
          >
            <div class="list-row-icon" :class="priorityIconBg(issue.priority)">
              <Wrench :size="18" :class="priorityIconColor(issue.priority)" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-semibold text-gray-900 truncate">{{ issue.title }}</p>
              <p class="text-xs text-gray-500 mt-0.5 truncate">{{ issue.category }}</p>
            </div>
            <StatusBadge :value="issue.status" />
            <ChevronRight :size="16" class="text-gray-300 flex-shrink-0 ml-1" />
          </div>
        </div>
      </div>

      <!-- Property info preview -->
      <div>
        <div class="flex items-center justify-between mb-2 px-1">
          <p class="label-upper">Your Unit</p>
          <button class="text-xs text-navy font-medium touchable" @click="router.push({ name: 'lease' })">More info</button>
        </div>
        <div v-if="infoLoading" class="h-14 bg-white rounded-2xl animate-pulse" />
        <div v-else-if="infoItems.length > 0" class="list-section">
          <div
            v-for="item in infoItems.slice(0, 3)"
            :key="item.id"
            class="list-row"
          >
            <div class="list-row-icon bg-navy/8">
              <component :is="iconForType(item.icon_type)" :size="18" class="text-navy" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-xs text-gray-500">{{ item.label }}</p>
              <p class="text-sm font-medium text-gray-900 truncate">{{ maskValue(item) }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- AI Chat FAB -->
    <button class="fab" @click="router.push({ name: 'chat-list' })">
      <MessageCircle :size="26" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Wrench, ChevronRight, CheckCircle, MessageCircle, FileSignature, Wifi, Zap, Droplets, Lock, Shield } from 'lucide-vue-next'
import AppHeader from '../../components/AppHeader.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const scrollEl = ref<HTMLElement | null>(null)
const isScrolled = ref(false)

const activeIssues = ref<any[]>([])
const issuesLoading = ref(true)
const infoItems = ref<any[]>([])
const infoLoading = ref(true)
const signingCta = ref(false)

const greeting = computed(() => {
  const hour = new Date().getHours()
  const name = auth.user?.full_name?.split(' ')[0] || 'there'
  if (hour < 12) return `Good morning, ${name}`
  if (hour < 17) return `Good afternoon, ${name}`
  return `Good evening, ${name}`
})

function onScroll() {
  isScrolled.value = (scrollEl.value?.scrollTop ?? 0) > 20
}

function priorityIconBg(p: string) {
  return { urgent: 'bg-danger-50', high: 'bg-warning-50', medium: 'bg-info-50', low: 'bg-gray-100' }[p] ?? 'bg-gray-100'
}
function priorityIconColor(p: string) {
  return { urgent: 'text-danger-600', high: 'text-warning-600', medium: 'text-info-600', low: 'text-gray-500' }[p] ?? 'text-gray-500'
}

function iconForType(type: string) {
  return { wifi: Wifi, electricity: Zap, water: Droplets, alarm: Shield, gate: Lock }[type] ?? Lock
}

function maskValue(item: any) {
  const sensitive = ['wifi', 'alarm', 'gate', 'key']
  return sensitive.includes(item.icon_type) ? '••••••••' : item.value
}

onMounted(async () => {
  try {
    const [issuesRes, infoRes] = await Promise.allSettled([
      api.get('/maintenance/', { params: { status: 'open,in_progress', page_size: 3 } }),
      api.get('/properties/unit-info/'),
    ])
    if (issuesRes.status === 'fulfilled') activeIssues.value = issuesRes.value.data.results ?? issuesRes.value.data
    if (infoRes.status === 'fulfilled') infoItems.value = infoRes.value.data.results ?? infoRes.value.data

    // Check for pending signing
    try {
      const leasesRes = await api.get('/leases/')
      const leases = leasesRes.data.results ?? leasesRes.data
      if (leases.length > 0) {
        const subsRes = await api.get('/esigning/submissions/', { params: { lease: leases[0].id } })
        const subs = subsRes.data.results ?? subsRes.data
        signingCta.value = subs.some((s: any) =>
          s.signers?.some((sg: any) => sg.email === auth.user?.email && sg.status === 'pending')
        )
      }
    } catch { /* signing CTA is optional */ }
  } finally {
    issuesLoading.value = false
    infoLoading.value = false
  }
})
</script>
