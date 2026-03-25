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
    <div v-else class="text-center text-gray-400 py-16">Loading...</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'

const stats = ref<any>(null)

onMounted(async () => {
  try {
    const { data } = await api.get('/properties/owner/dashboard/')
    stats.value = data
  } catch { /* ignore */ }
})
</script>
