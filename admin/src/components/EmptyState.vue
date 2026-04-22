<!-- Re-exports from states/EmptyState for backward-compatibility.
     New code should import directly from ./states/EmptyState.vue -->
<template>
  <StatesEmptyState v-bind="$props">
    <slot />
    <template v-if="$slots.secondary" #secondary>
      <slot name="secondary" />
    </template>
  </StatesEmptyState>
</template>

<script setup lang="ts">
import StatesEmptyState from './states/EmptyState.vue'
import type { Component } from 'vue'

withDefaults(defineProps<{
  title: string
  description?: string
  icon?: Component
}>(), {})
</script>
