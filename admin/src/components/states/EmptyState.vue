<template>
  <div class="flex flex-col items-center justify-center py-14 px-6 text-center">
    <!-- Icon ring -->
    <div class="w-14 h-14 rounded-full bg-navy/5 flex items-center justify-center text-navy/40 mb-4">
      <component :is="icon" :size="24" />
    </div>

    <!-- Heading -->
    <h3 class="text-sm font-semibold text-gray-900 mb-1">{{ title }}</h3>

    <!-- Description -->
    <p v-if="description" class="text-xs text-gray-400 max-w-xs mb-5 leading-relaxed">{{ description }}</p>
    <div v-else class="mb-5" />

    <!-- Primary CTA slot (e.g. a button) -->
    <slot />

    <!-- Secondary link slot (e.g. a router-link or plain text link) -->
    <div v-if="$slots.secondary" class="mt-3">
      <slot name="secondary" />
    </div>
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
