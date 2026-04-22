<template>
  <!-- Table skeleton: renders skeleton rows inside a <tbody> replacement -->
  <template v-if="variant === 'table'">
    <div
      role="status"
      aria-busy="true"
      :aria-label="label"
      class="divide-y divide-gray-100"
    >
      <div
        v-for="i in rows"
        :key="i"
        class="flex items-center gap-4 px-4 py-3 animate-pulse"
      >
        <div v-if="showAvatar" class="w-9 h-9 rounded-full bg-gray-100 flex-shrink-0" />
        <div class="flex-1 space-y-1.5">
          <div class="h-3.5 bg-gray-100 rounded" :style="`width: ${widths[i % widths.length]}`" />
          <div v-if="doubleRow" class="h-2.5 bg-gray-50 rounded w-1/3" />
        </div>
        <div v-if="showBadge" class="h-5 w-14 bg-gray-100 rounded-full" />
      </div>
    </div>
  </template>

  <!-- Card skeleton: renders stacked card placeholders -->
  <template v-else-if="variant === 'cards'">
    <div
      role="status"
      aria-busy="true"
      :aria-label="label"
      class="grid gap-4"
      :class="gridClass"
    >
      <div
        v-for="i in rows"
        :key="i"
        class="card p-5 space-y-3 animate-pulse"
      >
        <div class="h-3 bg-gray-100 rounded w-1/4" />
        <div class="h-4 bg-gray-100 rounded w-2/3" />
        <div class="h-3 bg-gray-100 rounded w-full" />
        <div class="h-3 bg-gray-50 rounded w-4/5" />
      </div>
    </div>
  </template>

  <!-- Detail skeleton: full-page detail view placeholder -->
  <template v-else>
    <div
      role="status"
      aria-busy="true"
      :aria-label="label"
      class="space-y-4 animate-pulse"
    >
      <div class="h-7 bg-gray-100 rounded w-48" />
      <div class="h-4 bg-gray-50 rounded w-72" />
      <div class="card p-5 space-y-3 mt-4">
        <div class="h-4 bg-gray-100 rounded w-1/3" />
        <div class="h-4 bg-gray-100 rounded w-2/3" />
        <div class="h-4 bg-gray-100 rounded w-1/2" />
        <div class="h-4 bg-gray-50 rounded w-5/6" />
        <div class="h-4 bg-gray-50 rounded w-3/4" />
      </div>
    </div>
  </template>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  /** Skeleton layout variant */
  variant?: 'table' | 'cards' | 'detail' | 'form'
  /** Number of skeleton rows / cards to render */
  rows?: number
  /** Show circular avatar placeholder in table rows */
  showAvatar?: boolean
  /** Show badge placeholder at the right of table rows */
  showBadge?: boolean
  /** Show a second, shorter line beneath the primary skeleton line */
  doubleRow?: boolean
  /** Columns for card grid (Tailwind class fragment, e.g. "grid-cols-1 md:grid-cols-3") */
  gridCols?: string
  /** aria-label for the status region */
  label?: string
}>(), {
  variant: 'table',
  rows: 5,
  showAvatar: false,
  showBadge: false,
  doubleRow: false,
  gridCols: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
  label: 'Loading…',
})

const widths = ['60%', '75%', '50%', '80%', '65%']

const gridClass = computed(() => props.gridCols)
</script>
