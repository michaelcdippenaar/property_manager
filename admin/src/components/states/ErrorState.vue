<template>
  <div class="flex flex-col items-center justify-center py-14 px-6 text-center">
    <!-- Icon ring -->
    <div class="w-14 h-14 rounded-full bg-danger-50 flex items-center justify-center text-danger-400 mb-4">
      <WifiOff v-if="offline" :size="24" />
      <AlertCircle v-else :size="24" />
    </div>

    <!-- Heading -->
    <h3 class="text-sm font-semibold text-gray-900 mb-1">{{ title }}</h3>

    <!-- Message -->
    <p class="text-xs text-gray-400 max-w-xs mb-5 leading-relaxed">{{ message }}</p>

    <!-- Retry button -->
    <button
      v-if="onRetry"
      class="btn-primary btn-sm"
      :disabled="retrying"
      @click="handleRetry"
    >
      <Loader2 v-if="retrying" :size="13" class="animate-spin" />
      <RefreshCw v-else :size="13" />
      {{ retrying ? 'Retrying…' : 'Try again' }}
    </button>

    <!-- Support link -->
    <a
      href="mailto:support@klikk.co.za"
      class="mt-3 text-xs text-gray-400 hover:text-navy transition-colors underline underline-offset-2"
    >
      Contact support
    </a>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { AlertCircle, Loader2, RefreshCw, WifiOff } from 'lucide-vue-next'

const props = withDefaults(defineProps<{
  /** Short heading shown above the message */
  title?: string
  /** Longer explanation shown below the heading */
  message?: string
  /** Pass a callback to enable the Retry button */
  onRetry?: (() => void | Promise<void>) | null
  /** Show offline/network-specific icon and copy */
  offline?: boolean
}>(), {
  title: 'Something went wrong',
  message: 'We couldn\'t load this data. Check your connection and try again.',
  onRetry: null,
  offline: false,
})

const retrying = ref(false)

async function handleRetry() {
  if (!props.onRetry) return
  retrying.value = true
  try {
    await props.onRetry()
  } finally {
    retrying.value = false
  }
}
</script>
