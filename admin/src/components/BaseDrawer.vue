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
      <div v-if="open" class="fixed inset-0 z-50 flex" :class="side === 'right' ? 'justify-end' : 'justify-start'">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="$emit('close')" />

        <!-- Panel -->
        <Transition
          :enter-active-class="`transition ease-out duration-200`"
          :enter-from-class="side === 'right' ? 'translate-x-full' : '-translate-x-full'"
          enter-to-class="translate-x-0"
          :leave-active-class="`transition ease-in duration-150`"
          leave-from-class="translate-x-0"
          :leave-to-class="side === 'right' ? 'translate-x-full' : '-translate-x-full'"
        >
          <div
            v-if="open"
            class="relative bg-white shadow-2xl w-full flex flex-col overflow-hidden"
            :class="sizeClass"
          >
            <!-- Header -->
            <div v-if="title || $slots.header" class="flex items-center justify-between px-5 py-4 border-b border-gray-100 flex-shrink-0">
              <slot name="header">
                <h2 class="text-sm font-semibold text-gray-900">{{ title }}</h2>
              </slot>
              <button
                @click="$emit('close')"
                class="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <X :size="18" />
              </button>
            </div>

            <!-- Body -->
            <div class="flex-1 overflow-y-auto">
              <slot />
            </div>

            <!-- Footer -->
            <div v-if="$slots.footer" class="px-5 py-4 border-t border-gray-100 flex justify-end gap-2 flex-shrink-0">
              <slot name="footer" />
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { X } from 'lucide-vue-next'

const props = withDefaults(defineProps<{
  open: boolean
  title?: string
  side?: 'left' | 'right'
  size?: 'sm' | 'md' | 'lg' | 'xl'
}>(), {
  side: 'right',
  size: 'md',
})

defineEmits<{ close: [] }>()

const sizeClass = computed(() => ({
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
}[props.size]))
</script>
