<template>
  <Teleport to="body">
    <div class="fixed bottom-5 right-5 z-[999] flex flex-col gap-2 pointer-events-none">
      <TransitionGroup
        enter-active-class="transition ease-out duration-300"
        enter-from-class="opacity-0 translate-y-2 scale-95"
        enter-to-class="opacity-100 translate-y-0 scale-100"
        leave-active-class="transition ease-in duration-200"
        leave-from-class="opacity-100 translate-y-0 scale-100"
        leave-to-class="opacity-0 translate-y-2 scale-95"
      >
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="pointer-events-auto flex items-center gap-2.5 px-4 py-2.5 rounded-xl shadow-lg text-sm font-medium min-w-[260px] max-w-sm"
          :class="variantClass[toast.type]"
        >
          <component :is="variantIcon[toast.type]" :size="16" class="flex-shrink-0" />
          <span class="flex-1">{{ toast.message }}</span>
          <button @click="dismiss(toast.id)" class="p-0.5 opacity-60 hover:opacity-100 transition-opacity">
            <X :size="14" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useToast } from '../composables/useToast'
import { Check, AlertTriangle, Info, XCircle, X } from 'lucide-vue-next'

const { toasts, dismiss } = useToast()

const variantClass: Record<string, string> = {
  success: 'bg-success-600 text-white',
  error:   'bg-danger-600 text-white',
  warning: 'bg-warning-500 text-white',
  info:    'bg-info-600 text-white',
}

const variantIcon: Record<string, any> = {
  success: Check,
  error:   XCircle,
  warning: AlertTriangle,
  info:    Info,
}
</script>
