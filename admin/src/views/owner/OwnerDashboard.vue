<template>
  <div class="space-y-5">
    <div v-if="stats" class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="card p-4">
        <div class="text-xs text-gray-400 uppercase tracking-wide">Properties</div>
        <div class="text-2xl font-bold text-navy mt-1">{{ stats.total_properties }}</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-gray-400 uppercase tracking-wide">Units</div>
        <div class="text-2xl font-bold text-gray-700 mt-1">{{ stats.total_units }}</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-gray-400 uppercase tracking-wide">Occupancy</div>
        <div class="text-2xl font-bold text-success-600 mt-1">{{ stats.occupancy_rate }}%</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-gray-400 uppercase tracking-wide">Active Issues</div>
        <div class="text-2xl font-bold text-warning-600 mt-1">{{ stats.active_issues }}</div>
      </div>
    </div>
    <div v-else class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div v-for="i in 4" :key="i" class="card p-4 animate-pulse">
        <div class="h-3 bg-gray-100 rounded w-2/3 mb-3"></div>
        <div class="h-7 bg-gray-100 rounded w-1/2"></div>
      </div>
    </div>

    <!-- Onboarding in progress -->
    <div v-if="pendingOnboardings.length > 0" class="card p-5">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-xs font-semibold uppercase tracking-wide text-navy flex items-center gap-1.5">
          <ClipboardList :size="13" /> Tenant onboarding in progress
        </h2>
      </div>
      <div class="space-y-3">
        <div v-for="ob in pendingOnboardings" :key="ob.id" class="flex items-center gap-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm font-medium text-gray-800 truncate">{{ ob.tenant_name }}</span>
              <span class="text-xs font-semibold text-gray-600 tabular-nums ml-2">{{ ob.progress }}%</span>
            </div>
            <div class="h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                class="h-full bg-navy rounded-full transition-all duration-500"
                :style="{ width: `${ob.progress}%` }"
              />
            </div>
            <p class="text-xs text-gray-400 mt-0.5 truncate">{{ ob.lease_number }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Overdue maintenance widget -->
    <OverdueMaintenanceWidget :max-preview="3" />

    <!-- AI Lease Builder CTA -->
    <RouterLink to="/owner/leases"
      class="card p-5 flex items-center gap-4 hover:shadow-md transition-shadow cursor-pointer group no-underline block"
    >
      <div class="w-12 h-12 rounded-xl bg-navy/8 flex items-center justify-center flex-shrink-0 group-hover:bg-navy/12 transition-colors">
        <Sparkles :size="22" class="text-navy" />
      </div>
      <div class="flex-1 min-w-0">
        <div class="text-sm font-semibold text-gray-900">Draft a Lease with AI</div>
        <div class="text-xs text-gray-500 mt-0.5">Generate an RHA-compliant lease agreement in minutes — just answer a few questions.</div>
      </div>
      <ChevronRight :size="18" class="text-gray-400 flex-shrink-0 group-hover:text-navy transition-colors" />
    </RouterLink>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { Sparkles, ChevronRight, ClipboardList } from 'lucide-vue-next'
import api from '../../api'
import OverdueMaintenanceWidget from '../../components/OverdueMaintenanceWidget.vue'

const stats = ref<any>(null)
const pendingOnboardings = ref<any[]>([])

onMounted(async () => {
  try {
    const [dashRes, onboardingRes] = await Promise.allSettled([
      api.get('/properties/owner/dashboard/'),
      api.get('/tenant/onboarding/?page_size=10'),
    ])
    if (dashRes.status === 'fulfilled') stats.value = dashRes.value.data
    if (onboardingRes.status === 'fulfilled') {
      const all = onboardingRes.value.data.results ?? onboardingRes.value.data
      pendingOnboardings.value = all.filter((ob: any) => !ob.is_complete).slice(0, 5)
    }
  } catch { /* ignore */ }
})
</script>
