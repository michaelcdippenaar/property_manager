<template>
  <div class="relative" :class="wrapClass">
    <Search :size="14" class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
    <input
      :value="modelValue"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      class="input pl-8"
      :placeholder="placeholder"
    />
    <button
      v-if="modelValue"
      @click="$emit('update:modelValue', '')"
      class="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 text-gray-400 hover:text-gray-600 rounded transition-colors"
    >
      <X :size="13" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { Search, X } from 'lucide-vue-next'

withDefaults(defineProps<{
  modelValue: string
  placeholder?: string
  wrapClass?: string
}>(), {
  placeholder: 'Search…',
  wrapClass: 'max-w-xs',
})

defineEmits<{ 'update:modelValue': [value: string] }>()
</script>
