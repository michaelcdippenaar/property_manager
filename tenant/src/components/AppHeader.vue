<template>
  <div class="page-header">
    <!-- Back row (shown when depth > 1) -->
    <div v-if="showBack" class="flex items-center px-3 pt-2 pb-0">
      <button
        class="flex items-center gap-0.5 text-white/80 py-2 px-2 -ml-2 touchable rounded-xl active:bg-white/10"
        @click="handleBack"
      >
        <ChevronLeft :size="22" />
        <span class="text-[15px]">{{ backLabel }}</span>
      </button>

      <!-- Collapsed title in back-row mode -->
      <span v-if="isScrolled" class="flex-1 text-center text-[15px] font-semibold text-white pr-10 truncate">
        {{ title }}
      </span>
    </div>

    <!-- Large title -->
    <div
      class="px-5 transition-all duration-200"
      :class="isScrolled && showBack ? 'py-1 opacity-0 pointer-events-none h-0 overflow-hidden' : 'pt-3 pb-4'"
    >
      <h1 class="text-2xl font-bold text-white leading-tight">{{ title }}</h1>
      <p v-if="subtitle" class="text-white/60 text-sm mt-0.5">{{ subtitle }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

const props = withDefaults(defineProps<{
  title: string
  subtitle?: string
  showBack?: boolean
  backLabel?: string
  isScrolled?: boolean
}>(), {
  showBack: false,
  backLabel: 'Back',
  isScrolled: false,
})

const emit = defineEmits<{ back: [] }>()
const router = useRouter()

function handleBack() {
  emit('back')
  if (!router.currentRoute.value.redirectedFrom) {
    router.back()
  }
}
</script>
