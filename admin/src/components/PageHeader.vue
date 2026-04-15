<template>
  <div class="mb-6">
    <Breadcrumb v-if="crumbs && crumbs.length" :items="crumbs" class="mb-2" />
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2.5">
          <button
            v-if="back"
            class="p-1.5 -ml-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors flex-shrink-0"
            aria-label="Back"
            @click="onBack"
          >
            <ArrowLeft :size="18" />
          </button>
          <h1 class="text-xl font-bold text-gray-900 tracking-tight truncate">
            <slot name="title">{{ title }}</slot>
          </h1>
          <slot name="title-adornment" />
        </div>
        <p v-if="$slots.subtitle || subtitle" class="text-sm text-gray-500 mt-0.5">
          <slot name="subtitle">{{ subtitle }}</slot>
        </p>
        <slot name="under-title" />
      </div>
      <div v-if="$slots.actions" class="flex-shrink-0">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import Breadcrumb, { type BreadcrumbItem } from './Breadcrumb.vue'

const props = defineProps<{
  title?: string
  subtitle?: string
  crumbs?: BreadcrumbItem[]
  back?: boolean
}>()

const router = useRouter()
function onBack() {
  router.back()
}
</script>
