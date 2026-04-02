<template>
  <node-view-wrapper
    as="span"
    class="inline"
  >
    <span
      class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[11px]
             font-medium cursor-grab active:cursor-grabbing select-none align-baseline leading-tight"
      :class="[chipClasses, selected ? 'ring-2 ring-navy/40' : '']"
      contenteditable="false"
      :title="node.attrs.fieldName"
      data-drag-handle
      draggable="true"
    >
      <component :is="iconComponent" :size="11" class="flex-shrink-0" />
      {{ displayLabel }}
    </span>
  </node-view-wrapper>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { nodeViewProps, NodeViewWrapper } from '@tiptap/vue-3'
import { User, Home, FileText, Calendar, Briefcase } from 'lucide-vue-next'

const props = defineProps(nodeViewProps)

const displayLabel = computed(() =>
  props.node.attrs.label || props.node.attrs.fieldName?.replace(/_/g, ' ') || '?'
)

const chipClasses = computed(() => {
  const cat = props.node.attrs.category
  return {
    landlord: 'bg-blue-100 text-blue-700 border border-blue-200',
    tenant:   'bg-green-100 text-green-700 border border-green-200',
    property: 'bg-amber-100 text-amber-700 border border-amber-200',
    lease:    'bg-purple-100 text-purple-700 border border-purple-200',
    agent:    'bg-cyan-100 text-cyan-700 border border-cyan-200',
  }[cat] ?? 'bg-gray-100 text-gray-600 border border-gray-200'
})

const iconComponent = computed(() => {
  return {
    landlord: User,
    tenant: User,
    property: Home,
    lease: FileText,
    agent: Briefcase,
  }[props.node.attrs.category] ?? Calendar
})
</script>
