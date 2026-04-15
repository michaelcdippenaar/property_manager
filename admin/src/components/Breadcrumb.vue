<template>
  <nav v-if="items.length" aria-label="Breadcrumb" class="flex items-center text-xs text-gray-500">
    <ol class="flex items-center flex-wrap gap-x-1.5 gap-y-0.5">
      <li v-for="(item, i) in items" :key="i" class="flex items-center gap-x-1.5">
        <RouterLink
          v-if="item.to && i < items.length - 1"
          :to="item.to"
          class="hover:text-navy hover:underline underline-offset-2 transition-colors"
        >
          {{ item.label }}
        </RouterLink>
        <span
          v-else
          :class="i === items.length - 1 ? 'font-semibold text-gray-700' : ''"
          :aria-current="i === items.length - 1 ? 'page' : undefined"
        >
          {{ item.label }}
        </span>
        <ChevronRight
          v-if="i < items.length - 1"
          :size="14"
          class="text-gray-400 flex-shrink-0"
          aria-hidden="true"
        />
      </li>
    </ol>
  </nav>
</template>

<script setup lang="ts">
import { RouterLink, type RouteLocationRaw } from 'vue-router'
import { ChevronRight } from 'lucide-vue-next'

export interface BreadcrumbItem {
  label: string
  to?: RouteLocationRaw
}

defineProps<{ items: BreadcrumbItem[] }>()
</script>
