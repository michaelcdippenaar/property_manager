<template>
  <div class="space-y-5">
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="card p-5 animate-pulse space-y-2">
        <div class="h-4 bg-gray-100 rounded w-1/3"></div>
        <div class="h-3 bg-gray-100 rounded w-2/3"></div>
      </div>
    </div>
    <EmptyState
      v-else-if="!properties.length"
      title="No properties found"
      :icon="Building2"
    />
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="p in properties" :key="p.id" class="card p-5 space-y-3">
        <div class="font-medium text-gray-900">{{ p.name }}</div>
        <div class="text-xs text-gray-500">{{ p.city }} — {{ p.property_type }}</div>
        <div class="grid grid-cols-3 gap-2 text-center text-sm">
          <div><div class="text-lg font-bold text-navy">{{ p.unit_count }}</div><div class="text-micro text-gray-400">Units</div></div>
          <div><div class="text-lg font-bold text-success-600">{{ p.occupied_units }}</div><div class="text-micro text-gray-400">Occupied</div></div>
          <div><div class="text-lg font-bold text-warning-600">{{ p.active_issues }}</div><div class="text-micro text-gray-400">Issues</div></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Building2 } from 'lucide-vue-next'
import api from '../../api'
import EmptyState from '../../components/EmptyState.vue'

const loading = ref(true)
const properties = ref<any[]>([])

onMounted(async () => {
  try {
    const { data } = await api.get('/properties/owner/properties/')
    properties.value = data
  } finally {
    loading.value = false
  }
})
</script>
