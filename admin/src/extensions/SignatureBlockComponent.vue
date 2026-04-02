<template>
  <node-view-wrapper as="span" class="inline-block align-middle">
    <!-- Date / Initials: compact chip like merge fields (same size as text) -->
    <span
      v-if="node.attrs.fieldType === 'date' || node.attrs.fieldType === 'initials'"
      class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[11px]
             font-medium cursor-grab active:cursor-grabbing select-none align-baseline leading-tight"
      :class="[chipClasses, selected ? 'ring-2 ring-navy/40' : '']"
      contenteditable="false"
      :title="node.attrs.fieldName"
      data-drag-handle
      draggable="true"
    >
      <component :is="iconComponent" :size="11" class="flex-shrink-0" />
      {{ chipLabel }}
      <button
        v-if="editor.isEditable"
        @click="deleteNode"
        class="ml-0.5 p-0 hover:text-red-500 transition-colors"
        @mousedown.stop
      >
        <X :size="10" />
      </button>
    </span>

    <!-- Signature: larger card with controls -->
    <span
      v-else
      class="inline-flex items-center gap-1.5 px-2 py-1.5 rounded-lg border-2 border-dashed select-none group whitespace-nowrap align-middle"
      :class="[blockClasses, selected ? 'ring-2 ring-navy/40' : '']"
      contenteditable="false"
    >
      <!-- Drag handle -->
      <span
        class="flex-shrink-0 p-0.5 rounded cursor-grab active:cursor-grabbing text-gray-300 hover:text-gray-500 hover:bg-gray-100/80 transition-colors"
        data-drag-handle
        draggable="true"
        title="Drag to reposition"
      >
        <GripVertical :size="12" />
      </span>

      <!-- Icon -->
      <span class="w-6 h-6 rounded-full inline-flex items-center justify-center flex-shrink-0" :class="iconBgClass">
        <component :is="iconComponent" :size="12" :class="iconClass" />
      </span>

      <!-- Info (compact) -->
      <span class="min-w-0">
        <span class="text-xs font-semibold truncate block" :class="iconClass">
          {{ displayLabel }}
        </span>
        <span class="text-[9px] text-gray-400 uppercase tracking-wider leading-tight block">
          {{ node.attrs.fieldType }} · {{ roleName }}
        </span>
      </span>

      <!-- Role selector (only in edit mode) -->
      <select
        v-if="editor.isEditable"
        :value="node.attrs.signerRole"
        @change="updateAttributes({ signerRole: ($event.target as HTMLSelectElement).value })"
        class="text-[10px] border border-gray-200 rounded px-1 py-0.5 bg-white/80 focus:ring-1 focus:ring-navy/30 flex-shrink-0"
        @mousedown.stop
        @dragstart.stop
      >
        <option value="landlord">Landlord</option>
        <option value="tenant_1">Tenant 1</option>
        <option value="tenant_2">Tenant 2</option>
        <option value="tenant_3">Tenant 3</option>
        <option value="witness">Witness</option>
        <option value="agent">Agent</option>
      </select>

      <!-- Delete button -->
      <button
        v-if="editor.isEditable"
        @click="deleteNode"
        class="p-0.5 rounded hover:bg-red-100 text-gray-300 hover:text-red-500 transition-colors flex-shrink-0"
        title="Remove"
        @mousedown.stop
      >
        <X :size="12" />
      </button>
    </span>
  </node-view-wrapper>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { nodeViewProps, NodeViewWrapper } from '@tiptap/vue-3'
import {
  PenTool, Type, Calendar, X, GripVertical,
} from 'lucide-vue-next'

const props = defineProps(nodeViewProps)

const displayLabel = computed(() =>
  props.node.attrs.label || `${props.node.attrs.fieldType} — ${props.node.attrs.signerRole}`
)

// Short label for compact chips (initials, date)
const chipLabel = computed(() => {
  const role = (props.node.attrs.signerRole || 'signer').replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())
  if (props.node.attrs.fieldType === 'initials') return `initials ${role}`
  if (props.node.attrs.fieldType === 'date') return `date ${role}`
  return displayLabel.value
})

const roleName = computed(() =>
  (props.node.attrs.signerRole || 'signer').replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())
)

// ── Date/Initials chip classes (same style as merge field chips) ────
const chipClasses = computed(() => {
  const role = props.node.attrs.signerRole
  return {
    landlord:  'bg-blue-100 text-blue-700 border border-blue-200',
    tenant_1:  'bg-green-100 text-green-700 border border-green-200',
    tenant_2:  'bg-purple-100 text-purple-700 border border-purple-200',
    tenant_3:  'bg-orange-100 text-orange-700 border border-orange-200',
    witness:   'bg-amber-100 text-amber-700 border border-amber-200',
    agent:     'bg-cyan-100 text-cyan-700 border border-cyan-200',
  }[role] ?? 'bg-gray-100 text-gray-600 border border-gray-200'
})

// ── Signature card classes ────────────────────────────────────────
const blockClasses = computed(() => ({
  landlord:  'border-blue-300 bg-blue-50/60',
  tenant_1:  'border-green-300 bg-green-50/60',
  tenant_2:  'border-purple-300 bg-purple-50/60',
  tenant_3:  'border-orange-300 bg-orange-50/60',
  witness:   'border-amber-300 bg-amber-50/60',
  agent:     'border-cyan-300 bg-cyan-50/60',
}[props.node.attrs.signerRole] ?? 'border-gray-300 bg-gray-50/60'))

const iconBgClass = computed(() => ({
  landlord:  'bg-blue-100',
  tenant_1:  'bg-green-100',
  tenant_2:  'bg-purple-100',
  tenant_3:  'bg-orange-100',
  witness:   'bg-amber-100',
  agent:     'bg-cyan-100',
}[props.node.attrs.signerRole] ?? 'bg-gray-100'))

const iconClass = computed(() => ({
  landlord:  'text-blue-600',
  tenant_1:  'text-green-600',
  tenant_2:  'text-purple-600',
  tenant_3:  'text-orange-600',
  witness:   'text-amber-600',
  agent:     'text-cyan-600',
}[props.node.attrs.signerRole] ?? 'text-gray-600'))

const iconComponent = computed(() => ({
  signature: PenTool,
  initials: Type,
  date: Calendar,
}[props.node.attrs.fieldType] ?? PenTool))
</script>
