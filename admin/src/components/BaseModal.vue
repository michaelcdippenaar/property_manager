<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition ease-out duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition ease-in duration-150"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="$emit('close')" />

        <!-- Panel -->
        <Transition
          enter-active-class="transition ease-out duration-200"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition ease-in duration-150"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
          @after-enter="activate"
          @before-leave="deactivate"
        >
          <div
            v-if="open"
            ref="trapRef"
            role="dialog"
            aria-modal="true"
            :aria-labelledby="title ? modalTitleId : undefined"
            class="relative bg-white rounded-xl sm:rounded-2xl shadow-2xl w-full flex flex-col overflow-hidden max-h-[90vh]"
            :class="sizeClass"
          >
            <!-- Header -->
            <div v-if="title || $slots.header" class="flex items-center justify-between px-4 py-3 sm:px-6 sm:py-4 border-b border-gray-100">
              <slot name="header">
                <h2 :id="modalTitleId" class="text-sm font-semibold text-gray-900">{{ title }}</h2>
              </slot>
              <button
                v-if="closable"
                @click="$emit('close')"
                aria-label="Close dialog"
                class="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors focus-visible:outline-2 focus-visible:outline-navy focus-visible:outline-offset-1"
              >
                <X :size="18" />
              </button>
            </div>

            <!-- Body -->
            <div class="flex-1 overflow-y-auto px-4 py-4 sm:px-6 sm:py-5">
              <slot />
            </div>

            <!-- Footer -->
            <div v-if="$slots.footer" class="px-4 py-3 sm:px-6 sm:py-4 border-t border-gray-100 flex justify-end gap-2">
              <slot name="footer" />
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, useId } from 'vue'
import { X } from 'lucide-vue-next'
import { useFocusTrap } from '../composables/useFocusTrap'

const props = withDefaults(defineProps<{
  open: boolean
  title?: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
  closable?: boolean
}>(), {
  size: 'md',
  closable: true,
})

const emit = defineEmits<{ close: [] }>()

const modalTitleId = useId()

const { trapRef, activate, deactivate } = useFocusTrap(() => emit('close'))

const sizeClass = computed(() => ({
  sm: 'sm:max-w-sm',
  md: 'sm:max-w-md',
  lg: 'sm:max-w-lg',
  xl: 'sm:max-w-xl',
}[props.size]))
</script>
