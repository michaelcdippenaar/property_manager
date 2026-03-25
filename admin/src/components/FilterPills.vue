<template>
  <div class="flex items-center gap-1.5 flex-wrap">
    <button
      v-for="option in options"
      :key="option.value"
      @click="$emit('update:modelValue', option.value)"
      class="pill"
      :class="modelValue === option.value ? 'pill-active' : ''"
    >
      <component v-if="option.icon" :is="option.icon" :size="13" class="flex-shrink-0" />
      {{ option.label }}
      <span v-if="option.count != null" class="text-xs opacity-70">({{ option.count }})</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

export interface PillOption {
  label: string
  value: string
  count?: number
  icon?: Component
}

defineProps<{
  modelValue: string
  options: PillOption[]
}>()

defineEmits<{ 'update:modelValue': [value: string] }>()
</script>
