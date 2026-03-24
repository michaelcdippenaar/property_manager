<template>
  <div class="space-y-5">
    <!-- Sub-navigation tabs -->
    <div class="flex items-center gap-1 border-b border-gray-200">
      <RouterLink
        v-for="tab in tabs"
        :key="tab.to"
        :to="tab.to"
        class="flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px"
        :class="isActive(tab.to)
          ? 'border-navy text-navy'
          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
      >
        <component :is="tab.icon" :size="15" />
        {{ tab.label }}
      </RouterLink>
    </div>

    <RouterView />
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { Wrench, Truck } from 'lucide-vue-next'

const route = useRoute()

const tabs = [
  { to: '/maintenance',           icon: Wrench, label: 'Requests' },
  { to: '/maintenance/suppliers',  icon: Truck,  label: 'Suppliers' },
]

function isActive(to: string) {
  if (to === '/maintenance') return route.path === '/maintenance'
  return route.path.startsWith(to)
}
</script>
