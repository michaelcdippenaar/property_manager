<template>
  <div class="flex flex-col items-center justify-center py-12 px-4 text-center">
    <div class="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center text-gray-400 mb-4">
      <component :is="icon" :size="22" />
    </div>
    <h3 class="text-sm font-semibold text-gray-900 mb-1">{{ title }}</h3>
    <p v-if="description" class="text-xs text-gray-400 max-w-xs mb-4">{{ description }}</p>
    <slot />
  </div>
</template>

<script setup lang="ts">
import { Inbox } from 'lucide-vue-next'
import type { Component } from 'vue'

withDefaults(defineProps<{
  title: string
  description?: string
  icon?: Component
}>(), {
  icon: Inbox as any,
})
</script>
