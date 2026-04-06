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
        <div class="text-2xl font-bold text-green-600 mt-1">{{ stats.occupancy_rate }}%</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-gray-400 uppercase tracking-wide">Active Issues</div>
        <div class="text-2xl font-bold text-amber-600 mt-1">{{ stats.active_issues }}</div>
      </div>
    </div>
    <div v-else class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div v-for="i in 4" :key="i" class="card p-4 animate-pulse">
        <div class="h-3 bg-gray-100 rounded w-2/3 mb-3"></div>
        <div class="h-7 bg-gray-100 rounded w-1/2"></div>
      </div>
    </div>

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
import { Sparkles, ChevronRight } from 'lucide-vue-next'
import api from '../../api'

const stats = ref<any>(null)

onMounted(async () => {
  try {
    const { data } = await api.get('/properties/owner/dashboard/')
    stats.value = data
  } catch { /* ignore */ }
})
</script>
