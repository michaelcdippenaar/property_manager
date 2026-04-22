<template>
  <div class="list-row">
    <div
      class="list-row-icon flex-shrink-0"
      :class="done ? 'bg-success-50' : 'bg-gray-100'"
    >
      <CheckCircle2 v-if="done" :size="18" class="text-success-500" />
      <Mail v-else-if="icon === 'mail'" :size="18" class="text-gray-400" />
      <Banknote v-else-if="icon === 'banknote'" :size="18" class="text-gray-400" />
      <CalendarDays v-else-if="icon === 'calendar'" :size="18" class="text-gray-400" />
      <KeyRound v-else-if="icon === 'key'" :size="18" class="text-gray-400" />
      <Phone v-else-if="icon === 'phone'" :size="18" class="text-gray-400" />
      <Circle v-else :size="18" class="text-gray-400" />
    </div>
    <div class="flex-1 min-w-0">
      <p
        class="text-sm font-semibold"
        :class="done ? 'text-success-700' : 'text-gray-800'"
      >{{ label }}</p>
      <p class="text-xs mt-0.5" :class="done ? 'text-success-600' : 'text-gray-400'">{{ description }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { CheckCircle2, Mail, Banknote, CalendarDays, KeyRound, Phone, Circle } from 'lucide-vue-next'

defineProps<{
  icon: 'mail' | 'banknote' | 'calendar' | 'key' | 'phone'
  label: string
  description: string
  done: boolean
}>()
</script>
