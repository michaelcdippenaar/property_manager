<template>
  <div
    class="flex items-start gap-3 rounded-xl px-3 py-2.5 transition-colors"
    :class="[
      done ? 'bg-success-50 border border-success-100' : deferred ? 'bg-gray-50 border border-gray-100' : 'bg-white border border-gray-100 hover:border-gray-200',
    ]"
  >
    <!-- Check icon / circle -->
    <div
      class="mt-0.5 w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0"
      :class="done ? 'bg-success-500' : deferred ? 'bg-gray-200' : 'bg-gray-100'"
    >
      <Check v-if="done" :size="12" class="text-white" />
      <span v-else class="block w-2 h-2 rounded-full" :class="deferred ? 'bg-gray-300' : 'bg-gray-300'" />
    </div>

    <!-- Text -->
    <div class="flex-1 min-w-0">
      <p class="text-sm font-medium" :class="done ? 'text-success-700 line-through opacity-70' : deferred ? 'text-gray-400' : 'text-gray-800'">
        {{ label }}
        <span v-if="deferred" class="ml-1 text-xs font-normal text-gray-400 no-underline">(v2)</span>
      </p>
      <p class="text-xs text-gray-400 mt-0.5">{{ description }}</p>
      <p v-if="done && doneAt" class="text-micro text-gray-400 mt-0.5">
        Completed {{ formatDateTime(doneAt) }}
      </p>
    </div>

    <!-- CTA -->
    <button
      v-if="!done"
      class="flex-shrink-0 btn-ghost btn-sm text-xs"
      :class="deferred ? 'opacity-50' : ''"
      :disabled="loading"
      @click.stop="emit('tick')"
    >
      <Loader2 v-if="loading" :size="12" class="animate-spin" />
      <span v-else>{{ ctaLabel }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { Check, Loader2 } from 'lucide-vue-next'

defineProps<{
  label: string
  description: string
  done: boolean
  doneAt?: string | null
  loading?: boolean
  ctaLabel?: string
  deferred?: boolean
}>()

const emit = defineEmits<{
  (e: 'tick'): void
}>()

function formatDateTime(iso: string): string {
  try {
    return new Intl.DateTimeFormat('en-ZA', {
      day: 'numeric', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}
</script>
